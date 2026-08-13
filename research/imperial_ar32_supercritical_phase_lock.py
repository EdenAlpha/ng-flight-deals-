import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512; C=128; P=32; TRAIN=1024; END=3072
CHANNELS=(0,32,64,96)
COARSE_STEPS=(267,320,384,512,768)
RESET_STEP=128; BEAM=24
RESET_PENALTIES=(2.0,6.0,12.0)
SAFETY=1-1e-9
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P); mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P: pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P): v += float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/267.0).astype(np.int64)
        R[:,t]=pred+267*k
    me=float(np.max(np.abs(X[:,:TRAIN]-R)))
    if me>eps*(1+1e-10): raise RuntimeError(('prefix hard',me,eps))
    return mb,cd,R

def pred_from_state(states,co):
    B=states.shape[0]
    v=np.full(B,float(co[-1]),np.float64)
    for j in range(P): v += float(co[j])*states[:,-1-j]
    return np.rint(v).astype(np.int64)

def symbol_cost(k):
    return math.log2(1.0+abs(int(k)))

def beam_channel(x,co,prefix_r,eps,step,reset_penalty):
    L=len(x); W=BEAM
    states=prefix_r[-P:].astype(np.int64)[None,:].copy()
    costs=np.zeros(1,np.float64)
    parents=np.full((L,W),-1,np.int16)
    kinds=np.zeros((L,W),np.uint8)
    syms=np.zeros((L,W),np.int32)
    counts=np.zeros(L,np.int16)
    total_reset_cands=0; total_coarse_cands=0; parent_no_coarse=0
    bound=eps*SAFETY
    for t in range(L):
        pred=pred_from_state(states,co); cand=[]
        for b in range(states.shape[0]):
            lo=int(math.ceil((float(x[t])-bound-int(pred[b]))/step-1e-12))
            hi=int(math.floor((float(x[t])+bound-int(pred[b]))/step+1e-12))
            had=False
            if lo<=hi:
                for k in range(lo,hi+1):
                    rr=int(pred[b])+step*k
                    if abs(float(x[t])-rr)<=eps*(1+1e-10):
                        had=True; total_coarse_cands+=1
                        cc=float(costs[b])+symbol_cost(k)
                        cand.append((cc,0,abs(k),b,k,rr))
            if not had: parent_no_coarse+=1
            rlo=int(math.ceil((float(x[t])-bound-int(pred[b]))/RESET_STEP-1e-12))
            rhi=int(math.floor((float(x[t])+bound-int(pred[b]))/RESET_STEP+1e-12))
            if rlo>rhi: raise RuntimeError(('no reset state',t,b,pred[b],x[t]))
            for q in range(rlo,rhi+1):
                rr=int(pred[b])+RESET_STEP*q
                if abs(float(x[t])-rr)>eps*(1+1e-10): continue
                total_reset_cands+=1
                cc=float(costs[b])+reset_penalty+0.35*symbol_cost(q)
                cand.append((cc,1,abs(q),b,q,rr))
        if not cand: raise RuntimeError(('beam died',step,reset_penalty,t))
        cand.sort(key=lambda z:(z[0],z[1],z[2],z[4],z[3]))
        sel=cand[:W]; B2=len(sel)
        ns=np.empty((B2,P),np.int64); nc=np.empty(B2,np.float64)
        for q,z in enumerate(sel):
            cc,kind,_,b,sym,rr=z
            ns[q,:-1]=states[b,1:]; ns[q,-1]=rr; nc[q]=cc
            parents[t,q]=b; kinds[t,q]=kind; syms[t,q]=sym
        counts[t]=B2; states,costs=ns,nc
    b=int(np.argmin(costs)); kind=np.empty(L,np.uint8); sym=np.empty(L,np.int64)
    for t in range(L-1,-1,-1):
        kind[t]=kinds[t,b]; sym[t]=syms[t,b]; b=int(parents[t,b])
        if t>0 and b<0: raise RuntimeError(('bad traceback',t,b))
    return kind,sym,{'reset_fraction':float(np.mean(kind==1)),
                     'parent_no_coarse_fraction':float(parent_no_coarse/max(1,sum(int(v) for v in counts))),
                     'mean_coarse_candidates_per_step':float(total_coarse_cands/L),
                     'mean_reset_candidates_per_step':float(total_reset_cands/L),
                     'final_beams':int(counts[-1])}

def reconstruct(kind,sym,co,prefix_r,step):
    state=prefix_r[-P:].astype(np.int64).copy(); out=np.empty(len(sym),np.int64)
    for t in range(len(sym)):
        v=float(co[-1])
        for j in range(P): v += float(co[j])*state[-1-j]
        pred=int(np.rint(v)); ss=RESET_STEP if int(kind[t]) else step
        rr=pred+ss*int(sym[t]); out[t]=rr
        state[:-1]=state[1:]; state[-1]=rr
    return out

def kframe(vals):
    vals=np.asarray(vals,np.int64).ravel()
    if vals.size==0: return 0,'empty',vals.copy()
    b,rep,dec=m.encode_k(vals.reshape(1,-1))
    return int(b)+20,rep,np.asarray(dec,dtype=np.int64).ravel()

