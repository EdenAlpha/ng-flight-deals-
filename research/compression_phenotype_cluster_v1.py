#!/usr/bin/env python3
from __future__ import annotations
import glob,json,math,os,sys
import numpy as np

FEATURES=(
 'time_delta_nonzero_fraction',
 'time_delta_entropy_bits',
 'time_delta_zstd_bps',
 'carrier_bps',
 'carrier_transition_nonzero_fraction',
 'space_delta_nonzero_fraction',
 'lorenzo_zstd_bps',
 'adjacent_space_corr',
 'temporal_lag1_corr',
 'best_temporal_corr',
 'best_neighbor_shift_corr',
 'spectral_entropy_2d',
 'top256_energy',
 'svd16_energy',
 'svd16_centered_energy',
)


def load_rows(root):
    files=sorted(glob.glob(os.path.join(root,'**','compression_phenotype_*.json'),recursive=True))
    rows=[]
    for p in files:
        d=json.load(open(p));m=d['summary']['metrics']
        v=[]
        for k in FEATURES:
            x=float(m[k]['median'])
            if k in ('adjacent_space_corr','temporal_lag1_corr','best_temporal_corr','best_neighbor_shift_corr'):
                x=abs(x)
            v.append(x)
        rows.append({'dataset':d['dataset'],'file':p,'shape':d['shape'],'global_std':d['global_std'],'eps':d['eps'],'vector':v,'summary':d['summary']})
    if len(rows)<2:raise RuntimeError(('need >=2 phenotype files',files))
    return rows


def pairwise(z):
    n=z.shape[0];D=np.zeros((n,n),float)
    for i in range(n):
        for j in range(i+1,n):
            D[i,j]=D[j,i]=float(np.sqrt(np.mean((z[i]-z[j])**2)))
    return D


def agglomerate(D,names):
    clusters={i:[i] for i in range(len(names))};active=list(clusters);nextid=len(names);merges=[]
    def dist(a,b):
        vals=[D[i,j] for i in clusters[a] for j in clusters[b]]
        return float(np.mean(vals))
    while len(active)>1:
        best=None
        for ai in range(len(active)):
            for bi in range(ai+1,len(active)):
                a,b=active[ai],active[bi];dd=dist(a,b)
                if best is None or dd<best[0]:best=(dd,a,b)
        dd,a,b=best;members=clusters[a]+clusters[b];clusters[nextid]=members
        merges.append({'distance':dd,'left':[names[i] for i in clusters[a]],'right':[names[i] for i in clusters[b]],'merged':[names[i] for i in members]})
        active=[x for x in active if x not in (a,b)]+[nextid];nextid+=1
    return merges


def main(root):
    rows=load_rows(root);names=[r['dataset'] for r in rows];X=np.asarray([r['vector'] for r in rows],float)
    mu=X.mean(axis=0);sd=X.std(axis=0);sd=np.where(sd>1e-12,sd,1.0);Z=(X-mu)/sd
    D=pairwise(Z);nearest=[]
    for i,n in enumerate(names):
        idx=[j for j in range(len(names)) if j!=i];j=min(idx,key=lambda q:D[i,q]);nearest.append({'dataset':n,'nearest':names[j],'distance':float(D[i,j])})
    out={'kind':'seismic-compression-phenotype-v1','principle':'Dataset labels are never used to form the fingerprint or distance. Every file is represented by error-bounded state-transition rates, actual generic transformed byte rates, carrier behavior, causal correlations, propagation-shift coherence, spectral concentration and low-rank concentration measured at the same 10%-global-std epsilon. Families are empirical neighborhoods in this compression-rate/structure space rather than hardcoded seismic names.','features':list(FEATURES),'datasets':[{k:v for k,v in r.items() if k!='summary'} for r in rows],'raw_feature_matrix':{names[i]:{FEATURES[j]:float(X[i,j]) for j in range(len(FEATURES))} for i in range(len(names))},'zscore_distance_matrix':{names[i]:{names[j]:float(D[i,j]) for j in range(len(names))} for i in range(len(names))},'nearest_neighbors':nearest,'average_link_merges':agglomerate(D,names)}
    json.dump(out,open('compression_phenotype_cluster_v1.json','w'),indent=2)
    print('NEAREST',json.dumps(nearest,indent=2),flush=True)
    print('MERGES',json.dumps(out['average_link_merges'],indent=2),flush=True)
    print('FEATURES',json.dumps(out['raw_feature_matrix'],indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1] if len(sys.argv)>1 else '.')
