import json,sys
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=4;NT=4096;TRAIN=1024;P=32;C0=2304
STEPS=(256,224,192);LENS=(2,3,4);MAX_TRIES=1<<15;NB=8;MODEL_BYTES=177;TB=1024
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
NCTX=9*9*NB*4

def clip4(x):return int(max(-4,min(4,int(x))))+4
def ctx(prev,left,pos,pref):return (((clip4(prev)*9+clip4(left))*NB+pos)*4+pref)
def zig1(k):return (int(k)<<1)^(int(k)>>63)
def unzig1(u):return (int(u)>>1)^-(int(u)&1)

def update_symbol(counts,k,prev,left):
 u=zig1(k)&((1<<NB)-1);pref=0
 for bp in range(NB-1,-1,-1):
  bit=(u>>bp)&1;pos=NB-1-bp;cx=ctx(prev,left,pos,pref);counts[cx,bit]+=1
  if int(counts[cx,0]+counts[cx,1])>16384:counts[cx]=(counts[cx]+1)//2
  pref=((pref<<1)|bit)&3

def seed_prefix(counts,K):
 for t in range(K.shape[1]):
  for c in range(K.shape[0]):
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;update_symbol(counts,int(K[c,t]),prev,left)

def update_block(counts,K,c,t0,t1):
 for t in range(t0,t1):
  prev=int(K[c,t-1]);left=int(K[c-1,t]) if c else 0;update_symbol(counts,int(K[c,t]),prev,left)

@njit(cache=True)
def next_u64(x):
 x ^= x >> np.uint64(12);x ^= x << np.uint64(25);x ^= x >> np.uint64(27)
 return x,x*np.uint64(2685821657736338717)

@njit(cache=True)
def nclip(x):
 if x<-4:return 0
 if x>4:return 8
 return x+4

@njit(cache=True)
def nctx(prev,left,pos,pref):return (((nclip(prev)*9+nclip(left))*NB+pos)*4+pref)

@njit(cache=True)
def arpred(a,b,hist):
 z=a
 for j in range(P):z+=float(b[j])*float(hist[P-1-j])
 return int(np.rint(z))

@njit(cache=True)
def sample_symbol(state,counts,prev,left):
 u=0;pref=0
 for bp in range(NB-1,-1,-1):
  pos=NB-1-bp;cx=nctx(prev,left,pos,pref);c0=int(counts[cx,0]);c1=int(counts[cx,1]);tot=c0+c1
  state,r=next_u64(state);q=int(r%np.uint64(tot));bit=0 if q<c0 else 1;u=(u<<1)|bit;pref=((pref<<1)|bit)&3
 k=(u>>1)^-(u&1)
 return state,k

@njit(cache=True)
def candidate(idx,seed,step,L,a,b,hist0,prevk,leftk,counts):
 state=seed^(np.uint64(idx+1)*np.uint64(0x9E3779B97F4A7C15));hist=hist0.copy();K=np.empty(L,np.int16);R=np.empty(L,np.int32);pk=prevk
 for j in range(L):
  state,k=sample_symbol(state,counts,pk,int(leftk[j]));p=arpred(a,b,hist);r=p+step*k
  K[j]=k;R[j]=r;hist[:-1]=hist[1:];hist[-1]=r;pk=k
 return K,R

@njit(cache=True)
def search(x,eps,seed,step,L,a,b,hist0,prevk,leftk,counts,maxtries):
 for idx in range(maxtries):
  K,R=candidate(idx,seed,step,L,a,b,hist0,prevk,leftk,counts);ok=True
  for j in range(L):
   if abs(float(x[j])-float(R[j]))>eps:ok=False;break
  if ok:return idx,K,R
 return maxtries,np.empty(0,np.int16),np.empty(0,np.int32)

@njit(cache=True)
def fallback(x,step,L,a,b,hist0):
 hist=hist0.copy();K=np.empty(L,np.int16);R=np.empty(L,np.int32)
 for j in range(L):
  p=arpred(a,b,hist);k=int(np.rint((float(x[j])-p)/step));r=p+step*k;K[j]=k;R[j]=r;hist[:-1]=hist[1:];hist[-1]=r
 return K,R

@njit(cache=True)
def replay(K,step,L,a,b,hist0):
 hist=hist0.copy();R=np.empty(L,np.int32)
 for j in range(L):
  p=arpred(a,b,hist);r=p+step*int(K[j]);R[j]=r;hist[:-1]=hist[1:];hist[-1]=r
 return R

