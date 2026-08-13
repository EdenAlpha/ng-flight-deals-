import json,sys,math
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_persistent_ar32_full_array_jit as a
import imperial_decoder_phase_automaton as dm

a.m.m.STEP=267
P=32;STEP=267;L=8;TRAIN=1024;DICT_END=15000;TARGET_START=15000;TARGET_END=30000
MAX_C=2048;TARGET_C0=512;TARGET_LOCAL=np.arange(0,128,4,dtype=np.int64)
WIDTHS=(128,512,2048);NSAMPLE=4096;SEARCH_PAD=16.0

def fit_build(X):
    co=a.m.r.fit_shared(X[:,:TRAIN],P);mb,cd=a.m.r.model_frame(co);R,K=a.build(X,cd);return cd,R,K

def lin_effect_matrix(co):
    A=np.zeros((L,L),np.float64)
    for j in range(L):
        d=np.zeros(P,np.float64)
        for t in range(L):
            pred=float(co[-1]) * 0.0
            for q in range(P):pred+=float(co[q])*d[-1-q]
            y=pred+(STEP if t==j else 0.0);A[t,j]=y;d[:-1]=d[1:];d[-1]=y
    return A

def exact_openloop(state,co):
    s=state.astype(np.int64).copy();b=np.empty(L,np.int64)
    for t in range(L):
        v=float(co[-1])
        for q in range(P):v+=float(co[q])*float(s[-1-q])
        y=int(np.rint(v));b[t]=y;s[:-1]=s[1:];s[-1]=y
    return b

def exact_replay(state,co,k):
    s=state.astype(np.int64).copy();out=np.empty(L,np.int64)
    for t in range(L):
        v=float(co[-1])
        for q in range(P):v+=float(co[q])*float(s[-1-q])
        y=int(np.rint(v))+STEP*int(k[t]);out[t]=y;s[:-1]=s[1:];s[-1]=y
    return out

def phrase_rows(K):
    n=(DICT_END-TRAIN)//L
    return np.ascontiguousarray(K[:,TRAIN:TRAIN+n*L].reshape(K.shape[0]*n,L))

