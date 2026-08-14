import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_spatiotemporal_super_oracle as base

C=128;NT=4096;H=32;MAXLAG=64;M=H+MAXLAG;TB=1024;STEP=267
REGIONS=(("hard",512),("easy",2304))
DCS=(-64,-32,-16,-8,-4,-2,-1,1,2,4,8,16,32,64)
DTS=(-64,-32,-16,-8,-4,-2,-1,1,2,4,8,16,32,64)
TOP=32
a.NT=NT


def current_spatial(E):
    # Same impossible all-other-sensors current-time conditioning as PR #469,
    # but evaluated only where the cross-lag oracle has complete +/-64 support.
    Z=E[:,M:NT-M]
    mu=Z.mean(axis=1)
    Zc=Z-mu[:,None]
    S=(Zc@Zc.T)/float(Zc.shape[1])
    scale=max(float(np.trace(S))/C,1.0)
    S.flat[::C+1]+=1e-6*scale
    O=np.linalg.inv(S)
    B=np.empty((C,C),np.float64)
    for c in range(C):
        B[c,:]=-O[c,:]/O[c,c];B[c,c]=0.0
    return mu[:,None]+B@(Z-mu[:,None]),B,mu


def crosslag_fit(E,Y):
    # Deliberately impossible moveout oracle. For each target channel, every
    # candidate is the TRUE residual of another sensor at a positive or negative
    # time shift. Feature selection and regression use the complete target and
    # are supplied to the decoder for zero bits.
    T=np.arange(M,NT-M,dtype=np.int32)
    P=np.zeros_like(Y,np.float64); selections=[]; coeffs=[]
    for c in range(C):
        cols=[]; ids=[]
        for dc in DCS:
            j=c+dc
            if j<0 or j>=C: continue
            for dt in DTS:
                cols.append(E[j,T+dt]);ids.append((int(dc),int(dt)))
        F=np.stack(cols,axis=1).astype(np.float64)
        y=Y[c].astype(np.float64)
        fc=F-F.mean(axis=0,keepdims=True);yc=y-y.mean()
        den=np.sqrt(np.sum(fc*fc,axis=0)*max(float(np.sum(yc*yc)),1e-30))
        corr=np.abs((fc.T@yc)/np.maximum(den,1e-30))
        pick=np.argsort(corr)[-min(TOP,F.shape[1]):]
        Fs=F[:,pick]
        A=np.concatenate([np.ones((Fs.shape[0],1),np.float64),Fs],axis=1)
        # Tiny target-scaled ridge stabilizes almost-collinear shifted traces.
        G=A.T@A;rhs=A.T@y
        ridge=1e-8*max(float(np.trace(G))/G.shape[0],1.0)
        G.flat[::G.shape[0]+1]+=ridge
        co=np.linalg.solve(G,rhs)
        P[c]=A@co
        selections.append([ids[int(i)] for i in pick]);coeffs.append(co)
    return P,selections,coeffs


def encode_fixed_prediction(X,P,eps):
    K=np.zeros((C,NT),np.int32)
    K[:,M:NT-M]=np.rint((X[:,M:NT-M]-P[:,M:NT-M])/STEP).astype(np.int32)
    R=P+STEP*K.astype(np.float64)
    R[:,:M]=X[:,:M];R[:,NT-M:]=X[:,NT-M:]
    P[:,:M]=X[:,:M];P[:,NT-M:]=X[:,NT-M:]
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+1e-12):raise RuntimeError(('hard',me,eps))
    b,nbits,sbits,Kd=a.arithmetic(K)
    if not np.array_equal(Kd,K):raise RuntimeError('K decode')
    Rd=P+STEP*Kd.astype(np.float64);Rd[:,:M]=X[:,:M];Rd[:,NT-M:]=X[:,NT-M:]
    dme=float(np.max(np.abs(X-Rd)))
    if dme>eps*(1+1e-12):raise RuntimeError(('replay',dme,eps))
    return b,K,dme,nbits,sbits


