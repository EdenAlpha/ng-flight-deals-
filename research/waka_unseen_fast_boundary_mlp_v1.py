#!/usr/bin/env python3
"""Source-trained boundary waveform model on the fast unseen-Waka 16x32 stack.

The direct residual representation and strongest universal interior model remain
unchanged.  Only samples excluded by the interior probability feature builder are
replaced: x=0 traces plus temporal start/end edges.  A small boundary probability
MLP is trained exclusively from the same Kahu/Opunake/Tui source tiles already
used by the universal model.  Its features use only current-trace past history
and fully decoded neighboring traces/rows; no future current-trace value is used.

Held-out Waka remains absent from source fitting and normalization.  The main
interior model uses the independently positive 1024-symbol causal adaptation
cadence; every target chunk is charged before update.  Ideal probability-rate
diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q

FRZEN_GAIN=1.9125539732547088
FAST_GAIN=1.9455818821962128
FRZEN_FAST_BOUNDARY_GAIN=1.9628853073434482
fr.CHUNK=1024
B_EPOCHS=8
B_HIDDEN=(160,112,80)
_BMODEL=None
_BMU=None
_BSD=None
_orig_fit=s.wide_fit


def _reconstructed_state(R):
    """Reconstruct decoder-normalized waveform state S=Y/step from integer residuals."""
    R=np.asarray(R);ny,nx,nt=R.shape;S=np.empty(R.shape,np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        sp=q.b.W*S[y,x-1,t]+(1-q.b.W)*S[y-1,x,t]
                        ps=q.b.W*S[y,x-1,t-1]+(1-q.b.W)*S[y-1,x,t-1] if t else 0.
                    else:
                        sp=S[y,x-1,t];ps=S[y,x-1,t-1] if t else 0.
                    p=q.b.A*sp+(S[y,x,t-1]-q.b.A*ps if t else 0.)
                elif y>0:
                    p=q.b.A*S[y-1,x,t]+(S[y,x,t-1]-q.b.A*S[y-1,x,t-1] if t else 0.)
                elif t:p=S[y,x,t-1]
                else:p=0.
                S[y,x,t]=p+int(R[y,x,t])
    return S


def _win(z,t,r=q.b.RAD):
    n=len(z);a=t-r;b=t+r+1;out=np.zeros(2*r+1,np.float64);aa=max(0,a);bb=min(n,b);out[aa-a:bb-a]=z[aa:bb];return out


def _hist(z,t,n=q.b.HIST):
    out=np.zeros(n,np.float64);a=max(0,t-n);v=np.asarray(z[a:t],np.float64);out[n-len(v):]=v
    if len(v):out-=v[-1]
    return out


def boundary_features_from_R(R):
    R=np.asarray(R);S=_reconstructed_state(R);ny,nx,nt=R.shape;Z=np.zeros(nt,np.float64);Fv=[];Tv=[]
    coords=[]
    for y in range(ny):
        for t in range(nt):coords.append((y,0,t))
        for x in range(1,nx):
            for t in range(14):coords.append((y,x,t))
            for t in range(nt-q.b.RAD-1,nt):coords.append((y,x,t))
    for y,x,t in coords:
        cur=S[y,x];cr=R[y,x]
        l=S[y,x-1] if x else Z;lr=R[y,x-1] if x else Z
        u=S[y-1,x] if y else Z;ur=R[y-1,x] if y else Z
        ul=S[y-1,x-1] if y and x else Z;ulr=R[y-1,x-1] if y and x else Z
        f=[];f.extend(_hist(cur,t).tolist());f.extend(_hist(cr,t).tolist())
        for z in (l,u,ul):
            w=_win(z,t);f.extend((w-z[t]).tolist())
        for z in (lr,ur,ulr):f.extend(_win(z,t).tolist())
        is_x0=1.0 if x==0 else 0.0;is_start=1.0 if x>0 and t<14 else 0.0;is_end=1.0 if x>0 and t>=nt-q.b.RAD-1 else 0.0
        relstart=t/13.0 if is_start else 0.0;relend=(t-(nt-q.b.RAD-1))/q.b.RAD if is_end else 0.0
        f += [float(cur[t-1]) if t else 0.,float(l[t]),float(u[t]),float(ul[t]),float(cur[t-1]-l[t-1]) if t and x else 0.,float(cur[t-1]-u[t-1]) if t and y else 0.,is_x0,is_start,is_end,relstart,relend,1.0 if y==0 else 0.0,min(y,15)/15.0]
        Fv.append(f);Tv.append(int(R[y,x,t]))
    return np.asarray(Fv,np.float32),np.asarray(Tv,np.int32)


def _boundary_R(X,eps):
    # q.b.build creates the exact frozen residual lattice; reuse R and discard interior features.
    _,_,_,R=q.b.build(X,eps);return R


def patched_fit(train_tiles,seed):
    global _BMODEL,_BMU,_BSD
    net,mu,sd,static=_orig_fit(train_tiles,seed)
    AA=[];TT=[]
    for ti,(X,eps) in enumerate(train_tiles):
        R=_boundary_R(X,eps);A,T=boundary_features_from_R(R);AA.append(A);TT.append(T);print('BOUNDARY_MLP_SOURCE',ti,A.shape,flush=True)
    A=np.concatenate(AA);T=np.concatenate(TT);_BMU=A.mean(0);_BSD=A.std(0);_BSD[_BSD<.1]=1.;A=(A-_BMU)/_BSD;Y=q.b.cls(T)
    h1,h2,h3=B_HIDDEN
    class BM(nn.Module):
        def __init__(self,d):
            super().__init__();self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,q.b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(seed+44000);_BMODEL=BM(A.shape[1]);opt=torch.optim.AdamW(_BMODEL.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(B_EPOCHS):
        _BMODEL.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(_BMODEL(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('BOUNDARY_MLP_FIT',seed,ep,tot/len(Xt),flush=True)
    _BMODEL.eval()
    for p in _BMODEL.parameters():p.requires_grad_(False)
    return net,mu,sd,static


def boundary_mlp_bits(_static,R,I):
    if _BMODEL is None:raise RuntimeError('boundary model not initialized')
    A,T=boundary_features_from_R(R);A=(A-_BMU)/_BSD;X=torch.from_numpy(A);Y=torch.from_numpy(q.b.cls(T));bits=0.;_BMODEL.eval()
    with torch.no_grad():
        for i in range(0,len(X),16384):
            lp=F.log_softmax(_BMODEL(X[i:i+16384]),1)/math.log(2);yy=Y[i:i+16384];bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    return bits


def main(a):
    s.wide_fit=patched_fit;q.boundary_bits=boundary_mlp_bits;s.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-fast-adapt-source-boundary-mlp-v1';out['adaptation_chunk']=fr.CHUNK;out['boundary_model']='source-only causal waveform MLP';out['boundary_hidden']=list(B_HIDDEN);out['boundary_epochs']=B_EPOCHS;out['boundary_training_uses_waka']=False;out['boundary_features_use_future_current_trace']=False;out['residual_representation_changed']=False;out['fast_reference_gain']=FAST_GAIN;out['fast_fixed_boundary_reference_gain']=FRZEN_FAST_BOUNDARY_GAIN
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['positions_crossing_2x']=int(sum(z['gain_vs_sz3_ideal']>=2 for z in out['adapt_rows']));out['note']='Boundary probability model is trained exclusively on the same non-Waka source tiles as the universal model. Waka is absent from all fitting/normalization; main target adaptation remains strictly post-charge. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('BOUNDARY_MLP_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
