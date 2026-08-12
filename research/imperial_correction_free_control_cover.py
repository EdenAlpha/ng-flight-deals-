import json,sys,math
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix,vstack
from pysz import sz,szConfig,szErrorBoundMode

PC=32;PT=64;SAFETY=1-1e-5
HFACT=(1.0,0.75,0.5)
PHASES=(0,1,2,3)
SPECS=(
 ('hard_start_a',0,512),('hard_start_b',14464,512),
 ('easy_a',0,1280),('easy_b',14464,2560),
 ('medium_a',0,3328),('medium_b',14464,4480),
 ('far_a',0,6272),('far_edge',14464,6880),
)
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
  if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
  row=(int(b.size),'T' if tr else 'CT',me)
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
 for name,x in [('raw',a)]:
  dt=dtype_for(x);blob=ZC.compress(np.ascontiguousarray(x).astype(dt).tobytes());rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=x.size).astype(np.int32).reshape(x.shape)
  if not np.array_equal(rr,x):raise RuntimeError('raw roundtrip')
  c.append((len(blob)+24,name+'_'+dt.str))
 if a.ndim==2:
  dtv=a.copy();dtv[:,1:]-=a[:,:-1];dt=dtype_for(dtv);blob=ZC.compress(dtv.astype(dt).tobytes());rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape);dec=np.cumsum(rr,axis=1,dtype=np.int32)
  if not np.array_equal(dec,a):raise RuntimeError('dt roundtrip')
  c.append((len(blob)+24,'dt_'+dt.str))
  dsv=a.copy();dsv[1:]-=a[:-1];dt=dtype_for(dsv);blob=ZC.compress(dsv.astype(dt).tobytes());rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape);dec=np.cumsum(rr,axis=0,dtype=np.int32)
  if not np.array_equal(dec,a):raise RuntimeError('ds roundtrip')
  c.append((len(blob)+24,'ds_'+dt.str))
  L=a.copy();L[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];dt=dtype_for(L);blob=ZC.compress(L.astype(dt).tobytes());rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape);dec=rr.copy()
  for i in range(1,dec.shape[0]):
   for j in range(1,dec.shape[1]):dec[i,j]=rr[i,j]+dec[i-1,j]+dec[i,j-1]-dec[i-1,j-1]
  if not np.array_equal(dec,a):raise RuntimeError('lorenzo roundtrip')
  c.append((len(blob)+24,'lorenzo_'+dt.str))
 nz=a!=0;support=ZC.compress(np.packbits(nz.astype(np.uint8).ravel(),bitorder='little').tobytes());vals=a[nz];dt=dtype_for(vals);vb=ZC.compress(vals.astype(dt).tobytes()) if vals.size else b''
 mask=np.unpackbits(np.frombuffer(ZD.decompress(support),np.uint8),bitorder='little')[:a.size].astype(bool).reshape(a.shape);vv=np.frombuffer(ZD.decompress(vb),dtype=dt).astype(np.int32) if vals.size else np.empty(0,np.int32);dec=np.zeros_like(a);dec[mask]=vv
 if not np.array_equal(dec,a):raise RuntimeError('sparse roundtrip')
 c.append((len(support)+len(vb)+48,'sparse_'+dt.str))
 return min(c)


