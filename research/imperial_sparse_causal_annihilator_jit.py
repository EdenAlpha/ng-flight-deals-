import sys, numpy as np
from numba import njit
import imperial_sparse_causal_annihilator as m

@njit(cache=True)
def _recur(X,R,K,dtv,dcv,coeff,intercept,maxdt):
    nc,nt=X.shape
    for t in range(maxdt,nt):
        for c in range(nc):
            p=intercept
            for j in range(coeff.size):
                dt=dtv[j]; dc=dcv[j]; cc=c+dc
                if cc<0 or cc>=nc: continue
                p += coeff[j]*R[cc,t-dt]
            if p>200000.0: p=200000.0
            elif p< -200000.0: p=-200000.0
            pi=int(np.rint(p))
            k=int(np.rint((X[c,t]-pi)/m.STEP))
            K[c,t]=k; R[c,t]=pi+m.STEP*k

def encode_model_jit(X,offs,beta,eps,name):
    maxdt=max(dt for dt,dc in offs)
    R=np.empty_like(X,dtype=np.int64); K=np.zeros_like(X,dtype=np.int64)
    R[:,:maxdt]=(m.STEP*np.rint(X[:,:maxdt]/m.STEP)).astype(np.int64)
    if float(np.max(np.abs(X[:,:maxdt]-R[:,:maxdt])))>128.000001: raise RuntimeError('seed err')
    dtv=np.asarray([x[0] for x in offs],np.int64); dcv=np.asarray([x[1] for x in offs],np.int64)
    coeff=np.asarray(beta[1:],np.float64); intercept=float(np.float32(beta[0]))
    _recur(np.asarray(X,np.float64),R,K,dtv,dcv,coeff,intercept,maxdt)
    me=float(np.max(np.abs(X-R)))
    if me>128.000001 or me>eps: raise RuntimeError(('hard error',name,me,eps))
    seed_bytes,seed_rep=m.encode_array((R[:,:maxdt]//m.STEP).astype(np.int64))
    inv_bytes=0; reps={}
    for t0 in range(maxdt,m.NT,1024):
        t1=min(m.NT,t0+1024); b,rep=m.encode_array(K[:,t0:t1]); inv_bytes+=b; reps[rep]=reps.get(rep,0)+1
    model_bytes=32+4*len(beta)+2*len(offs); total=model_bytes+seed_bytes+inv_bytes
    return {'name':name,'bytes':int(total),'bps':8*total/X.size,'model_bytes':model_bytes,'seed_bytes':seed_bytes,
            'innovation_bytes':inv_bytes,'seed_rep':seed_rep,'innovation_reps':reps,'maxerr':me,'taps':len(offs),
            'offsets':[list(x) for x in offs],'coefficients':[float(x) for x in beta]}

m.encode_model=encode_model_jit
if __name__=='__main__': m.main(sys.argv[1])
