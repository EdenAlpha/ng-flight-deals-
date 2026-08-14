import json,sys,math
import h5py,numpy as np,zstandard as zstd
from scipy.special import ndtr,ndtri
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_ar32_state_normalized_residual_support as s
import imperial_decoder_phase_automaton as m

Q=257;N=1<<22;L=g.L;NTARGET=512;RIDGE=s.RIDGE
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()


def fit_scale(TF,TY):
    A=TF.T@TF+RIDGE*np.eye(TF.shape[1]);w=np.linalg.solve(A,TF.T@TY).astype(np.float32)
    # Serialize the actual decoder model used below.
    wb=ZC.compress(w.astype('<f4').tobytes());wd=np.frombuffer(ZD.decompress(wb),'<f4').copy()
    raw=np.exp(TF@wd.astype(np.float64));lo,hi=np.percentile(raw,[1,99]).astype(np.float32)
    bounds=np.asarray([lo,hi],dtype='<f4');bb=ZC.compress(bounds.tobytes());bd=np.frombuffer(ZD.decompress(bb),'<f4').copy()
    return len(wb)+len(bb)+32,wd,float(bd[0]),float(bd[1])


def scales(F,w,lo,hi):
    return np.clip(np.exp(F@w.astype(np.float64)),lo,hi)


def fit_empirical_copula(V):
    n,d=V.shape;probs=np.linspace(0,1,Q)
    qt=np.quantile(V,probs,axis=0,method='linear').T.astype(np.float32)
    Z=np.empty_like(V,dtype=np.float64)
    for j in range(d):
        order=np.argsort(V[:,j],kind='mergesort');r=np.empty(n,np.float64);r[order]=(np.arange(n)+0.5)/n
        Z[:,j]=ndtri(np.clip(r,1e-6,1-1e-6))
    corr=np.corrcoef(Z,rowvar=False);corr=(corr+corr.T)*0.5
    ev,U=np.linalg.eigh(corr);ev=np.maximum(ev,1e-4);corr=(U*ev)@U.T
    D=np.sqrt(np.diag(corr));corr=corr/(D[:,None]*D[None,:]);chol=np.linalg.cholesky(corr+1e-6*np.eye(d)).astype(np.float32)
    # Fully serialize potential decoder metadata.
    qb=ZC.compress(qt.astype('<f4').tobytes());cb=ZC.compress(chol.astype('<f4').tobytes())
    qtd=np.frombuffer(ZD.decompress(qb),'<f4').reshape(qt.shape).copy();chd=np.frombuffer(ZD.decompress(cb),'<f4').reshape(chol.shape).copy()
    return len(qb)+len(cb)+64,qtd,chd,corr


def inv_quantile(U,qt):
    x=np.clip(U,0,1)*(Q-1);ii=np.floor(x).astype(np.int32);ff=x-ii;ii=np.minimum(ii,Q-2)
    out=np.empty(U.shape,np.float32)
    for d in range(L):
        a=qt[d,ii[:,d]];b=qt[d,ii[:,d]+1];out[:,d]=a+(b-a)*ff[:,d]
    return out


