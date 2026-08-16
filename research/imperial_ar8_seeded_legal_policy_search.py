import json,sys,math,collections
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

P=8
TRAIN=256
STEP=266
NSEEDS=20
HEADER=32
SELECTOR=1


def zz(v):return 2*v if v>=0 else -2*v-1

def costs(K):
    vals=np.asarray(K,np.int32).ravel();cnt=collections.Counter(int(v) for v in vals);den=len(vals)+0.5*max(1,len(cnt));freq={k:-math.log2((n+0.5)/den) for k,n in cnt.items()}
    U=np.array([zz(int(v)) for v in vals],np.uint64);nb=max(1,int(U.max()).bit_length());bp=[]
    for b in range(nb):
        p=(float(np.mean((U>>b)&1))*len(vals)+0.5)/(len(vals)+1);bp.append(min(max(p,1e-8),1-1e-8))
    return freq,bp

def pred(hist,t,coef):
    if t<P:return 0
    v=float(coef[-1])
    for j in range(P):v+=float(coef[j])*float(hist[-1-j])
    return int(np.rint(v))

def bcost(k,bp):
    u=zz(int(k));z=0.0
    for b,p in enumerate(bp):z+=-math.log2(p if ((u>>b)&1) else 1-p)
    return z

def path_policy(x,eps,coef,cidx,policy,freq,bp):
    hist=();ks=[];b=eps*(1-2e-12);branches=0
    for t in range(x.size):
        pr=pred(hist,t,coef);lo=int(math.ceil((float(x[t])-b-pr)/STEP));hi=int(math.floor((float(x[t])+b-pr)/STEP))
        if lo>hi:raise RuntimeError(('empty',cidx,t,pr,x[t]))
        opts=list(range(lo,hi+1))
        if len(opts)>1:
            branches+=1
            if policy=='freq':k=min(opts,key=lambda q:freq.get(int(q),max(freq.values())+2))
            elif policy=='bits':k=min(opts,key=lambda q:bcost(q,bp))
            elif policy=='abs':k=min(opts,key=lambda q:(abs(q),q))
            elif policy=='nearest':k=min(opts,key=lambda q:abs(float(x[t])-(pr+STEP*q)))
            else:
                seed=int(policy[4:]);h=((t+1)*0x9E3779B1 ^ (cidx+1)*0x85EBCA6B ^ seed*0xC2B2AE35)&0xffffffff;k=opts[h%len(opts)]
        else:k=opts[0]
        r=pr+STEP*k
        if abs(float(x[t])-r)>eps*(1+1e-10):raise RuntimeError(('hard candidate',cidx,t,k,r,x[t]))
        hist=(hist+(int(r),))[-P:];ks.append(int(k))
    return tuple(ks),branches

def nearest(X,eps,coef,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pr=ar.predict_hist(R,c,t,coef,P,'shared');k=int(np.rint((float(X[c,t])-pr)/step));R[c,t]=pr+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('nearest hard',step,me))
    return R,K,me

def replay(X,eps,coef,K,step):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,coef,P,'shared')+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('replay hard',step,me))
    return me

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);co=ar.fit_shared(X[:,:TRAIN],P);mb,coef=ar.model_frame(co)
    _,K0,me0=nearest(X,eps,coef,STEP);b0,_,K0d,d0=rr.restricted_rank_frame(K0);base266=int(mb)+int(b0)+HEADER+SELECTOR
    _,K7,me7=nearest(X,eps,coef,267);b7,_,K7d,d7=rr.restricted_rank_frame(K7);floor267=int(mb)+int(b7)+HEADER+SELECTOR
    K=np.ascontiguousarray(K0.copy());best_payload=int(b0);audit=[];accepted=0
    policies=('nearest','freq','bits','abs')+tuple(f'seed{i}' for i in range(NSEEDS))
    for cidx in range(K.shape[0]):
        freq,bp=costs(K);pool={tuple(int(v) for v in K[cidx])};br={}
        for pol in policies:
            q,nbr=path_policy(X[cidx],eps,coef,cidx,pol,freq,bp);pool.add(q);br[pol]=nbr
        cur=tuple(int(v) for v in K[cidx]);bestrow=cur;before=best_payload;tested=0
        for cand in pool:
            if cand==cur:continue
            trial=K.copy();trial[cidx]=np.asarray(cand,np.int32);pb,_,Kd,_=rr.restricted_rank_frame(trial);tested+=1
            if not np.array_equal(Kd,trial):raise RuntimeError(('rank replay',cidx))
            if int(pb)<best_payload:best_payload=int(pb);bestrow=cand
        changed=bestrow!=cur
        if changed:K[cidx]=np.asarray(bestrow,np.int32);accepted+=1
        audit.append({'channel':cidx,'unique_policy_paths':len(pool),'exact_streams_tested':tested,'payload_before':before,'payload_after':best_payload,'accepted':bool(changed),'policy_branch_counts':br})
        print(json.dumps({k:v for k,v in audit[-1].items() if k!='policy_branch_counts'}),flush=True)
    bf,_,Kf,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kf,K):raise RuntimeError('final rank replay')
    me=replay(X,eps,coef,Kf,STEP);total=int(mb)+int(bf)+HEADER+SELECTOR
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'order':P,'step':STEP,'nseeds':NSEEDS,'model_bytes':int(mb),'ar8_step266_baseline':{'bytes':base266,'payload_bytes':int(b0),'maxerr':me0},'ar8_step267_floor':{'bytes':floor267,'payload_bytes':int(b7),'maxerr':me7},'seeded_search':{'bytes':total,'payload_bytes':int(bf),'maxerr':me,'accepted_channels':accepted,'delta_vs_ar8_267':total-floor267,'gain_vs_ar8_267':floor267/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total,'detail':detail},'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'audit':audit,'scope':'Fast decoder-real Session-Seeded-GPS analogue on the AR8 winner. At step266 the encoder deterministically generates many source-legal AR8 trajectories by using public seeded branch policies plus frequency/bit/absolute-value policies whenever two legal K states exist. These policies are encoder search only: no seed is transmitted because the final exact K field is still physically encoded with PR512 restricted ranking. Each candidate channel trajectory is judged by the ACTUAL complete K-stream bytes, not its policy score. The final K stream is independently decoded, causally replayed with the charged AR8 model, and checked against the unchanged source hard-error bound. AR8 step267 is rerun as a strict floor.'}
    json.dump(out,open('imperial_ar8_seeded_legal_policy_search.json','w'),indent=2)
    print(json.dumps({'summary':{'ar8_266_before':base266,'seeded_after':total,'ar8_267_floor':floor267,'old_ar32':old['bytes'],'sz3':int(szb),'accepted_channels':accepted,'delta_vs_floor':total-floor267,'gain_vs_floor':floor267/total,'gain_vs_old_ar32':old['bytes']/total,'gain_vs_sz3':szb/total}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
