#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import numpy as np

from compression_phenotype_cluster_v1 import FEATURES

CORR = {'adjacent_space_corr','temporal_lag1_corr','best_temporal_corr','best_neighbor_shift_corr'}
FAMILY = {
    'f1': 'carrier_sparse_wavefield',
    'tie': 'carrier_sparse_wavefield',
    'soda': 'lattice_sparse_state',
    'forge': 'lattice_sparse_state',
    'brady': 'spectral_coherent_array',
    'imperial': 'dense_innovation_ar',
}
ENGINE = {
    'carrier_sparse_wavefield': 'marine_anchor_carrier_pr6',
    'lattice_sparse_state': 'soda_or_forge_lattice',
    'spectral_coherent_array': 'spectral_topn',
    'dense_innovation_ar': 'ar32_zsm',
}


def vec(d):
    m=d['summary']['metrics'];v=[]
    for k in FEATURES:
        x=float(m[k]['median'])
        if k in CORR:x=abs(x)
        v.append(x)
    return np.asarray(v,float)


def load(pattern):
    out=[]
    for p in sorted(glob.glob(pattern,recursive=True)):
        try:d=json.load(open(p))
        except Exception:continue
        if isinstance(d,dict) and 'summary' in d and 'dataset' in d:
            out.append((str(d['dataset']),p,d,vec(d)))
    return out


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--prototypes',required=True)
    ap.add_argument('--targets',required=True)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    prot=load(os.path.join(a.prototypes,'**','compression_phenotype_*.json'))
    targ=load(os.path.join(a.targets,'**','blind_phenotype_*.json'))
    # Avoid accidentally treating the v1 cluster aggregate as a prototype.
    prot=[r for r in prot if r[0] in FAMILY]
    if len(prot)!=6:raise RuntimeError(('expected six frozen prototypes',[(x[0],x[1]) for x in prot]))
    if not targ:raise RuntimeError('no blind targets')
    X=np.stack([x[3] for x in prot]);mu=X.mean(0);sd=X.std(0);sd=np.where(sd>1e-12,sd,1.0)
    Z=(X-mu)/sd
    rows=[]
    for name,p,d,v in targ:
        z=(v-mu)/sd
        dist=np.sqrt(np.mean((Z-z[None,:])**2,axis=1))
        order=np.argsort(dist)
        first,second=int(order[0]),int(order[1])
        proto=prot[first][0];fam=FAMILY[proto]
        rows.append({
            'target':name,
            'predicted_prototype':proto,
            'predicted_family':fam,
            'predicted_engine_family':ENGINE[fam],
            'distance':float(dist[first]),
            'second_prototype':prot[second][0],
            'second_distance':float(dist[second]),
            'confidence_ratio_second_over_first':float(dist[second]/max(dist[first],1e-12)),
            'all_distances':{prot[i][0]:float(dist[i]) for i in range(len(prot))},
            'target_vector':{FEATURES[i]:float(v[i]) for i in range(len(FEATURES))},
        })
    out={
      'kind':'seismic-compression-phenotype-blind-classification-v2',
      'rules_frozen_before_target_engine_scores':True,
      'prototype_scaling_only':True,
      'features':list(FEATURES),
      'prototype_to_family':FAMILY,
      'family_to_existing_engine':ENGINE,
      'predictions':rows,
      'principle':'Target seismic names/categories/formats do not enter the distance. Scaling is fit only on the six frozen pre-Waka prototypes. The target is assigned by its numeric compression phenotype before any all-engine target score is read.'
    }
    json.dump(out,open(a.out,'w'),indent=2)
    print('BLIND_PREDICTIONS',json.dumps(rows,indent=2),flush=True)

if __name__=='__main__':main()
