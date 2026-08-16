import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192
BASE={
 'hard':{'ar32_bytes':661373,'sz3_bytes':754436},
 'easy':{'ar32_bytes':237943,'sz3_bytes':282633},
 'medium':{'ar32_bytes':416391,'sz3_bytes':460273},
 'far':{'ar32_bytes':551268,'sz3_bytes':636418},
}
HEADER=48
PASSES=3
MODES=('l1','log','zero_log')

@njit(cache=True)
def clipi(x,lo,hi):
 if x<lo:return lo
 if x>hi:return hi
 return x

@njit(cache=True)
def causal_lorenzo(lo,hi):
 C,T=lo.shape;R=np.empty((C,T),np.int32)
 for t in range(T):
  for c in range(C):
   if c==0 and t==0:p=0
   elif c==0:p=int(R[c,t-1])
   elif t==0:p=int(R[c-1,t])
   else:p=int(R[c,t-1])+int(R[c-1,t])-int(R[c-1,t-1])
   R[c,t]=clipi(p,int(lo[c,t]),int(hi[c,t]))
 return R

@njit(cache=True)
def lorenzo(R):
 C,T=R.shape;D=np.empty((C,T),np.int32)
 for t in range(T):
  for c in range(C):
   if c==0 and t==0:d=int(R[c,t])
   elif c==0:d=int(R[c,t])-int(R[c,t-1])
   elif t==0:d=int(R[c,t])-int(R[c-1,t])
   else:d=int(R[c,t])-int(R[c,t-1])-int(R[c-1,t])+int(R[c-1,t-1])
   D[c,t]=d
 return D

@njit(cache=True)
def cost1(d,mode):
 a=abs(int(d))
 if mode==0:return float(a)
 if mode==1:return math.log2(1.0+a)
 if a==0:return 0.0
 return 10.0+math.log2(1.0+a)

@njit(cache=True)
def local_cost(D,c,t,delta,mode):
 C,T=D.shape;s=0.0
 s+=cost1(int(D[c,t])+delta,mode)
 if t+1<T:s+=cost1(int(D[c,t+1])-delta,mode)
 if c+1<C:s+=cost1(int(D[c+1,t])-delta,mode)
 if c+1<C and t+1<T:s+=cost1(int(D[c+1,t+1])+delta,mode)
 return s

@njit(cache=True)
def addcand(a,n,x,lo,hi):
 x=clipi(x,lo,hi)
 for i in range(n):
  if a[i]==x:return n
 a[n]=x;return n+1

@njit(cache=True)
def sweep(R,D,lo,hi,mode,reverse):
 C,T=R.shape;changes=0
 # At one site only four Lorenzo defects depend on x. Their roots plus interval
 # endpoints are the complete breakpoints for the L1/log/zero-log surrogates.
 for kk in range(C*T):
  z=C*T-1-kk if reverse else kk
  t=z//C;c=z-t*C
  cur=int(R[c,t]);L=int(lo[c,t]);H=int(hi[c,t]);cand=np.empty(12,np.int64);n=0
  n=addcand(cand,n,cur,L,H);n=addcand(cand,n,L,L,H);n=addcand(cand,n,H,L,H)
  # Root of D[c,t] + (x-cur) = 0.
  n=addcand(cand,n,cur-int(D[c,t]),L,H)
  if t+1<T:n=addcand(cand,n,cur+int(D[c,t+1]),L,H)
  if c+1<C:n=addcand(cand,n,cur+int(D[c+1,t]),L,H)
  if c+1<C and t+1<T:n=addcand(cand,n,cur-int(D[c+1,t+1]),L,H)
  best=cur;bc=local_cost(D,c,t,0,mode)
  for i in range(n):
   x=int(cand[i]);q=local_cost(D,c,t,x-cur,mode)
   if q<bc-1e-12 or (abs(q-bc)<=1e-12 and abs(x-cur)<abs(best-cur)):
    bc=q;best=x
  if best!=cur:
   de=best-cur;R[c,t]=best;D[c,t]+=de
   if t+1<T:D[c,t+1]-=de
   if c+1<C:D[c+1,t]-=de
   if c+1<C and t+1<T:D[c+1,t+1]+=de
   changes+=1
 return changes

