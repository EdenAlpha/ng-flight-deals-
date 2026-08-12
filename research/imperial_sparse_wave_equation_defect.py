import json,sys,math
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix
from pysz import sz,szConfig,szErrorBoundMode

NC=32;NT=64;SAFETY=1-1e-5;PHASE_FRAC=.5
# lambda = a/b in q_tt = lambda * q_xx + defect/b
LAMBDAS=((0,1),(1,8),(1,4),(1,2),(1,1))
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))
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
        z=np.iinfo(dt)
        if mn>=z.min and mx<=z.max:return dt
    return np.dtype('<i8')

def legal(X,eps):
    b=eps*SAFETY;h=b;phi=PHASE_FRAC*h
    lo=np.ceil((X-b-phi)/h-1e-12).astype(np.int32);hi=np.floor((X+b-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    q=np.rint((X-phi)/h).astype(np.int32);q=np.minimum(np.maximum(q,lo),hi)
    return lo,hi,q,h,phi

def defect(q,a,b):
    q=np.asarray(q,np.int32)
    return (b*(q[1:-1,2:]-2*q[1:-1,1:-1]+q[1:-1,:-2]) - a*(q[2:,1:-1]-2*q[1:-1,1:-1]+q[:-2,1:-1])).astype(np.int32)

def lin_minmax(coeffs,inds,lo,hi):
    mn=mx=0.0
    for co,(c,t) in zip(coeffs,inds):
        if co>=0:mn+=co*lo[c,t];mx+=co*hi[c,t]
        else:mn+=co*hi[c,t];mx+=co*lo[c,t]
    return mn,mx

def solve_sparse(lo,hi,q0,a,b):
    n=NC*NT;m=(NC-2)*(NT-2);zoff=n;doff=n+m;N=n+2*m
    obj=np.zeros(N,np.float64);obj[zoff:zoff+m]=1.;obj[doff:]=1e-10
    integ=np.zeros(N,np.int32);integ[:n]=1;integ[zoff:zoff+m]=1
    lb=np.concatenate([lo.ravel().astype(float),np.zeros(m),np.zeros(m)]);ub=np.concatenate([hi.ravel().astype(float),np.ones(m),np.full(m,np.inf)])
    A=lil_matrix((4*m,N),dtype=float);cl=np.full(4*m,-np.inf);cu=np.zeros(4*m);r=0;k=0
    def qi(c,t):return c*NT+t
    for c in range(1,NC-1):
        for t in range(1,NT-1):
            inds=((c,t+1),(c,t),(c,t-1),(c+1,t),(c-1,t));coef=(b,-2*b+2*a,b,-a,-a)
            mn,mx=lin_minmax(coef,inds,lo,hi);M=max(abs(mn),abs(mx),1.)
            for j,co in zip(inds,coef):A[r,qi(*j)]=co
            A[r,zoff+k]=-M;r+=1
            for j,co in zip(inds,coef):A[r,qi(*j)]=-co
            A[r,zoff+k]=-M;r+=1
            for j,co in zip(inds,coef):A[r,qi(*j)]=co
            A[r,doff+k]=-1;r+=1
            for j,co in zip(inds,coef):A[r,qi(*j)]=-co
            A[r,doff+k]=-1;r+=1;k+=1
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A.tocsr(),cl,cu),options={'time_limit':18.,'mip_rel_gap':0.01,'presolve':True})
    solved=bool(res.x is not None and np.all(np.isfinite(res.x[:n])))
    q=q0.copy() if not solved else np.rint(res.x[:n]).astype(np.int32).reshape(NC,NT)
    if np.any(q<lo)|np.any(q>hi):raise RuntimeError('solution outside legal box')
    gap=getattr(res,'mip_gap',None);gap=float(gap) if gap is not None and np.isfinite(gap) else None
    return q,solved,int(getattr(res,'status',-1)),gap

def pack_array(a):
    a=np.asarray(a);dt=dtype_for(a);blob=ZC.compress(np.ascontiguousarray(a).astype(dt).tobytes());rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape)
    if not np.array_equal(rr,a.astype(np.int32)):raise RuntimeError('array roundtrip')
    return len(blob)+24,dt.str

def encode_defect(D):
    D=np.asarray(D,np.int32);c=[]
    rb,rdt=pack_array(D);c.append((rb,'raw_'+rdt))
    T=D.copy();T[:,1:]=D[:,1:]-D[:,:-1];tb,tdt=pack_array(T);c.append((tb+8,'time_delta_'+tdt))
    nz=D!=0;sup=ZC.compress(np.packbits(nz.ravel().astype(np.uint8),bitorder='little').tobytes());vals=D[nz];vdt=dtype_for(vals);vb=ZC.compress(vals.astype(vdt).tobytes()) if vals.size else b''
    mask=np.unpackbits(np.frombuffer(ZD.decompress(sup),np.uint8),bitorder='little')[:D.size].astype(bool).reshape(D.shape);vv=np.frombuffer(ZD.decompress(vb),dtype=vdt).astype(np.int32) if vals.size else np.empty(0,np.int32);RR=np.zeros_like(D);RR[mask]=vv
    if not np.array_equal(RR,D):raise RuntimeError('sparse defect roundtrip')
    c.append((len(sup)+len(vb)+56,'sparse_'+vdt.str))
    return min(c)

