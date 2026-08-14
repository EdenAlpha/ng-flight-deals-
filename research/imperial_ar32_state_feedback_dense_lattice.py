import json,sys,math
from collections import Counter
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_zsm_stack as z

C=128;P=32;TRAIN=1024;END=5120;BEAM=96
REGIONS=(('hard',512),('easy',2304))
CHANNELS=(0,32,64,96)
STEPS=(267,224,192,160,128)
MODES=('prefix_nll','zsm_surrogate')
WINDOWS=(4,8,64)
SAFETY=1-1e-9


def predict(state,co):
    return int(np.rint(float(co[0])+float(np.dot(np.asarray(co[1:],np.float32),state[::-1].astype(np.float32)))))


def greedy(x,co,step):
    n=len(x);R=np.zeros(n,np.int32);K=np.zeros(n,np.int32)
    state=np.zeros(P,np.int32)
    for t in range(n):
        p=0 if t<P else predict(state,co)
        k=int(np.rint((float(x[t])-p)/step));rr=p+step*k;K[t]=k;R[t]=rr
        if t<P:
            state[:-1]=state[1:];state[-1]=rr
        else:
            state[:-1]=state[1:];state[-1]=rr
    return K,R


def replay(K,co,step):
    R=np.zeros(len(K),np.int32);state=np.zeros(P,np.int32)
    for t,k in enumerate(K):
        p=0 if t<P else predict(state,co);rr=p+step*int(k);R[t]=rr
        state[:-1]=state[1:];state[-1]=rr
    return R


def make_cost(prefix):
    cnt=Counter(int(q) for q in prefix);n=sum(cnt.values());alpha=.5;A=max(64,len(cnt)+32)
    p0=(cnt.get(0,0)+alpha)/(n+alpha*A)
    def nll(k):return -math.log2((cnt.get(int(k),0)+alpha)/(n+alpha*A))
    def score(mode,k,prev):
        k=int(k);prev=int(prev);mag=abs(k);d=abs(k-prev)
        if mode=='prefix_nll':return nll(k)+.12*math.log2(1+d)
        # Approximate the current ZSM language: zero flag, sign and gamma magnitude,
        # plus a weak transition term. All constants come only from the paid prefix.
        if k==0:return -math.log2(max(p0,1e-12))+.05*math.log2(1+d)
        nz=-math.log2(max(1-p0,1e-12));gamma=1.0+2.0*max(0,mag.bit_length()-1)
        return nz+1.0+gamma+.05*math.log2(1+d)
    return score


def beam_tail(x,co,step,prefix_r,prefix_k,eps,mode,costfn):
    L=len(x);states=prefix_r[-P:].astype(np.int32)[None,:].copy();cost=np.zeros(1,np.float64);prevk=np.array([int(prefix_k[-1])],np.int32)
    parents=np.full((L,BEAM),-1,np.int16);kstore=np.zeros((L,BEAM),np.int16);counts=np.zeros(L,np.int16)
    branch_parents=0;total_cands=0
    for t in range(L):
        B=states.shape[0];pred=np.empty(B,np.int32)
        for b in range(B):pred[b]=predict(states[b],co)
        cand=[];bound=eps*SAFETY
        for b in range(B):
            lo=int(math.ceil((float(x[t])-bound-int(pred[b]))/step-1e-12));hi=int(math.floor((float(x[t])+bound-int(pred[b]))/step+1e-12))
            if lo>hi:raise RuntimeError(('empty',step,mode,t,b))
            if hi>lo:branch_parents+=1
            for k in range(lo,hi+1):
                rr=int(pred[b])+step*k
                if abs(float(x[t])-rr)>eps*(1+1e-10):raise RuntimeError(('hard candidate',step,mode,t))
                cand.append((float(cost[b])+costfn(mode,k,prevk[b]),abs(k),abs(k-int(prevk[b])),b,k,rr))
        total_cands+=len(cand);cand.sort(key=lambda q:(q[0],q[1],q[2],q[4],q[3]));sel=cand[:BEAM];B2=len(sel)
        ns=np.empty((B2,P),np.int32);nc=np.empty(B2,np.float64);nk=np.empty(B2,np.int32)
        for j,q in enumerate(sel):
            cc,_,_,b,k,rr=q;ns[j,:-1]=states[b,1:];ns[j,-1]=rr;nc[j]=cc;nk[j]=k;parents[t,j]=b;kstore[t,j]=k
        counts[t]=B2;states,cost,prevk=ns,nc,nk
    b=int(np.argmin(cost));K=np.empty(L,np.int32)
    for t in range(L-1,-1,-1):
        K[t]=int(kstore[t,b]);b=int(parents[t,b])
        if t>0 and b<0:raise RuntimeError(('traceback',t))
    return K,{'mean_candidates_per_step':float(total_cands/L),'branch_parent_fraction':float(branch_parents/max(1,total_cands)),'final_beams':int(counts[-1])}


