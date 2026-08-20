#!/usr/bin/env python3
"""Stack two independently positive legal mechanisms on unseen Waka 16x32.

This experiment keeps the frozen stacked Waka setup intact while combining:
1) causal adaptation every 1024 modeled samples (instead of 4096), and
2) source-only topology-specific boundary probability tables.

Every target chunk is charged before adaptation. Waka is absent from source
fitting/normalization and from boundary-table initialization. Predictor,
quantizer, main probability architecture, target geometry, learning rate and
tail coding are unchanged. Ideal probability-rate diagnostic only; this is not
yet a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_full_replay_loso_v1 as fr

FROZEN_GAIN=1.9125539732547088
FAST_GAIN=1.9455818822
BOUNDARY_GAIN=1.9292694517
fr.CHUNK=1024
NSTART=14
NEND=q.b.RAD+1
NTYPE=2+2*NSTART+2*NEND
_BOUND_COST=None
_orig_fit=s.wide_fit

def residual_only(X,eps):
    step=2*float(eps)*.9999;X=np.asarray(X,np.float64);ny,nx,nt=X.shape
    R=np.empty(X.shape,np.int32);Y=np.empty(X.shape,np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        sp=q.b.W*Y[y,x-1,t]+(1-q.b.W)*Y[y-1,x,t]
                        ps=q.b.W*Y[y,x-1,t-1]+(1-q.b.W)*Y[y-1,x,t-1] if t else 0.
                    else:
                        sp=Y[y,x-1,t];ps=Y[y,x-1,t-1] if t else 0.
                    p=q.b.A*sp+(Y[y,x,t-1]-q.b.A*ps if t else 0.)
                elif y>0:
                    p=q.b.A*Y[y-1,x,t]+(Y[y,x,t-1]-q.b.A*Y[y-1,x,t-1] if t else 0.)
                elif t:p=Y[y,x,t-1]
                else:p=0.
                z=int(np.rint((X[y,x,t]-p)/step));R[y,x,t]=z;Y[y,x,t]=p+z*step
    return R

def boundary_counts(R):
    ny,nx,nt=R.shape;C=np.ones((NTYPE,q.b.NCLASS),np.float64)
    def add(tid,v):C[tid]+=np.bincount(q.b.cls(np.asarray(v).reshape(-1)),minlength=q.b.NCLASS)
    add(0,R[0,0,:])
    if ny>1:add(1,R[1:,0,:])
    for t in range(NSTART):
        add(2+2*t,R[0,1:,t])
        if ny>1:add(2+2*t+1,R[1:,1:,t])
    stop=nt-q.b.RAD-1;base=2+2*NSTART
    for k,t in enumerate(range(stop,nt)):
        add(base+2*k,R[0,1:,t])
        if ny>1:add(base+2*k+1,R[1:,1:,t])
    return C

def patched_fit(train_tiles,seed):
    global _BOUND_COST
    net,mu,sd,static=_orig_fit(train_tiles,seed)
    C=np.zeros((NTYPE,q.b.NCLASS),np.float64)
    for i,(X,eps) in enumerate(train_tiles):
        C+=boundary_counts(residual_only(X,eps));print('STACK_BOUNDARY_SOURCE',i,X.shape,flush=True)
    _BOUND_COST=-np.log2(C/C.sum(1,keepdims=True))
    return net,mu,sd,static

def topology_boundary_bits(_static,R,I):
    if _BOUND_COST is None:raise RuntimeError('boundary costs not initialized')
    ny,nx,nt=R.shape;bits=0.
    def cost(tid,v):
        z=np.asarray(v).reshape(-1)
        return float(_BOUND_COST[tid,q.b.cls(z)].sum()+q.b.gamma_bits(np.maximum(np.abs(z)-q.b.LIM,0)).sum())
    bits+=cost(0,R[0,0,:])
    if ny>1:bits+=cost(1,R[1:,0,:])
    for t in range(NSTART):
        bits+=cost(2+2*t,R[0,1:,t])
        if ny>1:bits+=cost(2+2*t+1,R[1:,1:,t])
    stop=nt-q.b.RAD-1;base=2+2*NSTART
    for k,t in enumerate(range(stop,nt)):
        bits+=cost(base+2*k,R[0,1:,t])
        if ny>1:bits+=cost(base+2*k+1,R[1:,1:,t])
    return bits

def main(a):
    s.wide_fit=patched_fit
    q.boundary_bits=topology_boundary_bits
    s.main(a)
    out=json.load(open(a.out))
    out['kind']='unseen-waka-16x32-fastadapt-topology-boundary-stack-v1'
    out['adaptation_chunk']=fr.CHUNK
    out['boundary_contexts']=NTYPE
    out['waka_used_in_base_training']=False
    out['boundary_initialization_uses_waka']=False
    out['predictor_changed']=False
    out['quantizer_changed']=False
    out['main_probability_architecture_changed']=False
    out['frozen_stack_reference_gain']=FROZEN_GAIN
    out['fast_adapt_reference_gain']=FAST_GAIN
    out['boundary_reference_gain']=BOUNDARY_GAIN
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows'])
    ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows'])
    samples=sum(z['samples'] for z in out['adapt_rows'])
    out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples)
    out['crosses_2x_weighted']=bool(out['full_replay_weighted_gain_vs_sz3']>=2.0)
    out['note']='Exact stack of two independently positive mechanisms: 1024-symbol post-charge adaptation plus 44 source-only topology boundary contexts. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2))
    print('FAST_BOUNDARY_STACK_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