def seedbase(step,L,c,bno):
 x=(0xA0761D6478BD642F^((step+1)*0xE7037ED1A0B428DB)^((L+1)*0x8EBC6AF09C88C6E3)^((c+1)*0x589965CC75374CC3)^((bno+1)*0x1D8E4E27C47D124F))
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
def kval(score):return max(0,min(15,(int(score)+128)//256))
def upd(score,v):return (15*int(score)+max(0,(int(v)+1).bit_length()-1)*256)//16

def dense_prefix(X,co,step):
 a=float(co[0]);b=np.asarray(co[1:],np.float32);R=np.zeros((C,TRAIN),np.int32);K=np.zeros((C,TRAIN),np.int32)
 for c in range(C):
  for t in range(TRAIN):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/step));K[c,t]=k;R[c,t]=p+step*k
 return R,K

def run_combo(X,co,step,L,eps):
 Rp,Kp=dense_prefix(X,co,step);pn,prep,Kpd=m.encode_k(Kp)
 if not np.array_equal(Kpd,Kp):raise RuntimeError((step,L,'prefix K decode'))
 # Rebuild prefix source through the exact Numba recurrence used by held-out blocks.
 a=float(co[0]);b=np.asarray(co[1:],np.float32);Rpd=np.zeros_like(Rp)
 for c in range(C):
  for t in range(TRAIN):
   if t<P:p=0
   else:p=arpred(a,b,Rpd[c,t-P:t].astype(np.int32))
   Rpd[c,t]=p+step*int(Kpd[c,t])
 if not np.array_equal(Rpd,Rp):
  # Prefix fitter used NumPy dot; if a platform rounding tie differs, the transmitted K remains authoritative.
  # Recompute legality from decoder-real prefix and reject only if hard error is violated.
  pe=float(np.max(np.abs(X[:,:TRAIN]-Rpd.astype(np.float64))))
  if pe>eps*(1+1e-12):raise RuntimeError((step,L,'prefix recurrence hard',pe,eps))
 counts=np.ones((NCTX,2),np.int32);seed_prefix(counts,Kpd)
 KE=np.zeros((C,NT),np.int32);RE=np.zeros((C,NT),np.int32);KE[:,:TRAIN]=Kpd;RE[:,:TRAIN]=Rpd
 bw=BW();score=10*256;fallback_k=[];indices=[];hits=[];esc=0;bno=0
 for t0 in range(TRAIN,NT,L):
  t1=t0+L
  for c in range(C):
   hist=RE[c,t0-P:t0].astype(np.int32);left=KE[c-1,t0:t1].astype(np.int16) if c else np.zeros(L,np.int16);pk=int(KE[c,t0-1])
   idx,K,R=search(X[c,t0:t1],eps,seedbase(step,L,c,bno),step,L,a,b,hist,pk,left,counts,MAX_TRIES);rk=kval(score);bw.rice(int(idx),rk);score=upd(score,idx);indices.append(int(idx))
   if idx==MAX_TRIES:
    K,R=fallback(X[c,t0:t1],step,L,a,b,hist);fallback_k.extend(int(v) for v in K);esc+=1
   else:hits.append(int(idx))
   KE[c,t0:t1]=K.astype(np.int32);RE[c,t0:t1]=R;update_block(counts,KE,c,t0,t1);bno+=1
 rice,nbit=bw.finish();fb=np.asarray(fallback_k,np.int16);fbs=Z.compress(fb.astype('<i2').tobytes());total=MODEL_BYTES+int(pn)+len(rice)+len(fbs)+66
 # Decoder-real replay from byte components.
 fbd=np.frombuffer(ZD.decompress(fbs),'<i2').astype(np.int16);fp=0;KD=np.zeros_like(KE);RD=np.zeros_like(RE);KD[:,:TRAIN]=Kpd;RD[:,:TRAIN]=Rpd
 counts2=np.ones((NCTX,2),np.int32);seed_prefix(counts2,Kpd);br=BR(rice,nbit);score=10*256;di=[];bno=0
 for t0 in range(TRAIN,NT,L):
  t1=t0+L
  for c in range(C):
   hist=RD[c,t0-P:t0].astype(np.int32);left=KD[c-1,t0:t1].astype(np.int16) if c else np.zeros(L,np.int16);pk=int(KD[c,t0-1]);rk=kval(score);idx=br.rice(rk);score=upd(score,idx);di.append(int(idx))
   if idx==MAX_TRIES:
    if fp+L>len(fbd):raise RuntimeError((step,L,'escape eof'))
    K=fbd[fp:fp+L];fp+=L;R=replay(K,step,L,a,b,hist)
   else:K,R=candidate(int(idx),seedbase(step,L,c,bno),step,L,a,b,hist,pk,left,counts2)
   KD[c,t0:t1]=K.astype(np.int32);RD[c,t0:t1]=R;update_block(counts2,KD,c,t0,t1);bno+=1
 if fp!=len(fbd) or br.i!=nbit or di!=indices or not np.array_equal(KD,KE) or not np.array_equal(RD,RE) or not np.array_equal(counts2,counts):
  raise RuntimeError((step,L,'container decode',fp,len(fbd),br.i,nbit,int(np.count_nonzero(KD!=KE)),int(np.count_nonzero(RD!=RE))))
 me=float(np.max(np.abs(X-RD.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError((step,L,'source hard',me,eps))
 blocks=C*((NT-TRAIN)//L);held=C*(NT-TRAIN)
 return {'step':step,'L':L,'bytes':total,'bps':8*total/X.size,'prefix_bytes':MODEL_BYTES+int(pn),'prefix_rep':prep,'rice_bytes':len(rice),'rice_bits':int(nbit),'fallback_bytes':len(fbs),'escape_blocks':esc,'blocks':blocks,'success_fraction':1-esc/blocks,'heldout_payload_bps':8*(len(rice)+len(fbs))/held,'mean_hit_index':float(np.mean(hits)) if hits else None,'median_hit_index':float(np.median(hits)) if hits else None,'max_hit_index':int(max(hits)) if hits else None,'maxerr':me}

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;X=np.asarray(d[:NT,C0:C0+C],np.float64).T
  _,co=h.fits(X);R267,K267=h.run_ar(X,co);base,nbit,nb,Kd=h.arithmetic(K267);R267d=h.decode_source(Kd,co);be=float(np.max(np.abs(X-R267d.astype(np.float64))))
  if be>eps*(1+1e-12):raise RuntimeError(('267 hard',be,eps))
  sz=0
  for t0 in range(0,NT,TB):n,_=m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
  rows=[]
  for L in LENS:
   if (NT-TRAIN)%L:raise RuntimeError(('bad L',L))
   for step in STEPS:
    r=run_combo(X,co,step,L,eps);r.update({'gain_vs_step267_arithmetic':base/r['bytes'],'gain_vs_sz3':sz/r['bytes'],'ratio_to_2x_sz3_target':r['bytes']/(sz/2)});rows.append(r);print(json.dumps(r,indent=2),flush=True)
  rows.sort(key=lambda r:r['bytes']);out={'region':'easy','c0':C0,'shape':[C,NT],'global_std':gstd,'eps':eps,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_arithmetic_bytes':base,'step267_arithmetic_bps':8*base/X.size,'step267_arithmetic_bits':int(nbit),'step267_symbol_bits':int(nb),'step267_maxerr':be,'best':rows[0],'rows':rows,
   'scope':'Constructive easy-region legal-set codebook sweep using the incumbent adaptive arithmetic law rather than a crude residual histogram. One transmitted prefix-only float32 Huber AR32+intercept is shared. For dense reconstruction steps 256/224/192 and held-out block lengths 2/3/4, the exact decoded first 1024 samples seed the same 9x9xbit-positionx2-bit-prefix binary context counts used by the incumbent arithmetic backend. For each later block, encoder and decoder freeze the current shared counts and generate the same deterministic stochastic K codebook by sampling every K bit from those adaptive context probabilities, with contexts driven by candidate previous-K and already-decoded current-left K. Every candidate is recursively reconstructed through the exact AR32 decoder state. Encoder sends only the adaptive-Rice index of the first whole block inside the unchanged +/-epsilon tube. Search failure at 2^15 is a real escape carrying exact fallback K in a Zstd stream. After either a hit or escape, both sides update the shared arithmetic counts from the accepted K before the next block. Model, prefix, index, escape and framing bytes are charged; complete K/source/count-state replay and max error are verified. Matched SZ3 and the exact step267 incumbent arithmetic codec are rerun on identical easy samples. This directly tests whether #411 failed because its codebook probability model and block length were too weak. No AI. Draft/do not merge.'}
  print(json.dumps({'summary':{'sz3_bps':out['sz3_bps'],'step267_bps':out['step267_arithmetic_bps'],'best':out['best']}},indent=2),flush=True);json.dump(out,open('imperial_easy_adaptive_ar_setcode.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
