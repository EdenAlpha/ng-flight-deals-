import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGIONS=(('hard',512),('easy',2304));C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
RIDGES=(1e-6,1e-4,1e-2,1e-1)

def true_history_prediction(X,co):
    a=float(co[0]);b=np.asarray(co[1:],np.float32);br=b[::-1].astype(np.float64)
    out=np.zeros(X.shape,np.int32)
    for c in range(C):
        x=np.asarray(X[c],np.float64)
        w=np.lib.stride_tricks.sliding_window_view(x,P)
        out[c,P:]=np.rint(a+w[:NT-P]@br).astype(np.int32)
    return out

def spatial_oracle(E,scale):
    mu=E.mean(axis=1,dtype=np.float64);Z=E-mu[:,None]
    G=(Z@Z.T)/Z.shape[1];v=float(np.trace(G))/C;lam=max(v*scale,1e-9)
    O=np.linalg.inv(G+lam*np.eye(C))
    d=np.diag(O);B=-O/d[:,None];np.fill_diagonal(B,0.0)
    S=mu[:,None]+B@Z
    return np.rint(S).astype(np.int32),float(lam),float(np.sqrt(np.mean((E-S)**2)))

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X)
            R0,K0=h.run_ar(X,co);base,_,_,D0=h.arithmetic(K0);RR=h.decode_source(D0,co)
            if not np.array_equal(R0,RR):raise RuntimeError((name,'baseline decode'))
            PT=true_history_prediction(X,co);E=X-PT.astype(np.float64)
            trials=[]
            for s in RIDGES:
                SP,lam,rmse=spatial_oracle(E,s);pred=PT.astype(np.int64)+SP.astype(np.int64)
                K=np.rint((X-pred)/STEP).astype(np.int32);R=pred+STEP*K.astype(np.int64)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((name,s,'hard',me,eps))
                b,_,_,Kd=h.arithmetic(K)
                if not np.array_equal(Kd,K):raise RuntimeError((name,s,'K decode'))
                trials.append({'ridge_scale':s,'ridge_lambda':lam,'bytes':int(b),'bps':8*b/X.size,'spatial_cond_rmse':rmse,'k_std':float(K.std()),'k_zero':float(np.mean(K==0)),'maxerr':me})
            best=min(trials,key=lambda z:z['bytes'])
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            best.update({'gain_vs_real':float(base/best['bytes']),'gain_vs_sz3':float(sz/best['bytes']),'ratio_to_2x':float(best['bytes']/(sz/2))})
            row={'region':name,'samples':int(X.size),'real_bytes':int(base),'real_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'trials':trials}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Deliberately impossible linear spatial ceiling. Huber AR32 is fitted as usual, but its temporal prediction is fed the ORIGINAL previous 32 source samples for free. The current temporal residual of every other one of the 127 sensors at the same time is also given to the predictor for free. A target-fitted 128x128 Gaussian conditional/precision model is free and predicts each channel from all other channels (zero diagonal); several ridge strengths are selected by actual exact-K arithmetic bytes. Only the resulting step267 K stream is charged. Exact K decode and source max-error are verified. This is not a codec claim; it is an overwhelmingly favorable ceiling on any linear same-time spatial-conditioning scheme. If it remains above the local 2x-SZ3 target, causal Cholesky/linear spatial models cannot close the gap.'},open('imperial_allneighbor_spatial_ceiling.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])