def content_stats(B):
    U,c=np.unique(np.ascontiguousarray(B).view(np.dtype((np.void,B.dtype.itemsize*L))).ravel(),return_counts=True)
    return int(len(U)),float(c.max()/c.sum()),float(-(c/c.sum()*np.log2(c/c.sum())).sum()/c.sum())

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=dm.stats(d);eps=.1*std
        nper=(DICT_END-TRAIN)//L;allK=np.empty((MAX_C*nper,L),np.int16);p=0;target_pack=None
        for c0 in range(0,MAX_C,128):
            X=np.asarray(d[:,c0:c0+128],np.float64).T;co,R,K=fit_build(X)
            B=phrase_rows(K)
            if int(B.min())<-32768 or int(B.max())>32767:raise RuntimeError(('K int16',c0,int(B.min()),int(B.max())))
            allK[p:p+len(B)]=B.astype(np.int16);p+=len(B)
            if c0==TARGET_C0:target_pack=(X,co,R,K)
            print(json.dumps({'built_channels':[c0,c0+127],'phrases_total':p}),flush=True)
        if p!=len(allK) or target_pack is None:raise RuntimeError((p,len(allK),target_pack is None))
    X,co,R,K=target_pack;A=lin_effect_matrix(co)
    # Fixed held-out block set. State history comes from the verified incumbent trajectory.
    blocks=[]
    for c in TARGET_LOCAL:
        for t in range(TARGET_START,TARGET_END-L+1,L):blocks.append((int(c),int(t)))
    sel=np.linspace(0,len(blocks)-1,min(NSAMPLE,len(blocks)),dtype=np.int64);blocks=[blocks[int(i)] for i in sel]
    rows=[]
    ranges={128:(TARGET_C0,TARGET_C0+128),512:(320,832),2048:(0,2048)}
    for width in WIDTHS:
        lo,hi=ranges[width];i0=lo*nper;i1=hi*nper;B=allK[i0:i1]
        uniq,freq=np.unique(B,axis=0,return_counts=True);V=(uniq.astype(np.float64)@A.T).astype(np.float32);tree=cKDTree(V,compact_nodes=True,balanced_tree=True)
        raw_bits=math.log2(len(B));uid_bits=math.log2(len(uniq));total_hits=0;legal_blocks=0;nearest=[];candidate_counts=[];chosen_freq_bits=[]
        for bi,(c,t) in enumerate(blocks):
            state=R[c,t-P:t];base=exact_openloop(state,co);y=X[c,t:t+L]-base
            dist,nn=tree.query(y,k=1,p=np.inf);nearest.append(float(dist));ids=tree.query_ball_point(y,r=eps+SEARCH_PAD,p=np.inf);candidate_counts.append(len(ids));ok=[]
            for q in ids:
                rr=exact_replay(state,co,uniq[int(q)])
                if float(np.max(np.abs(X[c,t:t+L]-rr)))<=eps*(1+1e-10):ok.append(int(q))
            if ok:
                legal_blocks+=1;total_hits+=len(ok)
                q=max(ok,key=lambda z:int(freq[z]));chosen_freq_bits.append(-math.log2(float(freq[q])/float(freq.sum())))
            if bi%512==0:print(json.dumps({'width':width,'target':bi,'approx_candidates':len(ids),'legal':len(ok),'nearest':nearest[-1]}),flush=True)
        F=legal_blocks/len(blocks);mean_fb=float(np.mean(chosen_freq_bits)/L) if chosen_freq_bits else None
        rows.append({'history_channels':width,'history_range':[lo,hi-1],'phrases':int(len(B)),'unique_phrases':int(len(uniq)),'duplicate_fraction':1-len(uniq)/len(B),'top_phrase_fraction':float(freq.max()/freq.sum()),'raw_location_index_bits':raw_bits,'raw_location_index_bps':raw_bits/L,'fixed_content_id_bits':uid_bits,'fixed_content_id_bps':uid_bits/L,'coverage_fraction_exact_recursive':F,'mean_legal_candidates_per_target':total_hits/len(blocks),'median_linear_nearest_linf':float(np.median(nearest)),'p90_linear_nearest_linf':float(np.percentile(nearest,90)),'median_linear_candidate_count':float(np.median(candidate_counts)),'mean_prefix_frequency_id_bps_on_hits':mean_fb})
        print(json.dumps(rows[-1],indent=2),flush=True)
    Atest=X[TARGET_LOCAL,TARGET_START:TARGET_END];sb,_=dm.szrun(Atest,eps);szbps=8*sb/Atest.size;target=szbps/2
    out={'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'phrase_length':L,'dictionary_time':[TRAIN,DICT_END],'target_time':[TARGET_START,TARGET_END],'target_channels':[int(TARGET_C0+c) for c in TARGET_LOCAL],'sampled_target_blocks':len(blocks),'matched_sz3_bytes':int(sb),'matched_sz3_bps':szbps,'two_x_target_bps':target,'rows':rows,'scope':'Same-record executable innovation-phrase coverage gate, not yet a codec. Every fixed 128-channel block is reconstructed by the incumbent persistent AR32 step267 codec. Nonoverlapping 8-symbol K phrases from t=1024..14999 across nested 128/512/2048 already-decoded channels form a decoder-known program dictionary. For the held-out hard-region t=15000..29999 target, a historical K phrase is replayed from the CURRENT target AR32 state; it is legal only if all eight recursively reconstructed samples satisfy the unchanged +/-epsilon hard bound. Candidate search uses the exact linearized impulse response of the target AR model with a 16-unit pad, then every candidate is validated through the actual rounded AR recurrence. No waveform or residual vector is transmitted as a dictionary. Raw location, unique-content ID and prefix-frequency ID rates are reported only as rate diagnostics; a real reference/mode/escape stream is required before any compression claim. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_same_minute_executable_k_phrases.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
