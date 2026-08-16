import json,sys,math,collections
import h5py,numpy as np
import imperial_ar32_restricted_address_sweep as s
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEP=266
P=32
BEAM=128
FINAL_PER_MODE=5
MODES=('freq','bits','abs','seed0','seed1','seed2')
HEADER=32
SELECTOR=1


def zzig(v):
    return 2*v if v>=0 else -2*v-1


def build_costs(K):
    vals=np.asarray(K,np.int32).ravel();cnt=collections.Counter(int(x) for x in vals)
    span=max(1,len(cnt));den=len(vals)+0.5*span
    freq={k:-math.log2((v+0.5)/den) for k,v in cnt.items()}
    U=np.array([zzig(int(x)) for x in vals],np.uint64);nb=max(1,int(U.max()).bit_length())
    bitp=[]
    for b in range(nb):
        p=(float(np.mean((U>>b)&1))*len(vals)+0.5)/(len(vals)+1.0)
        p=min(max(p,1e-8),1-1e-8);bitp.append(p)
    return cnt,freq,bitp


def symcost(k,mode,freq,bitp,t,c):
    base=freq.get(int(k),max(freq.values())+2.0)
    if mode=='freq':return base
    if mode=='abs':return math.log2(2+abs(int(k)))
    if mode=='bits':
        u=zzig(int(k));z=0.0
        for b,p in enumerate(bitp):z+=-math.log2(p if ((u>>b)&1) else (1-p))
        return z
    seed=int(mode[-1])
    # Deterministic tiny perturbation: encoder-only search diversification. It is not decoded or transmitted.
    h=((t+1)*0x9E3779B1 ^ (c+17)*0x85EBCA6B ^ (int(k)+257)*0xC2B2AE35 ^ seed*0x27D4EB2F)&0xffffffff
    noise=(h/4294967295.0)-0.5
    return base + 0.35*noise


def pred_hist(hist,t,coef):
    if t<P:return 0
    v=float(coef[-1])
    for j in range(P):v+=float(coef[j])*float(hist[-1-j])
    if not math.isfinite(v):raise RuntimeError(('nonfinite',t))
    return int(np.rint(v))


def beam_paths(x,eps,coef,mode,freq,bitp,cidx):
    # state = (surrogate score, last-P reconstructed history tuple, K prefix tuple)
    states=[(0.0,(),())];max_states=1;branch_events=0
    b=eps*(1-2e-12)
    for t in range(x.size):
        nxt=[]
        for sc,hist,ks in states:
            pred=pred_hist(hist,t,coef)
            lo=int(math.ceil((float(x[t])-b-pred)/STEP));hi=int(math.floor((float(x[t])+b-pred)/STEP))
            if lo>hi:raise RuntimeError(('empty legal',cidx,t,pred,x[t],lo,hi))
            if hi>lo:branch_events+=1
            for k in range(lo,hi+1):
                r=pred+STEP*k
                if abs(float(x[t])-r)>eps*(1+1e-10):raise RuntimeError(('candidate hard',cidx,t,k,r,x[t]))
                nh=(hist+(int(r),))[-P:]
                nxt.append((sc+symcost(k,mode,freq,bitp,t,cidx),nh,ks+(int(k),)))
        if len(nxt)>BEAM:
            nxt.sort(key=lambda q:q[0]);nxt=nxt[:BEAM]
        states=nxt;max_states=max(max_states,len(states))
    states.sort(key=lambda q:q[0])
    return [q[2] for q in states[:FINAL_PER_MODE]],{'mode':mode,'final_states':len(states),'max_states':max_states,'branch_events_seen':branch_events}