def generate(qt,chol):
    idx=np.arange(N,dtype=np.uint64);Z=np.empty((N,L),np.float32)
    for d in range(L):
        h=g.splitmix64(idx^(np.uint64(0xD1B54A32D192ED03)*np.uint64(d+1)))
        u=((h>>np.uint64(11)).astype(np.float64)+0.5)*(1.0/(1<<53));Z[:,d]=ndtri(np.clip(u,1e-12,1-1e-12)).astype(np.float32)
    Y=Z.astype(np.float64)@chol.T.astype(np.float64);return inv_quantile(ndtr(Y),qt)


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    ar_bytes,co,R0=g.fit_prefix(X,eps)
    TV,TF,TY=s.gather_train(X,R0,co);HV,HF=s.gather_held(X,R0,co,eps)
    scale_bytes,w,lo,hi=fit_scale(TF,TY);tsp=scales(TF,w,lo,hi);hsp=scales(HF,w,lo,hi)
    TN=TV/tsp[:,None];HN=HV/hsp[:,None]
    copula_bytes,qt,chol,corr=fit_empirical_copula(TN)
    print(json.dumps({'training_vectors':len(TN),'heldout_vectors':len(HN),'candidate_count':N,'scale_model_bytes':scale_bytes,'copula_model_bytes':copula_bytes}),flush=True)
    CAND=generate(qt,chol);tree=cKDTree(CAND,compact_nodes=True,balanced_tree=True)
    sel=np.linspace(0,len(HN)-1,NTARGET,dtype=np.int64)
    hit_indices=[];counts=[];nearest_abs=[]
    for qi,j in enumerate(sel):
        y=HN[j];sc=float(hsp[j]);r=(eps+0.500001)/sc
        ids=tree.query_ball_point(y,r=r,p=np.inf)
        good=[]
        if ids:
            ids=np.asarray(ids,dtype=np.int64)
            # Actual decoder reconstruction rounds scaled normalized codeword to integer residual.
            phys=np.rint(CAND[ids].astype(np.float64)*sc)
            ok=np.max(np.abs(HV[j][None,:]-phys),axis=1)<=eps*(1+1e-10)
            good=ids[ok]
        hit_indices.append(int(np.min(good)) if len(good) else None);counts.append(int(len(good)))
        dn=float(tree.query(y,k=1,p=np.inf)[0]);nearest_abs.append(max(0.0,dn*sc-0.5))
        if qi%64==0:print(json.dumps({'target':qi,'scale':sc,'hits':counts[-1],'min_index':hit_indices[-1],'nearest_abs_lower_bound':nearest_abs[-1]}),flush=True)
    hits=np.asarray([x is not None for x in hit_indices]);F=float(np.mean(hits))
    p_hat=float(-math.log1p(-F)/N) if 0<F<1 else (1.0 if F>=1 else 0.0)
    pred24=float(1-math.exp(-p_hat*(1<<24))) if p_hat>0 else 0.0
    if 0<p_hat<1:
        geom_bits=float(-math.log2(p_hat)-((1-p_hat)/p_hat)*math.log2(1-p_hat));geom_bps=geom_bits/L
    elif p_hat>=1:geom_bits=geom_bps=0.0
    else:geom_bits=geom_bps=None
    q=[x for x in hit_indices if x is not None];idxq={}
    if q:
        for p in (10,25,50,75,90,95,99):idxq[str(p)]=float(np.percentile(q,p))
    szb=g.szrun(X[g.TARGET_CH,g.TRAIN:g.END],eps);szbps=8*szb[0]/(len(g.TARGET_CH)*(g.END-g.TRAIN));target=szbps/2
    rawtree=cKDTree(TV,compact_nodes=True,balanced_tree=True);dr,_=rawtree.query(HV,k=1,p=np.inf)
    ntree=cKDTree(TN,compact_nodes=True,balanced_tree=True);dn,_=ntree.query(HN,k=1,p=np.inf);da=dn*hsp
    out={'global_std':std,'eps':eps,'hard_region_c0':g.C0,'ar_order':g.P,'block_length':L,'candidate_count':N,'candidate_index_bits':22,
         'training_vectors':len(TN),'heldout_vectors':len(HN),'sampled_targets':NTARGET,'ar_model_bytes':ar_bytes,'scale_model_bytes':scale_bytes,'copula_model_bytes':copula_bytes,
         'scale_coefficients_float32':w.tolist(),'scale_clip':[lo,hi],'max_abs_offdiag_rank_gaussian_corr':float(np.max(np.abs(corr-np.eye(L)))),
         'raw_prefix_fraction_within_2eps':float(np.mean(dr<=2*eps)),'state_normalized_prefix_fraction_within_2eps':float(np.mean(da<=2*eps)),
         'coverage_fraction_at_2pow22':F,'mean_exact_hits_per_target':float(np.mean(counts)),'median_exact_hits_per_target':float(np.median(counts)),
         'nearest_abs_lower_bound_median':float(np.median(nearest_abs)),'nearest_abs_lower_bound_p90':float(np.percentile(nearest_abs,90)),'hit_index_percentiles':idxq,
         'estimated_per_candidate_hit_probability':p_hat,'predicted_coverage_at_2pow24_poisson':pred24,'estimated_geometric_index_bits_per_block':geom_bits,'estimated_geometric_index_bps':geom_bps,
         'matched_sz3_bps':szbps,'two_x_target_bps':target,'ratio_estimated_geometric_bps_to_2x_target':geom_bps/target if geom_bps is not None else None,
         'scope':'State-normalized procedural hard-box covering diagnostic, NOT a compression claim. This is the missing follow-up promised by the state-normalization audit. A six-parameter scale model is fitted only from the already decoded AR32 prefix, serialized as float32, and every 8-D residual block is divided by a scale the decoder can recompute from its own state. A 257-point-per-coordinate empirical marginal model plus 8x8 Gaussian copula is then fitted in normalized space, serialized/decoded, and a fixed SplitMix64 index generates exactly 2^22 normalized codewords. For 512 deterministic held-out hard blocks, candidate radius is eps/decoder-known scale and every reported hit is rechecked after actual scaled-codeword rounding in original amplitude units. Candidate ordering is deterministic, so a hit has a decoder-regenerable index; Poisson/geometric rates are diagnostics only until a sequential index/escape codec exists. Matched SZ3 supplies the local 2x target. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_state_normalized_procedural_cover.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
