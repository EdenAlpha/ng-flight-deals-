import json, math, sys
import h5py
import numpy as np
from scipy.spatial import cKDTree
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128; NT=30000; RAD=133; HALF=15000
CBS=(2,4,10,14,20)
BS=(8,16)
KS=(1,4,16,64,256,1024,4096)
KNN=16

def h2(p):
    if p<=0.0 or p>=1.0:return 0.0
    return -p*math.log2(p)-(1-p)*math.log2(1-p)

def blocks(A,B,t0,t1):
    # channel-major, non-overlapping temporal blocks; decoder/source alignment is fixed.
    n=(t1-t0)//B
    return np.ascontiguousarray(A[:,t0:t0+n*B].reshape(A.shape[0],n,B).reshape(-1,B))

def analyze(X,R,B):
    P=blocks(R,B,0,HALF).astype(np.float64,copy=False)
    Y=blocks(X,B,HALF,NT).astype(np.float64,copy=False)
    tree=cKDTree(P,compact_nodes=True,balanced_tree=True)
    dist,idx=tree.query(Y,k=KNN,p=np.inf,distance_upper_bound=RAD,workers=-1)
    if KNN==1:
        dist=dist[:,None];idx=idx[:,None]
    finite=np.isfinite(dist)
    anyhit=finite[:,0]
    nearest=idx[:,0]
    valid_nearest=nearest[anyhit]
    # Count how often a prototype appears anywhere among the 16 nearest legal candidates.
    cand=idx[finite]
    counts=np.bincount(cand,minlength=P.shape[0]) if cand.size else np.zeros(P.shape[0],np.int64)
    order=np.argsort(counts)[::-1]
    top=[]
    for K in KS:
        K=min(K,P.shape[0])
        chosen=order[:K]
        # membership among returned legal candidate set; this is a conservative lower bound
        # on coverage by the selected vocabulary because only KNN legal neighbours are enumerated.
        mask=np.isin(idx,chosen) & finite
        cov=float(np.mean(np.any(mask,axis=1)))
        optimistic_flag=h2(cov)/B
        optimistic_addr=(cov*math.ceil(math.log2(max(1,K))))/B
        top.append({'K':int(K),'coverage_lower_bound':cov,'flag_entropy_bps':optimistic_flag,'fixed_address_bps':optimistic_addr,'flag_plus_address_bps':optimistic_flag+optimistic_addr})
    # Entropy of nearest-prototype identities among hits: diagnostic address floor if nearest IDs were entropy coded.
    if valid_nearest.size:
        cc=np.bincount(valid_nearest,minlength=P.shape[0]);q=cc[cc>0].astype(np.float64);q/=q.sum();hid=float(-(q*np.log2(q)).sum())
        unique_used=int(np.count_nonzero(cc))
    else:
        hid=0.0;unique_used=0
    zero=np.zeros(B,np.float64)
    zero_cov=float(np.mean(np.max(np.abs(Y-zero),axis=1)<=RAD))
    return {
        'B':B,'train_prototypes':int(P.shape[0]),'test_blocks':int(Y.shape[0]),
        'any_legal_prototype_fraction':float(np.mean(anyhit)),
        'nearest_identity_entropy_bits_per_hit':hid,
        'nearest_identity_entropy_bps_over_all_samples':float(np.mean(anyhit)*hid/B),
        'nearest_unique_prototypes_used':unique_used,
        'zero_prototype_coverage':zero_cov,
        'top_vocabulary':top,
        'knn':KNN,
        'note':'Top-vocabulary coverage is conservative: candidates are limited to the 16 nearest legal prior reconstructed prototypes. All prototypes come only from the already reconstructed first half and are decoder-known for the second half.'
    }

def main(path,cb):
    cb=int(cb)
    if cb not in CBS:raise RuntimeError(('cb',cb))
    a.C=C;a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T
        _,hu=a.fits(X);R,K=a.run_ar(X,hu)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('hard',cb,me,eps))
        rows=[analyze(X,R,B) for B in BS]
        out={'cb':cb,'c0':c0,'eps':eps,'maxerr_ar_reconstruction':me,'rows':rows,'scope':'Held-out legal-prototype vocabulary audit. First 15000 samples are reconstructed with the existing Huber AR32/step267 path; those reconstructed blocks are decoder-known prototypes. Test source blocks come only from samples 15000:30000. A prototype hit is legal iff every coordinate is within integer radius 133. No source prototype, future information, or uncharged transmitted dictionary is used.'}
        print(json.dumps(out,indent=2),flush=True)
        json.dump(out,open(f'imperial_legal_prototype_vocab_cb{cb}.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
