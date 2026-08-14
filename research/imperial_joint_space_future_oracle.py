import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_two_sided_temporal_oracle as tor

C=128
NT=4096
H=32
STEP=267
TB=1024
REGIONS=(('hard',512),('easy',2304))
RIDGES=(1e-6,1e-4,1e-2,1e-1)
a.NT=NT


def temporal_oracle_prediction(X):
    P=np.zeros_like(X,np.float64)
    P[:,:H]=X[:,:H]
    P[:,NT-H:]=X[:,NT-H:]
    coeff=[]
    for c in range(C):
        p,co=tor.fit_predict_channel(X[c])
        P[c,H:NT-H]=p
        coeff.append(co)
    return P,coeff


def spatial_oracle_prediction(E,ridge):
    # E is the TRUE current residual after the impossible two-sided temporal
    # prediction. The decoder receives every other sensor's E at the same time
    # for free. A target-fitted Gaussian conditional model is also free.
    Z=E[:,H:NT-H].T.astype(np.float64)  # time x channels
    mu=np.mean(Z,axis=0)
    Zc=Z-mu
    S=(Zc.T@Zc)/max(Zc.shape[0]-1,1)
    scale=max(float(np.trace(S))/C,1e-12)
    Om=np.linalg.inv(S + float(ridge)*scale*np.eye(C))
    pred=np.empty_like(Zc)
    for c in range(C):
        w=-Om[c].copy()/Om[c,c]
        w[c]=0.0
        pred[:,c]=mu[c] + Zc@w
    out=np.zeros_like(E,np.float64)
    out[:,H:NT-H]=pred.T
    return out,Om,mu


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            # Real incumbent control.
            _,co=a.fits(X);Rb,Kb=a.run_ar(X,co);bb,_,_,Kbd=a.arithmetic(Kb)
            Rbd=a.decode_source(Kbd,co);bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))
            sz=0
            for t0 in range(0,NT,TB):
                n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)

            Pt,tcoef=temporal_oracle_prediction(X)
            Et=X-Pt
            cands=[]
            for ridge in RIDGES:
                Ps,Om,mu=spatial_oracle_prediction(Et,ridge)
                P=Pt+Ps
                # Boundaries are already exact/free under temporal oracle.
                K=np.zeros_like(X,np.int32)
                K[:,H:NT-H]=np.rint((X[:,H:NT-H]-P[:,H:NT-H])/STEP).astype(np.int32)
                R=P+STEP*K.astype(np.float64)
                me=float(np.max(np.abs(X-R)))
                if me>eps*(1+1e-12):raise RuntimeError((region,ridge,'oracle hard',me,eps))
                n,nbit,nb,Kd=a.arithmetic(K)
                if not np.array_equal(Kd,K):raise RuntimeError((region,ridge,'K decode'))
                Rd=P+STEP*Kd.astype(np.float64)
                dme=float(np.max(np.abs(X-Rd)))
                if dme>eps*(1+1e-12):raise RuntimeError((region,ridge,'replay hard',dme,eps))
                q={'ridge':float(ridge),'bytes':int(n),'bps':8*n/X.size,
                   'gain_vs_baseline':float(bb/n),'gain_vs_sz3':float(sz/n),
                   'ratio_to_2x_target':float(n/(sz/2.0)),
                   'zero_fraction':float(np.mean(K==0)),
                   'k_std':float(np.std(K.astype(np.float64))),
                   'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'maxerr':dme,
                   'free_temporal_coefficients':int(C*(2*H+1)),
                   'free_spatial_model_values':int(Om.size+mu.size),
                   'free_boundary_fraction':float(2*H/NT),
                   'free_current_other_sensor_residuals':True}
                cands.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            best=min(cands,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),
                 'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},'best_joint_oracle':best,'candidates':cands}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        out={'rows':rows,'scope':'Deliberately impossible JOINT spatiotemporal ceiling. First, every interior sample is predicted from the ORIGINAL previous 32 and next 32 source samples with a separate target-fitted per-channel linear model supplied for zero bits; boundaries are exact and free. Then the TRUE current residuals of all other 127 sensors are supplied to the decoder for zero bits, together with a target-fitted 128x128 Gaussian precision/conditional spatial model for zero bits. Only the resulting exact step267 K stream is charged through the normal cold-start arithmetic coder. This jointly dominates ordinary bidirectional temporal prediction plus all-neighbor linear spatial conditioning. If it remains above local 2x-SZ3, conventional joint linear space-time dependence cannot supply the missing factor. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_joint_space_future_oracle.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
