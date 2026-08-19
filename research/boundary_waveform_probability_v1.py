#!/usr/bin/env python3
"""Generic source-trained causal probability model for residual boundary samples."""
from __future__ import annotations
import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_quick_adapter_loso_v1 as q

EPOCHS=8
HIDDEN=(160,112,80)
_MODEL=None
_MU=None
_SD=None

def reconstructed_state(R):
    R=np.asarray(R);ny,nx,nt=R.shape;S=np.empty(R.shape,np.float64)
    for y in range(ny):
      for x in range(nx):
       for t in range(nt):
        if x>0:
         if y>0:
          sp=q.b.W*S[y,x-1,t]+(1-q.b.W)*S[y-1,x,t];ps=q.b.W*S[y,x-1,t-1]+(1-q.b.W)*S[y-1,x,t-1] if t else 0.
         else:sp=S[y,x-1,t];ps=S[y,x-1,t-1] if t else 0.
         p=q.b.A*sp+(S[y,x,t-1]-q.b.A*ps if t else 0.)
        elif y>0:p=q.b.A*S[y-1,x,t]+(S[y,x,t-1]-q.b.A*S[y-1,x,t-1] if t else 0.)
        elif t:p=S[y,x,t-1]
        else:p=0.
        S[y,x,t]=p+int(R[y,x,t])
    return S

def win(z,t,r=q.b.RAD):
    n=len(z);a=t-r;b=t+r+1;o=np.zeros(2*r+1,np.float64);aa=max(0,a);bb=min(n,b);o[aa-a:bb-a]=z[aa:bb];return o

def hist(z,t,n=q.b.HIST):
    o=np.zeros(n,np.float64);a=max(0,t-n);v=np.asarray(z[a:t],np.float64);o[n-len(v):]=v
    if len(v):o-=v[-1]
    return o

def features(R):
    R=np.asarray(R);S=reconstructed_state(R);ny,nx,nt=R.shape;Z=np.zeros(nt,np.float64);A=[];T=[]
    coords=[]
    for y in range(ny):
      for t in range(nt):coords.append((y,0,t))
      for x in range(1,nx):
       for t in range(14):coords.append((y,x,t))
       for t in range(nt-q.b.RAD-1,nt):coords.append((y,x,t))
    for y,x,t in coords:
      cur=S[y,x];cr=R[y,x];l=S[y,x-1] if x else Z;lr=R[y,x-1] if x else Z;u=S[y-1,x] if y else Z;ur=R[y-1,x] if y else Z;ul=S[y-1,x-1] if y and x else Z;ulr=R[y-1,x-1] if y and x else Z
      f=[];f.extend(hist(cur,t).tolist());f.extend(hist(cr,t).tolist())
      for z in (l,u,ul):
       w=win(z,t);f.extend((w-z[t]).tolist())
      for z in (lr,ur,ulr):f.extend(win(z,t).tolist())
      x0=1.0 if x==0 else 0.0;st=1.0 if x>0 and t<14 else 0.0;en=1.0 if x>0 and t>=nt-q.b.RAD-1 else 0.0
      f += [float(cur[t-1]) if t else 0.,float(l[t]),float(u[t]),float(ul[t]),float(cur[t-1]-l[t-1]) if t and x else 0.,float(cur[t-1]-u[t-1]) if t and y else 0.,x0,st,en,t/13.0 if st else 0.0,(t-(nt-q.b.RAD-1))/q.b.RAD if en else 0.0,1.0 if y==0 else 0.0,min(y,15)/15.0,t/float(max(1,nt-1)),x/float(max(1,nx-1))]
      A.append(f);T.append(int(R[y,x,t]))
    return np.asarray(A,np.float32),np.asarray(T,np.int32)

def install(base_module):
    original=base_module.wide_fit
    def fit(train_tiles,seed):
      global _MODEL,_MU,_SD
      net,mu,sd,static=original(train_tiles,seed);AA=[];TT=[]
      for i,(X,eps) in enumerate(train_tiles):
       _,_,_,R=q.b.build(q.crop(X),eps);a,t=features(R);AA.append(a);TT.append(t);print('BOUND_WAVE_SOURCE',seed,i,a.shape,flush=True)
      a=np.concatenate(AA);t=np.concatenate(TT);_MU=a.mean(0);_SD=a.std(0);_SD[_SD<.1]=1.;a=(a-_MU)/_SD;y=q.b.cls(t);h1,h2,h3=HIDDEN
      class M(nn.Module):
       def __init__(self,d):super().__init__();self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,q.b.NCLASS))
       def forward(self,x):return self.net(x)
      torch.manual_seed(seed+44000);_MODEL=M(a.shape[1]);opt=torch.optim.AdamW(_MODEL.parameters(),lr=2e-3,weight_decay=3e-4);X=torch.from_numpy(a);Y=torch.from_numpy(y);idx=torch.arange(len(X));bs=8192
      for ep in range(EPOCHS):
       _MODEL.train();perm=idx[torch.randperm(len(idx))];tot=0.
       for j0 in range(0,len(perm),bs):
        j=perm[j0:j0+bs];loss=F.cross_entropy(_MODEL(X[j]),Y[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
       print('BOUND_WAVE_FIT',seed,ep,tot/len(X),flush=True)
      _MODEL.eval();
      for p in _MODEL.parameters():p.requires_grad_(False)
      return net,mu,sd,static
    def bits(_static,R,I):
      if _MODEL is None:raise RuntimeError('boundary waveform model missing')
      a,t=features(R);a=(a-_MU)/_SD;X=torch.from_numpy(a);Y=torch.from_numpy(q.b.cls(t));total=0.;_MODEL.eval()
      with torch.no_grad():
       for j0 in range(0,len(X),16384):
        lp=F.log_softmax(_MODEL(X[j0:j0+16384]),1)/math.log(2);yy=Y[j0:j0+16384];total+=float((-lp[torch.arange(len(yy)),yy]).sum())
      total+=float(q.b.gamma_bits(np.maximum(np.abs(t)-q.b.LIM,0)).sum());return total
    base_module.wide_fit=fit;q.boundary_bits=bits
