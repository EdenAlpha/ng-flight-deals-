import json,sys,math
from collections import Counter
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;END=4096;COARSE=256;HALF=128;BEAM=64
CHANNELS=(0,16,32,48,64,80,96,112)
MODES=(('pulse025',.25,.0),('pulse050',.50,.0),('pulse100',1.0,.0),('pulse200',2.0,.0),('switch050',.50,.50))
SAFETY=1-1e-9;ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def fit_prefix(X):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64);J=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        q=np.rint((X[:,t]-pred)/COARSE).astype(np.int64);R[:,t]=pred+COARSE*q;J[:,t]=q
    if float(np.max(np.abs(X[:,:TRAIN]-R)))>128.000001:raise RuntimeError('prefix hard')
    return mb,cd,R,J

def make_nll(J):
    cnt=Counter(int(x) for x in J.ravel());n=sum(cnt.values());alpha=.5;A=max(64,len(cnt)+32)
    return lambda q:-math.log2((cnt.get(int(q),0)+alpha)/(n+alpha*A))

def jcost(j,prev,nll):return nll(j)+.12*math.log2(1+abs(int(j)-int(prev)))

def beam_channel(x,co,prefix_r,prefix_j,eps,pulse_pen,switch_pen,nll):
    L=len(x);W=BEAM;states=prefix_r[-P:].astype(np.int64)[None,:].copy();cost=np.zeros(1,np.float64);prevj=np.array([int(prefix_j[-1])],np.int64);prevb=np.zeros(1,np.int8)
    parents=np.full((L,W),-1,np.int16);jstore=np.zeros((L,W),np.int16);bstore=np.zeros((L,W),np.int8);counts=np.zeros(L,np.int16)
    totalcand=0;bothpar=0
    for t in range(L):
        Bn=states.shape[0];v=np.full(Bn,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*states[:,-1-q]
        pred=np.rint(v).astype(np.int64);cand=[];bound=eps*SAFETY
        for z in range(Bn):
            lo=int(math.ceil((float(x[t])-bound-int(pred[z]))/HALF-1e-12));hi=int(math.floor((float(x[t])+bound-int(pred[z]))/HALF+1e-12))
            if lo>hi:raise RuntimeError(('empty',t,z))
            pars=set()
            for kf in range(lo,hi+1):
                b=int(kf&1);j=int((kf-b)//2);rr=int(pred[z])+HALF*kf;err=abs(float(x[t])-rr)
                if err>eps*(1+1e-10):raise RuntimeError(('hard candidate',err,eps))
                pars.add(b);cc=float(cost[z])+jcost(j,int(prevj[z]),nll)+pulse_pen*b+switch_pen*(b!=int(prevb[z]))
                cand.append((cc,abs(j),b,z,j,rr))
            if len(pars)==2:bothpar+=1
        totalcand+=len(cand);cand.sort(key=lambda a:(a[0],a[1],a[2],a[4],a[3]));sel=cand[:W];n2=len(sel)
        ns=np.empty((n2,P),np.int64);nc=np.empty(n2,np.float64);nj=np.empty(n2,np.int64);nb=np.empty(n2,np.int8)
        for q,a in enumerate(sel):
            cc,_,b,z,j,rr=a;ns[q,:-1]=states[z,1:];ns[q,-1]=rr;nc[q]=cc;nj[q]=j;nb[q]=b;parents[t,q]=z;jstore[t,q]=j;bstore[t,q]=b
        counts[t]=n2;states,cost,prevj,prevb=ns,nc,nj,nb
    z=int(np.argmin(cost));JJ=np.empty(L,np.int64);BB=np.empty(L,np.int8)
    for t in range(L-1,-1,-1):
        JJ[t]=int(jstore[t,z]);BB[t]=int(bstore[t,z]);z=int(parents[t,z])
        if t>0 and z<0:raise RuntimeError(('traceback',t,z))
    return JJ,BB,{'both_parity_parent_fraction':float(bothpar/max(1,sum(int(q) for q in counts))),'mean_candidates_per_step':float(totalcand/L),'final_beams':int(counts[-1])}

def reconstruct(J,B,co,prefix_r):
    state=prefix_r[-P:].astype(np.int64).copy();R=np.empty(len(J),np.int64)
    for t in range(len(J)):
        v=float(co[-1])
        for q in range(P):v+=float(co[q])*state[-1-q]
        pred=int(np.rint(v));rr=pred+COARSE*int(J[t])+HALF*int(B[t]);R[t]=rr;state[:-1]=state[1:];state[-1]=rr
    return R

def greedy(x,co,prefix_r):
    state=prefix_r[-P:].astype(np.int64).copy();J=np.empty(len(x),np.int64);R=np.empty(len(x),np.int64)
    for t in range(len(x)):
        v=float(co[-1])
        for q in range(P):v+=float(co[q])*state[-1-q]
        pred=int(np.rint(v));j=int(np.rint((float(x[t])-pred)/COARSE));rr=pred+COARSE*j;J[t]=j;R[t]=rr;state[:-1]=state[1:];state[-1]=rr
    return J,R

def kframe(A):
    fr=m.encode_k(np.asarray(A,np.int64));return int(fr[0])+20,fr[1],fr[2]

def bframe(B):
    a=np.asarray(B,np.uint8);packed=np.packbits(a.ravel(),bitorder='little').tobytes();blob=ZC.compress(packed);raw=ZD.decompress(blob);back=np.unpackbits(np.frombuffer(raw,np.uint8),bitorder='little')[:a.size].reshape(a.shape).astype(np.uint8)
    if not np.array_equal(back,a):raise RuntimeError('B roundtrip')
    return len(blob)+24,back

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    mb,co,R0,J0=fit_prefix(X);nll=make_nll(J0);target=X[:,TRAIN:END];idx=list(CHANNELS)
    G=[];GR=[]
    for c in CHANNELS:
        j,rr=greedy(target[c],co,R0[c]);G.append(j);GR.append(rr)
    G=np.stack(G);GR=np.stack(GR);gme=float(np.max(np.abs(target[idx]-GR)))
    if gme>128.000001:raise RuntimeError(('greedy hard',gme))
    gb,grep,Gd=kframe(G);gd=np.stack([reconstruct(Gd[i],np.zeros(Gd.shape[1],np.uint8),co,R0[c]) for i,c in enumerate(CHANNELS)])
    if not np.array_equal(gd,GR):raise RuntimeError('greedy decode')
    rows=[]
    for name,pp,sp in MODES:
        JJ=[];BB=[];stats=[]
        for c in CHANNELS:
            j,b,st=beam_channel(target[c],co,R0[c],J0[c],eps,pp,sp,nll);JJ.append(j);BB.append(b);stats.append(st)
        JJ=np.stack(JJ);BB=np.stack(BB);jb,jrep,Jd=kframe(JJ);bb,Bd=bframe(BB);RR=np.stack([reconstruct(Jd[i],Bd[i],co,R0[c]) for i,c in enumerate(CHANNELS)])
        me=float(np.max(np.abs(target[idx]-RR)))
        if me>eps*(1+1e-10):raise RuntimeError(('final hard',name,me,eps))
        total=jb+bb+1;row={'mode':name,'bytes':total,'bps':8*total/JJ.size,'J_bytes':jb,'J_bps':8*jb/JJ.size,'J_rep':jrep,'B_bytes':bb,'B_bps':8*bb/BB.size,'B_one_fraction':float(np.mean(BB)),'B_transition_fraction':float(np.mean(BB[:,1:]!=BB[:,:-1])),'greedy_bytes':gb,'greedy_bps':8*gb/G.size,'gain_vs_greedy':gb/total,'maxerr':me,'greedy_maxerr':gme,'J_zero_fraction':float(np.mean(JJ==0)),'greedy_J_zero_fraction':float(np.mean(G==0)),'J_std':float(JJ.std()),'greedy_J_std':float(G.std()),'J_changed_fraction':float(np.mean(JJ!=G)),'median_both_parity_parent_fraction':float(np.median([z['both_parity_parent_fraction'] for z in stats]))}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'coarse_step':COARSE,'control_offset':HALF,'ar_order':P,'model_bytes':mb,'hard_region_c0':C0,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0+c for c in CHANNELS],'beam_width':BEAM,'greedy':{'bytes':gb,'bps':8*gb/G.size,'rep':grep,'maxerr':gme},'best':rows[0],'rows':rows,
         'scope':'Half-step AR32 control-channel screen. The current persistent codec is B=0 in R=P+256J+128B. A shared AR32 model is fit/decoded only from hard-region t<1024. On eight fixed hard channels over t=1024..4095, a width-64 beam uses the full unchanged public +/-epsilon interval and enumerates every legal 128-spaced state. Each fine state is factored into coarse innovation J plus one control bit B. Beam costs use prefix-defined J codelength plus fixed B pulse/switch penalties. Final accounting does NOT use the surrogate: J is encoded by the actual self-decoding innovation frame; B is actually bit-packed, Zstd-compressed, decoded, and charged; one selector byte is charged. Decoder recursively regenerates the AR state from decoded J/B and final hard error is verified. This tests whether a sparse half-step distortion actuator can noise-shape future coarse innovations enough to pay for its own control plane. No AI; held-out hard-zone screen.'}
    print(json.dumps({'greedy':out['greedy'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_halfstep_control_channel.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
