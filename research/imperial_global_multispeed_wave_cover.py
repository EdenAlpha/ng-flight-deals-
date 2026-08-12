import json,sys,math
import h5py,numpy as np
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix,vstack

NC=12;NT=40;SAFETY=1-1e-5;PHASE_FRAC=.5;B=4
# lambda=A/B = 0,.25,.5,.75,1,1.25,1.5
AS=(0,1,2,3,4,5,6)
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def legal(X,eps):
    bd=eps*SAFETY;h=bd;phi=PHASE_FRAC*h
    lo=np.ceil((X-bd-phi)/h-1e-12).astype(np.int32)
    hi=np.floor((X+bd-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    q0=np.rint((X-phi)/h).astype(np.int32);q0=np.minimum(np.maximum(q0,lo),hi)
    return lo,hi,q0,h,phi

def d_coeff(A):
    # B*q_tt - A*q_xx at (c,t)
    return (B,(-2*B+2*A),B,-A,-A)

def d_bounds(A,c,t,lo,hi):
    inds=((c,t+1),(c,t),(c,t-1),(c+1,t),(c-1,t));co=d_coeff(A)
    mn=mx=0.
    for k,(cc,tt) in zip(co,inds):
        if k>=0:mn+=k*lo[cc,tt];mx+=k*hi[cc,tt]
        else:mn+=k*hi[cc,tt];mx+=k*lo[cc,tt]
    return mn,mx

def nearest_union_coverage(q):
    covered=0;hist={A:0 for A in AS};m=(NC-2)*(NT-2)
    for c in range(1,NC-1):
        for t in range(1,NT-1):
            vals=[]
            qtt=int(q[c,t+1]-2*q[c,t]+q[c,t-1]);qxx=int(q[c+1,t]-2*q[c,t]+q[c-1,t])
            for A in AS:
                if B*qtt-A*qxx==0:vals.append(A)
            if vals:
                covered+=1;hist[min(vals,key=lambda A:abs(A-B))]+=1
    return covered/m,hist

def solve(lo,hi,q0):
    n=NC*NT;m=(NC-2)*(NT-2);K=len(AS)
    qoff=0;yoff=n;zoff=n+m*K;N=n+m*K+m
    # Lexicographic in scale: each exception costs 1.0. All mode tie-break costs summed <0.01.
    obj=np.zeros(N,np.float64);obj[zoff:]=1.0
    for s in range(m):
        for ki,A in enumerate(AS):obj[yoff+s*K+ki]=1e-6*abs(A-B)
    integ=np.ones(N,np.int32)
    lb=np.concatenate([lo.ravel().astype(float),np.zeros(m*K+m)])
    ub=np.concatenate([hi.ravel().astype(float),np.ones(m*K+m)])
    # 2 constraints per (site,mode): y=1 => D_A=0.
    Aineq=lil_matrix((2*m*K,N),dtype=float);cub=np.empty(2*m*K,float);clb=np.full(2*m*K,-np.inf);r=0;s=0
    def qi(c,t):return c*NT+t
    for c in range(1,NC-1):
        for t in range(1,NT-1):
            inds=((c,t+1),(c,t),(c,t-1),(c+1,t),(c-1,t))
            for ki,A in enumerate(AS):
                co=d_coeff(A);mn,mx=d_bounds(A,c,t,lo,hi);M=max(abs(mn),abs(mx),1.)
                # D + M*y <= M ; -D + M*y <= M
                for kk,(cc,tt) in zip(co,inds):Aineq[r,qi(cc,tt)]=kk
                Aineq[r,yoff+s*K+ki]=M;cub[r]=M;r+=1
                for kk,(cc,tt) in zip(co,inds):Aineq[r,qi(cc,tt)]=-kk
                Aineq[r,yoff+s*K+ki]=M;cub[r]=M;r+=1
            s+=1
    # Exactly one explanation per interior point: one source-free speed OR exception.
    Aeq=lil_matrix((m,N),dtype=float);s=0
    for c in range(1,NC-1):
        for t in range(1,NT-1):
            for ki in range(K):Aeq[s,yoff+s*K+ki]=1.0
            Aeq[s,zoff+s]=1.0;s+=1
    Aall=vstack([Aineq.tocsr(),Aeq.tocsr()],format='csr')
    low=np.concatenate([clb,np.ones(m)]);high=np.concatenate([cub,np.ones(m)])
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(Aall,low,high),
             options={'time_limit':35.0,'mip_rel_gap':0.0,'presolve':True})
    if res.x is None: return None,{'status':int(getattr(res,'status',-1)),'message':str(getattr(res,'message','no solution'))}
    q=np.rint(res.x[:n]).astype(np.int32).reshape(NC,NT)
    Y=np.rint(res.x[yoff:zoff]).astype(np.int8).reshape(m,K);z=np.rint(res.x[zoff:]).astype(np.int8)
    if np.any(q<lo)|np.any(q>hi):raise RuntimeError('q outside legal')
    if np.any(Y.sum(axis=1)+z!=1):raise RuntimeError('explanation assignment')
    # Verify every active mode is exactly source-free on the integer solution.
    modehist={A:0 for A in AS};si=0;viol=0
    for c in range(1,NC-1):
        for t in range(1,NT-1):
            qtt=int(q[c,t+1]-2*q[c,t]+q[c,t-1]);qxx=int(q[c+1,t]-2*q[c,t]+q[c-1,t])
            ks=np.flatnonzero(Y[si])
            if ks.size:
                A=AS[int(ks[0])];modehist[A]+=1
                if B*qtt-A*qxx!=0:viol+=1
            si+=1
    if viol:raise RuntimeError(('active mode violation',viol))
    gap=getattr(res,'mip_gap',None);gap=float(gap) if gap is not None and np.isfinite(gap) else None
    return q,{'status':int(getattr(res,'status',-1)),'message':str(getattr(res,'message','')),'mip_gap':gap,
              'exception_fraction':float(np.mean(z)),'source_free_fraction':float(1-np.mean(z)),'exceptions':int(z.sum()),'sites':m,
              'mode_histogram':{str(A):int(modehist[A]) for A in AS},'objective':float(res.fun)}

def entropy_hist(h):
    n=np.asarray(list(h.values()),float);n=n[n>0]
    if not n.size:return 0.
    p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;lo,hi,q0,h,phi=legal(X,eps)
            nearcov,nearhist=nearest_union_coverage(q0)
            q,info=solve(lo,hi,q0)
            row={'tile':name,'t0':t0,'c0':c0,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std()),
                 'nearest_union_source_free_fraction':nearcov,'nearest_mode_histogram':{str(k):int(v) for k,v in nearhist.items()},
                 'mean_legal_states':float(np.mean(hi-lo+1))}
            row.update(info)
            if q is not None:
                me=float(np.max(np.abs(X-(phi+h*q.astype(float)))))
                if me>eps*(1+5e-6):raise RuntimeError(('hard error',name,me,eps))
                row['maxerr']=me;row['mode_entropy_bits_per_covered_site']=entropy_hist({int(k):v for k,v in info['mode_histogram'].items()})
            rows.append(row);print(json.dumps(row),flush=True)
        solved=[r for r in rows if 'source_free_fraction' in r]
        out={'std':std,'eps':eps,'patch_shape':[NC,NT],'B':B,'A_values':list(AS),'lambdas':[A/B for A in AS],
             'rows':rows,'aggregate':{'mean_source_free_fraction':float(np.mean([r['source_free_fraction'] for r in solved])) if solved else None,
                                     'median_source_free_fraction':float(np.median([r['source_free_fraction'] for r in solved])) if solved else None,
                                     'min_source_free_fraction':min((r['source_free_fraction'] for r in solved),default=None),
                                     'mean_nearest_union_source_free_fraction':float(np.mean([r['nearest_union_source_free_fraction'] for r in rows]))},
             'scope':'Existence ceiling for switching local wave physics. Every sample is an integer reconstruction variable constrained only by its unchanged +/-10%-global-std interval. For each interior spacetime site, the solver may choose exactly one source-free discrete wave law B*q_tt=A*q_xx from lambda in {0,.25,.5,.75,1,1.25,1.5}, or mark that site as an exception. A global MILP minimizes exception count; tiny mode preference only breaks equal-coverage ties. No byte-compression claim. A solver solution is constructive; if mip_gap is nonzero it is an achieved lower bound on source-free coverage, not a proven optimum.'}
        print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_global_multispeed_wave_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
