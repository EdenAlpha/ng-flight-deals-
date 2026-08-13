import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512; C=128; P=32; TRAIN=1024; END=4096
CHANNELS=(0,16,32,48,64,80,96,112)
SUB=128; STEPS=(384,512,640,768,1024); BEAM=48
SWITCH_PENALTIES=(0.25,0.5,1.0,2.0,4.0)
SAFETY=1-1e-9
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P); mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P: pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/267.0).astype(np.int64); R[:,t]=pred+267*k
    me=float(np.max(np.abs(X[:,:TRAIN]-R)))
    if me>eps*(1+1e-10):raise RuntimeError(('prefix hard',me,eps))
    return mb,cd,R

def pred_states(S,co):
    v=np.full(S.shape[0],float(co[-1]),np.float64)
    for j in range(P):v+=float(co[j])*S[:,-1-j]
    return np.rint(v).astype(np.int64)

def scost(k,pk):return math.log2(1+abs(int(k)))+.10*math.log2(1+abs(int(k)-int(pk)))

def beam_channel(x,co,prefix,eps,step,spen):
    M=step//SUB; L=len(x); W=BEAM; bound=eps*SAFETY
    states=prefix[-P:].astype(np.int64)[None,:].copy(); costs=np.zeros(1); phase=np.zeros(1,np.int8); prevk=np.zeros(1,np.int32)
    parents=np.full((L,W),-1,np.int16); pstore=np.zeros((L,W),np.int8); kstore=np.zeros((L,W),np.int16); counts=np.zeros(L,np.int16)
    legal_counts=0; same_possible=0
    for t in range(L):
        pred=pred_states(states,co); cand=[]
        for b in range(states.shape[0]):
            parent_has_same=False
            for ph in range(M):
                phi=SUB*ph; k=int(np.rint((float(x[t])-int(pred[b])-phi)/step)); rr=int(pred[b])+phi+step*k
                if abs(float(x[t])-rr)>eps*(1+1e-10):continue
                legal_counts+=1
                if ph==int(phase[b]):parent_has_same=True
                cc=float(costs[b])+scost(k,int(prevk[b]))+spen*(ph!=int(phase[b]))
                cand.append((cc,ph!=int(phase[b]),abs(k),ph,b,k,rr))
            if parent_has_same:same_possible+=1
        if not cand:raise RuntimeError(('beam died',step,spen,t))
        cand.sort(key=lambda z:(z[0],z[1],z[2],z[3],z[5],z[4])); sel=cand[:W]; n=len(sel)
        ns=np.empty((n,P),np.int64); nc=np.empty(n); npv=np.empty(n,np.int8); nk=np.empty(n,np.int32)
        for q,z in enumerate(sel):
            cc,_,_,ph,b,k,rr=z; ns[q,:-1]=states[b,1:];ns[q,-1]=rr;nc[q]=cc;npv[q]=ph;nk[q]=k
            parents[t,q]=b;pstore[t,q]=ph;kstore[t,q]=k
        counts[t]=n;states,costs,phase,prevk=ns,nc,npv,nk
    b=int(np.argmin(costs)); PH=np.empty(L,np.uint8); K=np.empty(L,np.int64)
    for t in range(L-1,-1,-1):
        PH[t]=pstore[t,b];K[t]=kstore[t,b];b=int(parents[t,b])
        if t>0 and b<0:raise RuntimeError(('traceback',t,b))
    return K,PH,{'phase_switch_fraction':float(np.mean(PH[1:]!=PH[:-1])),'distinct_phases':int(np.unique(PH).size),'mean_legal_phase_candidates':float(legal_counts/L),'same_phase_possible_parent_fraction':float(same_possible/max(1,sum(map(int,counts))))}

def kframe(A):
    fr=m.encode_k(np.asarray(A,np.int64));return int(fr[0])+20,fr[1],np.asarray(fr[2],np.int64)

def phase_frame(PH,M):
    PH=np.asarray(PH,np.uint8);c=[]
    raw=PH.tobytes();z=ZC.compress(raw);back=np.frombuffer(ZD.decompress(z),np.uint8,count=PH.size).reshape(PH.shape).copy()
    if not np.array_equal(back,PH):raise RuntimeError('phase raw rt')
    c.append((len(z)+28,'state_u8_zstd',back))
    D=np.empty_like(PH);D[:,0]=PH[:,0];D[:,1:]=(PH[:,1:].astype(np.int16)-PH[:,:-1].astype(np.int16))%M
    zd=ZC.compress(D.tobytes());dd=np.frombuffer(ZD.decompress(zd),np.uint8,count=D.size).reshape(D.shape).copy();rr=np.empty_like(PH);rr[:,0]=dd[:,0]
    for t in range(1,PH.shape[1]):rr[:,t]=(rr[:,t-1].astype(np.int16)+dd[:,t].astype(np.int16))%M
    if not np.array_equal(rr,PH):raise RuntimeError('phase delta rt')
    c.append((len(zd)+28,'delta_mod_u8_zstd',rr))
    sw=np.zeros_like(PH,dtype=bool);sw[:,0]=True;sw[:,1:]=PH[:,1:]!=PH[:,:-1]
    mb=ZC.compress(np.packbits(sw.ravel(),bitorder='little').tobytes()); vals=PH[sw];vb=ZC.compress(vals.tobytes())
    md=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little')[:sw.size].reshape(sw.shape).astype(bool);vv=np.frombuffer(ZD.decompress(vb),np.uint8,count=vals.size);rr=np.empty_like(PH);p=0
    for cidx in range(PH.shape[0]):
        cur=0
        for t in range(PH.shape[1]):
            if md[cidx,t]:cur=int(vv[p]);p+=1
            rr[cidx,t]=cur
    if not np.array_equal(rr,PH):raise RuntimeError('phase switch rt')
    c.append((len(mb)+len(vb)+52,'switch_mask_values',rr))
    return min(c,key=lambda z:z[0])