def solve_controls(ZX,bound,h,phi):
 cc=np.arange(PC)[:,None];tt=np.arange(PT)[None,:];mask=((cc+tt)&1)==0
 coords=np.argwhere(mask);n=len(coords);idx=-np.ones((PC,PT),np.int32)
 for k,(c,t) in enumerate(coords):idx[c,t]=k
 vals=ZX[mask]
 lo=np.ceil((vals-bound-phi)/h-1e-12).astype(np.int32);hi=np.floor((vals+bound-phi)/h+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty control legal set')
 q0=np.rint((vals-phi)/h).astype(np.int32);q0=np.minimum(np.maximum(q0,lo),hi)
 # Variables = integer control q[0:n] + continuous deviation d[0:n].
 cobj=np.concatenate([np.zeros(n),np.ones(n)])
 integrality=np.concatenate([np.ones(n,np.int32),np.zeros(n,np.int32)])
 lb=np.concatenate([lo.astype(np.float64),np.zeros(n)])
 ub=np.concatenate([hi.astype(np.float64),np.full(n,np.inf)])
 mats=[];lbs=[];ubs=[]
 # d >= |q-q0|
 A=lil_matrix((2*n,2*n),dtype=np.float64)
 for i in range(n):
  A[2*i,i]=1;A[2*i,n+i]=-1;ubs.append(float(q0[i]));lbs.append(-np.inf)
  A[2*i+1,i]=-1;A[2*i+1,n+i]=-1;ubs.append(float(-q0[i]));lbs.append(-np.inf)
 mats.append(A.tocsr())
 interior=[]
 # Every interior omitted point must be reconstructed directly by the average of
 # its four controls, with no correction symbol at all.
 rows=[];rl=[];ru=[]
 for c in range(1,PC-1):
  for t in range(1,PT-1):
   if mask[c,t]:continue
   nb=[idx[c-1,t],idx[c+1,t],idx[c,t-1],idx[c,t+1]]
   if min(nb)<0:raise RuntimeError('checker topology')
   interior.append((c,t));rows.append(nb)
   rl.append(4*(ZX[c,t]-bound-phi)/h);ru.append(4*(ZX[c,t]+bound-phi)/h)
 B=lil_matrix((len(rows),2*n),dtype=np.float64)
 for r,nb in enumerate(rows):
  for j in nb:B[r,j]=1.0
 mats.append(B.tocsr());lbs.extend(rl);ubs.extend(ru)
 M=vstack(mats,format='csr');cons=LinearConstraint(M,np.asarray(lbs),np.asarray(ubs))
 res=milp(cobj,integrality=integrality,bounds=Bounds(lb,ub),constraints=cons,options={'time_limit':15.0,'mip_rel_gap':0.0,'presolve':True})
 feasible=bool(res.x is not None and np.all(np.isfinite(res.x[:n])))
 q=q0.copy() if not feasible else np.rint(res.x[:n]).astype(np.int32)
 if np.any(q<lo)|np.any(q>hi):raise RuntimeError('solver illegal control')
 Q=np.zeros((PC,PT),np.int32);Q[mask]=q
 return mask,Q,feasible,int(getattr(res,'status',-1)),float(getattr(res,'fun',np.nan)),interior,float(np.mean(hi-lo+1)),float(np.mean(q!=q0))


def evaluate(X,eps,hfac,phase):
 bound=eps*SAFETY;s=np.where(np.arange(PT)%2==0,1.0,-1.0);ZX=X*s[None,:]
 h=hfac*bound;phi=h*phase/4.0
 mask,Q,feasible,status,obj,interior,mean_states,changed=solve_controls(ZX,bound,h,phi)
 P=np.zeros_like(ZX);P[mask]=phi+h*Q[mask]
 for c,t in np.argwhere(~mask):
  sv=[];tv=[]
  if c>0:sv.append(P[c-1,t])
  if c+1<PC:sv.append(P[c+1,t])
  if t>0:tv.append(P[c,t-1])
  if t+1<PT:tv.append(P[c,t+1])
  ss=sum(sv)/len(sv) if sv else 0.;vv=sum(tv)/len(tv) if tv else 0.
  P[c,t]=(ss+vv)/2 if sv and tv else (ss if sv else vv)
 miss=~mask;K=np.rint((ZX[miss]-P[miss])/(2*bound)).astype(np.int32);P[miss]+=2*bound*K
 R=P*s[None,:];me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
 # Interior constraints should annihilate corrections whenever MILP found a feasible point.
 km=np.zeros_like(mask,dtype=np.int32);km[miss]=K
 inz=float(np.mean([km[c,t]!=0 for c,t in interior])) if interior else 0.0
 A0=Q[0::2,0::2];A1=Q[1::2,1::2];a0=encode_int(A0);a1=encode_int(A1);kr=encode_int(K)
 total=a0[0]+a1[0]+kr[0]+64
 return {'h_over_eps':hfac,'phase':phase,'bytes':total,'control_bytes':a0[0]+a1[0],'control_reps':[a0[1],a1[1]],'correction_bytes':kr[0],'correction_rep':kr[1],
         'correction_nonzero_fraction':float(np.mean(K!=0)),'interior_correction_nonzero_fraction':inz,'solver_feasible':feasible,'solver_status':status,'solver_objective':obj,
         'mean_legal_control_states':mean_states,'changed_control_fraction':changed,'maxerr':me}


def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+PT,c0:c0+PC],np.float64).T;sb=szrun(X,eps);tiles.append({'tile':name,'t0':t0,'c0':c0,'raw_bytes':X.size*2,'sz3_bytes':sb[0],'sz3_orientation':sb[1]})
   for hf in HFACT:
    for ph in PHASES:
     r=evaluate(X,eps,hf,ph);r.update({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
  combos=[]
  for hf in HFACT:
   for ph in PHASES:
    rr=[r for r in rows if r['h_over_eps']==hf and r['phase']==ph];b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=sum(t['raw_bytes']//2 for t in tiles)
    combos.append({'h_over_eps':hf,'phase':ph,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/n,'feasible_patch_fraction':float(np.mean([r['solver_feasible'] for r in rr])),
                   'median_interior_correction_nonzero':float(np.median([r['interior_correction_nonzero_fraction'] for r in rr])),'max_interior_correction_nonzero':max(r['interior_correction_nonzero_fraction'] for r in rr),
                   'median_all_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'median_legal_control_states':float(np.median([r['mean_legal_control_states'] for r in rr])),
                   'median_changed_controls':float(np.median([r['changed_control_fraction'] for r in rr])),'control_bytes':sum(r['control_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr)})
  combos.sort(key=lambda x:(-x['feasible_patch_fraction'],x['bytes']))
  out={'std':std,'eps':eps,'patch_shape':[PC,PT],'specs':[list(x) for x in SPECS],'h_factors':list(HFACT),'phases':list(PHASES),'combos':combos,'rows':rows,
       'scope':'Global integer correction-free control-cover screen. On each 32x64 Nyquist-demodulated checkerboard patch, every retained control is an integer variable constrained only by its own unchanged +/-10%-global-std legal interval. One MILP chooses all controls jointly so every interior omitted sample lies inside its hard-error interval under the exact four-neighbor checkerboard interpolation, eliminating interior correction symbols whenever feasible. Boundary misses still receive fully counted exact 2epsilon corrections. Control and correction bytes are actually Zstd serialized and final reconstruction is hard-error verified. Exploratory patch screen, no whole-file claim.'}
  print(json.dumps({'best':combos[:12]},indent=2),flush=True);json.dump(out,open('imperial_correction_free_control_cover.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
