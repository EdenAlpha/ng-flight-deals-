import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32;STEP=267;TRAIN=1024;END=8192;C=128
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
m.STEP=STEP

def pred(R,c,t,co,kind):
    if t<P:return 0
    cc=co if kind=='shared' else co[c]
    v=float(cc[-1])
    for j in range(P):v+=float(cc[j])*float(R[c,t-1-j])
    if not math.isfinite(v) or abs(v)>1e12:raise RuntimeError(('unstable predictor',kind,c,t,v))
    return int(np.rint(v))

def encode(X,eps,kind):
    train=X[:,:TRAIN]
    co=r.fit_shared(train,P) if kind=='shared' else r.fit_per_channel(train,P)
    mb,cd=r.model_frame(co)
    R=np.zeros(X.shape,np.int64);K=np.zeros(X.shape,np.int64)
    for c in range(C):
        for t in range(X.shape[1]):
            p=pred(R,c,t,cd,kind);k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError(('hard encode',kind,c,t,X[c,t],p,k,y,eps))
            R[c,t]=y;K[c,t]=k
    kb,rep,kd=m.encode_k(K);kd=np.asarray(kd,np.int64).reshape(K.shape)
    if not np.array_equal(kd,K):raise RuntimeError(('K decode',kind))
    D=np.zeros_like(R)
    for c in range(C):
        for t in range(X.shape[1]):D[c,t]=pred(D,c,t,cd,kind)+STEP*int(kd[c,t])
    if not np.array_equal(D,R):raise RuntimeError(('state decode',kind))
    me=float(np.max(np.abs(X-D)))
    if me>eps*(1+1e-10):raise RuntimeError(('hard final',kind,me,eps))
    target_bytes_est=None
    # Also encode held-out innovations only to separate model/startup effects while
    # leaving the full-stream byte result as the primary decoder-real number.
    hb,hrep,hdec=m.encode_k(K[:,TRAIN:]);hdec=np.asarray(hdec,np.int64).reshape(C,END-TRAIN)
    if not np.array_equal(hdec,K[:,TRAIN:]):raise RuntimeError('heldout K decode')
    return {'bytes':int(mb+kb+20),'model_bytes':int(mb),'innovation_bytes':int(kb+20),'rep':rep,'bps':8*(mb+kb+20)/X.size,
            'heldout_innovation_bytes':int(hb+20),'heldout_innovation_bps':8*(hb+20)/(C*(END-TRAIN)),'heldout_rep':hrep,
            'maxerr':me,'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'k_abs1_fraction':float(np.mean(np.abs(K[:,TRAIN:])==1)),
            'median_abs_k':float(np.median(np.abs(K[:,TRAIN:])))}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T
            rr=[]
            for kind in ('shared','per_channel'):
                try:z=encode(X,eps,kind)
                except Exception as e:
                    z={'kind':kind,'error':repr(e)};rr.append(z);print(json.dumps({'region':name,**z}),flush=True);continue
                z.update({'region':name,'c0':c0,'kind':kind});rr.append(z);rows.append(z);print(json.dumps(z),flush=True)
            ok={z['kind']:z for z in rr if 'bytes' in z}
            if 'shared' in ok and 'per_channel' in ok:
                print(json.dumps({'region':name,'per_channel_gain_vs_shared_full':ok['shared']['bytes']/ok['per_channel']['bytes'],
                                  'per_channel_gain_vs_shared_heldout_innovations':ok['shared']['heldout_innovation_bytes']/ok['per_channel']['heldout_innovation_bytes']}),flush=True)
    combos=[]
    for kind in ('shared','per_channel'):
        rr=[z for z in rows if z['kind']==kind]
        if len(rr)==len(SPECS):
            b=sum(z['bytes'] for z in rr);hb=sum(z['heldout_innovation_bytes'] for z in rr);n=C*END*len(rr);hn=C*(END-TRAIN)*len(rr)
            combos.append({'kind':kind,'bytes':b,'bps':8*b/n,'heldout_innovation_bytes':hb,'heldout_innovation_bps':8*hb/hn,
                           'model_bytes':sum(z['model_bytes'] for z in rr),'median_k_zero_fraction':float(np.median([z['k_zero_fraction'] for z in rr]))})
    if len(combos)==2:
        a={z['kind']:z for z in combos};gain_full=a['shared']['bytes']/a['per_channel']['bytes'];gain_h=a['shared']['heldout_innovation_bytes']/a['per_channel']['heldout_innovation_bytes']
    else:gain_full=gain_h=None
    out={'global_std':std,'eps':eps,'step':STEP,'order':P,'training_samples':TRAIN,'end_sample':END,'regions':[list(x) for x in SPECS],
         'rows':rows,'combos':combos,'per_channel_gain_vs_shared_full':gain_full,'per_channel_gain_vs_shared_heldout_innovations':gain_h,
         'scope':'Persistent per-channel AR32 gate. This specifically differs from the old short-tile p<=16 per-channel screen: each candidate is fit only from t<1024, float32 serialized/byte-decoded, then frozen while recursively encoding t=0..8191 at the current legal step267. Shared and per-channel models use identical innovation backend and hard-error checks. Primary bytes include the complete 8192-sample stream plus all model bytes. Held-out innovation bytes for t>=1024 are also reported only to isolate prediction quality from model/startup overhead. Four fixed hard/easy/medium/far 128-channel regions; no target-time model tuning, no AI, not a whole-array claim.'}
    print(json.dumps({'combos':combos,'gain_full':gain_full,'gain_heldout':gain_h},indent=2),flush=True);json.dump(out,open('imperial_per_channel_ar32_gate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
