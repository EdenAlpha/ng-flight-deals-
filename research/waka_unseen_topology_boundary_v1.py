#!/usr/bin/env python3
"""Topology-specific boundary coding patch for the frozen unseen-Waka 16x32 stack.

Forty-four topology contexts are initialized exclusively from source-survey
residuals. Waka is not used to initialize them. Predictor, quantizer, probability
model, target geometry and replay rules are unchanged. Ideal probability rate
only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_quick_adapter_loso_v1 as q
NSTART=14;NEND=q.b.RAD+1;NTYPE=2+2*NSTART+2*NEND
_BOUND_COST=None
_orig_fit=s.wide_fit

def residual_only(X,eps):
    step=2*float(eps)*.9999;X=np.asarray(X,np.float64);ny,nx,nt=X.shape;R=np.empty(X.shape,np.int32);Y=np.empty(X.shape,np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        sp=q.b.W*Y[y,x-1,t]+(1-q.b.W)*Y[y-1,x,t];ps=q.b.W*Y[y,x-1,t-1]+(1-q.b.W)*Y[y-1,x,t-1] if t else 0.
                    else:sp=Y[y,x-1,t];ps=Y[y,x-1,t-1] if t else 0.
                    p=q.b.A*sp+(Y[y,x,t-1]-q.b.A*ps if t else 0.)
                elif y>0:p=q.b.A*Y[y-1,x,t]+(Y[y,x,t-1]-q.b.A*Y[y-1,x,t-1] if t else 0.)
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
    net,mu,sd,static=_orig_fit(train_tiles,seed);C=np.zeros((NTYPE,q.b.NCLASS),np.float64)
    for i,(X,eps) in enumerate(train_tiles):C+=boundary_counts(residual_only(X,eps));print('BOUNDARY_SOURCE',i,X.shape,flush=True)
    _BOUND_COST=-np.log2(C/C.sum(1,keepdims=True));return net,mu,sd,static

def topology_boundary_bits(_static,R,I):
    if _BOUND_COST is None:raise RuntimeError('boundary costs not initialized')
    ny,nx,nt=R.shape;bits=0.
    def cost(tid,v):
        z=np.asarray(v).reshape(-1);return float(_BOUND_COST[tid,q.b.cls(z)].sum()+q.b.gamma_bits(np.maximum(np.abs(z)-q.b.LIM,0)).sum())
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

def install():
    s.wide_fit=patched_fit;q.boundary_bits=topology_boundary_bits
