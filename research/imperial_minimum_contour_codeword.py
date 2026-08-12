import json, math, sys
import h5py, numpy as np, zstandard as zstd
from scipy.optimize import milp, LinearConstraint, Bounds
from scipy.sparse import lil_matrix
from pysz import sz, szConfig, szErrorBoundMode

NC=32; NT=64; SAFETY=1-1e-5
PHASES=(0.0,0.5)
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()


def stats(d):
    s=ss=0.0; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.0,ss/n-m*m)))


def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32))
        cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg); R,_=sz.decompress(b,np.float32,A.shape)
        me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6): raise RuntimeError(('sz bound',me,eps))
        row=(int(b.size),'T' if tr else 'CT',me)
        if best is None or row[0]<best[0]: best=row
    return best


def legal_bounds(X,bound,h,phi):
    lo=np.ceil((X-bound-phi)/h-1e-12).astype(np.int32)
    hi=np.floor((X+bound-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi): raise RuntimeError('empty legal set')
    q0=np.rint((X-phi)/h).astype(np.int32)
    q0=np.minimum(np.maximum(q0,lo),hi)
    return lo,hi,q0


def solve_min_contour(lo,hi,q0):
    # Integer q per sample. Binary z per horizontal/vertical edge marks a label
    # transition. Continuous d gives an infinitesimal tie-break on transition
    # magnitude. Primary objective is the exact number of contour edges.
    n=NC*NT
    edges=[]
    def qi(c,t): return c*NT+t
    for c in range(NC):
        for t in range(NT-1): edges.append((qi(c,t),qi(c,t+1),(c,t),(c,t+1),'t'))
    for c in range(NC-1):
        for t in range(NT): edges.append((qi(c,t),qi(c+1,t),(c,t),(c+1,t),'x'))
    m=len(edges); zoff=n; doff=n+m; N=n+2*m
    obj=np.zeros(N,np.float64); obj[zoff:zoff+m]=1.0; obj[doff:]=1e-8
    integ=np.zeros(N,np.int32); integ[:n]=1; integ[zoff:zoff+m]=1
    lb=np.concatenate([lo.ravel().astype(np.float64),np.zeros(m),np.zeros(m)])
    ub=np.concatenate([hi.ravel().astype(np.float64),np.ones(m),np.full(m,np.inf)])
    A=lil_matrix((4*m,N),dtype=np.float64); cl=np.full(4*m,-np.inf); cu=np.zeros(4*m)
    r=0
    for k,(u,v,pu,pv,axis) in enumerate(edges):
        cu0,tu=pu; cv0,tv=pv
        mn=float(lo[cu0,tu]-hi[cv0,tv]); mx=float(hi[cu0,tu]-lo[cv0,tv]); M=max(abs(mn),abs(mx),1.0)
        A[r,u]=1; A[r,v]=-1; A[r,zoff+k]=-M; r+=1
        A[r,u]=-1; A[r,v]=1; A[r,zoff+k]=-M; r+=1
        A[r,u]=1; A[r,v]=-1; A[r,doff+k]=-1; r+=1
        A[r,u]=-1; A[r,v]=1; A[r,doff+k]=-1; r+=1
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A.tocsr(),cl,cu),
             options={'time_limit':35.0,'mip_rel_gap':0.0,'presolve':True})
    solved=bool(res.x is not None and np.all(np.isfinite(res.x[:n])))
    q=q0.copy() if not solved else np.rint(res.x[:n]).astype(np.int32).reshape(NC,NT)
    if np.any(q<lo) or np.any(q>hi): raise RuntimeError('optimized q outside legal set')
    gap=getattr(res,'mip_gap',None); gap=float(gap) if gap is not None and np.isfinite(gap) else None
    return q,solved,int(getattr(res,'status',-1)),gap


def dtype_for(a):
    a=np.asarray(a); mn=int(a.min()) if a.size else 0; mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max: return dt
    return np.dtype('<i8')


def seqs(q):
    yield 'row', q.ravel()
    yield 'col', q.T.ravel()
    a=q.copy()
    a[1::2]=a[1::2,::-1]
    yield 'row_snake', a.ravel()
    b=q.T.copy()
    b[1::2]=b[1::2,::-1]
    yield 'col_snake', b.ravel()


