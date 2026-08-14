import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=4096
H=32
TB=1024
STEP=267
REGIONS=(('hard',512),('easy',2304))
a.NT=NT


def fit_predict_channel(x):
    # Intentionally impossible ceiling: target source past+future samples and the
    # target-fitted per-channel linear model are all free side information.
    n=NT-2*H
    A=np.empty((n,2*H+1),np.float64)
    y=x[H:NT-H].astype(np.float64)
    A[:,0]=1.0
    j=1
    for lag in range(-H,0):
        A[:,j]=x[H+lag:NT-H+lag];j+=1
    for lag in range(1,H+1):
        A[:,j]=x[H+lag:NT-H+lag];j+=1
    # Small ridge only for numerical conditioning. Oracle coefficients are free.
    G=A.T@A
    scale=max(float(np.trace(G))/G.shape[0],1.0)
    G.flat[::G.shape[0]+1]+=1e-8*scale
    co=np.linalg.solve(G,A.T@y)
    p=A@co
    return p,co


def oracle_k(X):
    P=np.zeros_like(X,np.float64)
    K=np.zeros_like(X,np.int32)
    # Boundary samples are deliberately given exact originals for free too, so
    # their K cost is zero. This only strengthens the ceiling.
    P[:,:H]=X[:,:H]
    P[:,NT-H:]=X[:,NT-H:]
    coeff=[]
    for c in range(C):
        p,co=fit_predict_channel(X[c])
        P[c,H:NT-H]=p
        coeff.append(co)
    K[:,H:NT-H]=np.rint((X[:,H:NT-H]-P[:,H:NT-H])/STEP).astype(np.int32)
    R=P+STEP*K.astype(np.float64)
    return P,K,R,coeff


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            # Real incumbent on identical samples.
            _,co=a.fits(X);Rb,Kb=a.run_ar(X,co);bb,_,_,Kbd=a.arithmetic(Kb)
            Rbd=a.decode_source(Kbd,co);bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))

            P,K,R,coeff=oracle_k(X)
            me=float(np.max(np.abs(X-R)))
            if me>eps*(1+1e-12):raise RuntimeError((region,'oracle hard',me,eps))
            ob,obit,onb,Kd=a.arithmetic(K)
            if not np.array_equal(Kd,K):raise RuntimeError((region,'K decode'))
            Rd=P+STEP*Kd.astype(np.float64)
            dme=float(np.max(np.abs(X-Rd)))
            if dme>eps*(1+1e-12):raise RuntimeError((region,'oracle replay hard',dme,eps))

            sz=0
            for t0 in range(0,NT,TB):
                n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
            target=sz/2.0
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),
                 'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},
                 'two_sided_oracle':{'bytes':int(ob),'bps':8*ob/X.size,
                     'gain_vs_baseline':float(bb/ob),'gain_vs_sz3':float(sz/ob),
                     'ratio_to_2x_target':float(ob/target),
                     'zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),
                     'arithmetic_bits':int(obit),'symbol_bits':int(onb),'maxerr':dme,
                     'free_boundary_fraction':float((2*H)/NT),
                     'free_coefficients':int(C*(2*H+1))}}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'rows':rows,'scope':'Deliberately impossible temporal ceiling. For every target sample away from the edges, the predictor is given the ORIGINAL source values from the previous and next 32 times, and a separate per-channel 65-coefficient least-squares model fitted on the complete target region is also supplied to the decoder for zero bits. The first/last 32 source samples are additionally supplied exactly for free. Only the resulting exact step267 K stream is charged through the normal cold-start arithmetic coder. This is far more favorable than any deployable noncausal/block codec. If it remains above the local 2x-SZ3 target, ordinary two-sided temporal dependence cannot supply the missing factor. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_two_sided_temporal_oracle.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
