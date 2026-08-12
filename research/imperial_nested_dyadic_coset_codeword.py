import json,math,sys
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix
from pysz import sz,szConfig,szErrorBoundMode

NC=32;NT=64;H=128.0;SAFETY=1-1e-5
PHASES=(0.0,64.0)
PWEIGHTS=(0.25,1.0)
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()


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
  if me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
  row=(int(b.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def legal(X,eps,phase):
 b=eps*SAFETY
 lo=np.ceil((X-b-phase)/H-1e-12).astype(np.int32);hi=np.floor((X+b-phase)/H+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal')
 return lo,hi

def solve(lo,hi,pweight):
 n=NC*NT
 edges=[]
 def ii(c,t):return c*NT+t
 for c in range(NC):
  for t in range(NT-1):edges.append((ii(c,t),ii(c,t+1)))
 for c in range(NC-1):
  for t in range(NT):edges.append((ii(c,t),ii(c+1,t)))
 m=len(edges)
 # variables: B integer[n], p binary[n], zB binary[m], zP binary[m]
 bo=0;po=n;zbo=2*n;zpo=2*n+m;N=2*n+2*m
 obj=np.zeros(N,np.float64);obj[zbo:zbo+m]=1.0;obj[zpo:zpo+m]=pweight
 integ=np.zeros(N,np.int32);integ[bo:bo+n]=1;integ[po:po+n]=1;integ[zbo:zbo+m]=1;integ[zpo:zpo+m]=1
 blo=np.floor_divide(lo,2).astype(np.float64).ravel()-1;bhi=np.floor_divide(hi,2).astype(np.float64).ravel()+1
 lb=np.concatenate([blo,np.zeros(n),np.zeros(m),np.zeros(m)])
 ub=np.concatenate([bhi,np.ones(n),np.ones(m),np.ones(m)])
 # 2 constraints/sample for lo <= 2B+p <= hi; 4 constraints/edge.
 A=lil_matrix((2*n+4*m,N),dtype=np.float64);cl=np.full(2*n+4*m,-np.inf);cu=np.zeros(2*n+4*m)
 r=0
 lof=lo.ravel();hif=hi.ravel()
 for i in range(n):
  # 2B+p <= hi
  A[r,bo+i]=2;A[r,po+i]=1;cu[r]=float(hif[i]);r+=1
  # -(2B+p) <= -lo
  A[r,bo+i]=-2;A[r,po+i]=-1;cu[r]=float(-lof[i]);r+=1
 for k,(u,v) in enumerate(edges):
  # conservative tiny M from legal B range endpoints
  M=max(abs(blo[u]-bhi[v]),abs(bhi[u]-blo[v]),1.0)
  A[r,bo+u]=1;A[r,bo+v]=-1;A[r,zbo+k]=-M;r+=1
  A[r,bo+u]=-1;A[r,bo+v]=1;A[r,zbo+k]=-M;r+=1
  A[r,po+u]=1;A[r,po+v]=-1;A[r,zpo+k]=-1;r+=1
  A[r,po+u]=-1;A[r,po+v]=1;A[r,zpo+k]=-1;r+=1
 res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A.tocsr(),cl,cu),options={'time_limit':25.0,'mip_rel_gap':0.0,'presolve':True})
 if res.x is None:raise RuntimeError(('no MILP solution',getattr(res,'status',None)))
 B=np.rint(res.x[bo:bo+n]).astype(np.int32).reshape(NC,NT);p=np.rint(res.x[po:po+n]).astype(np.int32).reshape(NC,NT)
 q=2*B+p
 if np.any(q<lo)|np.any(q>hi):raise RuntimeError('illegal optimized state')
 gap=getattr(res,'mip_gap',None);gap=float(gap) if gap is not None and np.isfinite(gap) else None
 return B,p,q,int(getattr(res,'status',-1)),gap

def sdtype(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  z=np.iinfo(dt)
  if mn>=z.min and mx<=z.max:return dt
 raise RuntimeError((mn,mx))
def pack_B(B):
 c=[]
 for name,arr,inv in make_B_reps(B):
  dt=sdtype(arr);bb=Z.compress(np.ascontiguousarray(arr).astype(dt).tobytes());rr=np.frombuffer(D.decompress(bb),dt,count=arr.size).astype(np.int32).reshape(arr.shape);dec=inv(rr)
  if not np.array_equal(dec,B):raise RuntimeError(('B roundtrip',name))
  c.append((len(bb)+32,name+'_'+dt.str))
 return min(c)
def make_B_reps(B):
 yield 'raw',B.copy(),lambda r:r
 a=B.copy();a[:,1:]=B[:,1:]-B[:,:-1];yield 'dt',a,lambda r:np.cumsum(r,axis=1,dtype=np.int32)
 a=B.copy();a[1:]=B[1:]-B[:-1];yield 'ds',a,lambda r:np.cumsum(r,axis=0,dtype=np.int32)
 a=B.copy();a[1:,1:]=B[1:,1:]-B[:-1,1:]-B[1:,:-1]+B[:-1,:-1];a[0,1:]=B[0,1:]-B[0,:-1];a[1:,0]=B[1:,0]-B[:-1,0]
 yield 'lorenzo',a,lambda r:np.cumsum(np.cumsum(r,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
def pack_p(p):
 c=[]
 for name,a,undo in parity_reps(p):
  raw=np.packbits(a.astype(np.uint8).ravel(),bitorder='little').tobytes();bb=Z.compress(raw);bits=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:a.size].astype(np.int32).reshape(a.shape);dec=undo(bits)
  if not np.array_equal(dec,p):raise RuntimeError(('p roundtrip',name))
  c.append((len(bb)+32,name))
 return min(c)
def parity_reps(p):
 yield 'p_raw',p.copy(),lambda r:r
 a=p.copy();a[:,1:]=p[:,1:]^p[:,:-1]
 def ut(r):
  x=r.copy()
  for j in range(1,x.shape[1]):x[:,j]^=x[:,j-1]
  return x
 yield 'p_xort',a,ut
 a=p.copy();a[1:]=p[1:]^p[:-1]
 def us(r):
  x=r.copy()
  for i in range(1,x.shape[0]):x[i]^=x[i-1]
  return x
 yield 'p_xors',a,us

def edgefrac(a):
 dt=a[:,1:]!=a[:,:-1];ds=a[1:]!=a[:-1]
 return float((dt.sum()+ds.sum())/(dt.size+ds.size))
def evaluate(X,eps,phase,pw):
 lo,hi=legal(X,eps,phase);B,p,q,status,gap=solve(lo,hi,pw)
 bb=pack_B(B);pb=pack_p(p);total=bb[0]+pb[0]+56
 R=phase+H*q.astype(np.float64);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
 return {'bytes':total,'bps':8*total/X.size,'B_bytes':bb[0],'B_rep':bb[1],'p_bytes':pb[0],'p_rep':pb[1],'maxerr':me,'B_edge_fraction':edgefrac(B),'p_edge_fraction':edgefrac(p),'p_one_fraction':float(np.mean(p)),'mean_legal_states':float(np.mean(hi-lo+1)),'solver_status':status,'solver_gap':gap}

def nearest(X,eps,phase):
 lo,hi=legal(X,eps,phase);q=np.rint((X-phase)/H).astype(np.int32);q=np.minimum(np.maximum(q,lo),hi);B=np.floor_divide(q,2);p=q-2*B
 bb=pack_B(B);pb=pack_p(p);total=bb[0]+pb[0]+56;R=phase+H*q.astype(np.float64);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('nearest hard',me,eps))
 return {'bytes':total,'bps':8*total/X.size,'B_bytes':bb[0],'B_rep':bb[1],'p_bytes':pb[0],'p_rep':pb[1],'maxerr':me,'B_edge_fraction':edgefrac(B),'p_edge_fraction':edgefrac(p),'p_one_fraction':float(np.mean(p)),'mean_legal_states':float(np.mean(hi-lo+1))}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;tiles=[];rows=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;sb,ori=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size})
   for phase in PHASES:
    nr=nearest(X,eps,phase);nr.update({'tile':name,'phase':phase,'kind':'nearest','sz3_bytes':sb,'gain_vs_sz3':sb/nr['bytes']});rows.append(nr)
    for pw in PWEIGHTS:
     r=evaluate(X,eps,phase,pw);r.update({'tile':name,'phase':phase,'kind':'synth','pweight':pw,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes']});rows.append(r);print(json.dumps({'tile':name,'phase':phase,'pweight':pw,'result':r}),flush=True)
  combos=[]
  for phase in PHASES:
   for kind,pw in [('nearest',None)]+[('synth',x) for x in PWEIGHTS]:
    rr=[r for r in rows if r['phase']==phase and r['kind']==kind and (kind=='nearest' or r['pweight']==pw)]
    b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=NC*NT*len(rr)
    combos.append({'phase':phase,'kind':kind,'pweight':pw,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,'median_B_edge_fraction':float(np.median([r['B_edge_fraction'] for r in rr])),'median_p_edge_fraction':float(np.median([r['p_edge_fraction'] for r in rr])),'mean_p_bytes_fraction':float(sum(r['p_bytes'] for r in rr)/b),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes'])
  out={'std':std,'eps':eps,'fine_step':H,'coarse_step':256,'phases':list(PHASES),'pweights':list(PWEIGHTS),'patch_shape':[NC,NT],'specs':[list(x) for x in SPECS],'combos':combos,'rows':rows,'scope':'Nested dyadic/coset legal-codeword screen. Every sample is reconstructed on a 128-spaced dyadic grid, giving roughly 2-3 legal states under the unchanged 10%-global-std hard bound. State q is factored exactly as q=2B+p where B is a coarse 256-level symbol and p is a binary coset. One global MILP jointly chooses all legal states to minimize coarse B contour edges plus weighted parity contour edges. B and p are then actually serialized separately through decoder-real Zstd representations, byte-decoded, recombined, and hard-error verified. Two fixed 128-grid phases and two parity weights are frozen across hard/easy/medium/far 32x64 patches; matched SZ3 is rerun identically. Patch screen only, no whole-array claim. No AI.'}
  print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_nested_dyadic_coset_codeword.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
