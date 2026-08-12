import json,sys,math
import h5py,numpy as np
from scipy.optimize import linprog
from scipy.sparse import csr_matrix,vstack,hstack,eye

NC=8;NT=32;SAFETY=1-2e-5
SLOPES=(-4.0,-3.0,-2.0,-1.5,-1.0,-0.75,-0.5,-0.25,0.25,0.5,0.75,1.0,1.5,2.0,3.0,4.0)
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))
ROUNDS=7;DELTA=0.03

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def dictionary():
    cols=[];meta=[]
    for slope in SLOPES:
        us=[t-slope*c for c in range(NC) for t in range(NT)]
        for tau in range(int(math.floor(min(us))),int(math.ceil(max(us)))+1):
            v=np.zeros((NC,NT),np.float64)
            for c in range(NC):
                for t in range(NT):
                    u=t-slope*c;w=max(0.0,1.0-abs(u-tau))
                    if w:v[c,t]=w
            if np.any(v):cols.append(v.ravel());meta.append((slope,tau))
    D=np.asarray(cols,np.float64).T
    return D,meta,int(np.linalg.matrix_rank(D,tol=1e-10))

def solve(X,eps,D,meta):
    n=X.size;p=D.shape[1];x=X.ravel()/eps;bd=SAFETY;lo=x-bd;hi=x+bd
    Ds=csr_matrix(D);I=eye(p,format='csr');Z=csr_matrix((n,p))
    # variables [a signed, u>=|a|]. Reconstruction bounds are represented as A_ub.
    A=vstack([
        hstack([ Ds,csr_matrix((n,p))]),
        hstack([-Ds,csr_matrix((n,p))]),
        hstack([ I,-I]),
        hstack([-I,-I]),
    ],format='csr')
    b=np.concatenate([hi,-lo,np.zeros(p),np.zeros(p)])
    bounds=[(None,None)]*p+[(0,None)]*p
    w=np.ones(p,np.float64);history=[];a=None
    for it in range(ROUNDS):
        c=np.concatenate([np.zeros(p),w])
        res=linprog(c,A_ub=A,b_ub=b,bounds=bounds,method='highs')
        if not res.success:raise RuntimeError(('LP failed',it,res.status,res.message))
        a=np.asarray(res.x[:p]);R=(D@a).reshape(X.shape)*eps;me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-5):raise RuntimeError(('hard error',it,me,eps))
        abs_a=np.abs(a);thresholds={str(th):int(np.sum(abs_a>th)) for th in (1e-6,.01,.03,.1,.3,1.0)}
        history.append({'round':it,'weighted_l1':float(res.fun),'l1_eps_units':float(abs_a.sum()),'support_thresholds_eps_units':thresholds,'maxerr':me})
        nw=1.0/(abs_a+DELTA);nw/=np.median(nw);w=nw
    abs_a=np.abs(a);support=np.flatnonzero(abs_a>.03);hist={str(s):0 for s in SLOPES}
    for j in support:hist[str(meta[int(j)][0])]+=1
    # Effective concentration: number of largest atoms needed for 90/95/99% coefficient L1 mass.
    ss=np.sort(abs_a)[::-1];cs=np.cumsum(ss);tot=float(cs[-1]) if cs.size else 0.
    def nfrac(fr):return int(np.searchsorted(cs,fr*tot)+1) if tot>0 else 0
    return {'atoms':p,'active_atoms_gt_0p03eps':int(support.size),'active_fraction_vs_samples':float(support.size/n),
            'atoms_for_90pct_l1':nfrac(.90),'atoms_for_95pct_l1':nfrac(.95),'atoms_for_99pct_l1':nfrac(.99),
            'maxerr':history[-1]['maxerr'],'maxerr_over_eps':history[-1]['maxerr']/eps,'l1_eps_units':float(abs_a.sum()),
            'max_abs_coefficient_eps_units':float(abs_a.max()),'slope_support_histogram_gt_0p03eps':hist,'history':history}

def main(path):
    D,meta,rank=dictionary();print(json.dumps({'shape':list(D.shape),'rank':rank}),flush=True)
    if rank<NC*NT:raise RuntimeError(('dictionary rank',rank))
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;r=solve(X,eps,D,meta);r.update({'tile':name,'t0':t0,'c0':c0,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std())});rows.append(r);print(json.dumps({k:r[k] for k in r if k!='history'}),flush=True)
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'slopes_samples_per_channel':list(SLOPES),'dictionary_atoms':D.shape[1],'dictionary_rank':rank,'rounds':ROUNDS,'reweight_delta_eps_units':DELTA,'rows':rows,
             'aggregate':{'median_active_atoms_gt_0p03eps':float(np.median([r['active_atoms_gt_0p03eps'] for r in rows])),'median_active_fraction_vs_samples':float(np.median([r['active_fraction_vs_samples'] for r in rows])),'median_atoms_for_95pct_l1':float(np.median([r['atoms_for_95pct_l1'] for r in rows])),'max_atoms_for_95pct_l1':max(r['atoms_for_95pct_l1'] for r in rows)},
             'scope':'Bound-free characteristic-superposition audit. A dense, full-rank bidirectional traveling-wave dictionary spans slopes roughly corresponding to 500-8000 m/s. Each source patch is only its unchanged +/-10%-global-std box. Seven convex iteratively reweighted-L1 solves choose a legal synthesized wavefield while progressively penalizing weak characteristic amplitudes; no binary activation big-M is used and coefficient magnitudes are unbounded. Final samples are hard-error verified. This is a sparsity/atomic-norm diagnostic, not a byte-compression claim and not a proof of global L0 optimality.'}
        print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_reweighted_characteristic_atomic_norm.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
