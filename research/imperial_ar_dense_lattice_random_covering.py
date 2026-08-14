import json,sys
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=2;NT=4096;TRAIN=1024;P=32;L=6;MAX_TRIES=1<<16;STEPS=(256,224,192);TB=1024;MODEL_BYTES=177
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

# ---- robust source predictor, transmitted as float32 ----
def fit_huber(X):
 n=C*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);j=0
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 for _ in range(6):
  r=y-A@co;w=np.minimum(1.,267./np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 raw=np.asarray(co,np.float32).astype('<f4').tobytes();dec=np.frombuffer(raw,'<f4').astype(np.float32)
 return dec

def greedy(X,co,step,end=NT):
 R=np.zeros((C,end),np.int32);K=np.zeros((C,end),np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(end):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/step));K[c,t]=k;R[c,t]=p+step*k
 return R,K

def decode(K,co,step):
 R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(K.shape[0]):
  for t in range(K.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   R[c,t]=p+step*int(K[c,t])
 return R

# Prefix exact K defines a decoder-known contextual probability table. Observations get weight 32 and every K gets unit smoothing.
def build_cdf(K):
 kmin=int(K.min())-8;kmax=int(K.max())+8;A=kmax-kmin+1;cnt=np.ones((81,A),np.int64)
 for c in range(C):
  for t in range(TRAIN):
   pv=int(K[c,t-1]) if t else 0;lf=int(K[c-1,t]) if c else 0;ctx=(max(-4,min(4,pv))+4)*9+(max(-4,min(4,lf))+4);kk=int(K[c,t])-kmin
   if 0<=kk<A:cnt[ctx,kk]+=32
 cdf=np.cumsum(cnt,axis=1,dtype=np.int64);tot=cdf[:,-1].copy();return kmin,cdf,tot

@njit(cache=True)
def next_u64(x):
 x ^= x >> np.uint64(12);x ^= x << np.uint64(25);x ^= x >> np.uint64(27);return x,x*np.uint64(2685821657736338717)
@njit(cache=True)
def sample_k(state,ctx,kmin,cdf,tot):
 state,u=next_u64(state);r=int(u%np.uint64(tot[ctx]));lo=0;hi=cdf.shape[1]
 while lo<hi:
  md=(lo+hi)//2
  if r<int(cdf[ctx,md]):hi=md
  else:lo=md+1
 return state,kmin+lo
@njit(cache=True)
def arpred(a,b,hist):
 z=a
 for j in range(P):z+=float(b[j])*float(hist[P-1-j])
 return int(np.rint(z))
@njit(cache=True)
def candidate(idx,seed,step,a,b,hist0,prevk,leftk,kmin,cdf,tot):
 state=seed^(np.uint64(idx+1)*np.uint64(0x9E3779B97F4A7C15));hist=hist0.copy();K=np.empty(L,np.int16);R=np.empty(L,np.int32);pk=prevk
 for j in range(L):
  p=arpred(a,b,hist);lf=int(leftk[j]);ctx=(max(-4,min(4,pk))+4)*9+(max(-4,min(4,lf))+4);state,k=sample_k(state,ctx,kmin,cdf,tot);r=p+step*k
  K[j]=k;R[j]=r;hist[:-1]=hist[1:];hist[-1]=r;pk=k
 return K,R
@njit(cache=True)
def search(x,eps,seed,step,a,b,hist0,prevk,leftk,kmin,cdf,tot,maxtries):
 for idx in range(maxtries):
  K,R=candidate(idx,seed,step,a,b,hist0,prevk,leftk,kmin,cdf,tot);ok=True
  for j in range(L):
   if abs(float(x[j])-float(R[j]))>eps:ok=False;break
  if ok:return idx,K,R
 return maxtries,np.empty(0,np.int16),np.empty(0,np.int32)
@njit(cache=True)
def fallback(x,step,a,b,hist0):
 hist=hist0.copy();K=np.empty(L,np.int16);R=np.empty(L,np.int32)
 for j in range(L):
  p=arpred(a,b,hist);k=int(np.rint((float(x[j])-p)/step));r=p+step*k;K[j]=k;R[j]=r;hist[:-1]=hist[1:];hist[-1]=r
 return K,R

def seedbase(rid,step,c,bno):
 x=(0xA0761D6478BD642F ^ ((rid+1)*0xE7037ED1A0B428DB) ^ ((step+1)*0x8EBC6AF09C88C6E3) ^ ((c+1)*0x589965CC75374CC3) ^ ((bno+1)*0x1D8E4E27C47D124F))
 return np.uint64(x&((1<<64)-1))

class BW:
 def __init__(self):self.a=[]
 def bit(self,b):self.a.append(1 if b else 0)
 def bits(self,v,n):
  for j in range(n-1,-1,-1):self.bit((v>>j)&1)
 def rice(self,v,k):
  q=int(v)>>k
  for _ in range(q):self.bit(0)
  self.bit(1)
  if k:self.bits(int(v)&((1<<k)-1),k)
 def finish(self):
  z=bytearray((len(self.a)+7)//8)
  for i,b in enumerate(self.a):
   if b:z[i>>3]|=1<<(7-(i&7))
  return bytes(z),len(self.a)
class BR:
 def __init__(self,d,n):self.d=d;self.n=n;self.i=0
 def bit(self):
  if self.i>=self.n:raise RuntimeError('rice eof')
  b=(self.d[self.i>>3]>>(7-(self.i&7)))&1;self.i+=1;return b
 def bits(self,n):
  v=0
  for _ in range(n):v=(v<<1)|self.bit()
  return v
 def rice(self,k):
  q=0
  while self.bit()==0:q+=1
  return (q<<k)|(self.bits(k) if k else 0)
def kval(score):return max(0,min(20,(int(score)+128)//256))
def upd(score,v):return (15*int(score)+max(0,(int(v)+1).bit_length()-1)*256)//16

def run_setcode(X,co,step,eps,rid):
 Rp,Kp=greedy(X,co,step,TRAIN);pn,prep,Kpd=m.encode_k(Kp)
 if not np.array_equal(Kpd,Kp):raise RuntimeError(('prefix K decode',step))
 Rpd=decode(Kpd,co,step)
 if not np.array_equal(Rpd,Rp):raise RuntimeError(('prefix source decode',step))
 kmin,cdf,tot=build_cdf(Kpd);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 KE=np.zeros((C,NT),np.int32);RE=np.zeros((C,NT),np.int32);KE[:,:TRAIN]=Kpd;RE[:,:TRAIN]=Rpd
 bw=BW();score=12*256;fallback_k=[];indices=[];esc=0;hits=[]
 for c in range(C):
  for bno,t0 in enumerate(range(TRAIN,NT,L)):
   t1=t0+L;hist=RE[c,t0-P:t0].astype(np.int32);left=KE[c-1,t0:t1].astype(np.int16) if c else np.zeros(L,np.int16);pk=int(KE[c,t0-1])
   idx,K,R=search(X[c,t0:t1],eps,seedbase(rid,step,c,bno),step,a,b,hist,pk,left,kmin,cdf,tot,MAX_TRIES);k=kval(score);bw.rice(int(idx),k);score=upd(score,idx);indices.append(int(idx))
   if idx==MAX_TRIES:
    K,R=fallback(X[c,t0:t1],step,a,b,hist);fallback_k.extend(int(x) for x in K);esc+=1
   else:hits.append(int(idx))
   KE[c,t0:t1]=K.astype(np.int32);RE[c,t0:t1]=R
 rice,nbit=bw.finish();fb=np.asarray(fallback_k,np.int16);fbs=Z.compress(fb.astype('<i2').tobytes());total_bytes=MODEL_BYTES+int(pn)+len(rice)+len(fbs)+64
 # Decoder replays exact prefix, indices and fallback K.
 fbd=np.frombuffer(ZD.decompress(fbs),'<i2').astype(np.int16);fp=0;KD=np.zeros_like(KE);RD=np.zeros_like(RE);KD[:,:TRAIN]=Kpd;RD[:,:TRAIN]=Rpd;br=BR(rice,nbit);score=12*256;di=[]
 for c in range(C):
  for bno,t0 in enumerate(range(TRAIN,NT,L)):
   t1=t0+L;k=kval(score);idx=br.rice(k);score=upd(score,idx);di.append(int(idx));hist=RD[c,t0-P:t0].astype(np.int32);left=KD[c-1,t0:t1].astype(np.int16) if c else np.zeros(L,np.int16);pk=int(KD[c,t0-1])
   if idx==MAX_TRIES:
    if fp+L>len(fbd):raise RuntimeError(('fallback eof',step));K=fbd[fp:fp+L];fp+=L
    # reconstruct from transmitted K
    R=np.empty(L,np.int32);hh=hist.copy()
    for j in range(L):p=int(np.rint(a+float(np.dot(b,hh[::-1].astype(np.float32)))));R[j]=p+step*int(K[j]);hh[:-1]=hh[1:];hh[-1]=R[j]
   else:K,R=candidate(int(idx),seedbase(rid,step,c,bno),step,a,b,hist,pk,left,kmin,cdf,tot)
   KD[c,t0:t1]=K.astype(np.int32);RD[c,t0:t1]=R
 if fp!=len(fbd) or br.i!=nbit or di!=indices or not np.array_equal(KD,KE) or not np.array_equal(RD,RE):raise RuntimeError(('set container decode',step,fp,len(fbd),br.i,nbit))
 me=float(np.max(np.abs(X-RD.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('set hard',step,me,eps))
 return {'bytes':total_bytes,'bps':8*total_bytes/X.size,'prefix_bytes':int(pn)+MODEL_BYTES,'prefix_rep':prep,'rice_bytes':len(rice),'rice_bits':int(nbit),'fallback_bytes':len(fbs),'escape_blocks':esc,'blocks':C*((NT-TRAIN)//L),'success_fraction':1-esc/(C*((NT-TRAIN)//L)),'mean_hit_index':float(np.mean(hits)) if hits else None,'median_hit_index':float(np.median(hits)) if hits else None,'maxerr':me}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for rid,(region,c0) in enumerate(REGIONS):
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=fit_huber(X)
   sz=0
   for t0 in range(0,NT,TB):n,_=m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
   # ordinary exact-path step267 control on the same tiny region
   R267,K267=greedy(X,co,267);n267,rep267,D267=m.encode_k(K267);R267d=decode(D267,co,267);b267=MODEL_BYTES+int(n267)
   e267=float(np.max(np.abs(X-R267d.astype(np.float64))))
   if not np.array_equal(D267,K267) or e267>eps*(1+1e-12):raise RuntimeError((region,'267 control'))
   steps=[]
   for step in STEPS:
    Rg,Kg=greedy(X,co,step);ng,repg,Dg=m.encode_k(Kg);Rgd=decode(Dg,co,step);gb=MODEL_BYTES+int(ng);ge=float(np.max(np.abs(X-Rgd.astype(np.float64))))
    if not np.array_equal(Dg,Kg) or ge>eps*(1+1e-12):raise RuntimeError((region,step,'greedy control'))
    sc=run_setcode(X,co,step,eps,rid);sc.update({'step':step,'greedy_bytes':gb,'greedy_bps':8*gb/X.size,'gain_set_vs_same_step_greedy':gb/sc['bytes'],'gain_set_vs_step267':b267/sc['bytes'],'gain_set_vs_sz3':sz/sc['bytes'],'ratio_to_2x_sz3_target':sc['bytes']/(sz/2),'greedy_rep':repg});steps.append(sc)
   best=min(steps,key=lambda x:x['bytes']);row={'region':region,'c0':c0,'shape':[C,NT],'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_bytes':b267,'step267_bps':8*b267/X.size,'step267_rep':rep267,'step267_maxerr':e267,'best':best,'steps':steps}
   rows.append(row);print(json.dumps({'region':region,'sz3_bytes':sz,'step267_bytes':b267,'best':best},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'block_length':L,'max_tries':MAX_TRIES,'steps':list(STEPS),'rows':rows,'scope':'Constructive decoder-real dense-lattice AR32 random-covering gate. Two contiguous channels from hard/easy/medium/far are fit with one transmitted float32 Huber AR32+intercept from t<1024. For each step 256/224/192 the greedy prefix K is exactly encoded and decoded, then deterministically defines a smoothed contextual P(K|clipped previous K,current-left K). On every held-out six-sample block encoder and decoder share a public stochastic K codebook. Each candidate is recursively reconstructed through the exact AR32 decoder state; encoder chooses the first trajectory whose every source reconstruction satisfies the unchanged hard-error epsilon and transmits only its adaptive-Rice index. Decoder regenerates it without source intervals. Search failure at 2^16 is a real escape with exact fallback K appended to a Zstd stream. Model, prefix, Rice, fallback and framing bytes are charged; the entire trajectory is replayed and source hard error verified. Same-step exact-K, step267 exact-K and matched SZ3 controls are rerun. This specifically tests whether the extra legal-path branching created by a denser-than-267 reconstruction lattice can be exploited as probability-mass coding rather than paid as exact K symbols. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar_dense_lattice_random_covering.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