def zsm_bytes(K):
    oldc,oldn=z.C,z.NT;z.C,z.NT=K.shape
    try:
        out=[]
        for W in WINDOWS:
            bb,bits=z.encode_zsm(K,W);D=z.decode_zsm(bb,bits,W)
            if not np.array_equal(D,K):raise RuntimeError(('zsm decode',W))
            out.append((len(bb),W,int(bits)))
        return min(out),out
    finally:z.C,z.NT=oldc,oldn


def main(path):
    oldc,oldn=a.C,a.NT;a.C=C;a.NT=END
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;_,co=a.fits(X)
            for step in STEPS:
                pref=[];gfull=[];grec=[]
                for c in CHANNELS:
                    K,R=greedy(X[c],co,step);pref.append((K[:TRAIN].copy(),R[:TRAIN].copy()));gfull.append(K);grec.append(R)
                G=np.stack(gfull);GR=np.stack(grec);gx=X[list(CHANNELS)]
                gme=float(np.max(np.abs(gx-GR.astype(np.float64))))
                if gme>eps*(1+1e-10):raise RuntimeError((region,step,'greedy hard',gme,eps))
                (gpay,gw,gbits),_=zsm_bytes(G);gbytes=gpay+a.MODEL_BYTES+33
                for mode in MODES:
                    KK=[];stats=[]
                    for j,c in enumerate(CHANNELS):
                        pk,pr=pref[j];costfn=make_cost(pk);tail,st=beam_tail(X[c,TRAIN:END],co,step,pr,pk,eps,mode,costfn);KK.append(np.concatenate([pk,tail]));stats.append(st)
                    KK=np.stack(KK);RR=np.stack([replay(KK[j],co,step) for j in range(len(CHANNELS))]);me=float(np.max(np.abs(gx-RR.astype(np.float64))))
                    if me>eps*(1+1e-10):raise RuntimeError((region,step,mode,'beam hard',me,eps))
                    (pay,w,bits),cand=zsm_bytes(KK);bb=pay+a.MODEL_BYTES+35 # window + step + mode selectors/framing
                    row={'region':region,'step':step,'mode':mode,'channels':[c0+c for c in CHANNELS],'samples':int(KK.size),'bytes':int(bb),'bps':8*bb/KK.size,'window':int(w),'arithmetic_bits':int(bits),'maxerr':me,
                         'same_step_greedy_bytes':int(gbytes),'same_step_greedy_bps':8*gbytes/G.size,'same_step_gain':float(gbytes/bb),'same_step_greedy_window':int(gw),'same_step_greedy_maxerr':gme,
                         'changed_fraction':float(np.mean(KK!=G)),'zero_fraction':float(np.mean(KK==0)),'greedy_zero_fraction':float(np.mean(G==0)),'k_std':float(KK.std()),'greedy_k_std':float(G.std()),
                         'mean_candidates_per_step':float(np.mean([q['mean_candidates_per_step'] for q in stats])),'branch_parent_fraction':float(np.mean([q['branch_parent_fraction'] for q in stats]))}
                    rows.append(row);print(json.dumps(row,indent=2),flush=True)
            rr=[q for q in rows if q['region']==region];base=min((q for q in rr if q['step']==267),key=lambda q:q['same_step_greedy_bytes'])['same_step_greedy_bytes'];best=min(rr,key=lambda q:q['bytes'])
            print(json.dumps({'region':region,'step267_greedy_bytes':base,'best':best},indent=2),flush=True)
        out={'global_std':float(gstd),'eps':float(eps),'train':TRAIN,'end':END,'beam_width':BEAM,'steps':list(STEPS),'modes':list(MODES),'rows':rows,
             'scope':'Modern dense-lattice state-feedback gate. Huber AR32 is fit only from the standard first-1024 prefix of each 128-channel region. Four precommitted channels are reconstructed through t=5119. For each source step 267/224/192/160/128, greedy and width-96 beam paths use the SAME shared Huber AR32 model and identical greedy prefix. After t=1024 the beam enumerates every reconstruction inside the unchanged public +/-epsilon interval; each chosen reconstruction is fed back into the recursive AR32 decoder state, so current distortion can alter future predictions. Two fixed prefix-derived search costs are tested. The winning K paths are not scored as byte claims: every complete prefix+tail K matrix is actually encoded and decoded by the modern ZSM arithmetic language with W=4/8/64, reconstructed independently at its declared step, and hard-error verified. Conservative bytes are charged for model/framing and window/step/mode selectors. This specifically tests the dense state-feedback degree of freedom not covered by old PR325 step256 or fixed-predictor legal-set experiments.'}
        json.dump(out,open('imperial_ar32_state_feedback_dense_lattice.json','w'),indent=2)
    a.C,a.NT=oldc,oldn
if __name__=='__main__':main(sys.argv[1])
