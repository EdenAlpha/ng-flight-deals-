import json,sys,math
from collections import Counter
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;END=5120;STEP=256;BEAM=64
CHANNELS=(0,16,32,48,64,80,96,112)
MODES=('magnitude','delta','zero_bias','prefix_nll')
SAFETY=1-1e-9

def fit_and_prefix(X):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/STEP).astype(np.int64);R[:,t]=pred+STEP*k;K[:,t]=k
    if float(np.max(np.abs(X[:,:TRAIN]-R)))>128.000001:raise RuntimeError('prefix hard error')
    return mb,cd,R,K

def make_nll(K):
    cnt=Counter(int(x) for x in K.ravel());n=sum(cnt.values());alpha=.5;A=max(64,len(cnt)+32)
    def f(k):return -math.log2((cnt.get(int(k),0)+alpha)/(n+alpha*A))
    return f

def addcost(mode,k,prev,nll):
    a=abs(int(k));d=abs(int(k)-int(prev))
    if mode=='magnitude':return math.log2(1+a)
    if mode=='delta':return .55*math.log2(1+a)+math.log2(1+d)
    if mode=='zero_bias':return 0.0 if k==0 else 1.0+math.log2(1+a)
    if mode=='prefix_nll':return nll(k)+.15*math.log2(1+d)
    raise ValueError(mode)

def beam_channel(x,co,prefix_r,prefix_k,eps,mode,nll):
    L=len(x);W=BEAM;states=prefix_r[-P:].astype(np.int64)[None,:].copy();cost=np.zeros(1,np.float64);prevk=np.array([int(prefix_k[-1])],np.int64)
    parents=np.full((L,W),-1,np.int16);kstore=np.zeros((L,W),np.int16);counts=np.zeros(L,np.int16)
    branch_sites=0;total_candidates=0
    for t in range(L):
        B=states.shape[0];v=np.full(B,float(co[-1]),np.float64)
        for j in range(P):v+=float(co[j])*states[:,-1-j]
        pred=np.rint(v).astype(np.int64)
        cand=[]
        bound=eps*SAFETY
        for b in range(B):
            lo=int(math.ceil((float(x[t])-bound-int(pred[b]))/STEP-1e-12));hi=int(math.floor((float(x[t])+bound-int(pred[b]))/STEP+1e-12))
            if lo>hi:raise RuntimeError(('empty legal',t,b,pred[b],x[t],lo,hi))
            if hi>lo:branch_sites+=1
            for k in range(lo,hi+1):
                rr=int(pred[b])+STEP*k;err=abs(float(x[t])-rr)
                if err>eps*(1+1e-10):raise RuntimeError(('candidate hard',err,eps))
                cand.append((float(cost[b])+addcost(mode,k,int(prevk[b]),nll),abs(k),b,k,rr))
        total_candidates+=len(cand);cand.sort(key=lambda z:(z[0],z[1],z[3],z[2]));sel=cand[:W];B2=len(sel)
        ns=np.empty((B2,P),np.int64);nc=np.empty(B2,np.float64);npk=np.empty(B2,np.int64)
        for q,z in enumerate(sel):
            cc,_,b,k,rr=z;ns[q,:-1]=states[b,1:];ns[q,-1]=rr;nc[q]=cc;npk[q]=k;parents[t,q]=b;kstore[t,q]=k
        counts[t]=B2;states,cost,prevk=ns,nc,npk
    b=int(np.argmin(cost));ks=np.empty(L,np.int64)
    for t in range(L-1,-1,-1):
        ks[t]=int(kstore[t,b]);b=int(parents[t,b])
        if t>0 and b<0:raise RuntimeError(('bad traceback',t,b))
    return ks,float(np.min(cost)),{'branch_parent_fraction':float(branch_sites/max(1,sum(int(c) for c in counts))),'mean_candidates_per_step':float(total_candidates/L),'final_beams':int(counts[-1])}

def reconstruct_target(ks,co,prefix_r):
    state=prefix_r[-P:].astype(np.int64).copy();R=np.empty(len(ks),np.int64)
    for t,k in enumerate(ks):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*state[-1-j]
        pred=int(np.rint(v));rr=pred+STEP*int(k);R[t]=rr;state[:-1]=state[1:];state[-1]=rr
    return R