def encode_boundaries(q):
    v=np.concatenate([q[:,0],q[:,1],q[0,2:],q[-1,2:]]).astype(np.int32);return pack_array(v)

def decode_from_parts(q,D,a,b):
    # simulate what the decoder knows: two initial time slices + both spatial boundaries + D
    R=np.zeros_like(q,np.int32);R[:,0]=q[:,0];R[:,1]=q[:,1];R[0,2:]=q[0,2:];R[-1,2:]=q[-1,2:]
    for t in range(1,NT-1):
        lap=R[2:,t]-2*R[1:-1,t]+R[:-2,t];num=a*lap+D[:,t-1]
        if np.any(num % b):raise RuntimeError(('nondivisible recurrence',a,b,t))
        R[1:-1,t+1]=2*R[1:-1,t]-R[1:-1,t-1]+num//b
    return R

def entropy(a):
    _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def eval_q(X,eps,q,h,phi,a,b,kind,solved=True,status=0,gap=None):
    D=defect(q,a,b);bd=encode_boundaries(q);de=encode_defect(D);R=decode_from_parts(q,D,a,b)
    if not np.array_equal(R,q):raise RuntimeError(('PDE decode mismatch',kind,a,b))
    Y=phi+h*R.astype(np.float64);me=float(np.max(np.abs(X-Y)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
    total=bd[0]+de[0]+64
    return {'kind':kind,'lambda_num':a,'lambda_den':b,'lambda':a/b,'bytes':total,'bps':8*total/X.size,'boundary_bytes':bd[0],'boundary_rep':bd[1],'defect_bytes':de[0],'defect_rep':de[1],'defect_nonzero_fraction':float(np.mean(D!=0)),'defect_abs1_fraction':float(np.mean(np.abs(D)==1)),'defect_entropy_bps':entropy(D),'maxerr':me,'solver_returned_solution':solved,'solver_status':status,'solver_mip_gap':gap}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;tiles=[];rows=[]
        cache=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;sb=szrun(X,eps);lo,hi,q0,h,phi=legal(X,eps)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/X.size,'local_std':float(X.std())})
            cache.append((name,X,sb,lo,hi,q0,h,phi))
            for a,b in LAMBDAS:
                r=eval_q(X,eps,q0,h,phi,a,b,'nearest');r.update({'tile':name,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes']});rows.append(r)
        # Optimize every candidate. Same lambda is later aggregated across all four patches.
        for name,X,sb,lo,hi,q0,h,phi in cache:
            for a,b in LAMBDAS:
                q,ok,st,gap=solve_sparse(lo,hi,q0,a,b);r=eval_q(X,eps,q,h,phi,a,b,'sparsest',ok,st,gap);r.update({'tile':name,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes']});rows.append(r)
                print(json.dumps({'tile':name,'lambda':a/b,'kind':'sparsest','bps':r['bps'],'sz3_bps':8*sb[0]/X.size,'gain':r['gain_vs_sz3'],'nz':r['defect_nonzero_fraction'],'solver':ok}),flush=True)
        combos=[];n=NC*NT*len(SPECS);szsum=sum(x['sz3_bytes'] for x in tiles)
        for a,b in LAMBDAS:
            for kind in ('nearest','sparsest'):
                rr=[r for r in rows if r['lambda_num']==a and r['lambda_den']==b and r['kind']==kind];tot=sum(r['bytes'] for r in rr)
                combos.append({'lambda_num':a,'lambda_den':b,'lambda':a/b,'kind':kind,'bytes':tot,'sz3_bytes':szsum,'bps':8*tot/n,'gain_vs_sz3':szsum/tot,'median_defect_nonzero':float(np.median([r['defect_nonzero_fraction'] for r in rr])),'median_defect_entropy_bps':float(np.median([r['defect_entropy_bps'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'solver_solution_fraction':float(np.mean([r['solver_returned_solution'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes'])
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'phase_fraction':PHASE_FRAC,'lambdas':[list(x) for x in LAMBDAS],'tiles':tiles,'combos':combos,'rows':rows,'scope':'Physics-defect codec screen. Each sample is only an L-infinity hard-error interval. For each rational wave Courant factor lambda=a/b, a global MILP chooses every legal lattice state jointly to minimize the exact number of nonzero discrete wave-equation defects b*q_tt-a*q_xx. Decoder receives only two initial time slices, both spatial boundary traces, and the exact defect field; it regenerates all interior samples recursively. Boundary and defect streams are actually Zstd serialized/decoded and final samples are hard-error verified. lambda=0 is a temporal-curvature control; nonzero lambdas test true propagation structure. Matched SZ3 is rerun on identical patches. Exploratory patch screen, no whole-array claim.'}
        print(json.dumps({'best':combos[:10]},indent=2));json.dump(out,open('imperial_sparse_wave_equation_defect.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
