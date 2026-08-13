import sys,json,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_additive_block_cover as b

_CACHE={}; TRAIN_STATS=[]

def assign_linf(V,C):
    idx=np.empty(len(V),np.int32);dist=np.empty(len(V),np.float64)
    for s in range(0,len(V),512):
        A=V[s:s+512];D=np.max(np.abs(A[:,None,:]-C[None,:,:]),axis=2);q=np.argmin(D,axis=1);idx[s:s+len(A)]=q;dist[s:s+len(A)]=D[np.arange(len(A)),q]
    return idx,dist

def linf_stage(V,k,seed):
    # Deterministic farthest-point k-center initialization in Chebyshev geometry.
    C=np.empty((k,V.shape[1]),np.float64);C[0]=np.median(V,axis=0);best=np.max(np.abs(V-C[0]),axis=1)
    for j in range(1,k):
        q=int(np.argmax(best));C[j]=V[q];d=np.max(np.abs(V-C[j]),axis=1);best=np.minimum(best,d)
    # L-infinity Lloyd refinement: assign by Chebyshev distance, update each
    # center to the coordinatewise midrange of its assigned bounding box.
    for _ in range(5):
        idx,dist=assign_linf(V,C);old=C.copy()
        for j in range(k):
            A=V[idx==j]
            if len(A):C[j]=0.5*(A.min(axis=0)+A.max(axis=0))
        if np.array_equal(np.rint(old),np.rint(C)):break
    C=np.rint(C).astype(np.int32);idx,dist=assign_linf(V,C.astype(np.float64));res=V-C[idx]
    TRAIN_STATS.append({'stage':len(TRAIN_STATS)+1,'k':k,'median_linf':float(np.median(dist)),'p90_linf':float(np.quantile(dist,.9)),'p99_linf':float(np.quantile(dist,.99)),'max_linf':float(dist.max()),'residual_std':float(res.std())})
    return C,res,idx

def train_codebooks(V):
    TRAIN_STATS.clear();c1,r1,_=linf_stage(V,256,101);c2,r2,_=linf_stage(r1,256,202);c3,r3,i3=linf_stage(r2,256,303)
    cnt=np.bincount(i3,minlength=256);order=np.argsort(-cnt,kind='stable');return c1,c2,c3[order]

def exact_search(y,c1,c2,c3):
    key=(id(c1),id(c2));z=_CACHE.get(key)
    if z is None:
        n2=len(c2);sums=(c1[:,None,:].astype(np.float64)+c2[None,:,:].astype(np.float64)).reshape(-1,b.L);tree=cKDTree(sums,compact_nodes=True,balanced_tree=True);z=(tree,sums,n2);_CACHE[key]=z
    tree,sums,n2=z;queries=y[None,:].astype(np.float64)-c3.astype(np.float64);dist,idx=tree.query(queries,k=1,p=np.inf,workers=1);g=int(np.argmin(dist));pidx=int(idx[g]);i1=pidx//n2;i2=pidx%n2;v=sums[pidx].astype(np.int64)+c3[g].astype(np.int64)
    return int(i1),int(i2),int(g),v,float(dist[g])

b.train_codebooks=train_codebooks;b.search=exact_search;b.N3S=(64,256);b.BEAM=0
if __name__=='__main__':
    b.main(sys.argv[1])
    p='imperial_ar32_additive_block_cover.json';d=json.load(open(p));d['codebook_training_geometry']='three-stage deterministic L-infinity k-center / bounding-box-midrange refinement, not L2 k-means';d['training_stage_stats']=TRAIN_STATS;d['scope']=d['scope']+' This branch replaces all L2 k-means stages with Chebyshev/L-infinity covering training aligned to the actual max-error acceptance geometry and searches the full additive codebook exactly.';json.dump(d,open('imperial_ar32_linf_additive_cover.json','w'),indent=2)
