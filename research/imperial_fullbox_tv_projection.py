import json,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;PASSES=5;HEADER=40
VARIANTS=(('time_only',4,0),('balanced',1,1),('time4',4,1),('space4',1,4))
BASE={'hard':{'ar32_bytes':661373,'sz3_bytes':754436},'easy':{'ar32_bytes':237943,'sz3_bytes':282633},'medium':{'ar32_bytes':416391,'sz3_bytes':460273},'far':{'ar32_bytes':551268,'sz3_bytes':636418}}

@njit(cache=True)
def clipi(x,lo,hi):
 if x<lo:return lo
 if x>hi:return hi
 return x

@njit(cache=True)
def locost(R,c,t,x,wt,ws):
 C,T=R.shape;s=0
 if wt:
  if t:s+=wt*abs(x-int(R[c,t-1]))
  if t+1<T:s+=wt*abs(x-int(R[c,t+1]))
 if ws:
  if c:s+=ws*abs(x-int(R[c-1,t]))
  if c+1<C:s+=ws*abs(x-int(R[c+1,t]))
 return s

@njit(cache=True)
def sweep(R,lo,hi,wt,ws,rev):
 C,T=R.shape;ch=0
 for kk in range(C*T):
  z=C*T-1-kk if rev else kk;t=z//C;c=z-t*C
  L=int(lo[c,t]);H=int(hi[c,t]);cur=int(R[c,t]);cand=np.empty(8,np.int64);n=0
  cand[n]=cur;n+=1;cand[n]=L;n+=1;cand[n]=H;n+=1
  if wt and t:cand[n]=clipi(int(R[c,t-1]),L,H);n+=1
  if wt and t+1<T:cand[n]=clipi(int(R[c,t+1]),L,H);n+=1
  if ws and c:cand[n]=clipi(int(R[c-1,t]),L,H);n+=1
  if ws and c+1<C:cand[n]=clipi(int(R[c+1,t]),L,H);n+=1
  best=cur;bc=locost(R,c,t,cur,wt,ws)
  for i in range(n):
   x=int(cand[i]);q=locost(R,c,t,x,wt,ws)
   if q<bc or (q==bc and abs(x-cur)<abs(best-cur)):bc=q;best=x
  if best!=cur:R[c,t]=best;ch+=1
 return ch

@njit(cache=True)
def optimize(R0,lo,hi,wt,ws):
 R=R0.copy();tot=0
 for p in range(PASSES):
  ch=sweep(R,lo,hi,wt,ws,p%2==1);tot+=ch
  if ch==0:break
 return R,tot

def metrics(R):
 dt=R[:,1:].astype(np.int64)-R[:,:-1].astype(np.int64);ds=R[1:,:].astype(np.int64)-R[:-1,:].astype(np.int64)
 return {'time_equal_fraction':float(np.mean(dt==0)),'space_equal_fraction':float(np.mean(ds==0)),'time_absdiff_mean':float(np.mean(np.abs(dt))),'space_absdiff_mean':float(np.mean(np.abs(ds)))}

def materialize(X,eps,R,name,changes):
 fr=m.encode_k(np.asarray(R,np.int32));Rd=np.asarray(fr[2],np.int32)
 if not np.array_equal(Rd,R):raise RuntimeError(('decode',name))
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',name,me,eps))
 out={'kind':name,'bytes':int(fr[0])+HEADER,'bps':8*(int(fr[0])+HEADER)/X.size,'rep':fr[1],'maxerr':me,'optimizer_changes':int(changes)};out.update(metrics(Rd));return out

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;lo=np.ceil(X-eps).astype(np.int32);hi=np.floor(X+eps).astype(np.int32)
   widths=hi.astype(np.int64)-lo.astype(np.int64)+1
   R0=np.rint(X).astype(np.int32);R0=np.minimum(np.maximum(R0,lo),hi);rr=[]
   for name,wt,ws in VARIANTS:
    R,ch=optimize(R0,lo,hi,wt,ws);r=materialize(X,eps,R,name,ch);r.update({'region':region,'c0':c0,'wt':wt,'ws':ws,'mean_legal_integer_states':float(widths.mean()),'ar32_bytes':BASE[region]['ar32_bytes'],'sz3_bytes':BASE[region]['sz3_bytes'],'gain_vs_ar32':BASE[region]['ar32_bytes']/r['bytes'],'gain_vs_sz3':BASE[region]['sz3_bytes']/r['bytes']});rr.append(r);print(json.dumps(r),flush=True)
   best=min(rr,key=lambda x:x['bytes']);rows.append({'region':region,'best':best,'all':rr})
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'passes':PASSES,'variants':[list(x) for x in VARIANTS],'header_bytes':HEADER,'rows':rows,'controls':'Pinned exact PR420 AR32/SZ3 bytes on identical canonical 128x8192 regions and global epsilon.','scope':'Full-integer hard-box anisotropic total-variation projection. Every source sample exposes its complete legal integer interval under the unchanged absolute error bound. Starting from the rounded source, alternating raster/reverse coordinate descent replaces each reconstruction by the exact best local candidate among its legal interval endpoints and clipped neighboring values, monotonically reducing weighted temporal/spatial L1 variation. time-only, balanced, 4:1 time:space and 1:4 time:space objectives are fixed in advance. No optimization state is transmitted. The final complete integer reconstruction field is serialized through the existing exact raw/delta/Lorenzo/zigzag/XOR/Gray/bitplane Zstd menu, byte-decoded, and source-domain hard-error verified. This tests piecewise-flat 2-D geometry using all ~267 legal integer states/sample; it is not the coarse 256-grid overlap problem and has no oracle or post-hoc repair.'}
  json.dump(out,open('imperial_fullbox_tv_projection.json','w'),indent=2)
  print(json.dumps({'summary':[{'region':x['region'],'kind':x['best']['kind'],'bytes':x['best']['bytes'],'bps':x['best']['bps'],'gain_ar32':x['best']['gain_vs_ar32'],'gain_sz3':x['best']['gain_vs_sz3'],'teq':x['best']['time_equal_fraction'],'seq':x['best']['space_equal_fraction'],'rep':x['best']['rep']} for x in rows]},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])