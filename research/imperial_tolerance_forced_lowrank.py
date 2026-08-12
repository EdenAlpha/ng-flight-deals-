import json,sys,math
import h5py
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;RANKS=(4,8,12,16,24,32,48,64);ITERS=35;SAFETY=1-1e-5
SPECS=(('easy',14488,1696),('medium',14488,3392),('hard',14488,6784))

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))

def rankproj(Y,k):
 # Exact best rank-k Frobenius projection, exploiting only a 128x128 eigenproblem.
 G=Y@Y.T
 w,U=np.linalg.eigh(G);U=U[:,-k:]
 return U@(U.T@Y)

def violation(L,X,b):
 E=np.abs(L-X)-b
 return float(max(0.0,E.max())),float(np.mean(E>0)),float(np.sqrt(np.mean((L-X)**2)))

def ap(X,b,k):
 Y=X.copy();best=None
 for it in range(ITERS):
  L=rankproj(Y,k);v,f,rm=violation(L,X,b)
  row=(v,f,rm,it,L)
  if best is None or (v,f,rm)<best[:3]:best=row
  Y=np.clip(L,X-b,X+b)
 return best

def dr(X,b,k):
 Z=X.copy();best=None
 for it in range(ITERS):
  B=np.clip(Z,X-b,X+b)
  R=rankproj(2*B-Z,k)
  # R itself is rank-k; judge whether that rank-k point lies in the source box.
  v,f,rm=violation(R,X,b)
  row=(v,f,rm,it,R)
  if best is None or (v,f,rm)<best[:3]:best=row
  Z=Z+R-B
 return best

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  bb,_=sz.compress(A,cfg);R,_=sz.decompress(bb,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
  if best is None or int(bb.size)<best['bytes']:best={'bytes':int(bb.size),'orientation':'T' if tr else 'CT','ratio':A.nbytes/int(bb.size),'maxerr':me}
 return best

def factor_floor_bytes(k):
 # Information-accounting floor only, not a codec claim: number of real factors in U(Cxk)+V(kxT).
 return {'float32':4*k*(C+T),'float16':2*k*(C+T),'int8':k*(C+T)}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);pub=.1*std;b=pub*SAFETY;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,pub);tiles.append({'tile':name,'t0':t0,'c0':c0,'local_std':float(X.std()),'eps_over_local_std':pub/float(X.std()),'sz3':sb})
   for k in RANKS:
    for meth,fn in [('alternating_projection',ap),('douglas_rachford',dr)]:
     v,frac,rm,it,L=fn(X,b,k)
     # Numerical rank and singular spectrum of the actual candidate are audited.
     s=np.linalg.svd(L,compute_uv=False);nr=int(np.sum(s>max(s[0]*1e-10,1e-9))) if s.size and s[0]>0 else 0
     exact=bool(v<=pub*5e-6)
     rows.append({'tile':name,'rank_target':k,'method':meth,'iterations':it+1,'max_excess_over_internal_box':v,'violating_fraction':frac,'rmse':rm,'rmse_over_eps':rm/pub,'numerical_rank':nr,'exact_hard_box_feasible_found':exact,'factor_raw_floor_bytes':factor_floor_bytes(k),'matched_sz3_bytes':sb['bytes'],'float16_factor_floor_gain_vs_sz3':sb['bytes']/factor_floor_bytes(k)['float16'],'int8_factor_floor_gain_vs_sz3':sb['bytes']/factor_floor_bytes(k)['int8']})
  # For each tile, smallest rank at which this concrete nonconvex search found an exact point.
  summary=[]
  for name,_,_ in SPECS:
   rr=[r for r in rows if r['tile']==name];ok=[r for r in rr if r['exact_hard_box_feasible_found']]
   summary.append({'tile':name,'smallest_found_exact_rank':min((r['rank_target'] for r in ok),default=None),'best_max_excess':min(r['max_excess_over_internal_box'] for r in rr),'best_fraction_violating':min(r['violating_fraction'] for r in rr),'best_rows':sorted(rr,key=lambda r:(r['max_excess_over_internal_box'],r['violating_fraction']))[:5]})
  out={'std':std,'public_eps':pub,'internal_box_halfwidth':b,'shape_per_tile':[C,T],'ranks':list(RANKS),'iterations_per_method':ITERS,'tiles':tiles,'summary':summary,'rows':rows,'scope':'Tolerance-forced algebraic-rank feasibility screen. It searches for a rank-k matrix lying directly inside every sample interval [x-eps,x+eps], using alternating projections and nonconvex Douglas-Rachford. Finding feasibility is constructive; failure is NOT an impossibility proof. Factor byte numbers are raw coefficient-count floors only, not compressed-container claims.'}
  print(json.dumps({'summary':summary},indent=2),flush=True);json.dump(out,open('imperial_tolerance_forced_lowrank.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
