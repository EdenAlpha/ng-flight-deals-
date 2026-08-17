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
    sf.build_numba(Xi[:,:64],cod,tab,1,64,False)
    for _ in range(2):
        _,K,ctxs,vals=sf.build_numba(Xi,cod,tab,1,4096,True)
        nt=sf.refit(ctxs,vals,tab)
        if np.array_equal(nt,tab): break
        tab=nt
    R,K,_,_=sf.build_numba(Xi,cod,tab,1,NT,False)
    return Xi,R.astype(np.int64),K.astype(np.int64),tab


def knn_hper(A,rng,k=5):
    Q=np.asarray(A,np.float64)+rng.uniform(-.5,.5,np.asarray(A).shape)
    nn=NearestNeighbors(n_neighbors=k+1,metric='chebyshev',n_jobs=-1).fit(Q)
    d,_=nn.kneighbors(Q)
    r=np.maximum(d[:,-1],1e-12)
    B=Q.shape[1]; M=Q.shape[0]
    return float((digamma(M)-digamma(k)+B*np.mean(np.log(2*r)))/math.log(2)/B)


def corrected(A,rng,H0):
    real=knn_hper(A,rng)
    S=np.stack([rng.permutation(A[:,j]) for j in range(A.shape[1])],axis=1)
    shuf=knn_hper(S,rng)
    h=real-(shuf-H0)
    return {'real_hper':real,'shuffle_hper':shuf,'bias_corrected_hper':h,
            'hardbox_268_diagnostic_bps':h-math.log2(268)}


def main(path):
    with h5py.File(path,'r') as hf:
        X=np.asarray(hf['Acoustic'][:,C0:C0+C],np.float64).T
    Xi,R,K,tab=rebuild_incumbent(X)
    me=float(np.max(np.abs(X-R)))
    if me>133.0: raise RuntimeError(('incumbent replay',me))
    P=R-STEP*K
    N=Xi-P
    seq=N.T.reshape(-1)
    H0=entropy_discrete(seq)

    scan=[]
    for B in (1,2,4,8,16,32):
        reps=[]; nrep=3 if B<=16 else 2; M=14000 if B<=16 else 10000
        for seed in range(nrep):
            rng=np.random.default_rng(700+B*10+seed)
            st=rng.integers(0,len(seq)-B,M)
            A=np.stack([seq[s:s+B] for s in st])
            z=corrected(A,rng,H0); z['seed']=seed; reps.append(z)
        row={'B':B,'mean_corrected_hper':float(np.mean([r['bias_corrected_hper'] for r in reps])),
             'mean_hardbox_268_diagnostic_bps':float(np.mean([r['hardbox_268_diagnostic_bps'] for r in reps])),
             'sd_corrected_hper':float(np.std([r['bias_corrected_hper'] for r in reps],ddof=1)) if len(reps)>1 else 0.0,
             'replicates':reps}
        scan.append(row); print(json.dumps({'scan_block':row}),flush=True)

    rectangles=[]
    # True 2-D blocks capture both channel and time dependence; larger shapes are deliberately included
    # even though KNN bias becomes harder and therefore remain diagnostics, not proofs.
    for ht,w,M in ((2,4,14000),(4,4,14000),(4,8,9000),(8,4,9000),(16,2,9000),(8,8,6500),(16,4,6500),(32,2,6500)):
        reps=[]; B=ht*w
        for seed in range(2):
            rng=np.random.default_rng(13000+B*10+ht+seed)
            cs=rng.integers(0,C-w+1,M); ts=rng.integers(0,NT-ht+1,M)
            A=np.stack([N[c:c+w,t:t+ht].T.reshape(-1) for c,t in zip(cs,ts)])
            z=corrected(A,rng,H0); z['seed']=seed; reps.append(z)
        row={'shape':[ht,w],'B':B,
             'mean_corrected_hper':float(np.mean([r['bias_corrected_hper'] for r in reps])),
             'mean_hardbox_268_diagnostic_bps':float(np.mean([r['hardbox_268_diagnostic_bps'] for r in reps])),
             'replicates':reps}
        rectangles.append(row); print(json.dumps({'rectangle':row}),flush=True)

    out={'scope':('Empirical finite-block entropy-rate diagnostic on the exact PR658 incumbent innovation. '
                  'The innovation transform was rebuilt causally from the canonical record; it preserves the source information. '
                  'For the full 133.697 hard tolerance and integer sources, any one reconstruction value is compatible with at most '
                  '268 source integers, motivating the Shannon-volume subtraction log2(268). KNN block entropy is bias-corrected '
                  'with coordinate-shuffled controls pinned to the exactly known scalar marginal entropy. THIS IS NOT A RIGOROUS '
                  'FINITE-FILE IMPOSSIBILITY PROOF: KNN estimation, finite-sample/high-dimensional bias, stationarity/smoothness, and '
                  'unseen higher-order dependence remain caveats. 2-D rectangles are included because 1-D scan blocks underrepresent '
                  'joint space-time dependence.'),
         'shape':[C,NT],'current_exact_bytes':CURRENT_BYTES,'current_exact_bps':8*CURRENT_BYTES/(C*NT),
         'matched_sz3_bytes':MATCHED_SZ3,'two_x_target_bps':TARGET_BPS,'maxerr_incumbent':me,
         'innovation_scalar_entropy_exact':H0,'log2_268':math.log2(268),'scan_blocks':scan,'rectangles':rectangles}
    json.dump(out,open('imperial_entropy_rate_floor.json','w'),indent=2)
    print(json.dumps({'summary':out},indent=2),flush=True)

if __name__=='__main__': main(sys.argv[1])
