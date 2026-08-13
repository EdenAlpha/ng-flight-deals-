import json,sys,math
import h5py,numpy as np
from scipy.special import ndtri
from scipy.spatial import cKDTree
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;END=8192;L=8;STEP=267
TARGET_CH=np.arange(0,128,4,dtype=np.int64)
N=1<<22; NTARGET=512; MIX=4
MASK=np.uint64(0xffffffffffffffff)

def splitmix64(x):
    x=(x+np.uint64(0x9E3779B97F4A7C15))&MASK
    z=x.copy();z=((z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9))&MASK
    z=((z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB))&MASK
    return z^(z>>np.uint64(31))

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/STEP).astype(np.int64);R[:,t]=pred+STEP*k
    if float(np.max(np.abs(X[:,:TRAIN]-R)))>eps*(1+1e-10):raise RuntimeError('prefix hard')
    return int(mb),cd,R

def openloop(state,co):
    s=state.astype(np.int64).copy();base=np.empty(L,np.int64)
    for i in range(L):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*s[-1-j]
        y=int(np.rint(v));base[i]=y;s[:-1]=s[1:];s[-1]=y
    return base

def train_vectors(X,R,co):
    out=[]
    for c in range(C):
        for t in range(P,TRAIN-L+1,L):out.append(X[c,t:t+L]-openloop(R[c,t-P:t],co))
    return np.asarray(out,np.float64)

def heldout_vectors(X,R0,co,eps):
    V=[]
    for c in TARGET_CH:
        state=R0[c,-P:].copy()
        for t in range(TRAIN,END,L):
            base=openloop(state,co);src=X[c,t:t+L];V.append(src-base)
            # Advance with honest incumbent step267, not source values.
            for q in range(L):
                vv=float(co[-1])
                for j in range(P):vv+=float(co[j])*state[-1-j]
                pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/STEP));rr=pred+STEP*k
                if abs(float(src[q])-rr)>eps*(1+1e-10):raise RuntimeError('incumbent hard')
                state[:-1]=state[1:];state[-1]=rr
    V=np.asarray(V,np.float64)
    sel=np.linspace(0,len(V)-1,NTARGET,dtype=np.int64)
    return V,V[sel],sel

def fit_mixture(V):
    norm=np.sqrt(np.mean(V*V,axis=1));cuts=np.quantile(norm,[.25,.5,.75]);lab=np.digitize(norm,cuts)
    means=[];chols=[];weights=[]
    for j in range(MIX):
        A=V[lab==j];mu=A.mean(axis=0);cov=np.cov(A,rowvar=False,bias=True)
        ridge=max(1.0,float(np.trace(cov))/L*1e-5);cov=cov+ridge*np.eye(L);chol=np.linalg.cholesky(cov)
        means.append(mu);chols.append(chol);weights.append(len(A)/len(V))
    return np.asarray(means),np.asarray(chols),np.asarray(weights)

