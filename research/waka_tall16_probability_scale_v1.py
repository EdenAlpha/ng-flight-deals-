#!/usr/bin/env python3
"""Dynamic nonlocal waveform-attention ablation for Waka 16x128.

Preserves the exact frozen 16x32-vs-16x128 extraction, residual predictor,
training/test regions, hidden widths and training budget. The only change is a
causal probability feature: use the current trace's already-decoded recent
history to retrieve similar nonlocal previously decoded traces, then expose the
best match and a soft top-4 continuation/residual summary. Immediate x-1/x-2
neighbors are excluded because the frozen base model already sees them.
No current/future unknown sample is used. Ideal probability rate only.
"""
from __future__ import annotations
import argparse,json
import numpy as np
import waka_tall16_probability_scale_base_v1 as base

HIST=10
TOPK=4
MIN_DISTANCE=3
TEMPERATURE=6.0
_ORIG_FEATURE_BATCH=base.feature_batch

def attention_feature_batch(S,R,flat):
    F,T=_ORIG_FEATURE_BATCH(S,R,flat)
    ny,nx,nt=S.shape;ntm=nt-base.b.RAD-15
    flat=np.asarray(flat,np.int64);q0=flat//ntm;t=14+(flat%ntm);x=1+(q0%(nx-1));y=q0//(nx-1)
    # availability, best cosine similarity, normalized spatial distance,
    # best-match waveform/residual windows, soft top-k waveform/residual windows.
    extra=np.zeros((len(flat),3+4*(2*base.b.RAD+1)),dtype=np.float32)
    groups=y.astype(np.int64)*nx+x.astype(np.int64)
    for code in np.unique(groups):
        sel=np.flatnonzero(groups==code)
        yg=int(y[sel[0]]);xg=int(x[sel[0]])
        # Exclude x-1 and x-2: they are already explicit base features.
        cand=np.arange(0,max(0,xg-MIN_DISTANCE+1),dtype=np.int64)
        if cand.size==0:continue
        tt=t[sel]
        # Query/key = recent causal waveform shape, centered on last decoded value.
        offs=np.arange(-HIST,0,dtype=np.int64)
        qhist=np.stack([S[yg,xg,tt+o] for o in offs],axis=1)
        qhist-=qhist[:,-1,None]
        khist=np.stack([S[yg,cand[None,:],tt[:,None]+o] for o in offs],axis=2)
        khist-=khist[:,:,-1,None]
        qn=np.sqrt(np.sum(qhist*qhist,axis=1,keepdims=True)+1e-4)
        kn=np.sqrt(np.sum(khist*khist,axis=2)+1e-4)
        cos=np.einsum('nh,nkh->nk',qhist,khist)/(qn*kn)
        k=min(TOPK,cand.size)
        top=np.argpartition(-cos,k-1,axis=1)[:,:k]
        topcos=np.take_along_axis(cos,top,axis=1)
        order=np.argsort(-topcos,axis=1);top=np.take_along_axis(top,order,axis=1);topcos=np.take_along_axis(topcos,order,axis=1)
        topj=cand[top];bestj=topj[:,0]
        w=np.exp(TEMPERATURE*(topcos-topcos.max(axis=1,keepdims=True)));w/=w.sum(axis=1,keepdims=True)
        extra[sel,0]=1.0
        extra[sel,1]=topcos[:,0].astype(np.float32)
        extra[sel,2]=((xg-bestj)/max(1,xg)).astype(np.float32)
        c=3
        center_best=S[yg,bestj,tt]
        center_top=S[yg,topj,tt[:,None]]
        for o in range(-base.b.RAD,base.b.RAD+1):
            extra[sel,c]=(S[yg,bestj,tt+o]-center_best).astype(np.float32);c+=1
        for o in range(-base.b.RAD,base.b.RAD+1):
            extra[sel,c]=R[yg,bestj,tt+o].astype(np.float32);c+=1
        for o in range(-base.b.RAD,base.b.RAD+1):
            vv=S[yg,topj,tt[:,None]+o]-center_top;extra[sel,c]=np.sum(w*vv,axis=1).astype(np.float32);c+=1
        for o in range(-base.b.RAD,base.b.RAD+1):
            rr=R[yg,topj,tt[:,None]+o];extra[sel,c]=np.sum(w*rr,axis=1).astype(np.float32);c+=1
    return np.concatenate([F,extra],axis=1),T

base.feature_batch=attention_feature_batch

def main(a):
    base.main(a)
    out=json.load(open(a.out));out['kind']='waka-paired-learned-probability-scale-16x32-vs-16x128-waveform-attention-v1';out['nonlocal_feature']='causal waveform-history retrieval over previously decoded traces';out['topk']=TOPK;out['minimum_nonlocal_distance']=MIN_DISTANCE;out['attention_temperature']=TEMPERATURE;out['future_unknown_samples_used']=False;out['only_change_from_frozen_16x128_gate']='dynamic nonlocal probability context';out['note']='Ideal probability-rate diagnostic; same residual representation and held-out regions as frozen 16x128 scale gate.'
    with open(a.out,'w') as f:json.dump(out,f,indent=2)
    print('ATTENTION_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