def encode_seq(name,s):
    s=np.asarray(s,np.int32)
    d=np.empty_like(s); d[0]=s[0]; d[1:]=s[1:]-s[:-1]
    dt=dtype_for(d); blob=ZC.compress(d.astype(dt).tobytes())
    dd=np.frombuffer(ZD.decompress(blob),dtype=dt,count=d.size).astype(np.int32)
    rr=np.cumsum(dd,dtype=np.int32)
    if not np.array_equal(rr,s): raise RuntimeError('seq roundtrip')
    return len(blob)+24, name+'_delta_'+dt.str


def encode_q(q):
    cands=[]
    dt=dtype_for(q); raw=ZC.compress(np.ascontiguousarray(q).astype(dt).tobytes())
    rr=np.frombuffer(ZD.decompress(raw),dtype=dt,count=q.size).astype(np.int32).reshape(q.shape)
    if not np.array_equal(rr,q): raise RuntimeError('raw roundtrip')
    cands.append((len(raw)+24,'raw_'+dt.str))
    for name,s in seqs(q): cands.append(encode_seq(name,s))
    return min(cands)


def entropy(a):
    _,cnt=np.unique(np.asarray(a).ravel(),return_counts=True); p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def metrics(q):
    dt=q[:,1:]!=q[:,:-1]; dx=q[1:,:]!=q[:-1,:]
    return {'temporal_transition_fraction':float(np.mean(dt)),
            'spatial_transition_fraction':float(np.mean(dx)),
            'all_edge_transition_fraction':float((dt.sum()+dx.sum())/(dt.size+dx.size)),
            'state_entropy_bps':entropy(q),
            'unique_states':int(np.unique(q).size)}


def evaluate(X,eps,phase_frac):
    bound=eps*SAFETY; h=bound; phi=phase_frac*h
    lo,hi,q0=legal_bounds(X,bound,h,phi)
    q,solved,status,gap=solve_min_contour(lo,hi,q0)
    out=[]
    for kind,qq in [('nearest',q0),('min_contour',q)]:
        enc=encode_q(qq); R=phi+h*qq.astype(np.float64); me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6): raise RuntimeError(('hard error',kind,me,eps))
        r={'kind':kind,'bytes':enc[0],'rep':enc[1],'bps':8*enc[0]/X.size,'maxerr':me,
           'mean_legal_states':float(np.mean(hi-lo+1))}; r.update(metrics(qq)); out.append(r)
    return out,{'solver_returned_solution':solved,'solver_status':status,'solver_mip_gap':gap,'phase_fraction':phase_frac}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,std=stats(d); eps=.1*std; rows=[]; tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T; sb=szrun(X,eps)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/X.size,'local_std':float(X.std())})
            for ph in PHASES:
                rr,sol=evaluate(X,eps,ph)
                for r in rr:
                    r.update({'tile':name,'t0':t0,'c0':c0,'phase_fraction':ph,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes']}); r.update(sol); rows.append(r)
                print(json.dumps({'tile':name,'phase':ph,'sz3_bps':8*sb[0]/X.size,'rows':rr,'solver':sol}),flush=True)
        combos=[]
        for ph in PHASES:
            for kind in ('nearest','min_contour'):
                rr=[r for r in rows if r['phase_fraction']==ph and r['kind']==kind]
                b=sum(r['bytes'] for r in rr); s=sum(t['sz3_bytes'] for t in tiles); n=NC*NT*len(rr)
                combos.append({'phase_fraction':ph,'kind':kind,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,
                               'median_edge_transition_fraction':float(np.median([r['all_edge_transition_fraction'] for r in rr])),
                               'median_state_entropy_bps':float(np.median([r['state_entropy_bps'] for r in rr])),
                               'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),
                               'solver_solution_fraction':float(np.mean([r['solver_returned_solution'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes'])
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'specs':[list(x) for x in SPECS],'phases':list(PHASES),'tiles':tiles,'combos':combos,'rows':rows,
             'scope':'Global minimum-contour legal codeword screen. Every source sample is only an L-infinity interval. One MILP jointly chooses all legal lattice states to minimize the exact count of unequal horizontal/vertical neighbor labels, with infinitesimal total-variation magnitude tie-break. The resulting field is actually serialized through raw or fixed row/column/snake delta traversals with Zstd, byte-decoded and hard-error verified. Nearest legal states and matched SZ3 are rerun on identical hard/easy/medium/far 32x64 patches. Patch screen only; no whole-array claim.'}
        print(json.dumps({'combos':combos},indent=2),flush=True); json.dump(out,open('imperial_minimum_contour_codeword.json','w'),indent=2)

if __name__=='__main__': main(sys.argv[1])
