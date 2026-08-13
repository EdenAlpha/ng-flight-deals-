import json,sys,math
import h5py,numpy as np,zstandard as zstd
from scipy.special import ndtr,ndtri
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_decoder_phase_automaton as m

Q=257;N=1<<22;L=g.L;MASK=g.MASK
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def fit_empirical_copula(V):
    n,d=V.shape
    # Tiny robust marginal model: 257 empirical quantiles per coordinate.
    probs=np.linspace(0,1,Q)
    qt=np.quantile(V,probs,axis=0,method='linear').T
    qt=np.rint(qt).astype(np.int32)
    # Fit dependence after exact rank->Gaussian normalization, so tails and
    # marginal quantization are handled by the empirical tables, not Gaussian raw amplitudes.
    Z=np.empty_like(V,dtype=np.float64)
    for j in range(d):
        order=np.argsort(V[:,j],kind='mergesort');r=np.empty(n,np.float64);r[order]=(np.arange(n)+0.5)/n
        Z[:,j]=ndtri(np.clip(r,1e-6,1-1e-6))
    corr=np.corrcoef(Z,rowvar=False);corr=(corr+corr.T)*0.5
    w,U=np.linalg.eigh(corr);w=np.maximum(w,1e-4);corr=(U*w)@U.T
    D=np.sqrt(np.diag(corr));corr=corr/(D[:,None]*D[None,:]);chol=np.linalg.cholesky(corr+1e-6*np.eye(d))
    return qt,chol.astype(np.float32),corr.astype(np.float32)

def model_frame(qt,chol):
    # Fully charge a potential decoder model; quantiles delta-coded per dimension.
    dq=qt.copy().astype(np.int32);dq[:,1:]-=qt[:,:-1]
    qb=ZC.compress(dq.astype('<i4').tobytes());cb=ZC.compress(chol.astype('<f4').tobytes())
    qd=np.frombuffer(ZD.decompress(qb),'<i4').reshape(qt.shape).copy();qd[:,1:]=np.cumsum(qd[:,1:],axis=1)+qd[:,:1]
    cd=np.frombuffer(ZD.decompress(cb),'<f4').reshape(chol.shape).copy()
    if not np.array_equal(qd,qt):raise RuntimeError('quantile model rt')
    if not np.array_equal(cd,chol):raise RuntimeError('chol model rt')
    return len(qb)+len(cb)+64,qd,cd

def inv_quantile(U,qt):
    # Piecewise-linear inverse of the 257-point empirical CDF table.
    x=np.clip(U,0,1)*(Q-1);i=np.floor(x).astype(np.int32);f=x-i;i=np.minimum(i,Q-2)
    out=np.empty(U.shape,np.float32)
    for d in range(L):
        a=qt[d,i[:,d]].astype(np.float32);b=qt[d,i[:,d]+1].astype(np.float32);out[:,d]=a+(b-a)*f[:,d]
    np.rint(out,out=out);return out

def generate(qt,chol):
    idx=np.arange(N,dtype=np.uint64);Z=np.empty((N,L),np.float32)
    for d in range(L):
        h=g.splitmix64(idx^(np.uint64(0xD1B54A32D192ED03)*np.uint64(d+1)))
        u=((h>>np.uint64(11)).astype(np.float64)+0.5)*(1.0/(1<<53));Z[:,d]=ndtri(np.clip(u,1e-12,1-1e-12)).astype(np.float32)
    Y=Z.astype(np.float64)@chol.T.astype(np.float64);U=ndtr(Y);return inv_quantile(U,qt)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps);TV=g.train_vectors(X,R0,co);HV,H,sel=g.heldout_vectors(X,R0,co,eps)
    qt,chol,corr=fit_empirical_copula(TV);modb,qtd,chd=model_frame(qt,chol)
    print(json.dumps({'training_vectors':len(TV),'sampled_targets':len(H),'candidate_count':N,'copula_model_bytes':modb,'max_abs_rank_corr':float(np.max(np.abs(corr-np.eye(L))))}),flush=True)
    CAND=generate(qtd,chd);tree=cKDTree(CAND,compact_nodes=True,balanced_tree=True)
    hit_indices=[];counts=[];nearest=[]
    for i,y in enumerate(H):
        ids=tree.query_ball_point(y,r=eps,p=np.inf);counts.append(len(ids));hit_indices.append(min(ids) if ids else None);nearest.append(float(tree.query(y,k=1,p=np.inf)[0]))
        if i%64==0:print(json.dumps({'target':i,'hits':len(ids),'min_index':hit_indices[-1],'nearest_linf':nearest[-1]}),flush=True)
    hits=np.asarray([x is not None for x in hit_indices]);F=float(hits.mean())
    p_hat=float(-math.log1p(-F)/N) if 0<F<1 else (1.0 if F>=1 else 0.0);pred24=float(1-math.exp(-p_hat*(1<<24))) if p_hat>0 else 0.0
    if 0<p_hat<1:
        geom_bits=float(-math.log2(p_hat)-((1-p_hat)/p_hat)*math.log2(1-p_hat));geom_bps=geom_bits/L
    elif p_hat>=1:geom_bits=geom_bps=0.0
    else:geom_bits=geom_bps=None
    q=[x for x in hit_indices if x is not None];idxq={}
    if q:
        for p in (10,25,50,75,90,95,99):idxq[str(p)]=float(np.percentile(q,p))
    szb=g.szrun(X[g.TARGET_CH,g.TRAIN:g.END],eps);szbps=8*szb[0]/(len(g.TARGET_CH)*(g.END-g.TRAIN));target=szbps/2
    out={'global_std':std,'eps':eps,'ar_order':g.P,'block_length':L,'candidate_count':N,'candidate_index_bits':22,'training_vectors':len(TV),'heldout_vectors':len(HV),'sampled_targets':len(H),'ar_model_bytes':mb,'copula_model_bytes':modb,'quantile_points_per_dimension':Q,'max_abs_offdiag_rank_gaussian_corr':float(np.max(np.abs(corr-np.eye(L)))),'coverage_fraction_at_2pow22':F,'mean_hits_per_target':float(np.mean(counts)),'median_hits_per_target':float(np.median(counts)),'nearest_linf_median':float(np.median(nearest)),'nearest_linf_p90':float(np.percentile(nearest,90)),'hit_index_percentiles':idxq,'estimated_per_candidate_hit_probability':p_hat,'predicted_coverage_at_2pow24_poisson':pred24,'estimated_geometric_index_bits_per_block':geom_bits,'estimated_geometric_index_bps':geom_bps,'matched_sz3_bps':szbps,'two_x_target_bps':target,'ratio_estimated_geometric_bps_to_2x_target':geom_bps/target if geom_bps is not None else None,'scope':'Procedural empirical-copula covering diagnostic, NOT a compression claim. Same AR32 prefix/held-out residual geometry as PR345, but candidate generation no longer assumes raw-amplitude Gaussian mixtures. Each of the 8 residual coordinates is represented by a 257-point empirical quantile table; dependence is represented by an 8x8 Gaussian copula fitted after rank normalization. Both potential decoder models are actually serialized/decoded and their bytes reported. A fixed SplitMix64 index deterministically generates correlated Gaussian ranks, which are mapped through the empirical inverse CDFs to 2^22 synthetic 8-D residual codewords. Exact L-infinity cKDTree queries test 512 held-out hard blocks against the unchanged +/-epsilon box. First-index/geometric and 2^24 coverage numbers remain diagnostic estimates only until a real seed/index codec is built. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_empirical_copula_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
