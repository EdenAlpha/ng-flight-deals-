import sys
import numpy as np
import imperial_gca_phase_policy_v2 as v

def fit_table_fast(N,K,spec):
    ctx=v.ctx_matrix(K,spec);nc=v.nctx(spec);tab=np.zeros(nc,np.int16);flatc=ctx.reshape(-1);flatn=N.reshape(-1)
    # Deterministic 1/4 thinning is enough for fitting because every context is capped anyway.
    ii=np.arange(0,len(flatc),4,dtype=np.int64);cc=flatc[ii];nn=flatn[ii]
    order=np.argsort(cc,kind='stable');sc=cc[order];uniq,starts,counts=np.unique(sc,return_index=True,return_counts=True);used=0
    coarse=np.unique(np.r_[[-133,133],np.arange(-128,129,16)]).astype(np.int64)
    for j,st,ct in zip(uniq,starts,counts):
        ids=order[st:st+ct];cap=384 if nc>1000 else 768
        if len(ids)>cap:ids=ids[np.linspace(0,len(ids)-1,cap,dtype=np.int64)]
        vals=nn[ids].astype(np.int64);used+=1
        Kc=np.floor_divide(vals[None,:]-coarse[:,None]+v.RAD,v.STEP);score=v.gamma_cost(Kc).sum(1);d0=int(coarse[int(np.argmin(score))])
        fine=np.arange(max(-v.RAD,d0-16),min(v.RAD,d0+16)+1,dtype=np.int64)
        Kf=np.floor_divide(vals[None,:]-fine[:,None]+v.RAD,v.STEP);score2=v.gamma_cost(Kf).sum(1);tab[int(j)]=int(fine[int(np.argmin(score2))])
    return tab,ctx,{'contexts':nc,'nonempty':used,'fit_stride':4}

v.fit_table=fit_table_fast
if __name__=='__main__':v.main(sys.argv[1])
