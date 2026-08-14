import json,math,sys
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=4;NT=8192;TRAIN=1024;L=8;MAX_TRIES=1<<18;TB=1024
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
MODES=('time1','avg','lorenzo','accel','both')

@njit(cache=True)
def _next_u64(x):
 x ^= x >> np.uint64(12); x ^= x << np.uint64(25); x ^= x >> np.uint64(27)
 return x, x*np.uint64(2685821657736338717)

@njit(cache=True)
def _pick_res(state,vals,cum,total):
 state,u=_next_u64(state);r=int(u % np.uint64(total));lo=0;hi=len(cum)
 while lo<hi:
  md=(lo+hi)//2
  if r<int(cum[md]):hi=md
  else:lo=md+1
 return state,int(vals[lo])

@njit(cache=True)
def _pred(mode,prev,prev2,left,leftprev,hasleft):
 if not hasleft:
  if mode==3 or mode==4:return 2*prev-prev2
  return prev
 if mode==0:return prev
 if mode==1:return (prev+left)//2
 if mode==2:return prev+(left-leftprev)
 if mode==3:return 2*prev-prev2
 return prev+((prev-prev2)+(left-leftprev))//2

@njit(cache=True)
def _candidate(idx,seedbase,mode,prev,prev2,left,leftprev,hasleft,vals,cum,total):
 state=np.uint64(seedbase) ^ (np.uint64(idx+1)*np.uint64(0x9E3779B97F4A7C15))
 if state==0:state=np.uint64(0xD1B54A32D192ED03)
 out=np.empty(L,np.int16);p=prev;p2=prev2;lp=leftprev
 for j in range(L):
  lv=int(left[j]) if hasleft else 0;pr=_pred(mode,p,p2,lv,lp,hasleft);state,res=_pick_res(state,vals,cum,total);q=pr+res
  out[j]=q;p2=p;p=q;lp=lv
 return out

@njit(cache=True)
def _search(loq,hiq,seedbase,mode,prev,prev2,left,leftprev,hasleft,vals,cum,total,maxtries):
 for idx in range(maxtries):
  q=_candidate(idx,seedbase,mode,prev,prev2,left,leftprev,hasleft,vals,cum,total)
  good=True
  for j in range(L):
   if int(q[j])<int(loq[j]) or int(q[j])>int(hiq[j]):good=False;break
  if good:return idx,q
 return maxtries,np.empty(0,np.int16)

def predictor(mode,prev,prev2,left,leftprev,hasleft):
 if not hasleft:return 2*prev-prev2 if mode in (3,4) else prev
 if mode==0:return prev
 if mode==1:return (prev+left)//2
 if mode==2:return prev+(left-leftprev)
 if mode==3:return 2*prev-prev2
 return prev+((prev-prev2)+(left-leftprev))//2

def residuals_for_mode(Q,mode):
 rr=[]
 for c in range(Q.shape[0]):
  for t in range(2,TRAIN):
   prev=int(Q[c,t-1]);prev2=int(Q[c,t-2]);has=c>0;left=int(Q[c-1,t]) if has else 0;lp=int(Q[c-1,t-1]) if has else 0
   rr.append(int(Q[c,t])-predictor(mode,prev,prev2,left,lp,has))
 return np.asarray(rr,np.int32)

