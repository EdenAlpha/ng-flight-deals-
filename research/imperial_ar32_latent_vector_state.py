import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r
import imperial_persistent_ar32_full_array_jit as a

STEP=267;P=32;C=128;TRAIN=1024;NT=8192;TB=1024
m.STEP=STEP;a.m.m.STEP=STEP
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
B_VALUES=(1,2,4,8,16,32)


def fit_build(X):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);R,K=a.build(X,cd)
    return cd,int(mb),R,K


def global_params(K):
    return fit_params(K,np.zeros(K.shape[1],np.int32),1)[0]


def fit_params(K,labels,B):
    K=np.asarray(K,np.int64);C0,T=K.shape;glob=None;models=[]
    for s in range(B):
        mask=labels==s;n=int(mask.sum())
        if n==0:
            models.append(None);continue
        X=K[:,mask];z=X==0;n0=z.sum(axis=1).astype(np.float64);nz=n-n0
        p0=(n0+0.5)/(n+1.0)
        npos=(X>0).sum(axis=1).astype(np.float64);pplus=(npos+0.5)/(nz+1.0)
        sm=np.where(z,0,np.abs(X)-1).sum(axis=1).astype(np.float64);mean=(sm+0.5)/(nz+1.0);rr=mean/(1.0+mean)
        rr=np.clip(rr,1e-8,1-1e-8);models.append({'p0':p0,'pplus':pplus,'r':rr,'n':n})
    # Empty states use the all-prefix law only for assignment; they will be removed later.
    if any(x is None for x in models):
        z=K==0;n=K.shape[1];n0=z.sum(axis=1).astype(np.float64);nz=n-n0;p0=(n0+.5)/(n+1.0)
        npos=(K>0).sum(axis=1).astype(np.float64);pp=(npos+.5)/(nz+1.0);sm=np.where(z,0,np.abs(K)-1).sum(axis=1).astype(np.float64);mean=(sm+.5)/(nz+1.0);rr=np.clip(mean/(1+mean),1e-8,1-1e-8);glob={'p0':p0,'pplus':pp,'r':rr,'n':n}
        models=[glob if x is None else x for x in models]
    return models


def state_costs(K,models):
    X=np.asarray(K,np.int64);z=X==0;cost=[]
    for md in models:
        p0=md['p0'][:,None];pp=md['pplus'][:,None];rr=md['r'][:,None]
        bits=np.empty(X.shape,np.float64);bits[z]=-np.broadcast_to(np.log2(np.maximum(p0,1e-300)),X.shape)[z]
        nz=~z
        if np.any(nz):
            sg=np.where(X>0,pp,1-pp);mag=np.abs(X)-1
            bb=(-np.log2(np.maximum(1-p0,1e-300))-np.log2(np.maximum(sg,1e-300))-
                np.log2(np.maximum(1-rr,1e-300))-mag*np.log2(np.maximum(rr,1e-300)))
            bits[nz]=bb[nz]
        cost.append(bits.sum(axis=0))
    return np.stack(cost,axis=0)


def quantile_labels(x,B):
    x=np.asarray(x,np.float64);th=np.quantile(x,np.arange(1,B)/B) if B>1 else np.empty(0)
    return np.searchsorted(th,x,side='right').astype(np.int32)


def initializations(K,B):
    if B==1:return [('one',np.zeros(K.shape[1],np.int32))]
    rms=np.sqrt(np.mean(K.astype(np.float64)**2,axis=0));out=[('rms',quantile_labels(rms,B)),('time_mod',(np.arange(K.shape[1])%B).astype(np.int32))]
    # Decoder-derived spatial pattern coordinate: first principal spatial direction of prefix innovations.
    A=K.astype(np.float64);A-=A.mean(axis=1,keepdims=True)
    try:
        u,s,vh=np.linalg.svd(A,full_matrices=False);pc=vh[0]
        out.append(('pc1',quantile_labels(pc,B)))
    except np.linalg.LinAlgError:pass
    # Fixed alternating-channel projection catches common/differential hardware modes without learned metadata.
    alt=(np.where(np.arange(K.shape[0])%2==0,1.0,-1.0)[:,None]*K).sum(axis=0)
    out.append(('alternating',quantile_labels(alt,B)))
    return out


def train_mixture(K,B):
    best=None
    for init,lab0 in initializations(K,B):
        lab=lab0.copy();prev=None
        for it in range(15):
            models=fit_params(K,lab,B);cost=state_costs(K,models);new=np.argmin(cost,axis=0).astype(np.int32)
            if np.array_equal(new,lab):break
            lab=new
        active=np.unique(lab);remap={int(s):i for i,s in enumerate(active)};lab2=np.array([remap[int(x)] for x in lab],np.int32);models=fit_params(K,lab2,len(active));cost=state_costs(K,models);bits=float(cost[lab2,np.arange(K.shape[1])].sum())
        state_bits=int(math.ceil(math.log2(max(1,len(active)))))*K.shape[1];score=bits+state_bits
        row=(score,init,lab2,models,it+1,bits,state_bits)
        if best is None or row[0]<best[0]:best=row
    return best