def replay_full(X,eps,coef,K):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,coef,P,'shared')+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('final hard',me,eps))
    return R,me


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    co=ar.fit_shared(X[:,:g.TRAIN],P);mb,coef=ar.model_frame(co)
    incumbent=g.ar32_baseline(X,eps)
    R0,K0,me0=s.build_ar(X,eps,STEP,coef)
    if R0 is None:raise RuntimeError(('baseline illegal',me0))
    rb0,_,RK0,det0=rr.restricted_rank_frame(K0)
    if not np.array_equal(RK0,K0):raise RuntimeError('baseline rank replay')
    baseline_total=int(mb)+int(rb0)+HEADER+SELECTOR
    K=np.ascontiguousarray(K0.copy());best_payload=int(rb0);audit=[];accepted=0
    for cidx in range(K.shape[0]):
        _,freq,bitp=build_costs(K)
        pool={tuple(int(v) for v in K[cidx])};mode_stats=[]
        for mode in MODES:
            paths,st=beam_paths(X[cidx],eps,coef,mode,freq,bitp,cidx);mode_stats.append(st);pool.update(paths)
        before=best_payload;bestrow=tuple(int(v) for v in K[cidx]);tested=0
        for cand in pool:
            if cand==bestrow:continue
            trial=K.copy();trial[cidx]=np.asarray(cand,np.int32)
            pb,_,Kd,_=rr.restricted_rank_frame(trial);tested+=1
            if not np.array_equal(Kd,trial):raise RuntimeError(('trial replay',cidx))
            if int(pb)<best_payload:
                best_payload=int(pb);bestrow=cand
        changed=bestrow!=tuple(int(v) for v in K[cidx])
        if changed:
            K[cidx]=np.asarray(bestrow,np.int32);accepted+=1
        audit.append({'channel':cidx,'candidate_paths':len(pool),'exact_streams_tested':tested,'payload_before':before,'payload_after':best_payload,'accepted':bool(changed),'mode_stats':mode_stats})
        print(json.dumps({k:v for k,v in audit[-1].items() if k!='mode_stats'}),flush=True)
    final_bytes,_,Kd,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError('final rank replay')
    R,me=replay_full(X,eps,coef,Kd)
    total=int(mb)+int(final_bytes)+HEADER+SELECTOR
    # Compare against the already proven step-267 restricted-rank winner from PR552, rerun locally for audit.
    R267,K267,me267=s.build_ar(X,eps,267,coef);b267,_,K267d,d267=rr.restricted_rank_frame(K267)
    if not np.array_equal(K267d,K267):raise RuntimeError('267 replay')
    winner267=int(mb)+int(b267)+HEADER+SELECTOR
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'beam':BEAM,'modes':list(MODES),'final_per_mode':FINAL_PER_MODE,'model_bytes':int(mb),'baseline_step266':{'bytes':baseline_total,'payload_bytes':int(rb0),'maxerr':me0},'pr552_step267_rerun':{'bytes':winner267,'payload_bytes':int(b267),'maxerr':me267},'nova_trellis':{'bytes':total,'payload_bytes':int(final_bytes),'maxerr':me,'accepted_channels':accepted,'gain_vs_step266':baseline_total/total,'gain_vs_pr552':winner267/total,'gain_vs_incumbent_ar32':incumbent['bytes']/total,'gain_vs_sz3':szb/total,'delta_vs_pr552':total-winner267,'delta_vs_incumbent_ar32':total-incumbent['bytes'],'detail':detail},'incumbent_ar32':incumbent,'sz3':{'bytes':int(szb),'orientation':ori},'audit':audit,'scope':'Decoder-real NOVA trellis gate on the winning AR32 coordinate system. At public step 266 (<2*epsilon), some causal AR32 samples admit more than one integer K whose reconstructed value stays inside the unchanged hard-error interval. The encoder spends computation exploring those branching per-channel trajectories with several deterministic beam-search scoring configurations, then evaluates the finalists using the ACTUAL PR512 restricted-rank byte stream. Only a candidate that physically shortens that exact stream is accepted. Search scores, beams, branches and search paths are not transmitted because the final K field is transmitted in full; decoder needs only the already charged AR32 model, public step selector, and exact restricted-rank K stream. Final K is independently decoded, the full AR32 reconstruction is causally replayed, and source max error is checked. This is the literal computation-for-communication principle: more encoder search, fewer transmitted bits.'}
    json.dump(out,open('imperial_ar32_nova_trellis_address.json','w'),indent=2)
    print(json.dumps({'summary':{'step266_before':baseline_total,'step266_after':total,'pr552_step267':winner267,'incumbent_ar32':incumbent['bytes'],'sz3':int(szb),'accepted_channels':accepted,'delta_vs_pr552':total-winner267,'gain_vs_pr552':winner267/total,'gain_vs_ar32':incumbent['bytes']/total,'gain_vs_sz3':szb/total}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
