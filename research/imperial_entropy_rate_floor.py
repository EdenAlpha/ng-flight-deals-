import json, math, sys
import h5py
import numpy as np
from scipy.special import digamma
from sklearn.neighbors import NearestNeighbors
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_state_residue_fast as sf

C=128; NT=30000; C0=512; STEP=267; RAD=133
CURRENT_BYTES=2464819; MATCHED_SZ3=2767977
TARGET_BPS=8.0*(MATCHED_SZ3/2.0)/(C*NT)


def entropy_discrete(x):
    _,cnt=np.unique(np.asarray(x).reshape(-1),return_counts=True)
    p=cnt/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def rebuild_incumbent(X):
    Xi=np.rint(X).astype(np.int64)
    _,co=ah.fits(X)
    _,cod=cg.model_frame(co)
    tab=np.zeros(81,np.int16)
    # Warm JIT, then reproduce the two training/refit passes of the exact prev_left winner in PR #658.
    sf.build_numba(Xi[:,:64],cod,tab,1,64,False)
    for _ in range(2):
        _,K,ctxs,vals=sf.build_numba(Xi,cod,tab,1,4096,True)
        nt=sf.refit(ctxs,vals,tab)
        if np.array_equal(nt,tab): break
        tab=nt
    R,K,_,_=sf.build_numba(Xi,cod,tab,1,NT,False)
    return Xi,R.astype(np.int64),K.astype(np.int64),tab


def knn_hper(A,rng,k=5):
    # Integer dequantization: adding U[-.5,.5] maps discrete entropy to differential entropy
    # for the exact one-dimensional distribution and gives a standard KNN joint-entropy estimator for blocks.
    Q=np.asarray(A,np.float64)+rng.uniform(-.5,.5,np.asarray(A).shape)
    nn=NearestNeighbors(n_neighbors=k+1,metric='chebyshev',n_jobs=-1).fit(Q)
    d,_=nn.kneighbors(Q)
    r=np.maximum(d[:,-1],1e-12)
    B=Q.shape[1]; M=Q.shape[0]
    return float((digamma(M)-digamma(k)+B*np.mean(np.log(2*r)))/math.log(2)/B)


def main(path):
    with h5py.File(path,'r') as hf:
        X=np.asarray(hf['Acoustic'][:,C0:C0+C],np.float64).T
    Xi,R,K,tab=rebuild_incumbent(X)
    me=float(np.max(np.abs(X-R)))
    if me>133.0: raise RuntimeError(('incumbent replay',me))
    # P is the exact decoder-generated predictor+phase center. N is a causal, invertible innovation
    # representation under the fixed incumbent model/state update.
    P=R-STEP*K
    N=Xi-P
    seq=N.T.reshape(-1)  # exact t-major/c-inner causal scan order
    H0=entropy_discrete(seq)
    rows=[]
    for B in (1,2,4,8,16,32):
        reps=[]
        nrep=3 if B<=16 else 2
        M=14000 if B<=16 else 10000
        for seed in range(nrep):
            rng=np.random.default_rng(700+B*10+seed)
            st=rng.integers(0,len(seq)-B,M)
            A=np.stack([seq[s:s+B] for s in st])
            real=knn_hper(A,rng)
            S=np.stack([rng.permutation(A[:,j]) for j in range(B)],axis=1)
            shuf=knn_hper(S,rng)
            # Control for the estimator's dimension-dependent bias by forcing the shuffled process
            # back to the exactly known scalar marginal entropy.
            corrected=real-(shuf-H0)
            reps.append({'seed':seed,'real_hper':real,'shuffle_hper':shuf,
                         'bias_corrected_hper':corrected,
                         'hardbox_268_diagnostic_bps':corrected-math.log2(268)})
        rows.append({'B':B,'mean_corrected_hper':float(np.mean([r['bias_corrected_hper'] for r in reps])),
                     'mean_hardbox_268_diagnostic_bps':float(np.mean([r['hardbox_268_diagnostic_bps'] for r in reps])),
                     'sd_corrected_hper':float(np.std([r['bias_corrected_hper'] for r in reps],ddof=1)) if len(reps)>1 else 0.0,
                     'replicates':reps})
        print(json.dumps({'block':rows[-1]}),flush=True)
    out={'scope':('Empirical finite-block entropy-rate diagnostic on the exact PR658 incumbent innovation. '
                  'For a hard per-sample tolerance of 133.697 and integer sources, any reconstruction value is compatible '
                  'with at most 268 source integers, motivating the Shannon volume subtraction log2(268). KNN block entropy '
                  'is bias-corrected using a coordinate-shuffled control with the same exactly known marginal entropy. '
                  'THIS IS NOT A RIGOROUS FINITE-FILE IMPOSSIBILITY PROOF: finite-sample KNN entropy, stationarity/smoothness, '
                  'and unseen higher-order dependence remain assumptions. It is a diagnostic of where the source entropy rate appears to sit.'),
         'shape':[C,NT],'current_exact_bytes':CURRENT_BYTES,'current_exact_bps':8*CURRENT_BYTES/(C*NT),
         'matched_sz3_bytes':MATCHED_SZ3,'two_x_target_bps':TARGET_BPS,'maxerr_incumbent':me,
         'innovation_scalar_entropy_exact':H0,'log2_268':math.log2(268),'blocks':rows}
    json.dump(out,open('imperial_entropy_rate_floor.json','w'),indent=2)
    print(json.dumps({'summary':out},indent=2),flush=True)

if __name__=='__main__': main(sys.argv[1])
