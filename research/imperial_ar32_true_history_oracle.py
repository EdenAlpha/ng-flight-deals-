import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024


def oracle_true_history(X,co):
    K=np.zeros(X.shape,np.int32);R=np.zeros(X.shape,np.int32)
    a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(NT):
            p=0 if t<P else int(np.rint(a+float(np.dot(b,X[c,t-P:t][::-1].astype(np.float32)))))
            k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X)
            R,K=h.run_ar(X,co);real,_,_,Kd=h.arithmetic(K);Rd=h.decode_source(Kd,co)
            if not np.array_equal(R,Rd):raise RuntimeError((region,'real decode'))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'real hard',me,eps))
            OR,OK=oracle_true_history(X,co);ome=float(np.max(np.abs(X-OR.astype(np.float64))))
            if ome>eps*(1+1e-12):raise RuntimeError((region,'oracle hard',ome,eps))
            ob,_,_,OKd=h.arithmetic(OK)
            if not np.array_equal(OKd,OK):raise RuntimeError((region,'oracle K decode'))
            sz=0
            for t0 in range(0,NT,TB):
                b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,
                 'real_bytes':int(real),'real_bps':8*real/X.size,
                 'oracle_true_history_bytes':int(ob),'oracle_true_history_bps':8*ob/X.size,
                 'oracle_gain_vs_real':float(real/ob),'oracle_gain_vs_sz3':float(sz/ob),
                 'oracle_ratio_to_2x_sz3_target':float(ob/(sz/2)),
                 'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,
                 'real_maxerr':me,'oracle_maxerr':ome,
                 'real_zero_fraction':float(np.mean(K==0)),'oracle_zero_fraction':float(np.mean(OK==0)),
                 'real_std_k':float(np.std(K)),'oracle_std_k':float(np.std(OK))}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'rows':rows,
                   'scope':'Deliberately impossible ceiling audit. The Huber AR32+intercept is fitted exactly as the real prefix-only codec, but for every t>=32 the oracle predictor is fed the ORIGINAL previous 32 source samples rather than decoder reconstruction. Those true samples are given for zero bits. Exact step267 innovations are then encoded through the same cold-start contextual arithmetic backend. This is not a codec claim: it measures the maximum benefit available from eliminating lossy decoder-state contamination while holding model, lattice and entropy backend fixed. If even this free-source-history oracle remains above the matched 2x-SZ3 target, periodic anchors/resets/state-correction schemes cannot close the gap through this mechanism. No AI.'},open('imperial_ar32_true_history_oracle.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
