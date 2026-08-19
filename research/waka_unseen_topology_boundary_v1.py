#!/usr/bin/env python3
"""Source-initialized, decoder-synchronized adaptive boundary coding.

Forty-four topology contexts are initialized only from Kahu/Opunake/Tui source
residuals. During held-out Waka coding, each boundary class is charged under the
current context counts and only then updates that context. Counts persist across
charged Waka positions. Base diagnostic rows snapshot/restore boundary state so
they cannot pre-adapt the actual causal stream. Tail magnitudes keep the same
universal gamma charge. Ideal probability-rate diagnostic only.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_full_replay_loso_v1 as fr
NSTART=14;NEND=q.b.RAD+1;NTYPE=2+2*NSTART+2*NEND
_BOUND_COUNTS=None
_orig_fit=s.wide_fit
_orig_score_base=fr.score_base

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
    global _BOUND_COUNTS
    net,mu,sd,static=_orig_fit(train_tiles,seed);C=np.zeros((NTYPE,q.b.NCLASS),np.float64)
    for i,(X,eps) in enumerate(train_tiles):C+=boundary_counts(residual_only(X,eps));print('ADAPT_BOUNDARY_SOURCE',i,X.shape,flush=True)
    _BOUND_COUNTS=C;return net,mu,sd,static

def adaptive_boundary_bits(_static,R,I):
    global _BOUND_COUNTS
    if _BOUND_COUNTS is None:raise RuntimeError('boundary counts not initialized')
    ny,nx,nt=R.shape;bits=0.
    def code(tid,v):
        nonlocal bits
        for raw in np.asarray(v).reshape(-1):
            c=int(q.b.cls(np.asarray([raw]))[0]);row=_BOUND_COUNTS[tid];bits+=-math.log2(float(row[c]/row.sum()));tail=max(abs(int(raw))-q.b.LIM,0);bits+=float(q.b.gamma_bits(np.asarray([tail]))[0]);row[c]+=1.0
    code(0,R[0,0,:])
    if ny>1:code(1,R[1:,0,:])
    for t in range(NSTART):
        code(2+2*t,R[0,1:,t])
        if ny>1:code(2+2*t+1,R[1:,1:,t])
    stop=nt-q.b.RAD-1;base=2+2*NSTART
    for k,t in enumerate(range(stop,nt)):
        code(base+2*k,R[0,1:,t])
        if ny>1:code(base+2*k+1,R[1:,1:,t])
    return bits

def score_base_without_state_change(net,mu,sd,static,X,eps,meta):
    global _BOUND_COUNTS
    snap=None if _BOUND_COUNTS is None else _BOUND_COUNTS.copy();out=_orig_score_base(net,mu,sd,static,X,eps,meta);_BOUND_COUNTS=snap;return out

def main(a):
    s.wide_fit=patched_fit;q.boundary_bits=adaptive_boundary_bits;fr.score_base=score_base_without_state_change;s.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-stacked-adaptive-topology-boundary-v1';out['boundary_contexts']=NTYPE;out['boundary_initialization_uses_waka']=False;out['boundary_updates_after_each_charged_symbol']=True;out['boundary_state_persists_across_target_positions']=True;out['base_rows_do_not_mutate_boundary_state']=True;out['frozen_stack_reference_gain']=1.9125539732547088
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['gain_improvement_over_frozen_stack']=float(out['full_replay_weighted_gain_vs_sz3']/1.9125539732547088);Path(a.out).write_text(json.dumps(out,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
