import json,sys,math,collections
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

P=8
STEP=266
TRAIN=256
BEAM=256
FINAL_PER_MODE=8
MODES=('freq','bits','abs','seed0','seed1','seed2')
HEADER=32
SELECTOR=1


def zzig(v):return 2*v if v>=0 else -2*v-1

def build_costs(K):
    vals=np.asarray(K,np.int32).ravel();cnt=collections.Counter(int(x) for x in vals);span=max(1,len(cnt));den=len(vals)+0.5*span
    freq={k:-math.log2((v+0.5)/den) for k,v in cnt.items()}
    U=np.array([zzig(int(x)) for x in vals],np.uint64);nb=max(1,int(U.max()).bit_length());bitp=[]
    for b in range(nb):
        p=(float(np.mean((U>>b)&1))*len(vals)+0.5)/(len(vals)+1.0);p=min(max(p,1e-8),1-1e-8);bitp.append(p)
    return freq,bitp

def symcost(k,mode,freq,bitp,t,c):
    base=freq.get(int(k),max(freq.values())+2.0)
    if mode=='freq':return base
    if mode=='abs':return math.log2(2+abs(int(k)))
    if mode=='bits':
        u=zzig(int(k));z=0.0
        for b,p in enumerate(bitp):z+=-math.log2(p if ((u>>b)&1) else (1-p))
        return z
    seed=int(mode[-1]);h=((t+1)*0x9E3779B1 ^ (c+17)*0x85EBCA6B ^ (int(k)+257)*0xC2B2AE35 ^ seed*0x27D4EB2F)&0xffffffff
    return base+0.45*((h/4294967295.0)-0.5)

def pred_hist(hist,t,coef):
    if t<P:return 0
    v=float(coef[-1])
    for j in range(P):v+=float(coef[j])*float(hist[-1-j])
    return int(np.rint(v))

def beam_paths(x,eps,coef,mode,freq,bitp,cidx):
    states=[(0.0,(),())];b=eps*(1-2e-12);max_states=1;branches=0
    for t in range(x.size):
        nxt=[]
        for sc,hist,ks in states:
            pred=pred_hist(hist,t,coef);lo=int(math.ceil((float(x[t])-b-pred)/STEP));hi=int(math.floor((float(x[t])+b-pred)/STEP))
            if lo>hi:raise RuntimeError(('empty legal',cidx,t,pred,x[t],lo,hi))
            if hi>lo:branches+=1
            for k in range(lo,hi+1):
                r=pred+STEP*k
                if abs(float(x[t])-r)>eps*(1+1e-10):raise RuntimeError(('hard candidate',cidx,t,k,r,x[t]))
                nxt.append((sc+symcost(k,mode,freq,bitp,t,cidx),(hist+(int(r),))[-P:],ks+(int(k),)))
        if len(nxt)>BEAM:
            nxt.sort(key=lambda q:q[0]);nxt=nxt[:BEAM]
        states=nxt;max_states=max(max_states,len(states))
    states.sort(key=lambda q:q[0])
    return [q[2] for q in states[:FINAL_PER_MODE]],{'mode':mode,'final_states':len(states),'max_states':max_states,'branch_events_seen':branches}

def build_nearest(X,eps,coef,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,P,'shared');k=int(np.rint((float(X[c,t])-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('nearest hard',step,me,eps))
    return R,K,me

def replay(X,eps,coef,K,step):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,coef,P,'shared')+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('final hard',step,me,eps))
    return R,me

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps)
    co=ar.fit_shared(X[:,:TRAIN],P);mb,coef=ar.model_frame(co)
    R0,K0,me0=build_nearest(X,eps,coef,STEP);b0,_,K0d,d0=rr.restricted_rank_frame(K0)
    if not np.array_equal(K0d,K0):raise RuntimeError('266 baseline replay')
    base266=int(mb)+int(b0)+HEADER+SELECTOR
    R7,K7,me7=build_nearest(X,eps,coef,267);b7,_,K7d,d7=rr.restricted_rank_frame(K7)
    if not np.array_equal(K7d,K7):raise RuntimeError('267 baseline replay')
    base267=int(mb)+int(b7)+HEADER+SELECTOR
    K=np.ascontiguousarray(K0.copy());best_payload=int(b0);audit=[];accepted=0
    for cidx in range(K.shape[0]):
        freq,bitp=build_costs(K);pool={tuple(int(v) for v in K[cidx])};stats=[]
        for mode in MODES:
            pp,st=beam_paths(X[cidx],eps,coef,mode,freq,bitp,cidx);pool.update(pp);stats.append(st)
        before=best_payload;cur=tuple(int(v) for v in K[cidx]);bestrow=cur;tested=0
        for cand in pool:
            if cand==cur:continue
            trial=K.copy();trial[cidx]=np.asarray(cand,np.int32);pb,_,Kd,_=rr.restricted_rank_frame(trial);tested+=1
            if not np.array_equal(Kd,trial):raise RuntimeError(('trial rank replay',cidx))
            if int(pb)<best_payload:best_payload=int(pb);bestrow=cand
        changed=bestrow!=cur
        if changed:K[cidx]=np.asarray(bestrow,np.int32);accepted+=1
        audit.append({'channel':cidx,'candidate_paths':len(pool),'exact_streams_tested':tested,'payload_before':before,'payload_after':best_payload,'accepted':bool(changed),'mode_stats':stats})
        print(json.dumps({k:v for k,v in audit[-1].items() if k!='mode_stats'}),flush=True)
    bf,_,Kf,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kf,K):raise RuntimeError('final rank replay')
    _,me=replay(X,eps,coef,Kf,STEP);total=int(mb)+int(bf)+HEADER+SELECTOR
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':P,'step':STEP,'beam':BEAM,'final_per_mode':FINAL_PER_MODE,'modes':list(MODES),'model_bytes':int(mb),'ar8_step266_baseline':{'bytes':base266,'payload_bytes':int(b0),'maxerr':me0},'ar8_step267_floor':{'bytes':base267,'payload_bytes':int(b7),'maxerr':me7},'nova':{'bytes':total,'payload_bytes':int(bf),'maxerr':me,'accepted_channels':accepted,'delta_vs_ar8_267':total-base267,'gain_vs_ar8_267':base267/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total,'detail':detail},'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'audit':audit,'scope':'Decoder-real AR8 NOVA trajectory search. PR564 established AR8 step267 + exact restricted ranking as the current 23,448-byte hard-tile champion. This gate moves to step266, where the same AR8 causal coordinate system creates more source-legal branch choices. The encoder explores those legal trajectories per channel using several deterministic beam objectives, but finalists are accepted only when the physically serialized full PR512 restricted-rank K stream becomes smaller. Search path/beam/score are encoder computation and are not transmitted; the final K stream is independently decoded and causally replayed with the charged AR8 model, then the original source hard-error bound is verified. The AR8 step267 champion is rerun in the same job as the strict floor.'}
    json.dump(out,open('imperial_ar8_nova_trellis_address.json','w'),indent=2)
    print(json.dumps({'summary':{'ar8_266_before':base266,'ar8_266_after':total,'ar8_267_floor':base267,'old_ar32':old['bytes'],'sz3':int(szb),'accepted_channels':accepted,'delta_vs_ar8_267':total-base267,'gain_vs_ar8_267':base267/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
