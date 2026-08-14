import gc,json,sys,math
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_ar32_state_normalized_residual_support as s
import imperial_decoder_phase_automaton as m

L=g.L; KNN=64; NTARGET=512; RIDGE=1e-3
# Eight local interpolation/extrapolation positions. 14 center bits + 6 neighbor bits
# + 3 alpha bits = 23 bits / 8 samples = 2.875 bps before escape/mode coding.
ALPHAS=np.asarray([-1.0,-0.5,0.25,0.5,0.75,1.0,1.5,2.0],np.float32)


def fit_scale_model(TF,TY):
    A=TF.T@TF+RIDGE*np.eye(TF.shape[1]); w=np.linalg.solve(A,TF.T@TY).astype(np.float32)
    raw=np.exp(TF@w.astype(np.float64)); lo,hi=np.percentile(raw,[1,99]); lo=np.float32(lo); hi=np.float32(hi)
    # Treat float32 coefficients and clipping bounds as the serialized decoder model.
    wd=w.copy(); lod=np.float32(lo); hid=np.float32(hi)
    return wd,lod,hid,int(4*(len(wd)+2)+32)


def scales(F,w,lo,hi):
    return np.clip(np.exp(F@w.astype(np.float64)),float(lo),float(hi))


def decoded_prefix_centers(R0,co,w,lo,hi):
    C=[]; NN=[]
    for c in range(g.C):
        for t in range(g.P,g.TRAIN-g.L+1,g.L):
            st=R0[c,t-g.P:t]; base=g.openloop(st,co); ph=R0[c,t:t+g.L].astype(np.float64)-base
            sc=float(scales(s.feat(st,base)[None,:],w,lo,hi)[0]); C.append(ph/sc); NN.append(sc)
    return np.asarray(C,np.float32),np.asarray(NN,np.float32)


def build_atlas(C):
    tree=cKDTree(C,compact_nodes=True,balanced_tree=True)
    dist,idx=tree.query(C,k=KNN+1,p=np.inf,workers=1); idx=idx[:,1:]; dist=dist[:,1:]
    n=len(C); nv=len(ALPHAS); out=np.empty((n*KNN*nv,L),np.float32); p=0
    # Alpha-major chunks keep peak memory low; the decoder can regenerate the same ordering.
    for a in range(0,n,256):
        ids=np.arange(a,min(a+256,n)); A=C[ids]; B=C[idx[ids]]; D=B-A[:,None,:]
        for alpha in ALPHAS:
            Z=(A[:,None,:]+float(alpha)*D).reshape(-1,L); q=len(Z); out[p:p+q]=Z; p+=q
    if p!=len(out): raise RuntimeError((p,len(out)))
    return out,dist


