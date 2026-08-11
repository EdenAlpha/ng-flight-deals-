import json,os,subprocess,numpy as np,zstandard as zstd
meta=json.load(open('data/forge_subcube_meta.json'));eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(64,64,512).astype(np.float32)
R=np.fromfile('diagnostic_rec.bin','<f4').reshape(64,64,512).astype(np.float32)
Z=zstd.ZstdCompressor(level=19)

def H(a):
 _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def zs(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dt=np.int8 if lo>=-128 and hi<=127 else np.int16 if lo>=-32768 and hi<=32767 else np.int32
 raw=len(Z.compress(a.astype(dt).tobytes()));m=a!=0;mv=len(Z.compress(np.packbits(m,bitorder='little').tobytes()+a[m].astype(dt).tobytes()));return min(raw,mv),raw,mv
def qmetric(Y,P,model_bytes):
 Q=np.rint((Y.astype(np.float64)-P.astype(np.float64))/(2*eps)).astype(np.int16);rec=P.astype(np.float64)+Q*(2*eps);b,raw,mv=zs(Q)
 return {'zero_frac':float(np.mean(Q==0)),'H0':H(Q),'stream_bytes':b,'raw_zstd':raw,'maskval_zstd':mv,'model_bytes':int(model_bytes),'total_bytes':int(b+model_bytes),'maxerr':float(np.max(np.abs(Y-rec)))}
def grids(kind):
 if kind=='x':
  I=np.arange(1,62,2);J=np.arange(0,64,2);Y=X[I[:,None],J[None,:],:].copy();L=R[(I-1)[:,None],J[None,:],:].copy();RR=R[(I+1)[:,None],J[None,:],:].copy()
 else:
  I=np.arange(0,64,2);J=np.arange(1,62,2);Y=X[I[:,None],J[None,:],:].copy();L=R[I[:,None],(J-1)[None,:],:].copy();RR=R[I[:,None],(J+1)[None,:],:].copy()
 return Y,L,RR

def fit_tile(Y,L,RR,sl0,sl1,radius,use_diff):
 ys=Y[sl0,sl1];ls=L[sl0,sl1];rs=RR[sl0,sl1];ntr=ys.shape[0]*ys.shape[1];N=512;valid=np.arange(radius,N-radius);cols=[]
 for k in range(-radius,radius+1):
  cols.append((.5*(ls[...,valid+k]+rs[...,valid+k])).reshape(-1).astype(np.float64))
  if use_diff:cols.append((.5*(rs[...,valid+k]-ls[...,valid+k])).reshape(-1).astype(np.float64))
 cols.append(np.ones(ntr*len(valid)));A=np.stack(cols,1);yy=ys[...,valid].reshape(-1).astype(np.float64);G=A.T@A;rhs=A.T@yy;reg=1e-8*(np.trace(G)/G.shape[0])*np.eye(G.shape[0]);reg[-1,-1]=0
 try:w=np.linalg.solve(G+reg,rhs)
 except np.linalg.LinAlgError:w=np.linalg.lstsq(A,yy,rcond=1e-8)[0]
 w=w.astype(np.float32)
 # Exact decoder-like float32 reconstruction for interior; simple average for temporal edge samples.
 Af=A.astype(np.float32);pred=(Af@w).reshape(ys.shape[0],ys.shape[1],-1);P=.5*(ls+rs);P[...,valid]=pred
 return P,w

def run(kind,tile,radius,use_diff):
 Y,L,RR=grids(kind);P=np.empty_like(Y);coeff=[]
 for a in range(0,Y.shape[0],tile):
  for b in range(0,Y.shape[1],tile):
   sl0=slice(a,min(a+tile,Y.shape[0]));sl1=slice(b,min(b+tile,Y.shape[1]));pp,w=fit_tile(Y,L,RR,sl0,sl1,radius,use_diff);P[sl0,sl1]=pp;coeff.append(w)
 coeff_count=sum(len(w) for w in coeff);model_bytes=4*coeff_count+64
 # One global scalar phase is unnecessary because each tile already contains a bias. Still test a decoder-transmitted global offset to optimize lattice phase.
 best=None
 for frac in np.linspace(-.5,.5,17):
  m=qmetric(Y,P+np.float32(frac*eps),model_bytes+4);m['phase_frac_eps']=float(frac)
  if best is None or m['total_bytes']<best['total_bytes']:best=m
 return {'kind':kind,'tile':tile,'radius':radius,'use_diff':use_diff,'tiles':len(coeff),'coeff_count':coeff_count,'best':best}
rows=[]
for kind in ['x','y']:
 for tile in [2,4,8,16,32]:
  for radius in [2,4,6,8,12]:
   for d in [False,True]:
    r=run(kind,tile,radius,d);rows.append(r);print('LOCAL',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['best']['total_bytes']);json.dump({'eps':eps,'rows':rows},open('forge_timefirst_local_filter_results.json','w'),indent=2)
print('BEST',json.dumps(rows[:30],indent=2),flush=True)
