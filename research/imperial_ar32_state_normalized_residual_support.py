import json,sys
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_procedural_random_cover as g
import imperial_decoder_phase_automaton as m

L=g.L;RIDGE=1e-3

def feat(state,base):
    s=np.asarray(state,np.float64);b=np.asarray(base,np.float64);ds=np.diff(s)
    vals=[1.0,np.log1p(np.std(s)),np.log1p(np.std(ds)),np.log1p(np.mean(np.abs(ds))),np.log1p(np.sqrt(np.mean(b*b))),np.log1p(abs(float(s[-1])))]
    return np.asarray(vals,np.float64)

def gather_train(X,R0,co):
    V=[];F=[];Y=[]
    for c in range(g.C):
        for t in range(g.P,g.TRAIN-g.L+1,g.L):
            st=R0[c,t-g.P:t];base=g.openloop(st,co);v=X[c,t:t+g.L]-base;V.append(v);F.append(feat(st,base));Y.append(np.log(max(1.0,float(np.sqrt(np.mean(v*v))))))
    return np.asarray(V,float),np.asarray(F,float),np.asarray(Y,float)

def gather_held(X,R0,co,eps):
    V=[];F=[];sc=[]
    for c in g.TARGET_CH:
        state=R0[c,-g.P:].copy()
        for t in range(g.TRAIN,g.END,g.L):
            base=g.openloop(state,co);src=X[c,t:t+g.L];v=src-base;V.append(v);F.append(feat(state,base))
            for q in range(g.L):
                vv=float(co[-1])
                for j in range(g.P):vv+=float(co[j])*state[-1-j]
                pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/g.STEP));rr=pred+g.STEP*k
                if abs(float(src[q])-rr)>eps*(1+1e-10):raise RuntimeError('held hard')
                state[:-1]=state[1:];state[-1]=rr
    return np.asarray(V,float),np.asarray(F,float)

def pd(a):
    return {str(p):float(np.percentile(a,p)) for p in (10,25,50,75,90,95,99)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:g.END,g.C0:g.C0+g.C],np.float64).T
    mb,co,R0=g.fit_prefix(X,eps);TV,TF,TY=gather_train(X,R0,co);HV,HF=gather_held(X,R0,co,eps)
    A=TF.T@TF+RIDGE*np.eye(TF.shape[1]);w=np.linalg.solve(A,TF.T@TY)
    tsp=np.exp(TF@w);hsp=np.exp(HF@w)
    # Keep scale bounded by the training domain to avoid a tiny extrapolation artifact.
    lo,hi=np.percentile(tsp,[1,99]);tsp=np.clip(tsp,lo,hi);hsp=np.clip(hsp,lo,hi)
    TN=TV/tsp[:,None];HN=HV/hsp[:,None]
    rawtree=cKDTree(TV,compact_nodes=True,balanced_tree=True);dr,_=rawtree.query(HV,k=1,p=np.inf)
    ntree=cKDTree(TN,compact_nodes=True,balanced_tree=True);dn,_=ntree.query(HN,k=1,p=np.inf);da=dn*hsp
    actual=np.sqrt(np.mean(HV*HV,axis=1));predcorr=float(np.corrcoef(np.log1p(actual),np.log1p(hsp))[0,1])
    out={'global_std':std,'eps':eps,'ar_order':g.P,'block_length':L,'training_vectors':len(TV),'heldout_vectors':len(HV),'scale_model':{'features':['bias','log1p_state_std','log1p_state_diff_std','log1p_state_mean_abs_diff','log1p_openloop_rms','log1p_abs_last_state'],'float64_coefficients':w.tolist(),'training_scale_p1_p99':[float(lo),float(hi)],'heldout_log_scale_correlation_with_actual_residual_rms':predcorr,'model_bytes_nominal_float32':int(4*len(w)+32)},'raw_prefix_nearest':{'linf_percentiles':pd(dr),'fraction_within_eps':float(np.mean(dr<=eps)),'fraction_within_2eps':float(np.mean(dr<=2*eps))},'state_normalized_prefix_nearest':{'absolute_linf_percentiles_after_target_rescale':pd(da),'fraction_within_eps':float(np.mean(da<=eps)),'fraction_within_2eps':float(np.mean(da<=2*eps)),'normalized_linf_percentiles':pd(dn)},'scale_stats':{'train_predicted_median':float(np.median(tsp)),'heldout_predicted_median':float(np.median(hsp)),'heldout_actual_residual_rms_median':float(np.median(actual))},'scope':'Decoder-state normalization audit, not a compression claim. Same AR32/open-loop 8-D residuals as PR345/349. A six-parameter log-linear scale model is fitted only on prefix blocks using decoder-known state features (recent reconstructed state/differences and open-loop predictor energy). Prefix and held-out residual blocks are divided by their predicted decoder-known scales, then exact Chebyshev nearest-neighbor support is measured. For each target the normalized distance is multiplied back by that target scale, so the epsilon test is in original amplitude units. If coverage improves strongly, a single normalized procedural codebook could represent state-dependent physical amplitudes with no per-block scale metadata. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_state_normalized_residual_support.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
