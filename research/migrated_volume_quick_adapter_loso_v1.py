#!/usr/bin/env python3
"""Four-survey leave-one-out diagnostic helper."""
from __future__ import annotations
import argparse,gc,json,math
from pathlib import Path
import numpy as np
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3
SURVEYS=('marine_waka_3d','marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
TRAIN_FRAC=.50;TEST_FRACS=(.15,.50,.85);MAX_TRAIN=220000;EPOCHS=3;XKEEP=24;HEADER_BYTES=128;CHUNK=4096;RANK=4;ADAPTER_LR=.08;FIRST_CHUNK_STEPS=4;LATER_CHUNK_STEPS=1;REPLAY_PER_TILE=6000;REPLAY_CAP=12000;REPLAY_STEPS_BETWEEN_TILES=2

def crop(X):
 X=np.asarray(X)
 if X.shape[1]<=XKEEP:return np.ascontiguousarray(X)
 x0=(X.shape[1]-XKEEP)//2;return np.ascontiguousarray(X[:,x0:x0+XKEEP,:])
def deterministic_subsample(A,T,cap):
 if len(T)<=cap:return A,T
 idx=np.linspace(0,len(T)-1,cap,dtype=np.int64);return A[idx],T[idx]
def fit_base(train_tiles,seed):
 import torch,torch.nn as nn,torch.nn.functional as F
 AA=[];TT=[];RR=[]
 for X,eps in train_tiles:
  A,T,_,R=b.build(crop(X),eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
 A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR);A,T=deterministic_subsample(A,T,MAX_TRAIN);mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T);sh=np.bincount(b.cls(fullR),minlength=b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh)
 class Base(nn.Module):
  def __init__(self,d):super().__init__();self.trunk=nn.Sequential(nn.Linear(d,160),nn.SiLU(),nn.LayerNorm(160),nn.Linear(160,112),nn.SiLU(),nn.Linear(112,64),nn.SiLU());self.head=nn.Linear(64,b.NCLASS)
  def latent(self,x):return self.trunk(x)
  def forward(self,x):return self.head(self.latent(x))
 torch.manual_seed(seed);np.random.seed(seed);net=Base(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);X=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(X));bs=8192
 for ep in range(EPOCHS):
  net.train();perm=idx[torch.randperm(len(idx))]
  for i in range(0,len(perm),bs):
   j=perm[i:i+bs];loss=F.cross_entropy(net(X[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step()
 net.eval()
 for p in net.parameters():p.requires_grad_(False)
 return net,mu,sd,static

def cls_bits(net,X,Y):
 import torch,torch.nn.functional as F
 bits=0.;XE=torch.from_numpy(X);YY=torch.from_numpy(Y);net.eval()
 with torch.no_grad():
  for i in range(0,len(XE),16384):
   yy=YY[i:i+16384];lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
 return bits

def boundary_bits(static,R,I):
 mask=np.zeros(R.shape,bool)
 for y,x,t in I:mask[int(y),int(x),int(t)]=True
 rb=R[~mask];return float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum())
