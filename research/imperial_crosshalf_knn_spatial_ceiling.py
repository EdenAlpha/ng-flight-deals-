import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGIONS=(('hard',512),('easy',2304));C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
KS=(1,4,16,64)
EVEN=np.arange(0,C,2);ODD=np.arange(1,C,2)

def true_history_prediction(X,co):
    a=float(co[0]);b=np.asarray(co[1:],np.float64);br=b[::-1]
    out=np.zeros(X.shape,np.int32)
    for c in range(C):
        x=np.asarray(X[c],np.float64)
        w=np.lib.stride_tricks.sliding_window_view(x,P)
        out[c,P:]=np.rint(a+w[:NT-P]@br).astype(np.int32)
    return out

def neighbor_order(E,features):
    rawT=E[features,:TRAIN].T.astype(np.float64);rawQ=E[features,TRAIN:].T.astype(np.float64)
    mu=rawT.mean(axis=0);sd=rawT.std(axis=0);sd[sd<1e-6]=1.0
    T=(rawT-mu)/sd;Q=(rawQ-mu)/sd
    qn=np.sum(Q*Q,axis=1)[:,None];tn=np.sum(T*T,axis=1)[None,:]
    D=qn+tn-2.0*(Q@T.T);np.maximum(D,0,out=D)
    kk=max(KS)
    cand=np.argpartition(D,kk-1,axis=1)[:,:kk]
    cd=np.take_along_axis(D,cand,axis=1)
    ord2=np.argsort(cd,axis=1)
    return np.take_along_axis(cand,ord2,axis=1),D

def predict_half(E,features,targets,order,k):
    # Oracle database (including target residual values on TRAIN) is free side information.
    Y=E[targets,:TRAIN].T.astype(np.float64)
    idx=order[:,:k]
    return Y[idx].mean(axis=1).T

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X)
            R0,K0=h.run_ar(X,co);base,_,_,D0=h.arithmetic(K0);RR=h.decode_source(D0,co)
            if not np.array_equal(R0,RR):raise RuntimeError((name,'baseline decode'))
            PT=true_history_prediction(X,co);E=X-PT.astype(np.float64)
            ord_evenfeat,De=neighbor_order(E,EVEN) # predict ODD from exact current EVEN residuals
            ord_oddfeat,Do=neighbor_order(E,ODD)   # predict EVEN from exact current ODD residuals
            trials=[]
            for k in KS:
                S=np.zeros_like(E)
                S[ODD,TRAIN:]=predict_half(E,EVEN,ODD,ord_evenfeat,k)
                S[EVEN,TRAIN:]=predict_half(E,ODD,EVEN,ord_oddfeat,k)
                pred=PT.astype(np.int64)+np.rint(S).astype(np.int64)
                K=np.rint((X-pred)/STEP).astype(np.int32);R=pred+STEP*K.astype(np.int64)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((name,k,'hard',me,eps))
                b,_,_,Kd=h.arithmetic(K)
                if not np.array_equal(Kd,K):raise RuntimeError((name,k,'K decode'))
                trials.append({'k':k,'bytes':int(b),'bps':8*b/X.size,'k_zero':float(np.mean(K==0)),'k_std':float(K.std()),'future_k_zero':float(np.mean(K[:,TRAIN:]==0)),'future_residual_rmse':float(np.sqrt(np.mean((X[:,TRAIN:]-pred[:,TRAIN:])**2))),'maxerr':me})
            best=min(trials,key=lambda z:z['bytes'])
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            best.update({'gain_vs_real':float(base/best['bytes']),'gain_vs_sz3':float(sz/best['bytes']),'ratio_to_2x':float(best['bytes']/(sz/2))})
            row={'region':name,'samples':int(X.size),'real_bytes':int(base),'real_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'trials':trials}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Deliberately impossible nonlinear spatial ceiling. Huber AR32 uses ORIGINAL true source history for free. For t>=1024, odd-channel temporal residuals are predicted nonparametrically from the exact current even-channel temporal residual vector, and even channels from the exact current odd-channel residual vector. A free source-trained 1024-sample nearest-neighbor database supplies target residuals; k=1/4/16/64 neighbors are selected by standardized Euclidean distance in the opposite 64-channel residual half. The database, neighbor identities, true current complementary-half residuals, and temporal source history are all zero-bit oracle side information. Only exact step267 K is arithmetic-coded and decoded, with full hard-error verification. This is not a codec claim; it is an extremely favorable nonlinear cross-sensor dependency ceiling. If it remains far above 2x-SZ3, a hidden deterministic/nonlinear spatial manifold is not a plausible explanation for the missing factor.'},open('imperial_crosshalf_knn_spatial_ceiling.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])