def heldout_score(K,models):
    cost=state_costs(K,models);lab=np.argmin(cost,axis=0).astype(np.int32);sym=float(cost[lab,np.arange(K.shape[1])].sum());B=len(models);sb=int(math.ceil(math.log2(max(1,B))))*K.shape[1]
    cnt=np.bincount(lab,minlength=B);p=cnt[cnt>0].astype(np.float64)/K.shape[1];H=float(-(p*np.log2(p)).sum()) if len(p) else 0.0
    rep=float(np.mean(lab[1:]==lab[:-1])) if K.shape[1]>1 else 1.0
    return {'symbol_bits':sym,'raw_state_bits':sb,'total_bits':sym+sb,'state_counts':cnt.tolist(),'state_entropy_bps_per_time':H,'state_repeat_fraction':rep,'labels':lab}


def frame_bytes(K):
    total=0;reps={}
    for t0 in range(0,K.shape[1],TB):
        fr=m.encode_k(K[:,t0:t0+TB]);total+=int(fr[0])+20;reps[fr[1]]=reps.get(fr[1],0)+1
        if not np.array_equal(fr[2],K[:,t0:t0+fr[2].shape[1]]):raise RuntimeError('K decode')
    return total,reps


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;summary=[];rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co,mb,R,K=fit_build(X);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'hard',me,eps))
            actual,reps=frame_bytes(K[:,TRAIN:]);ns=C*(NT-TRAIN);actual_bps=8*actual/ns
            sz=0
            for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
            szbps=8*sz/ns
            for B in B_VALUES:
                tr=train_mixture(K[:,:TRAIN],B);_,init,lab,models,it,train_sym,train_state=tr;ho=heldout_score(K[:,TRAIN:],models);bps=ho['total_bits']/ns
                row={'region':name,'requested_states':B,'active_states':len(models),'initialization':init,'train_iterations':it,
                     'train_symbol_bps':train_sym/(C*TRAIN),'train_state_bps':train_state/(C*TRAIN),
                     'heldout_symbol_bps':ho['symbol_bits']/ns,'heldout_state_bps':ho['raw_state_bits']/ns,'heldout_bps':bps,
                     'heldout_state_counts':ho['state_counts'],'heldout_state_entropy_bps_per_time':ho['state_entropy_bps_per_time'],
                     'heldout_state_repeat_fraction':ho['state_repeat_fraction'],'actual_backend_bps':actual_bps,'gain_bps_vs_actual':actual_bps-bps,
                     'gain_ratio_vs_actual':actual_bps/bps,'matched_sz3_bps':szbps,'two_x_target_bps':szbps/2,'rate_over_2x_target':bps/(szbps/2)}
                rows.append(row);print(json.dumps(row,indent=2),flush=True)
            rr=[x for x in rows if x['region']==name];best=min(rr,key=lambda x:x['heldout_bps'])
            summary.append({'region':name,'c0':c0,'actual_ar32_heldout_bytes':actual,'actual_ar32_heldout_bps':actual_bps,'actual_reps':reps,
                            'matched_sz3_bps':szbps,'two_x_target_bps':szbps/2,'best':best,'maxerr':me,'model_bytes':mb})
    out={'global_std':std,'eps':eps,'train_samples':TRAIN,'heldout_samples':NT-TRAIN,'states':list(B_VALUES),'summary':summary,'rows':rows,
         'scope':('Prefix-derived latent vector-state rate screen, not yet a byte arithmetic-container claim. Current decoder-real AR32 step267 K is unchanged and hard-error verified. For each 128-channel region, a deterministic finite mixture of channel-specific zero-inflated signed-geometric innovation laws is derived only from the first 1024 decoded K vectors. Deterministic EM-like hard assignment is tried from prefix-derived RMS, time-modulo, first-PC and alternating-channel initializations; empty states are removed and no target statistics alter the models. For each held-out 128-channel time vector, the encoder chooses the model giving minimum full-vector negative log likelihood, transmits that state at raw ceil(log2 active_states) bits per 128-sample vector, then would arithmetic-code the 128 innovations under the chosen prefix-derived channel laws. Reported heldout symbol bits are ideal arithmetic codelengths under those fixed laws; state bits are fully charged raw. The actual incumbent K backend and matched SZ3 are rerun. If this arbitrary low-cardinality spatial regime code cannot reveal material rate, collective hidden-state explanations are strongly constrained. No AI/neural model.')}
    json.dump(out,open('imperial_ar32_latent_vector_state.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