def entropy(a):
 _,n=np.unique(np.asarray(a),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def build_model(Q):
 rows=[]
 for mi,name in enumerate(MODES):
  r=residuals_for_mode(Q,mi);rows.append((entropy(r),mi,name,r))
 rows.sort(key=lambda x:(x[0],x[1]));H,mi,name,r=rows[0];vals,cnt=np.unique(r,return_counts=True);cum=np.cumsum(cnt,dtype=np.int64)
 return mi,name,vals.astype(np.int32),cum,int(cum[-1]),H,[{'mode':x[2],'entropy':x[0]} for x in rows]

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

def k_from_score(score):return max(0,min(20,(int(score)+128)//256))
def update_score(score,v):return (15*int(score)+int(max(0,(int(v)+1).bit_length()-1))*256)//16

def seedbase(region_id,c,block):
 x=(0xA0761D6478BD642F ^ ((region_id+1)*0xE7037ED1A0B428DB) ^ ((c+1)*0x8EBC6AF09C88C6E3) ^ ((block+1)*0x589965CC75374CC3))
 return x & ((1<<64)-1)

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;h=eps;rows=[]
  for rid,(region,c0) in enumerate(REGIONS):
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T
   Q=np.rint(X/h).astype(np.int16);R0=Q.astype(np.float64)*h
   if float(np.max(np.abs(X-R0)))>eps*(1+1e-12):raise RuntimeError((region,'nearest hard'))
   prefix_bytes,prep,Qpd=m.encode_k(Q[:,:TRAIN])
   if not np.array_equal(Qpd,Q[:,:TRAIN]):raise RuntimeError((region,'prefix decode'))
   mode,mname,vals,cum,total,H,modes=build_model(Qpd)
   lo=np.ceil((X-eps)/h-1e-12).astype(np.int16);hi=np.floor((X+eps)/h+1e-12).astype(np.int16)
   if np.any(lo>hi):raise RuntimeError((region,'empty legal'))
   QE=np.zeros_like(Q);QE[:,:TRAIN]=Qpd;bw=BW();fallback=[];indices=[];escapes=0;score=12*256;per_ch=[]
   for c in range(C):
    hits=[];esc=0
    for bno,t0 in enumerate(range(TRAIN,NT,L)):
     t1=t0+L;left=QE[c-1,t0:t1].astype(np.int16) if c>0 else np.zeros(L,np.int16);lp=int(QE[c-1,t0-1]) if c>0 else 0
     prev=int(QE[c,t0-1]);prev2=int(QE[c,t0-2]);idx,cand=_search(lo[c,t0:t1],hi[c,t0:t1],seedbase(rid,c,bno),mode,prev,prev2,left,lp,c>0,vals,cum,total,MAX_TRIES)
     k=k_from_score(score);bw.rice(int(idx),k);score=update_score(score,idx);indices.append(int(idx))
     if idx==MAX_TRIES:
      q=Q[c,t0:t1].copy();fallback.extend(int(x) for x in q);escapes+=1;esc+=1
     else:q=np.asarray(cand,np.int16);hits.append(int(idx))
     QE[c,t0:t1]=q
    per_ch.append({'local_channel':c,'escapes':esc,'blocks':(NT-TRAIN)//L,'success_fraction':1-esc/((NT-TRAIN)//L),'median_hit_index':float(np.median(hits)) if hits else None,'mean_hit_index':float(np.mean(hits)) if hits else None,'max_hit_index':int(max(hits)) if hits else None})
   rice,nbit=bw.finish();fb=np.asarray(fallback,np.int16);fbb=Z.compress(fb.astype('<i2').tobytes());total_bytes=int(prefix_bytes)+len(rice)+len(fbb)+64
   raw=ZD.decompress(fbb);fbd=np.frombuffer(raw,'<i2').astype(np.int16);fp=0;QD=np.zeros_like(Q);QD[:,:TRAIN]=Qpd
   mode2,name2,vals2,cum2,total2,H2,_=build_model(Qpd)
   if mode2!=mode or name2!=mname or total2!=total or not np.array_equal(vals2,vals) or not np.array_equal(cum2,cum):raise RuntimeError((region,'model rebuild'))
   br=BR(rice,nbit);score=12*256;decoded_indices=[]
   for c in range(C):
    for bno,t0 in enumerate(range(TRAIN,NT,L)):
     k=k_from_score(score);idx=br.rice(k);score=update_score(score,idx);decoded_indices.append(int(idx));t1=t0+L
     if idx==MAX_TRIES:
      if fp+L>len(fbd):raise RuntimeError((region,'fallback eof'))
      q=fbd[fp:fp+L];fp+=L
     elif idx<MAX_TRIES:
      left=QD[c-1,t0:t1].astype(np.int16) if c>0 else np.zeros(L,np.int16);lp=int(QD[c-1,t0-1]) if c>0 else 0
      q=_candidate(int(idx),seedbase(rid,c,bno),mode,int(QD[c,t0-1]),int(QD[c,t0-2]),left,lp,c>0,vals,cum,total)
     else:raise RuntimeError((region,'bad index',idx))
     QD[c,t0:t1]=q
   if fp!=len(fbd) or br.i!=nbit or decoded_indices!=indices:raise RuntimeError((region,'container parse',fp,len(fbd),br.i,nbit))
   if not np.array_equal(QD,QE):raise RuntimeError((region,'Q decode'))
   RR=QD.astype(np.float64)*h;me=float(np.max(np.abs(X-RR)))
   if me>eps*(1+1e-12):raise RuntimeError((region,'source hard',me,eps))
   sz=0
   for t0 in range(0,NT,TB):n,_=m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
   ns=X.size;held=(NT-TRAIN)*C;succ=1-escapes/(((NT-TRAIN)//L)*C);hit=[x for x in indices if x<MAX_TRIES]
   row={'region':region,'c0':c0,'shape':[C,NT],'samples':int(ns),'eps':eps,'lattice_h':h,'block_length':L,'max_tries':MAX_TRIES,
        'predictor_mode':mname,'prefix_residual_entropy':H,'mode_screen':modes,'prefix_bytes':int(prefix_bytes),'prefix_rep':prep,'rice_payload_bytes':len(rice),'rice_bits':int(nbit),'fallback_bytes':len(fbb),'fallback_values':int(len(fb)),'container_bytes':total_bytes,'bps':8*total_bytes/ns,
        'heldout_payload_bps':8*(len(rice)+len(fbb))/held,'escape_blocks':escapes,'total_blocks':((NT-TRAIN)//L)*C,'success_fraction':succ,
        'median_index':float(np.median(hit)) if hit else None,'mean_index':float(np.mean(hit)) if hit else None,
        'sz3_bytes':sz,'sz3_bps':8*sz/ns,'gain_vs_sz3':sz/total_bytes,'strict_2x_sz3_target_bytes':sz/2,'ratio_to_2x_target':total_bytes/(sz/2),'maxerr':me,'per_channel':per_ch}
   rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('mode_screen','per_channel')},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'rows':rows,'scope':'Constructive decoder-real random-covering/set-code pilot. No previous record is side information. The first 1024 samples of each four-channel region are nearest-q encoded exactly through encode_k and decoded; that decoded prefix deterministically selects one fixed causal predictor and builds its residual histogram. For every subsequent nonoverlapping 8-sample block, encoder and decoder share a deterministic stochastic codebook sampled from that prefix model using only public coordinates, already-decoded same-channel history and already-decoded left-channel Q. Encoder searches for the first generated candidate lying coordinatewise inside the source hard-error intervals and transmits only its integer codebook index using a decoder-synchronized adaptive Rice code. The decoder regenerates that whole block from the index without knowing the source intervals. Search failure at 2^18 candidates is a real escape: the nearest legal Q block is appended to a Zstd-compressed int16 escape stream. Prefix, Rice payload, escape payload and 64 framing bytes are all charged; the complete stream components are decoded, every index replayed, Q reproduced exactly, and final source max error checked. Matched SZ3 is rerun on identical samples. This is a constructive short-block approximation to probability-mass/set coding, not an entropy oracle. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_constructive_random_covering_setcode.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
