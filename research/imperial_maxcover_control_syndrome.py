import json,sys,math
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix,vstack
from pysz import sz,szConfig,szErrorBoundMode

PC=32;PT=64;SAFETY=1-1e-5
# PR257 showed h=epsilon is the best realized rate and all phases are close.
# Freeze two antipodal phases rather than reopen a large tuning sweep.
HFACT=(1.0,);PHASES=(1,3)
SPECS=(('hard',14464,512),('easy',14464,1280),('medium',14464,4480),('far',14464,6880))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
  row=(int(b.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def dtype_for(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  ii=np.iinfo(dt)
  if mn>=ii.min and mx<=ii.max:return dt
 return np.dtype('<i8')

def encode_int(a):
 a=np.asarray(a,np.int32);c=[]
 reps={'raw':a}
 if a.ndim==2:
  x=a.copy();x[:,1:]-=a[:,:-1];reps['dt']=x
  x=a.copy();x[1:]-=a[:-1];reps['ds']=x
  x=a.copy();x[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];reps['lorenzo']=x
 for name,x in reps.items():
  dt=dtype_for(x);blob=ZC.compress(np.ascontiguousarray(x).astype(dt).tobytes());c.append((len(blob)+24,name+'_'+dt.str))
 nz=a!=0;sup=ZC.compress(np.packbits(nz.astype(np.uint8).ravel(),bitorder='little').tobytes());v=a[nz];dt=dtype_for(v);vb=ZC.compress(v.astype(dt).tobytes()) if v.size else b''
 c.append((len(sup)+len(vb)+48,'sparse_'+dt.str))
 return min(c)

def build_problem(ZX,bound,h,phi):
 cc=np.arange(PC)[:,None];tt=np.arange(PT)[None,:];mask=((cc+tt)&1)==0
 coords=np.argwhere(mask);nq=len(coords);idx=-np.ones((PC,PT),np.int32)
 for k,(c,t) in enumerate(coords):idx[c,t]=k
 vals=ZX[mask];lo=np.ceil((vals-bound-phi)/h-1e-12).astype(np.int32);hi=np.floor((vals+bound-phi)/h+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal control')
 q0=np.rint((vals-phi)/h).astype(np.int32);q0=np.minimum(np.maximum(q0,lo),hi)
 interior=[];nbs=[];Ls=[];Us=[]
 for c in range(1,PC-1):
  for t in range(1,PT-1):
   if mask[c,t]:continue
   nb=[int(idx[c-1,t]),int(idx[c+1,t]),int(idx[c,t-1]),int(idx[c,t+1])]
   interior.append((c,t));nbs.append(nb)
   Ls.append(4*(ZX[c,t]-bound-phi)/h);Us.append(4*(ZX[c,t]+bound-phi)/h)
 nz=len(interior)
 # Variables q integer [nq], d continuous [nq], z binary [nz].
 N=2*nq+nz; mats=[];lbs=[];ubs=[]
 A=lil_matrix((2*nq,N),dtype=np.float64)
 for i in range(nq):
  A[2*i,i]=1;A[2*i,nq+i]=-1;lbs.append(-np.inf);ubs.append(float(q0[i]))
  A[2*i+1,i]=-1;A[2*i+1,nq+i]=-1;lbs.append(-np.inf);ubs.append(float(-q0[i]))
 mats.append(A.tocsr())
 # If z_j=0, require target omitted sample to be inside its hard-error interval.
 # If z_j=1, exact bound-derived big-M relaxes only that sample.
 B=lil_matrix((2*nz,N),dtype=np.float64);bl=[];bu=[]
 for j,(nb,L,U) in enumerate(zip(nbs,Ls,Us)):
  smin=float(sum(lo[k] for k in nb));smax=float(sum(hi[k] for k in nb))
  Mlo=max(0.,L-smin);Mup=max(0.,smax-U);zcol=2*nq+j
  for k in nb:B[2*j,k]=1.0;B[2*j+1,k]=1.0
  B[2*j,zcol]=Mlo;bl.append(L);bu.append(np.inf)
  B[2*j+1,zcol]=-Mup;bl.append(-np.inf);bu.append(U)
 mats.append(B.tocsr());lbs.extend(bl);ubs.extend(bu)
 M=vstack(mats,format='csr');cons=[LinearConstraint(M,np.asarray(lbs),np.asarray(ubs))]
 lb=np.r_[lo,np.zeros(nq),np.zeros(nz)];ub=np.r_[hi,np.full(nq,np.inf),np.ones(nz)]
 integ=np.r_[np.ones(nq,np.int32),np.zeros(nq,np.int32),np.ones(nz,np.int32)]
 return mask,idx,interior,nbs,lo,hi,q0,nq,nz,Bounds(lb,ub),cons,integ

def solve_maxcover(ZX,bound,h,phi):
 mask,idx,interior,nbs,lo,hi,q0,nq,nz,bounds,cons,integ=build_problem(ZX,bound,h,phi)
 # Stage 1: globally minimize number of exception samples.
 c1=np.r_[np.zeros(2*nq),np.ones(nz)]
 r1=milp(c1,integrality=integ,bounds=bounds,constraints=cons,options={'time_limit':30.0,'mip_rel_gap':0.0,'presolve':True})
 if r1.x is None:raise RuntimeError(('maxcover no feasible solution',r1.status,r1.message))
 zopt=int(round(float(np.sum(np.rint(r1.x[2*nq:])))))
 # Stage 2: among maximum-cover assignments, minimize total deviation from nearest legal controls.
 N=2*nq+nz;row=lil_matrix((1,N),dtype=np.float64);row[0,2*nq:]=1.0
 cons2=cons+[LinearConstraint(row.tocsr(),-np.inf,float(zopt)+1e-9)]
 c2=np.r_[np.zeros(nq),np.ones(nq),np.zeros(nz)]
 r2=milp(c2,integrality=integ,bounds=bounds,constraints=cons2,options={'time_limit':30.0,'mip_rel_gap':0.0,'presolve':True})
 r=r2 if r2.x is not None else r1
 q=np.rint(r.x[:nq]).astype(np.int32);z=np.rint(r.x[2*nq:]).astype(np.int8)
 if np.any(q<lo)|np.any(q>hi):raise RuntimeError('illegal control')
 Q=np.zeros((PC,PT),np.int32);Q[mask]=q
 return mask,Q,interior,z,zopt,float(np.mean(hi-lo+1)),float(np.mean(q!=q0)),int(r1.status),int(r2.status)

def evaluate(X,eps,phase):
 bound=eps*SAFETY;s=np.where(np.arange(PT)%2==0,1.,-1.);ZX=X*s[None,:];h=bound;phi=h*phase/4.
 mask,Q,interior,z,zopt,meanstates,changed,st1,st2=solve_maxcover(ZX,bound,h,phi)
 P=np.zeros_like(ZX);P[mask]=phi+h*Q[mask]
 for c,t in np.argwhere(~mask):
  sv=[];tv=[]
  if c>0:sv.append(P[c-1,t])
  if c+1<PC:sv.append(P[c+1,t])
  if t>0:tv.append(P[c,t-1])
  if t+1<PT:tv.append(P[c,t+1])
  ss=sum(sv)/len(sv) if sv else 0.;vv=sum(tv)/len(tv) if tv else 0.;P[c,t]=(ss+vv)/2 if sv and tv else (ss if sv else vv)
 miss=~mask;K=np.rint((ZX[miss]-P[miss])/(2*bound)).astype(np.int32);P[miss]+=2*bound*K;R=P*s[None,:]
 me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
 km=np.zeros((PC,PT),np.int32);km[miss]=K;actual=np.array([km[c,t]!=0 for c,t in interior])
 # Audit MILP exception prediction. z=0 must always imply zero actual correction.
 if np.any((z==0)&actual):raise RuntimeError(('MILP audit',int(np.sum((z==0)&actual))))
 a0=encode_int(Q[0::2,0::2]);a1=encode_int(Q[1::2,1::2]);kr=encode_int(K);total=a0[0]+a1[0]+kr[0]+64
 return {'phase':phase,'bytes':total,'control_bytes':a0[0]+a1[0],'correction_bytes':kr[0],'control_reps':[a0[1],a1[1]],'correction_rep':kr[1],
 'milp_exception_count':zopt,'milp_exception_fraction':zopt/len(interior),'actual_interior_correction_fraction':float(np.mean(actual)),'all_correction_nonzero_fraction':float(np.mean(K!=0)),
 'mean_legal_control_states':meanstates,'changed_control_fraction':changed,'stage1_status':st1,'stage2_status':st2,'maxerr':me}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+PT,c0:c0+PC],np.float64).T;sb=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb[0],'raw_bytes':X.size*2})
   for ph in PHASES:
    r=evaluate(X,eps,ph);r.update({'tile':name,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
  combos=[]
  for ph in PHASES:
   rr=[r for r in rows if r['phase']==ph];b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=sum(t['raw_bytes']//2 for t in tiles)
   combos.append({'phase':ph,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/n,'control_bytes':sum(r['control_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),
    'median_milp_exception_fraction':float(np.median([r['milp_exception_fraction'] for r in rr])),'median_actual_interior_correction_fraction':float(np.median([r['actual_interior_correction_fraction'] for r in rr])),'median_all_correction_nonzero_fraction':float(np.median([r['all_correction_nonzero_fraction'] for r in rr])),'median_changed_control_fraction':float(np.median([r['changed_control_fraction'] for r in rr]))})
  combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'patch_shape':[PC,PT],'specs':[list(x) for x in SPECS],'phases':list(PHASES),'combos':combos,'rows':rows,
   'scope':'Exact maximum-coverage checkerboard control-syndrome screen. After PR257 proved the all-zero-correction linear system infeasible, each interior omitted sample gets one binary exception variable. Stage-1 MILP globally minimizes the exception count under every retained control hard-error interval; stage-2 minimizes control movement at that exact exception count. Controls and remaining exact 2epsilon corrections are then actually Zstd serialized and final samples hard-error verified. Four precommitted regimes, h=epsilon, two fixed phases. No whole-file claim.'}
  print(json.dumps({'combos':combos,'rows':rows},indent=2),flush=True);json.dump(out,open('imperial_maxcover_control_syndrome.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
