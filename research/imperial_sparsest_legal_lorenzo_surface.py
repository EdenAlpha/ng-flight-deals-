import json,math,sys
import h5py,numpy as np,zstandard as zstd
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix
from pysz import sz,szConfig,szErrorBoundMode

NC=16;NT=64;SAFETY=1-1e-5
PHASES=(0.0,0.5)
SPECS=(
 ('hard0',14464,512),
 ('hard1',14464,640),
 ('easy0',14464,2304),
 ('easy1',14464,2560),
 ('medium',14464,4608),
 ('far',14464,6880),
)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()


def stats(d):
    s=ss=0.0;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.0,ss/n-m*m)))


def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32))
        cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape)
        me=float(np.max(np.abs(A-R)))
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


def lor_encode(q):
    q=np.asarray(q,np.int32)
    L=q.copy()
    L[0,1:]=q[0,1:]-q[0,:-1]
    L[1:,0]=q[1:,0]-q[:-1,0]
    L[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1]
    cands=[]
    dt=dtype_for(L);blob=ZC.compress(np.ascontiguousarray(L).astype(dt).tobytes())
    rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=L.size).astype(np.int32).reshape(L.shape)
    dec=np.cumsum(np.cumsum(rr,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
    if not np.array_equal(dec,q):raise RuntimeError('lor raw roundtrip')
    cands.append((len(blob)+40,'lor_raw_'+dt.str))
    nz=L!=0;sup=ZC.compress(np.packbits(nz.astype(np.uint8).ravel(),bitorder='little').tobytes());vals=L[nz];vdt=dtype_for(vals);vb=ZC.compress(vals.astype(vdt).tobytes()) if vals.size else b''
    mask=np.unpackbits(np.frombuffer(ZD.decompress(sup),np.uint8),bitorder='little')[:L.size].astype(bool).reshape(L.shape)
    vv=np.frombuffer(ZD.decompress(vb),dtype=vdt).astype(np.int32) if vals.size else np.empty(0,np.int32)
    LL=np.zeros_like(L);LL[mask]=vv;dec=np.cumsum(np.cumsum(LL,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
    if not np.array_equal(dec,q):raise RuntimeError('lor sparse roundtrip')
    cands.append((len(sup)+len(vb)+72,'lor_sparse_'+vdt.str))
    return min(cands),L


def legal_bounds(X,bound,h,phi):
    lo=np.ceil((X-bound-phi)/h-1e-12).astype(np.int32)
    hi=np.floor((X+bound-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    q0=np.rint((X-phi)/h).astype(np.int32)
    q0=np.minimum(np.maximum(q0,lo),hi)
    return lo,hi,q0


def solve_sparsest(lo,hi,q0):
    # Variables: integer q for every sample, binary z for every interior Lorenzo
    # innovation, continuous d >= |innovation|. Objective is lexicographic in
    # practice: one nonzero costs 1.0; all magnitude terms together are <~1e-3.
    n=NC*NT;m=(NC-1)*(NT-1)
    qoff=0;zoff=n;doff=n+m;N=n+2*m
    obj=np.zeros(N,np.float64);obj[zoff:zoff+m]=1.0;obj[doff:]=1e-8
    integ=np.zeros(N,np.int32);integ[:n]=1;integ[zoff:zoff+m]=1
    lb=np.concatenate([lo.ravel().astype(np.float64),np.zeros(m),np.zeros(m)])
    ub=np.concatenate([hi.ravel().astype(np.float64),np.ones(m),np.full(m,np.inf)])
    A=lil_matrix((4*m,N),dtype=np.float64);cl=np.full(4*m,-np.inf);cu=np.zeros(4*m)
    r=0;k=0
    def qi(c,t):return c*NT+t
    for c in range(1,NC):
        for t in range(1,NT):
            inds=(qi(c,t),qi(c-1,t),qi(c,t-1),qi(c-1,t-1));coef=(1.0,-1.0,-1.0,1.0)
            # Tight natural big-M from this sample quartet's legal state ranges.
            mn=float(lo[c,t]-hi[c-1,t]-hi[c,t-1]+lo[c-1,t-1])
            mx=float(hi[c,t]-lo[c-1,t]-lo[c,t-1]+hi[c-1,t-1])
            M=max(abs(mn),abs(mx),1.0)
            # innovation - M z <= 0; -innovation - M z <= 0
            for j,a in zip(inds,coef):A[r,j]=a
            A[r,zoff+k]=-M;r+=1
            for j,a in zip(inds,coef):A[r,j]=-a
            A[r,zoff+k]=-M;r+=1
            # innovation - d <= 0; -innovation - d <= 0
            for j,a in zip(inds,coef):A[r,j]=a
            A[r,doff+k]=-1.0;r+=1
            for j,a in zip(inds,coef):A[r,j]=-a
            A[r,doff+k]=-1.0;r+=1
            k+=1
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A.tocsr(),cl,cu),
             options={'time_limit':25.0,'mip_rel_gap':0.0,'presolve':True})
    solved=bool(res.x is not None and np.all(np.isfinite(res.x[:n])))
    q=q0.copy() if not solved else np.rint(res.x[:n]).astype(np.int32).reshape(NC,NT)
    if np.any(q<lo)|np.any(q>hi):raise RuntimeError('optimized q outside legal set')
    status=int(getattr(res,'status',-1));gap=getattr(res,'mip_gap',None)
    gap=float(gap) if gap is not None and np.isfinite(gap) else None
    return q,solved,status,gap


def entropy(a):
    _,cnt=np.unique(np.asarray(a).ravel(),return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def evaluate(X,eps,phase_frac):
    bound=eps*SAFETY;h=bound;phi=phase_frac*h
    lo,hi,q0=legal_bounds(X,bound,h,phi)
    q,solved,status,gap=solve_sparsest(lo,hi,q0)
    out=[]
    for name,qq in [('nearest',q0),('sparsest',q)]:
        enc,L=lor_encode(qq);R=phi+h*qq.astype(np.float64);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('hard error',name,me,eps))
        interior=L[1:,1:]
        out.append({'kind':name,'bytes':enc[0],'rep':enc[1],'bps':8*enc[0]/X.size,'maxerr':me,
                    'interior_nonzero_fraction':float(np.mean(interior!=0)),'interior_abs1_fraction':float(np.mean(np.abs(interior)==1)),
                    'lorenzo_entropy_bps':entropy(L),'mean_legal_states':float(np.mean(hi-lo+1))})
    return out,{'solver_returned_solution':solved,'solver_status':status,'solver_mip_gap':gap,'phase_fraction':phase_frac}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;sb=szrun(X,eps)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/X.size,'local_std':float(X.std())})
            for ph in PHASES:
                rr,sol=evaluate(X,eps,ph)
                by={x['kind']:x for x in rr}
                for r in rr:
                    r.update({'tile':name,'t0':t0,'c0':c0,'phase_fraction':ph,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes']})
                    r.update(sol);rows.append(r)
                print(json.dumps({'tile':name,'phase':ph,'sz3_bps':8*sb[0]/X.size,'nearest':by['nearest'],'sparsest':by['sparsest'],'solver':sol}),flush=True)
        combos=[]
        for ph in PHASES:
            for kind in ('nearest','sparsest'):
                rr=[r for r in rows if r['phase_fraction']==ph and r['kind']==kind]
                b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=NC*NT*len(rr)
                combos.append({'phase_fraction':ph,'kind':kind,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,
                               'median_interior_nonzero':float(np.median([r['interior_nonzero_fraction'] for r in rr])),
                               'median_lorenzo_entropy':float(np.median([r['lorenzo_entropy_bps'] for r in rr])),
                               'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'solver_solution_fraction':float(np.mean([r['solver_returned_solution'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes'])
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'specs':[list(x) for x in SPECS],'phases':list(PHASES),'tiles':tiles,'combos':combos,'rows':rows,
             'scope':'Global legal-surface synthesis screen. Each sample is only an interval constraint. With lattice spacing ~=epsilon, one MILP chooses every legal reconstruction state jointly to minimize the exact count of nonzero 2-D Lorenzo mixed-second-difference innovations, with an infinitesimal secondary L1 magnitude objective. The selected state field is actually serialized through an exact double-cumulative Lorenzo frame (raw or sparse Zstd), byte-decoded, and hard-error verified. Nearest legal states and matched SZ3 are rerun on the identical six 16x64 patches. This is a patch screen, not a whole-file claim.'}
        print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_sparsest_legal_lorenzo_surface.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
