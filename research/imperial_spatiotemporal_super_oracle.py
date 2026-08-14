import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_two_sided_temporal_oracle as temporal

C=128;NT=4096;H=32;TB=1024;STEP=267
REGIONS=(("hard",512),("easy",2304))
a.NT=NT


def temporal_prediction(X):
    P=np.zeros_like(X,np.float64);P[:,:H]=X[:,:H];P[:,NT-H:]=X[:,NT-H:]
    coeff=[]
    for c in range(C):
        p,co=temporal.fit_predict_channel(X[c]);P[c,H:NT-H]=p;coeff.append(co)
    return P,coeff


def spatial_conditional(E):
    # Impossible current-time oracle: the true residuals of all OTHER sensors
    # are available for free. One ridge precision matrix fitted on the complete
    # target region is also free. Conditional linear mean is -Omega_c,-c/Omega_cc.
    Z=E[:,H:NT-H]
    Zc=Z-Z.mean(axis=1,keepdims=True)
    S=(Zc@Zc.T)/float(Zc.shape[1])
    scale=max(float(np.trace(S))/C,1.0)
    S.flat[::C+1]+=1e-6*scale
    O=np.linalg.inv(S)
    B=np.empty((C,C),np.float64)
    for c in range(C):
        B[c,:]=-O[c,:]/O[c,c];B[c,c]=0.0
    # Include target-fitted residual means for free too.
    mu=Z.mean(axis=1)
    pred=mu[:,None]+B@(Z-mu[:,None])
    return pred,B,mu


def oracle_k(X):
    Pt,tco=temporal_prediction(X)
    E=X-Pt
    Ps,B,mu=spatial_conditional(E)
    P=Pt.copy();P[:,H:NT-H]+=Ps
    K=np.zeros((C,NT),np.int32)
    K[:,H:NT-H]=np.rint((X[:,H:NT-H]-P[:,H:NT-H])/STEP).astype(np.int32)
    R=P+STEP*K.astype(np.float64)
    return P,K,R,tco,B,mu


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            _,co=a.fits(X);Rb,Kb=a.run_ar(X,co);bb,_,_,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,co)
            bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))

            # Temporal-only impossible oracle control.
            Pt,Kt,Rt,tcoeff=temporal.oracle_k(X);tme=float(np.max(np.abs(X-Rt)))
            tb,tbit,tnb,Ktd=a.arithmetic(Kt)
            if not np.array_equal(Ktd,Kt) or tme>eps*(1+1e-12):raise RuntimeError((region,'temporal control'))

            P,K,R,tco,B,mu=oracle_k(X);me=float(np.max(np.abs(X-R)))
            if me>eps*(1+1e-12):raise RuntimeError((region,'super oracle hard',me,eps))
            ob,obit,onb,Kd=a.arithmetic(K)
            if not np.array_equal(Kd,K):raise RuntimeError((region,'super K decode'))
            Rd=P+STEP*Kd.astype(np.float64);dme=float(np.max(np.abs(X-Rd)))
            if dme>eps*(1+1e-12):raise RuntimeError((region,'super replay hard',dme,eps))

            sz=0
            for t0 in range(0,NT,TB):
                n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
            target=sz/2.0
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),
                 'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},
                 'temporal_oracle':{'bytes':int(tb),'bps':8*tb/X.size,'gain_vs_baseline':float(bb/tb),'ratio_to_2x_target':float(tb/target),'zero_fraction':float(np.mean(Kt==0))},
                 'spatiotemporal_super_oracle':{'bytes':int(ob),'bps':8*ob/X.size,'gain_vs_baseline':float(bb/ob),'gain_vs_temporal_oracle':float(tb/ob),'gain_vs_sz3':float(sz/ob),'ratio_to_2x_target':float(ob/target),'zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),'arithmetic_bits':int(obit),'symbol_bits':int(onb),'maxerr':dme,'free_boundary_fraction':float((2*H)/NT),'free_temporal_coefficients':int(C*(2*H+1)),'free_spatial_coefficients':int(C*(C-1)+C)}}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'rows':rows,'scope':'Deliberately impossible combined spatiotemporal ceiling. First, every interior sample is predicted from the ORIGINAL previous 32 and next 32 samples of the same sensor with target-fitted per-channel coefficients supplied free, exactly as the two-sided temporal oracle. Then the remaining current-time residual of each sensor is predicted from the TRUE current residuals of all other 127 sensors, also supplied free, using a full target-fitted ridge precision/conditional-mean matrix supplied free. First/last 32 source samples remain exact and free. Only the final step267 K stream is charged through the normal cold-start arithmetic coder. If this remains above the local 2x-SZ3 target, ordinary local linear spatiotemporal dependence cannot supply the missing factor. No AI. Draft/do not merge.'},open('imperial_spatiotemporal_super_oracle.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
