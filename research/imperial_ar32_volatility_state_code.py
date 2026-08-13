import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r
import imperial_persistent_ar32_full_array_jit as a

STEP=267;P=32;C=128;TRAIN=1024;NT=8192;TB=1024
m.STEP=STEP;a.m.m.STEP=STEP
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
GROUP_SIZES=(128,64,32,16)
STATE_COUNTS=(2,4,8,16)


def fit_build(X):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);R,K=a.build(X,cd)
    return cd,int(mb),R,K


def state_thresholds(scale,B):
    q=np.arange(1,B,dtype=np.float64)/B
    th=np.quantile(np.asarray(scale,np.float64),q,method='linear') if len(q) else np.empty(0)
    return np.asarray(th,np.float64)


def states(scale,th):return np.searchsorted(th,np.asarray(scale,np.float64),side='right').astype(np.int16)


def fit_zig_model(vals):
    x=np.asarray(vals,np.int64).ravel();n=len(x)
    if n==0:return {'p0':0.5,'pplus':0.5,'r':0.5,'n':0}
    z=x==0;n0=int(z.sum());nz=n-n0
    p0=(n0+0.5)/(n+1.0)
    if nz==0:return {'p0':p0,'pplus':0.5,'r':0.5,'n':n}
    xx=x[~z];npos=int((xx>0).sum());pplus=(npos+0.5)/(nz+1.0)
    sm=float((np.abs(xx)-1).sum());mean=(sm+0.5)/(nz+1.0);rr=mean/(1.0+mean)
    rr=float(np.clip(rr,1e-8,1-1e-8));return {'p0':float(p0),'pplus':float(pplus),'r':rr,'n':n}


def nll(vals,model):
    x=np.asarray(vals,np.int64).ravel();p0=model['p0'];pp=model['pplus'];rr=model['r'];z=x==0
    bits=np.empty(len(x),np.float64);bits[z]=-math.log2(max(p0,1e-300))
    if np.any(~z):
        q=x[~z];sg=np.where(q>0,pp,1-pp);mag=np.abs(q)-1
        bits[~z]=-np.log2(np.maximum(1-p0,1e-300))-np.log2(np.maximum(sg,1e-300))-math.log2(max(1-rr,1e-300))-mag*np.log2(max(rr,1e-300))
    return float(bits.sum())


def frame_bytes(K):
    total=0;reps={}
    for t0 in range(0,K.shape[1],TB):
        fr=m.encode_k(K[:,t0:t0+TB]);total+=int(fr[0])+20;reps[fr[1]]=reps.get(fr[1],0)+1
        if not np.array_equal(fr[2],K[:,t0:t0+fr[2].shape[1]]):raise RuntimeError('K decode')
    return total,reps


def evaluate(K,G,B):
    nc,nt=K.shape;held=nt-TRAIN;bits=0.0;state_raw_bits=0;models=[];state_diag=[]
    for c0 in range(0,nc,G):
        A=K[c0:c0+G]
        # One collective volatility statistic describes G simultaneous innovations.
        trscale=np.sqrt(np.mean(A[:,:TRAIN].astype(np.float64)**2,axis=0))
        tesca=np.sqrt(np.mean(A[:,TRAIN:].astype(np.float64)**2,axis=0))
        th=state_thresholds(trscale,B);st=states(trscale,th);se=states(tesca,th)
        mm=[]
        for s in range(B):mm.append(fit_zig_model(A[:,:TRAIN][:,st==s]))
        for s in range(B):
            mask=se==s
            if np.any(mask):bits+=nll(A[:,TRAIN:][:,mask],mm[s])
        state_raw_bits+=int(math.ceil(math.log2(B)))*held
        # Report state persistence/occupancy; raw fixed bits remain the charged cost.
        cnt=np.bincount(se,minlength=B);p=cnt[cnt>0].astype(np.float64)/held
        h=float(-(p*np.log2(p)).sum()) if len(p) else 0.0
        same=float(np.mean(se[1:]==se[:-1])) if held>1 else 1.0
        state_diag.append({'c0':c0,'thresholds':th.tolist(),'held_counts':cnt.tolist(),'held_entropy_bps_per_state':h,'held_repeat_fraction':same})
        models.append({'c0':c0,'models':mm})
    total=bits+state_raw_bits
    ns=nc*held
    return {'group_size':G,'state_count':B,'symbol_crossentropy_bits':bits,'raw_state_bits':state_raw_bits,
            'total_bits':total,'bps':total/ns,'symbol_bps':bits/ns,'state_bps':state_raw_bits/ns,
            'state_diagnostics':state_diag,'prefix_models':models}


def unconditioned(K,G):
    bits=0.0;nc,nt=K.shape;held=nt-TRAIN
    for c0 in range(0,nc,G):
        A=K[c0:c0+G];model=fit_zig_model(A[:,:TRAIN]);bits+=nll(A[:,TRAIN:],model)
    return bits/(nc*held)


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];summary=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co,mb,R,K=fit_build(X)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'hard',me,eps))
            actual,areps=frame_bytes(K[:,TRAIN:]);ns=C*(NT-TRAIN);actual_bps=8*actual/ns
            sz=0
            for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
            szbps=8*sz/ns
            combos=[]
            for G in GROUP_SIZES:
                base=unconditioned(K,G)
                for B in STATE_COUNTS:
                    q=evaluate(K,G,B);q['unconditioned_same_model_bps']=base;q['gain_bps_vs_unconditioned_model']=base-q['bps'];q['gain_bps_vs_actual_backend']=actual_bps-q['bps'];q['region']=name
                    combos.append(q)
            combos.sort(key=lambda x:x['bps']);best=combos[0]
            sr={'region':name,'c0':c0,'actual_ar32_heldout_bytes':actual,'actual_ar32_heldout_bps':actual_bps,'actual_reps':areps,
                'matched_sz3_bytes':sz,'matched_sz3_bps':szbps,'two_x_sz3_target_bps':szbps/2,'best':best,
                'best_gain_vs_actual':actual_bps/best['bps'],'best_over_2x_target':best['bps']/(szbps/2),'maxerr':me,'model_bytes':mb}
            summary.append(sr);rows.extend(combos);print(json.dumps({'summary':{k:v for k,v in sr.items() if k!='best'},'best':{k:v for k,v in best.items() if k not in ('state_diagnostics','prefix_models')}},indent=2),flush=True)
    out={'global_std':std,'eps':eps,'train_samples':TRAIN,'heldout_samples':NT-TRAIN,'order':P,'step':STEP,
         'group_sizes':list(GROUP_SIZES),'state_counts':list(STATE_COUNTS),'summary':summary,'rows':rows,
         'scope':('Collective-dependence rate screen, not yet a byte-container claim. Current decoder-real AR32 step267 innovations are unchanged, so hard-error reconstruction is identical and independently checked. For each 128-channel region, subgroups of G=128/64/32/16 channels share one volatility state per time sample. State thresholds and a zero-inflated signed-geometric innovation law for each state are learned only from the decoded first 1024 innovation samples. Held-out states are derived from the target subgroup RMS and therefore must be transmitted; this screen conservatively charges ceil(log2 B) raw bits per subgroup/time, i.e. log2(B)/G bits/sample, with no state compression. Held-out K symbols are scored under the prefix-trained state-conditioned probability law. An identical unconditioned signed-geometric model, the actual incumbent K backend, and matched SZ3 are reported. If the state-conditioned cross-entropy materially drops, the next branch will implement a real arithmetic coder; otherwise shared volatility cannot contain the missing ~1.1 bps. No AI.')}
    json.dump(out,open('imperial_ar32_volatility_state_code.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