def reconstruct(K,PH,co,prefix,step):
    state=prefix[-P:].astype(np.int64).copy();R=np.empty(len(K),np.int64)
    for t in range(len(K)):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*state[-1-j]
        pred=int(np.rint(v));rr=pred+SUB*int(PH[t])+step*int(K[t]);R[t]=rr;state[:-1]=state[1:];state[-1]=rr
    return R

def baseline(X,co,R0,eps):
    KK=[];RR=[]
    for c in CHANNELS:
        state=R0[c,-P:].astype(np.int64).copy();ks=[];rs=[]
        for xx in X[c,TRAIN:END]:
            v=float(co[-1])
            for j in range(P):v+=float(co[j])*state[-1-j]
            pred=int(np.rint(v));k=int(np.rint((float(xx)-pred)/267));rr=pred+267*k
            if abs(float(xx)-rr)>eps*(1+1e-10):raise RuntimeError('base hard')
            ks.append(k);rs.append(rr);state[:-1]=state[1:];state[-1]=rr
        KK.append(ks);RR.append(rs)
    K=np.asarray(KK);R=np.asarray(RR);kb,rep,Kd=kframe(K)
    if not np.array_equal(Kd,K):raise RuntimeError('base k rt')
    return K,R,kb,rep

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    mb,co,R0=fit_prefix(X,eps);G,GR,gb,grep=baseline(X,co,R0,eps);gbytes=mb+gb
    target=X[list(CHANNELS),TRAIN:END];gme=float(np.max(np.abs(target-GR)))
    sb,_=m.szrun(target,eps);rows=[]
    for step in STEPS:
        M=step//SUB
        for pen in SWITCH_PENALTIES:
            KK=[];PP=[];STS=[]
            for c in CHANNELS:
                k,p,st=beam_channel(X[c,TRAIN:END],co,R0[c],eps,step,pen);KK.append(k);PP.append(p);STS.append(st)
            KK=np.stack(KK);PP=np.stack(PP);kb,krep,Kd=kframe(KK);pb,prep,Pd=phase_frame(PP,M);RR=np.stack([reconstruct(Kd[i],Pd[i],co,R0[c],step) for i,c in enumerate(CHANNELS)])
            me=float(np.max(np.abs(target-RR)))
            if me>eps*(1+1e-10):raise RuntimeError(('candidate hard',step,pen,me))
            total=mb+kb+pb+1
            row={'step':step,'phase_count':M,'switch_penalty':pen,'bytes':total,'bps':8*total/KK.size,'model_bytes':mb,'coarse_bytes':kb,'coarse_bps':8*kb/KK.size,'coarse_rep':krep,'phase_bytes':pb,'phase_bps':8*pb/PP.size,'phase_rep':prep,'phase_switch_fraction':float(np.mean(PP[:,1:]!=PP[:,:-1])),'median_channel_switch_fraction':float(np.median([s['phase_switch_fraction'] for s in STS])),'mean_distinct_phases':float(np.mean([s['distinct_phases'] for s in STS])),'baseline_bytes':gbytes,'baseline_bps':8*gbytes/G.size,'gain_vs_step267':gbytes/total,'sz3_bytes':int(sb),'gain_vs_sz3':sb/total,'maxerr':me,'baseline_maxerr':gme}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'ar_order':P,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0+c for c in CHANNELS],'substep':SUB,'steps':list(STEPS),'switch_penalties':list(SWITCH_PENALTIES),'beam_width':BEAM,'baseline':{'step':267,'bytes':gbytes,'bps':8*gbytes/G.size,'model_bytes':mb,'coarse_bytes':gb,'rep':grep,'sz3_bytes':int(sb),'gain_vs_sz3':sb/gbytes,'maxerr':gme},'best':rows[0],'rows':rows,'scope':'Supercritical persistent-coset state codec. Unlike PR335, there is no fine-amplitude reset stream. For step S in {384,512,640,768,1024}, S is an integer multiple M of 128. The decoder carries a persistent coset phase phi=128*p, p in 0..M-1, and reconstructs R=P_AR32+phi+S*K. The union of all M cosets is exactly the 128 grid, so legal coverage exists everywhere under the unchanged public epsilon. A width-48 beam jointly chooses coarse K and persistent phase, charging fixed phase-switch penalties. Final accounting ignores the surrogate: K is actually encoded with the existing self-decoding innovation backend; the phase state is actually encoded/decoded by the best of raw-state, modulo-delta, or switch-mask+values frames; AR model/framing/mode bytes are charged; exact decoder recursion and hard error are verified. Step267 greedy and matched SZ3 are rerun on the same eight hard channels. No AI; directional screen, not whole-array.'}
    print(json.dumps({'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_supercritical_coset_hopping.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