def exact_hits(tree,atlas,y_norm,y_phys,scale,eps):
    rad=(eps+0.500001)/scale
    ids=tree.query_ball_point(y_norm,r=rad,p=np.inf)
    if not ids: return 0,None,None
    ids=np.asarray(ids,np.int64); phys=np.rint(atlas[ids].astype(np.float64)*scale)
    er=np.max(np.abs(phys-y_phys[None,:]),axis=1); ok=er<=eps*(1+1e-10)
    if not np.any(ok): return 0,None,float(np.min(er))
    good=ids[ok]; return int(np.sum(ok)),int(np.min(good)),float(np.min(er[ok]))


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,std=m.stats(d); eps=.1*std; X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps)
    TV,TF,TY=s.gather_train(X,R0,co); HV,HF=s.gather_held(X,R0,co,eps)
    w,lo,hi,scale_bytes=fit_scale_model(TF,TY); tsp=scales(TF,w,lo,hi); hsp=scales(HF,w,lo,hi)
    C,cscale=decoded_prefix_centers(R0,co,w,lo,hi)
    HN=HV/hsp[:,None]; sel=np.linspace(0,len(HV)-1,NTARGET,dtype=np.int64)
    print(json.dumps({'prefix_centers':len(C),'heldout_vectors':len(HV),'sampled_targets':len(sel),'scale_bytes':scale_bytes,'alphas':ALPHAS.tolist()}),flush=True)
    atlas,nbrdist=build_atlas(C); print(json.dumps({'implicit_codewords':len(atlas),'atlas_mb':atlas.nbytes/1e6}),flush=True)
    tree=cKDTree(atlas,compact_nodes=True,balanced_tree=True)
    counts=[]; first=[]; nearest=[]
    for qi,j in enumerate(sel):
        cnt,fst,er=exact_hits(tree,atlas,HN[j],HV[j],float(hsp[j]),eps); counts.append(cnt); first.append(fst)
        # Exact physical error of several nearest normalized candidates.
        dd,ii=tree.query(HN[j],k=8,p=np.inf); ii=np.atleast_1d(ii).astype(np.int64)
        pp=np.rint(atlas[ii].astype(np.float64)*float(hsp[j])); ne=float(np.min(np.max(np.abs(pp-HV[j][None,:]),axis=1))); nearest.append(ne)
        if qi%64==0: print(json.dumps({'target':qi,'hits':cnt,'first':fst,'nearest_exact_linf':ne}),flush=True)
    hit=np.asarray([x is not None for x in first]); F=float(np.mean(hit))
    szb=g.szrun(X[g.TARGET_CH,g.TRAIN:g.END],eps); szbps=8*szb[0]/(len(g.TARGET_CH)*(g.END-g.TRAIN)); target=szbps/2
    center_bits=int(math.ceil(math.log2(len(C)))); index_bits=center_bits+int(math.ceil(math.log2(KNN)))+int(math.ceil(math.log2(len(ALPHAS)))); index_bps=index_bits/L
    req_sz3=(szbps-target)/(szbps-index_bps) if index_bps<target else 1.0
    # Empirical nearest-prefix coverage is a useful generator-efficiency control.
    ptree=cKDTree(C,compact_nodes=True,balanced_tree=True); pcov=[]
    for j in sel:
        dd,ii=ptree.query(HN[j],k=1,p=np.inf); pp=np.rint(C[int(ii)].astype(np.float64)*float(hsp[j])); pcov.append(float(np.max(np.abs(pp-HV[j])))<=eps)
    out={'global_std':std,'eps':eps,'ar_order':g.P,'block_length':L,'decoder_known_prefix_centers':len(C),'scale_model_float32_coefficients':w.tolist(),'scale_clip':[float(lo),float(hi)],'scale_model_bytes':scale_bytes,'heldout_log_scale_correlation_with_actual_residual_rms':float(np.corrcoef(np.log1p(np.sqrt(np.mean(HV*HV,axis=1))),np.log1p(hsp))[0,1]),'nearest_neighbors_per_center':KNN,'alphas':ALPHAS.tolist(),'implicit_codewords':int(len(atlas)),'center_id_bits':center_bits,'neighbor_rank_bits':int(math.ceil(math.log2(KNN))),'alpha_bits':int(math.ceil(math.log2(len(ALPHAS)))),'nominal_index_bits_per_block':index_bits,'nominal_index_bps':index_bps,'prefix_neighbor_normalized_linf_median':float(np.median(nbrdist)),'prefix_neighbor_normalized_linf_p90':float(np.percentile(nbrdist,90)),'sampled_targets':len(sel),'direct_normalized_prefix_coverage_exact_eps':float(np.mean(pcov)),'atlas_coverage_fraction_exact_eps':F,'mean_valid_hits_per_target':float(np.mean(counts)),'median_valid_hits_per_target':float(np.median(counts)),'nearest_exact_linf_median':float(np.median(nearest)),'nearest_exact_linf_p90':float(np.percentile(nearest,90)),'first_hit_index_percentiles':({str(p):float(np.percentile([x for x in first if x is not None],p)) for p in (10,25,50,75,90,95,99)} if np.any(hit) else {}),'matched_sz3_bps':szbps,'two_x_target_bps':target,'nominal_index_bps_over_2x_target':index_bps/target,'minimum_atlas_coverage_to_beat_2x_if_escapes_cost_sz3':req_sz3,'scope':'State-normalized prefix-affine covering gate, NOT yet a compression claim. This is the untested constructive follow-up promised by PR350. A tiny transmitted float32 scale model is derived from prefix-only decoder-state features. Every decoder-known reconstructed prefix residual block is divided by its decoder-reproducible predicted scale. In that normalized 8-D space the decoder rebuilds a 64-nearest-neighbor graph and eight fixed affine interpolation/extrapolation points per edge, yielding >8 million zero-dictionary codewords. For each held-out block, the same decoder-state scale maps a normalized codeword back into physical residual units; candidates are accepted only after integer rounding and an exact unchanged +/-epsilon check. The 23-bit procedural address is 2.875 bps before mode/escape overhead, below the matched local 2x-SZ3 target. Target AR state is still held to the incumbent trajectory, so coverage is a geometry gate: a sequential codec is justified only if coverage becomes very high. No AI.'}
    print(json.dumps(out,indent=2),flush=True); json.dump(out,open('imperial_ar32_state_normalized_affine_atlas_cover.json','w'),indent=2)
    del tree,atlas; gc.collect()

if __name__=='__main__': main(sys.argv[1])