def real_bytes(KIND,SYM):
    flatk=KIND.ravel(); flats=SYM.ravel(); mask=(flatk==1)
    mb=ZC.compress(np.packbits(mask.astype(np.uint8),bitorder='little').tobytes())
    mdec=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little')[:mask.size].astype(bool)
    if not np.array_equal(mdec,mask): raise RuntimeError('mask decode')
    cb,crep,cdec=kframe(flats[~mask]); rb,rrep,rdec=kframe(flats[mask])
    out=np.empty_like(flats); out[~mdec]=cdec; out[mdec]=rdec
    if not np.array_equal(out,flats): raise RuntimeError('symbol frame decode')
    total=len(mb)+20+cb+rb+8
    return total,{'mask_bytes':len(mb)+20,'coarse_bytes':cb,'reset_bytes':rb,'coarse_rep':crep,'reset_rep':rrep,'reset_fraction':float(mask.mean())},mdec.reshape(KIND.shape),out.reshape(SYM.shape)

def greedy_baseline(X,co,R0,eps,step=267):
    KK=[]; RR=[]
    for c in CHANNELS:
        state=R0[c,-P:].astype(np.int64).copy(); klist=[]; rlist=[]
        for xx in X[c,TRAIN:END]:
            v=float(co[-1])
            for j in range(P): v+=float(co[j])*state[-1-j]
            pred=int(np.rint(v)); k=int(np.rint((float(xx)-pred)/step)); rr=pred+step*k
            if abs(float(xx)-rr)>eps*(1+1e-10): raise RuntimeError(('baseline hard',c,xx,pred,k,rr))
            klist.append(k);rlist.append(rr);state[:-1]=state[1:];state[-1]=rr
        KK.append(klist);RR.append(rlist)
    KK=np.asarray(KK,np.int64);RR=np.asarray(RR,np.int64); bb,rep,dec=kframe(KK)
    if not np.array_equal(dec.reshape(KK.shape),KK): raise RuntimeError('baseline decode')
    return KK,RR,bb+8,rep

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,std=m.stats(d); eps=.1*std; X=np.asarray(d[:,C0:C0+C],np.float64).T
    mb,co,R0=fit_prefix(X,eps)
    G,GR,gb,grep=greedy_baseline(X,co,R0,eps,267)
    gme=float(np.max(np.abs(X[list(CHANNELS),TRAIN:END]-GR)))
    rows=[]
    for step in COARSE_STEPS:
        for pen in RESET_PENALTIES:
            KIND=[];SYM=[];sts=[]
            for c in CHANNELS:
                ki,sy,st=beam_channel(X[c,TRAIN:END],co,R0[c],eps,step,pen);KIND.append(ki);SYM.append(sy);sts.append(st)
            KIND=np.stack(KIND);SYM=np.stack(SYM)
            total,parts,kd,sd=real_bytes(KIND,SYM)
            RR=[]
            for i,c in enumerate(CHANNELS): RR.append(reconstruct(kd[i].astype(np.uint8),sd[i],co,R0[c],step))
            RR=np.stack(RR);me=float(np.max(np.abs(X[list(CHANNELS),TRAIN:END]-RR)))
            if me>eps*(1+1e-10): raise RuntimeError(('candidate hard',step,pen,me,eps))
            row={'step':step,'reset_penalty':pen,'bytes':total,'bps':8*total/KIND.size,'gain_vs_step267':gb/total,
                 'baseline_bytes':gb,'baseline_bps':8*gb/G.size,'maxerr':me,'baseline_maxerr':gme,
                 'reset_fraction':parts['reset_fraction'],'mask_bytes':parts['mask_bytes'],'coarse_bytes':parts['coarse_bytes'],'reset_bytes':parts['reset_bytes'],
                 'coarse_rep':parts['coarse_rep'],'reset_rep':parts['reset_rep'],
                 'median_parent_no_coarse_fraction':float(np.median([s['parent_no_coarse_fraction'] for s in sts])),
                 'median_mean_coarse_candidates_per_step':float(np.median([s['mean_coarse_candidates_per_step'] for s in sts]))}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);best=rows[0]
    out={'global_std':std,'eps':eps,'ar_order':P,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0+c for c in CHANNELS],
         'beam_width':BEAM,'coarse_steps':list(COARSE_STEPS),'reset_step':RESET_STEP,'reset_penalties':list(RESET_PENALTIES),'model_bytes':mb,
         'baseline':{'step':267,'bytes':gb,'bps':8*gb/G.size,'rep':grep,'maxerr':gme},'best':best,'rows':rows,
         'scope':'Supercritical-lattice phase-lock gate. Persistent shared AR32 is fit only on hard-region t<1024. A legal step-267 prefix seeds decoder state. On four held-out hard-zone channels, the normal innovation lattice is deliberately widened beyond the universal 2epsilon covering limit (267/320/384/512/768). At each future sample a path may emit a coarse-lattice innovation if it lands inside the unchanged +/-10%-global-std box, or spend a 128-step legal reset state. A width-24 beam may choose resets even when coarse emission is currently possible, allowing distortion to steer future AR predictor phase. Final accounting uses an actually compressed reset mask plus separately self-decoded coarse/reset integer streams; decoded symbols regenerate the exact AR state and every sample is hard-error verified. Step267 greedy is rerun as the real-byte incumbent. No AI; directional hard-zone gate, not whole-array.'}
    print(json.dumps({'baseline':out['baseline'],'best':best},indent=2),flush=True);json.dump(out,open('imperial_ar32_supercritical_phase_lock.json','w'),indent=2)
if __name__=='__main__': main(sys.argv[1])