def generate_codebook(means,chols):
    idx=np.arange(N,dtype=np.uint64);mix=(splitmix64(idx^np.uint64(0x123456789abcdef0))&np.uint64(MIX-1)).astype(np.uint8)
    Z=np.empty((N,L),np.float32)
    for d in range(L):
        h=splitmix64(idx^(np.uint64(0xD1B54A32D192ED03)*np.uint64(d+1)))
        u=((h>>np.uint64(11)).astype(np.float64)+0.5)*(1.0/(1<<53));u=np.clip(u,1e-12,1-1e-12)
        Z[:,d]=ndtri(u).astype(np.float32)
    out=np.empty((N,L),np.float32)
    for j in range(MIX):
        q=np.flatnonzero(mix==j);out[q]=(Z[q].astype(np.float64)@chols[j].T+means[j]).astype(np.float32)
    np.rint(out,out=out)
    return out,mix

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError('sz hard')
        z=(int(b.size),me,'T' if tr else 'CT')
        if best is None or z[0]<best[0]:best=z
    return best

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0=fit_prefix(X,eps);TV=train_vectors(X,R0,co);HV,H,sel=heldout_vectors(X,R0,co,eps);means,chols,weights=fit_mixture(TV)
    print(json.dumps({'training_vectors':len(TV),'heldout_vectors':len(HV),'sampled_targets':len(H),'candidate_count':N,'mixture_weights':weights.tolist()}),flush=True)
    CAND,mix=generate_codebook(means,chols);tree=cKDTree(CAND,compact_nodes=True,balanced_tree=True)
    hit_indices=[];counts=[];nearest=[]
    for i,y in enumerate(H):
        ids=tree.query_ball_point(y,r=eps,p=np.inf)
        counts.append(len(ids));hit_indices.append(min(ids) if ids else None)
        nearest.append(float(tree.query(y,k=1,p=np.inf)[0]))
        if i%64==0:print(json.dumps({'target':i,'hits':len(ids),'min_index':hit_indices[-1],'nearest_linf':nearest[-1]}),flush=True)
    hits=np.array([x is not None for x in hit_indices]);F=float(hits.mean())
    if F>=1.0:p_hat=1.0
    elif F<=0.0:p_hat=0.0
    else:p_hat=float(-math.log1p(-F)/N)
    pred24=float(1-math.exp(-p_hat*(1<<24))) if p_hat>0 else 0.0
    if p_hat>0 and p_hat<1:
        geom_bits=float(-math.log2(p_hat)-((1-p_hat)/p_hat)*math.log2(1-p_hat));geom_bps=geom_bits/L
    elif p_hat>=1:geom_bits=0.0;geom_bps=0.0
    else:geom_bits=None;geom_bps=None
    q=[x for x in hit_indices if x is not None];idxq={}
    if q:
        for p in (10,25,50,75,90,95,99):idxq[str(p)]=float(np.percentile(q,p))
    szb=szrun(X[TARGET_CH,TRAIN:END],eps);target_bps=8*szb[0]/(len(TARGET_CH)*(END-TRAIN))/2
    out={'global_std':std,'eps':eps,'hard_region_c0':C0,'ar_order':P,'block_length':L,'candidate_count':N,'candidate_index_bits':22,
         'training_vectors':len(TV),'heldout_vectors':len(HV),'sampled_targets':len(H),'mixture_weights':weights.tolist(),'model_bytes':mb,
         'coverage_fraction_at_2pow22':F,'mean_hits_per_target':float(np.mean(counts)),'median_hits_per_target':float(np.median(counts)),
         'nearest_linf_median':float(np.median(nearest)),'nearest_linf_p90':float(np.percentile(nearest,90)),'hit_index_percentiles':idxq,
         'estimated_per_candidate_hit_probability':p_hat,'predicted_coverage_at_2pow24_poisson':pred24,'estimated_geometric_index_bits_per_block':geom_bits,
         'estimated_geometric_index_bps':geom_bps,'matched_sz3_bps':8*szb[0]/(len(TARGET_CH)*(END-TRAIN)),'two_x_target_bps':target_bps,
         'ratio_estimated_geometric_bps_to_2x_target':geom_bps/target_bps if geom_bps is not None else None,
         'scope':'Procedural random-cover diagnostic, NOT a compression claim. Shared AR32 and its legal step267 prefix are learned only from hard-region t<1024. 8-D open-loop residual blocks from that prefix fit a four-component norm-stratified Gaussian model (means/covariances are tiny potential decoder metadata). A fixed SplitMix64 construction generates exactly 2^22 deterministic candidate 8-D residual vectors; the encoder materializes them only for search and builds an exact L-infinity cKDTree. 512 deterministic held-out residual blocks from 32 hard channels are queried for every candidate lying inside the unchanged +/-epsilon box. Candidate ordering is deterministic, so the first compatible index is a potential codeword index; the decoder could regenerate only the indexed candidate from the same hash/model. Coverage scaling to 2^24 and geometric-index rate are explicitly Poisson/independence estimates, not realized bytes. Matched SZ3 on the full held-out array supplies the 2x rate target. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_procedural_random_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