@njit(cache=True)
def optimize(R0,lo,hi,mode,passes):
 R=R0.copy();D=lorenzo(R);changes=0
 for p in range(passes):
  ch=sweep(R,D,lo,hi,mode,p%2==1);changes+=ch
  if ch==0:break
 return R,D,changes

def materialize(X,eps,R,label,extra):
 fr=m.encode_k(np.asarray(R,np.int32));Rd=np.asarray(fr[2],np.int32)
 if not np.array_equal(Rd,R):raise RuntimeError(('frame replay',label))
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',label,me,eps))
 D=lorenzo(np.asarray(Rd,np.int32));b=int(fr[0])+HEADER
 return {'kind':label,'bytes':b,'bps':8*b/X.size,'rep':fr[1],'maxerr':me,'lorenzo_zero_fraction':float(np.mean(D==0)),'lorenzo_abs1_fraction':float(np.mean(np.abs(D)==1)),'lorenzo_std':float(D.std()),**extra}

def main(path):
 with h5py.File(path,'r') as f:
  data=f['Acoustic'];_,gstd=m.stats(data);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(data[:NT,c0:c0+C],np.float64).T
   lo=np.ceil(X-eps).astype(np.int32);hi=np.floor(X+eps).astype(np.int32)
   if np.any(lo>hi):raise RuntimeError(('empty',region))
   widths=hi.astype(np.int64)-lo.astype(np.int64)+1
   R0=causal_lorenzo(lo,hi)
   rr=[materialize(X,eps,R0,'causal_clip',{'objective':'causal','passes':0,'optimizer_changes':0})]
   for mi,name in enumerate(MODES):
    R,D,ch=optimize(R0,lo,hi,mi,PASSES)
    rr.append(materialize(X,eps,R,name,{'objective':name,'passes':PASSES,'optimizer_changes':int(ch)}))
   for r in rr:
    r.update({'region':region,'c0':c0,'mean_legal_integer_states':float(widths.mean()),'min_legal_integer_states':int(widths.min()),'max_legal_integer_states':int(widths.max()),'ar32_bytes':BASE[region]['ar32_bytes'],'sz3_bytes':BASE[region]['sz3_bytes'],'gain_vs_ar32':BASE[region]['ar32_bytes']/r['bytes'],'gain_vs_sz3':BASE[region]['sz3_bytes']/r['bytes']})
    print(json.dumps(r),flush=True)
   best=min(rr,key=lambda x:x['bytes']);rows.append({'region':region,'best':best,'all':rr})
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'passes':PASSES,'objectives':list(MODES),'header_bytes':HEADER,'controls':'Pinned exact PR420 run 31788514939 AR32/SZ3 bytes on identical canonical 128x8192 objects and epsilon. Candidate reconstruction streams are independently byte-decoded and source-domain hard-error verified.','rows':rows,'scope':'Full-integer hard-box 2-D Lorenzo projection. Unlike prior 256-spaced legal-grid experiments, every sample may choose any integer inside its exact +/-epsilon interval (about 267 legal states/sample). The causal seed reconstruction predicts each point with the already-decoded 2-D Lorenzo plane and clips that prediction directly into the legal interval, making the Lorenzo defect exactly zero whenever possible. Global coordinate descent then revisits the complete field. Changing one reconstruction value affects only four neighboring Lorenzo defects; for L1, log1p and zero-weighted-log surrogates, the local defect zero-crossings plus legal interval endpoints form a tiny deterministic candidate set, so all ~267 legal states need not be enumerated. The final chosen integer reconstruction field is serialized through the existing exact raw/delta/Lorenzo/zigzag/XOR/Gray/bitplane Zstd menu, byte-decoded, and checked against the source. The optimizer state is not transmitted. No oracle rate, coarse-grid restriction, target-trained probability model, or post-hoc repair.'}
  json.dump(out,open('imperial_fullbox_lorenzo_projection.json','w'),indent=2)
  print(json.dumps({'summary':[{'region':x['region'],'kind':x['best']['kind'],'bytes':x['best']['bytes'],'bps':x['best']['bps'],'gain_ar32':x['best']['gain_vs_ar32'],'gain_sz3':x['best']['gain_vs_sz3'],'zero':x['best']['lorenzo_zero_fraction'],'rep':x['best']['rep']} for x in rows]},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])