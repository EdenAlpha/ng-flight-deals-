import json,sys
import h5py,numpy as np
import imperial_fullhard_adaptive_gps_transfer as ag
import imperial_decoder_phase_automaton as m

C=128; NT=30000; C0=512; P=32; TRAIN=1024; STEP=267
MODEL_BYTES=177
OUTER_BYTES=34
HIST_AR32_ZSM=2478995
FAIR_AR32_RICHMAG=2469677
MATCHED_SZ3=2767977


def design(X):
    n=C*(TRAIN-P);A=np.empty((n,P+1),np.float64);y=np.empty(n,np.float64);j=0
    for c in range(C):
        x=np.asarray(X[c,:TRAIN],np.float64)
        for t in range(P,TRAIN):
            A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
    return A,y


def huber_fit(X):
    A,y=design(X);ls=np.linalg.lstsq(A,y,rcond=None)[0];co=ls.copy()
    for _ in range(6):
        r=y-A@co;w=np.minimum(1.0,267.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w)
        co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
    return np.asarray(co,np.float32)


def physical_model_frame(co):
    raw=np.asarray(co,np.float32).tobytes()
    if len(raw)>MODEL_BYTES:raise RuntimeError(('model overflow',len(raw),MODEL_BYTES))
    frame=raw+bytes(MODEL_BYTES-len(raw))
    cod=np.frombuffer(frame[:len(raw)],np.float32).copy()
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):
        raise RuntimeError('model replay')
    return frame,cod


def run_ar(X,co):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(X.shape[1]):
            p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def decode_source(K,co):
    R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(K.shape[1]):
            p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            R[c,t]=p+STEP*int(K[c,t])
    return R


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std
        X=np.asarray(d[:,C0:C0+C],np.float64).T
    if X.shape!=(C,NT):raise RuntimeError(('shape',X.shape))
    co=huber_fit(X);model,cod=physical_model_frame(co)
    R,K=run_ar(X,cod)
    me0=float(np.max(np.abs(X-R.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('encode hard',me0,eps))
    payload,Kd,detail=ag.transfer_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError('K replay')
    Rd=decode_source(Kd,cod)
    if not np.array_equal(Rd,R):raise RuntimeError('AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('decode hard',me,eps))
    total=OUTER_BYTES+len(model)+int(payload)
    out={'region':'hard_full','shape':[C,NT],'samples':C*NT,'global_std':std,'eps':eps,
         'generator':'audited_huber_ar32','order':P,'train':TRAIN,'step':STEP,
         'outer_bytes':OUTER_BYTES,'model_bytes':len(model),'payload_bytes':int(payload),'bytes':int(total),
         'bps':8*total/(C*NT),'maxerr':me,
         'historical_ar32_zsm_bytes':HIST_AR32_ZSM,'fair_ar32_richmag_bytes':FAIR_AR32_RICHMAG,
         'delta_vs_historical':int(total-HIST_AR32_ZSM),'delta_vs_fair_ar32':int(total-FAIR_AR32_RICHMAG),
         'gain_vs_historical':HIST_AR32_ZSM/total,'gain_vs_fair_ar32':FAIR_AR32_RICHMAG/total,
         'matched_sz3_bytes_from_pr610':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,
         'calibrated_families':{str(k):ag.a.ADAPT_FAMILIES[v] for k,v in ag.CAL_FAMILY.items()},'detail':detail,
         'scope':'Strongest-layer fusion gate. The generator is the exact 32-tap Huber AR construction audited in the historical Imperial family: first 1024 samples across all 128 hard channels, six Huber IRLS iterations, float32 coefficients, step267, cold start. Its coefficient vector is physically serialized into a conservative 177-byte model frame and decoded bit-exactly. The innovation K field is then encoded by the frozen Adaptive-GPS per-plane family learned only on the independent 128x1024 PR598 calibration block, with raw packed-Zstd fallback physically selected per plane. No full-object context-family search occurs. K is decoded exactly, all 3.84M AR samples are causally replayed and the original global-epsilon hard bound is checked. The strict current fair incumbent is PR610 AR32 richmag W4 at 2,469,677 B; the older 2,478,995 B number is reported only for history.'}
    json.dump(out,open('imperial_huber_ar32_adaptive_gps_fullhard.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':total,'payload':payload,'model':len(model),'outer':OUTER_BYTES,
        'fair_ar32':FAIR_AR32_RICHMAG,'delta_vs_fair':total-FAIR_AR32_RICHMAG,
        'gain_vs_fair':FAIR_AR32_RICHMAG/total,'historical':HIST_AR32_ZSM,
        'sz3':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'maxerr':me}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
