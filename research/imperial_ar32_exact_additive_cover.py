import sys,numpy as np
from scipy.spatial import cKDTree
import imperial_ar32_additive_block_cover as b

_CACHE={}

def exact_search(y,c1,c2,c3):
    key=(id(c1),id(c2))
    z=_CACHE.get(key)
    if z is None:
        n2=len(c2)
        sums=(c1[:,None,:].astype(np.float64)+c2[None,:,:].astype(np.float64)).reshape(-1,b.L)
        tree=cKDTree(sums,compact_nodes=True,balanced_tree=True)
        z=(tree,sums,n2);_CACHE[key]=z
    tree,sums,n2=z
    queries=y[None,:].astype(np.float64)-c3.astype(np.float64)
    dist,idx=tree.query(queries,k=1,p=np.inf,workers=1)
    g=int(np.argmin(dist));pidx=int(idx[g]);i1=pidx//n2;i2=pidx%n2
    v=sums[pidx].astype(np.int64)+c3[g].astype(np.int64)
    return int(i1),int(i2),int(g),v,float(dist[g])

b.search=exact_search
b.N3S=(64,256)
b.BEAM=0

if __name__=='__main__':b.main(sys.argv[1])
