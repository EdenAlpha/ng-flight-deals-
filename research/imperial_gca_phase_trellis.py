import json,math,sys
import h5py,numpy as np
import imperial_ar1_legal_trajectory_address as lt
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=lt.A;STEP=267;RAD=133;BEAM=64
PHASESETS=(('binary_extreme',(-133,133)),('ternary',(-133,0,133)),('quad',(-133,-44,44,133)))
LAMBDAS=(0.0,0.75,2.0)


def search_channel(x,coef,eps,C,left,phases,lam):
    a=float(coef[0]);b=float(coef[-1]);mid=min(range(len(phases)),key=lambda i:abs(phases[i]))
    states={(0,0,mid):0.0};layers=[];mx=1
    for t in range(x.size):
        cand={}
        for key,score in states.items():
            rp,prevk,prevbid=key;pred=0 if t==0 else int(np.rint(b+a*float(rp)));lk=int(left[t]) if left is not None else 0
            for bid,d in enumerate(phases):
                n=float(x[t])-pred-int(d);k=int(math.floor((n+RAD)/STEP+1e-12));r=pred+int(d)+STEP*k
                if abs(float(x[t])-r)>eps*(1+5e-10):continue
                sc=score+lt.local_cost('symbol_causal',k,prevk,lk,C)
                if t and bid!=prevbid:sc+=lam
                nk=(int(r),int(k),int(bid));old=cand.get(nk);row=(sc,key,int(k),int(bid))
                if old is None or sc<old[0]:cand[nk]=row
        if not cand:raise RuntimeError(('no legal phase state',t,phases,lam))
        if len(cand)>BEAM:cand=dict(sorted(cand.items(),key=lambda z:z[1][0])[:BEAM])
        layers.append(cand);states={k:v[0] for k,v in cand.items()};mx=max(mx,len(states))
    key=min(states,key=states.get);K=np.empty(x.size,np.int32);B=np.empty(x.size,np.int32);switches=0
    for t in range(x.size-1,-1,-1):
        sc,prev,k,bid=layers[t][key];K[t]=k;B[t]=bid
        if t and bid!=prev[2]:switches+=1
        key=prev
    return K,B,float(min(states.values())),switches,mx


def optimize(X,coef,K0,eps,phases,lam,C):
    K=K0.copy();B=np.zeros_like(K0,np.int32);sw=0;mx=0;scores=[]
    for c in range(K.shape[0]):
        left=K[c-1] if c else None
        k,b,sc,ss,mm=search_channel(X[c],coef,eps,C,left,phases,lam);K[c]=k;B[c]=b;sw+=ss;mx=max(mx,mm);scores.append(sc)
    R=np.zeros_like(K)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared');R[c,t]=pred+int(phases[int(B[c,t])])+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return K,B,R,{'switches':int(sw),'switch_fraction':sw/max(1,B.size-B.shape[0]),'max_beam_states':mx,'proxy_score':float(sum(scores)),'maxerr':me}


def replay(K,B,coef,phases):
    R=np.zeros_like(K)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared');R[c,t]=pred+int(phases[int(B[c,t])])+STEP*int(K[c,t])
    return R


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=fair.fit(X,1,'prefix64');model,mname=fair.encode_model(co);coef,pos=fair.decode_model(model,0,2)
    if pos!=len(model):raise RuntimeError('model trailing')
    R0,K0=fair.build(X,1,coef);basefb,_,Kd0,base_detail=A.hybrid_frame(K0)
    if not np.array_equal(Kd0,K0):raise RuntimeError('baseline K')
    base=fair.COMMON_HEADER+1+len(model)+int(basefb);C=lt.cost_model(K0);rows=[]
    for name,phases in PHASESETS:
        for lam in LAMBDAS:
            K,B,R,diag=optimize(X,coef,K0,eps,phases,lam,C)
            kfb,_,Kd,kdetail=A.hybrid_frame(K);bfb,_,Bd,bdetail=A.hybrid_frame(B)
            if not np.array_equal(Kd,K) or not np.array_equal(Bd,B):raise RuntimeError(('field replay',name,lam))
            Rd=replay(Kd,Bd,coef,phases)
            if not np.array_equal(Rd,R):raise RuntimeError(('source replay',name,lam))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard',name,lam,me,eps))
            total=fair.COMMON_HEADER+1+len(model)+1+int(kfb)+int(bfb)
            row={'phase_set':name,'phases':list(phases),'switch_penalty_bits':lam,'bytes':int(total),'delta_vs_baseline':int(total-base),'k_field_bytes':int(kfb),'phase_field_bytes':int(bfb),'model_bytes':len(model),'maxerr':me,'switches':diag['switches'],'switch_fraction':diag['switch_fraction'],'max_beam_states':diag['max_beam_states'],'proxy_score':diag['proxy_score'],'changed_k':int(np.sum(K!=K0)),'k_detail':kdetail,'phase_detail':bdetail}
            rows.append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('k_detail','phase_detail')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'beam':BEAM,'phase_sets':[(n,list(p)) for n,p in PHASESETS],'switch_penalties':list(LAMBDAS),'model_bytes':len(model),'model_rep':mname,'common_header_bytes':fair.COMMON_HEADER,'baseline_bytes':int(base),'baseline_k_field_bytes':int(basefb),'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Exact phase-choice trellis GCA on the strict AR1/prefix64 hard mini-tile. At each sample the encoder may choose one public lattice phase, then the unique K whose reconstruction lies inside the unchanged hard-error interval. A beam search optimizes the recursively coupled AR trajectory, with optional switching penalty to make the phase path cheaper. No phase choices are free: the full phase-index field and K field are separately materialized with the same exact hybrid arithmetic/rank frame and independently decoded. The decoder replays the selected public phase set plus AR1 model to reconstruct every sample and rechecks hard error. Final winner is actual combined bytes only.'};json.dump(out,open('imperial_gca_phase_trellis.json','w'),indent=2);print(json.dumps({'summary':{'baseline':base,'best':best['bytes'],'delta':best['bytes']-base,'phase_set':best['phase_set'],'lambda':best['switch_penalty_bits'],'k_field':best['k_field_bytes'],'phase_field':best['phase_field_bytes'],'changed_k':best['changed_k'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
