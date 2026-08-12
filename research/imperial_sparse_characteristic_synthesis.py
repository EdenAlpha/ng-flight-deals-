import json,sys,math
import h5py,numpy as np
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import csr_matrix,vstack,eye

NC=8;NT=32;SAFETY=1-2e-5
# Samples/channel. With ~4 m channel spacing and ~2 ms sampling these correspond
# approximately to propagation speeds 4000,2000,1000,500 m/s in both directions.
SLOPES=(-4.0,-2.0,-1.0,-0.5,0.5,1.0,2.0,4.0)
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def dictionary():
    cols=[];meta=[]
    for slope in SLOPES:
        us=[t-slope*c for c in range(NC) for t in range(NT)]
        tmin=int(math.floor(min(us)));tmax=int(math.ceil(max(us)))
        for tau in range(tmin,tmax+1):
            v=np.zeros((NC,NT),np.float64)
            for c in range(NC):
                for t in range(NT):
                    u=t-slope*c;w=max(0.0,1.0-abs(u-tau))
                    if w:v[c,t]=w
            if np.any(v):cols.append(v.ravel());meta.append((slope,tau))
    D=np.asarray(cols,np.float64).T
    rank=int(np.linalg.matrix_rank(D,tol=1e-10))
    return D,meta,rank

def solve(X,eps,D,meta):
    # Normalize amplitudes by epsilon; the hard box becomes width ~2 in these units.
    x=X.ravel()/eps;bd=SAFETY
    lo=x-bd;hi=x+bd;n=X.size;p=D.shape[1]
    amp=max(8.0,8.0*float(np.max(np.abs(x)))+8.0)
    # variables [a_p continuous, y_p binary], |a_j| <= amp*y_j
    obj=np.concatenate([np.zeros(p),np.ones(p)])
    integ=np.concatenate([np.zeros(p,np.int32),np.ones(p,np.int32)])
    lb=np.concatenate([np.full(p,-amp),np.zeros(p)]);ub=np.concatenate([np.full(p,amp),np.ones(p)])
    Ds=csr_matrix(D)
    I=eye(p,format='csr')
    # Reconstruction box + coefficient activation links.
    A=vstack([
        csr_matrix(np.hstack([D,np.zeros((n,p))])),
        csr_matrix(np.hstack([np.eye(p),-amp*np.eye(p)])),
        csr_matrix(np.hstack([-np.eye(p),-amp*np.eye(p)])),
    ],format='csr')
    low=np.concatenate([lo,np.full(p,-np.inf),np.full(p,-np.inf)])
    high=np.concatenate([hi,np.zeros(p),np.zeros(p)])
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(A,low,high),
             options={'time_limit':40.0,'mip_rel_gap':0.0,'presolve':True})
    if res.x is None:
        return {'status':int(getattr(res,'status',-1)),'message':str(getattr(res,'message','no solution'))}
    a=np.asarray(res.x[:p]);y=np.rint(res.x[p:]).astype(np.int8);R=(D@a).reshape(X.shape)*eps
    me=float(np.max(np.abs(X-R)));support=np.flatnonzero(np.abs(a)>1e-7)
    # Numerical consistency: any nonzero coefficient must have its selector on.
    if np.any(y[support]!=1):raise RuntimeError('inactive nonzero coefficient')
    gap=getattr(res,'mip_gap',None);gap=float(gap) if gap is not None and np.isfinite(gap) else None
    hist={str(s):0 for s in SLOPES}
    for j in support:hist[str(meta[int(j)][0])]+=1
    nbits_id=math.ceil(math.log2(p))
    return {'status':int(getattr(res,'status',-1)),'message':str(getattr(res,'message','')),'mip_gap':gap,
            'atoms':p,'dictionary_rank':int(np.linalg.matrix_rank(D,tol=1e-10)),'active_atoms':int(support.size),'active_fraction_vs_samples':float(support.size/n),
            'maxerr':me,'maxerr_over_eps':me/eps,'slope_support_histogram':hist,'coefficient_l1_eps_units':float(np.sum(np.abs(a))),
            'optimistic_8bit_coeff_plus_id_bps':float(support.size*(8+nbits_id)/n),
            'optimistic_16bit_coeff_plus_id_bps':float(support.size*(16+nbits_id)/n),
            'coefficient_id_bits':nbits_id}

def main(path):
    D,meta,rank=dictionary();print(json.dumps({'dictionary_shape':list(D.shape),'rank':rank,'slopes':SLOPES}),flush=True)
    if rank<NC*NT:raise RuntimeError(('dictionary not full rank',rank,NC*NT))
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;r=solve(X,eps,D,meta);r.update({'tile':name,'t0':t0,'c0':c0,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std())})
            if 'maxerr' in r and r['maxerr']>eps*(1+5e-5):raise RuntimeError(('hard error',name,r['maxerr'],eps))
            rows.append(r);print(json.dumps(r),flush=True)
        ok=[r for r in rows if 'active_atoms' in r]
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'samples_per_patch':NC*NT,'slopes_samples_per_channel':list(SLOPES),
             'dictionary_atoms':D.shape[1],'dictionary_rank':rank,'rows':rows,
             'aggregate':{'median_active_atoms':float(np.median([r['active_atoms'] for r in ok])) if ok else None,
                          'median_active_fraction_vs_samples':float(np.median([r['active_fraction_vs_samples'] for r in ok])) if ok else None,
                          'max_active_atoms':max((r['active_atoms'] for r in ok),default=None),
                          'median_optimistic_16bit_plus_id_bps':float(np.median([r['optimistic_16bit_coeff_plus_id_bps'] for r in ok])) if ok else None},
             'scope':'Existence ceiling for sparse characteristic-wave synthesis. Each 8x32 target patch is only its unchanged +/-10%-global-std L-infinity box. A full-rank overcomplete dictionary contains bidirectional traveling characteristic sequences f(t-s*c) with linear half-sample interpolation for physically relevant slopes. One MILP globally selects the minimum number of nonzero characteristic amplitudes whose synthesized wavefield lies inside every source interval. This is NOT yet a compression claim: coefficient precision/entropy and a self-contained byte representation are not implemented. The 8/16-bit+ID rates are optimistic dimensional accounting only.'}
        print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_sparse_characteristic_synthesis.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