def greedy_channel(x,co,prefix_r):
    state=prefix_r[-P:].astype(np.int64).copy();K=np.empty(len(x),np.int64);R=np.empty(len(x),np.int64)
    for t in range(len(x)):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*state[-1-j]
        pred=int(np.rint(v));k=int(np.rint((float(x[t])-pred)/STEP));rr=pred+STEP*k;K[t]=k;R[t]=rr;state[:-1]=state[1:];state[-1]=rr
    return K,R

def frame_bytes(K):
    fr=m.encode_k(np.asarray(K,np.int64));return int(fr[0])+20,fr[1],fr[2]

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    mb,co,R0,K0=fit_and_prefix(X);nll=make_nll(K0);target=X[:,TRAIN:END]
    G=[];GR=[]
    for c in CHANNELS:
        k,r0=greedy_channel(target[c],co,R0[c]);G.append(k);GR.append(r0)
    G=np.stack(G);GR=np.stack(GR);gme=float(np.max(np.abs(target[list(CHANNELS)]-GR)))
    if gme>128.000001:raise RuntimeError(('greedy error',gme))
    gb,grep,Gd=frame_bytes(G);gd=[]
    for i,c in enumerate(CHANNELS):gd.append(reconstruct_target(Gd[i],co,R0[c]))
    gd=np.stack(gd)
    if not np.array_equal(gd,GR):raise RuntimeError('greedy frame decode')
    rows=[]
    for mode in MODES:
        KK=[];stats=[]
        for c in CHANNELS:
            k,cost,st=beam_channel(target[c],co,R0[c],K0[c],eps,mode,nll);KK.append(k);stats.append(st)
        KK=np.stack(KK);bb,rep,Kd=frame_bytes(KK);RR=[]
        for i,c in enumerate(CHANNELS):RR.append(reconstruct_target(Kd[i],co,R0[c]))
        RR=np.stack(RR);me=float(np.max(np.abs(target[list(CHANNELS)]-RR)))
        if me>eps*(1+1e-10):raise RuntimeError(('beam hard',mode,me,eps))
        row={'mode':mode,'bytes':bb+1,'bps':8*(bb+1)/KK.size,'rep':rep,'greedy_bytes':gb,'greedy_bps':8*gb/G.size,'gain_vs_greedy':gb/(bb+1),'maxerr':me,'greedy_maxerr':gme,
             'k_zero_fraction':float(np.mean(KK==0)),'greedy_k_zero_fraction':float(np.mean(G==0)),'k_std':float(KK.std()),'greedy_k_std':float(G.std()),
             'changed_fraction':float(np.mean(KK!=G)),'mean_abs_k_change':float(np.mean(np.abs(KK-G))),
             'median_branch_parent_fraction':float(np.median([z['branch_parent_fraction'] for z in stats])),'median_candidates_per_step':float(np.median([z['mean_candidates_per_step'] for z in stats]))}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);best=rows[0]
    out={'global_std':std,'eps':eps,'step':STEP,'ar_order':P,'model_bytes':mb,'hard_region_c0':C0,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0+c for c in CHANNELS],'beam_width':BEAM,'modes':list(MODES),
         'greedy':{'bytes':gb,'bps':8*gb/G.size,'rep':grep,'maxerr':gme,'k_zero_fraction':float(np.mean(G==0)),'k_std':float(G.std())},'best':best,'rows':rows,
         'scope':'Trellis-coded AR32 state-control gate. One shared float32 AR32 model is fit/decoded only from the hard 128-channel prefix t<1024. On eight precommitted hard-zone channels for t=1024..5119, the ordinary codec greedily chooses nearest 256-step K (<=128 error). The new encoder instead maintains a 64-path beam over the AR decoder state. At every sample it enumerates EVERY integer K whose reconstruction lies inside the unchanged public +/-10%-global-std interval (not merely +/-128); alternative legal states differ by 256 and therefore alter future AR predictions. Four fixed additive search costs are tested; the selected K matrices are then encoded with the ACTUAL self-decoding K frame and a one-byte mode selector, decoded, recursively reconstructed, and hard-error verified. The search cost itself is not a decoder model and carries no hidden metadata; only actual K bytes count. This tests whether distortion freedom can act as a feedback control input/noise-shaping mechanism rather than a local quantizer choice. No AI; held-out hard-zone screen, not whole-array.'}
    print(json.dumps({'greedy':out['greedy'],'best':best},indent=2),flush=True);json.dump(out,open('imperial_ar32_trellis_state_control.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