def region(name,c0,d,eps):
    X=np.asarray(d[:NT,c0:c0+C],np.float64).T
    # PR469's impossible bidirectional own-channel predictor.
    Pt,tco=base.temporal_prediction(X)
    E=X-Pt
    # Give first/last 96 samples for free to all controls so the cross-lag
    # comparison is not helped merely by its larger lag support boundary.
    Ptemp=Pt.copy();Ptemp[:,:M]=X[:,:M];Ptemp[:,NT-M:]=X[:,NT-M:]
    bt,Kt,tme,_,_=encode_fixed_prediction(X,Ptemp,eps)

    Ps,B,mu=current_spatial(E)
    Pcur=Pt.copy();Pcur[:,M:NT-M]+=Ps;Pcur[:,:M]=X[:,:M];Pcur[:,NT-M:]=X[:,NT-M:]
    bc,Kc,cme,_,_=encode_fixed_prediction(X,Pcur,eps)

    Y=E[:,M:NT-M]-Ps
    Pxl,sel,coef=crosslag_fit(E,Y)
    Pmov=Pcur.copy();Pmov[:,M:NT-M]+=Pxl
    bm,Km,mme,mbits,msbits=encode_fixed_prediction(X,Pmov,eps)

    # Matched real baseline and SZ3 for the same region.
    _,co=a.fits(X);Rb,Kb=a.run_ar(X,co);bb,_,_,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,co)
    bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
    if bme>eps*(1+1e-12):raise RuntimeError((name,'baseline',bme,eps))
    sz=0
    for t0 in range(0,NT,TB):
        n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
    target=sz/2.0
    return {'region':name,'c0':c0,'samples':int(X.size),'eps':float(eps),'free_boundary_fraction':float(2*M/NT),
            'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'maxerr':bme},
            'sz3':{'bytes':int(sz),'bps':8*sz/X.size},
            'temporal_same_boundary':{'bytes':int(bt),'bps':8*bt/X.size,'gain_vs_baseline':float(bb/bt),'ratio_to_2x_target':float(bt/target),'zero_fraction':float(np.mean(Kt==0)),'maxerr':tme},
            'current_spatial_same_boundary':{'bytes':int(bc),'bps':8*bc/X.size,'gain_vs_temporal':float(bt/bc),'ratio_to_2x_target':float(bc/target),'zero_fraction':float(np.mean(Kc==0)),'maxerr':cme,'free_current_spatial_coefficients':int(C*C)},
            'crosslag_moveout_oracle':{'bytes':int(bm),'bps':8*bm/X.size,'gain_vs_temporal':float(bt/bm),'gain_vs_current_spatial':float(bc/bm),'gain_vs_baseline':float(bb/bm),'ratio_to_2x_target':float(bm/target),'zero_fraction':float(np.mean(Km==0)),'k_std':float(np.std(Km.astype(np.float64))),'maxerr':mme,'arithmetic_bits':int(mbits),'symbol_bits':int(msbits),'top_features_per_channel':TOP,'candidate_dc':list(DCS),'candidate_dt':list(DTS),'free_selected_feature_ids':int(sum(len(x) for x in sel)),'free_coefficients':int(sum(len(x) for x in coef))}}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        rows=[]
        for name,c0 in REGIONS:
            r=region(name,c0,d,eps);rows.append(r);print(json.dumps(r,indent=2),flush=True)
    json.dump({'rows':rows,'scope':'Deliberately impossible cross-channel/time-lag moveout ceiling. It starts from the PR469 target-fitted bidirectional own-channel predictor. It then supplies the true current residuals of all other sensors for free as a current-time spatial control. Finally, for each target channel it may inspect true residuals from other sensors at dc in +/-{1,2,4,8,16,32,64} and dt in +/-{1,2,4,8,16,32,64}, select its 32 strongest target-fitted cross-lag features, fit their coefficients on the complete target, and supply all selections/coefficients for zero bits. First/last 96 source samples are exact/free for every oracle control so lag support does not create an unfair relative boundary gain. Only the final step267 K stream is charged. This tests traveling-wave/moveout linear coherence that same-time all-neighbor conditioning and same-channel future prediction do not jointly represent. No AI. Draft/do not merge.'},open('imperial_crosslag_moveout_oracle.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
