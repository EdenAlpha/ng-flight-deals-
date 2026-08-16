import sys,numpy as np
import imperial_near2eps_hybrid_predictor_zsm as q

def make_selector_fixed(DL,DA,gc,bt):
    lc=q.gamma_cost(DL);ac=q.gamma_cost(DA);ngc=(q.C+gc-1)//gc;ngt=(q.NT+bt-1)//bt;S=np.zeros((ngc,ngt),np.uint8);sur=0.0
    for ic in range(ngc):
        c0=ic*gc;c1=min(q.C,c0+gc)
        for it in range(ngt):
            t0=it*bt;t1=min(q.NT,t0+bt);la=float(lc[c0:c1,t0:t1].sum());aa=float(ac[c0:c1,t0:t1].sum())
            if aa<la:S[ic,it]=1;sur+=aa
            else:sur+=la
    D=np.empty_like(DL)
    for ic in range(ngc):
        c0=ic*gc;c1=min(q.C,c0+gc)
        for it in range(ngt):
            t0=it*bt;t1=min(q.NT,t0+bt);D[c0:c1,t0:t1]=DA[c0:c1,t0:t1] if S[ic,it] else DL[c0:c1,t0:t1]
    return S,D,float(sur),float(np.mean(S))

q.make_selector=make_selector_fixed
if __name__=='__main__':q.main(sys.argv[1])
