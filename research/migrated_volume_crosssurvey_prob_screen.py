#!/usr/bin/env python3
"""Leave-Waka-out learned residual probability diagnostic.

Train a fixed probability model only on Kahu/Tui/Opunake native 3-D tiles and
score Waka tiles. Waka does not participate in fitting, normalization, tail
statistics, geometry parameters, or model selection. This is an information-
rate diagnostic, not yet a promoted production codec: it reports ideal coded
bits under decoder-fixed probabilities plus explicit universal tail costs and
static boundary costs, then compares against matched whole-tile SZ3.

This file is intentionally deterministic so the leave-one-survey-out gate can
be reproduced exactly from the frozen benchmark manifest.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
from general_seismic_numeric_io import matched_sz3

A=.96875; W=.8125; LIM=8; NCLASS=19; RAD=6; HIST=12; WINDOW=15000
TRAIN_IDS=('marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
TEST_ID='marine_waka_3d'; TRAIN_FRAC=.50; TEST_FRACS=(.05,.50,.95)

def extract(ds,manifest,epsj,frac):
 r=large.r; eps=float(epsj['datasets'][ds]['epsilon']); d=next(q for q in manifest['datasets'] if q['id']==ds);oo=[r.obj(u) for u in d['objects']]
 rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr);total=int(s.total_traces);center=int(round(frac*max(0,total-1)));st=max(0,min(total-WINDOW,center-WINDOW//2));n=min(WINDOW,total-st)
  H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,b+st) for a,b in geom['segments']]
  _,block,minlen,ny,nx=large.choose_large_group(seg);X,ids=large.read_tile(rr,s,block,minlen,nx)
  y0=max(0,(X.shape[0]-4)//2);x0=max(0,(X.shape[1]-32)//2);X=np.ascontiguousarray(X[y0:y0+4,x0:x0+32])
  return X,eps,{'fraction':frac,'shape':list(X.shape),'trace_first':int(ids[y0*nx+x0]),'geometry_mode':geom['mode']}
 finally:rr.close()

def build(X,eps):
 step=2*float(eps)*.9999;X=np.asarray(X,np.float64);ny,nx,nt=X.shape;R=np.empty(X.shape,np.int32);Y=np.empty(X.shape,np.float64)
 for y in range(ny):
  for x in range(nx):
   for t in range(nt):
    if x>0:
     if y>0:
      sp=W*Y[y,x-1,t]+(1-W)*Y[y-1,x,t]; ps=W*Y[y,x-1,t-1]+(1-W)*Y[y-1,x,t-1] if t else 0.
     else:sp=Y[y,x-1,t];ps=Y[y,x-1,t-1] if t else 0.
     p=A*sp+(Y[y,x,t-1]-A*ps if t else 0.)
    elif y>0:p=A*Y[y-1,x,t]+(Y[y,x,t-1]-A*Y[y-1,x,t-1] if t else 0.)
    elif t:p=Y[y,x,t-1]
    else:p=0.
    q=int(np.rint((X[y,x,t]-p)/step));R[y,x,t]=q;Y[y,x,t]=p+q*step
 S=Y/step;Z=np.zeros(nt);F=[];T=[];IDX=[]
 for y in range(ny):
  for x in range(1,nx):
   l=S[y,x-1];l2=S[y,x-2] if x>1 else l;u=S[y-1,x] if y else Z;ul=S[y-1,x-1] if y else Z
   lr=R[y,x-1];l2r=R[y,x-2] if x>1 else lr;ur=R[y-1,x] if y else Z;ulr=R[y-1,x-1] if y else Z;cr=R[y,x];cur=S[y,x]
   for t in range(14,nt-RAD-1):
    f=[];f.extend((cur[t-10:t]-cur[t-1]).tolist())
    for z in (l,l2,u,ul):f.extend((z[t-RAD:t+RAD+1]-z[t]).tolist())
    for z in (lr,l2r,ur,ulr):f.extend(np.asarray(z[t-RAD:t+RAD+1]).tolist())
    f.extend(cr[t-HIST:t].tolist());f += [l[t],l2[t],u[t],ul[t],l[t]-l2[t],l[t]-u[t],cur[t-1]-l[t-1],cur[t-1]-u[t-1]]
    F.append(f);T.append(int(cr[t]));IDX.append((y,x,t))
 return np.asarray(F,np.float32),np.asarray(T,np.int32),np.asarray(IDX,np.int16),R

def cls(t):return np.where(t<-LIM,17,np.where(t>LIM,18,t+LIM)).astype(np.int64)
def gamma_bits(v):
 v=np.asarray(v,np.int64);out=np.zeros(v.shape,np.float64);m=v>0;out[m]=2*np.floor(np.log2(v[m]))+1;return out

def main(a):
 import torch,torch.nn as nn,torch.nn.functional as F
 torch.manual_seed(20260818);np.random.seed(20260818)
 m=json.load(open(a.manifest));e=json.load(open(a.eps));train=[];trainR=[];meta=[]
 for ds in TRAIN_IDS:
  X,ep,md=extract(ds,m,e,TRAIN_FRAC);A0,T0,I0,R0=build(X,ep);train.append((A0,T0));trainR.append(R0.reshape(-1));md['dataset']=ds;meta.append(md);print('TRAIN_TILE',ds,md,flush=True)
 At=np.concatenate([q[0] for q in train]);Tt=np.concatenate([q[1] for q in train]);fulltrain=np.concatenate(trainR)
 mu=At.mean(0);sd=At.std(0);sd[sd<.1]=1;At=(At-mu)/sd;Yt=cls(Tt)
 sh=np.bincount(cls(fulltrain),minlength=NCLASS).astype(np.float64)+1.;sh/=sh.sum();static_cost=-np.log2(sh)
 class M(nn.Module):
  def __init__(self,d):super().__init__();self.net=nn.Sequential(nn.Linear(d,192),nn.SiLU(),nn.LayerNorm(192),nn.Linear(192,144),nn.SiLU(),nn.Linear(144,96),nn.SiLU(),nn.Linear(96,NCLASS))
  def forward(self,x):return self.net(x)
 net=M(At.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(At);Y=torch.from_numpy(Yt);idx=torch.arange(len(Xt));bs=8192
 for ep in range(8):
  net.train();perm=idx[torch.randperm(len(idx))];tot=0.
  for i in range(0,len(perm),bs):
   j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Y[j]);opt.zero_grad();loss.backward();opt.step();tot+=loss.detach().item()*len(j)
  if ep in (0,3,7):print('EPOCH',ep,tot/len(Xt),flush=True)
 rows=[]
 for frac in TEST_FRACS:
  X,ep,md=extract(TEST_ID,m,e,frac);Ae,Te,Ie,R=build(X,ep);Ae=(Ae-mu)/sd;Ye=cls(Te);bits=0.
  net.eval();XE=torch.from_numpy(Ae);YY=torch.from_numpy(Ye)
  with torch.no_grad():
   for i in range(0,len(XE),16384):
    lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);yy=YY[i:i+16384];bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
  tail=np.maximum(np.abs(Te)-LIM,0);bits+=float(gamma_bits(tail).sum())
  mask=np.zeros(R.shape,bool)
  for y,x,t in Ie:mask[int(y),int(x),int(t)]=True
  rb=R[~mask];bits+=float(static_cost[cls(rb)].sum()+gamma_bits(np.maximum(np.abs(rb)-LIM,0)).sum())
  sb,sme=matched_sz3(X,ep);ours=int(math.ceil(bits/8))+128;gain=float(sb/ours);bps=float(8*ours/X.size);target=float(4*sb/X.size)
  row={'dataset':TEST_ID,**md,'epsilon':ep,'samples':int(X.size),'ideal_fixed_model_bytes_plus_128_header':ours,'ideal_bps':bps,'sz3_bytes':int(sb),'sz3_bps':float(8*sb/X.size),'gain_vs_sz3_ideal':gain,'two_x_target_bps':target,'crosses_2x_ideal':bool(gain>=2),'sz3_maxerr':float(sme),'waka_used_in_training':False,'tail_code':'Elias-gamma','boundary_probability_source':'training surveys only'}
  rows.append(row);print('WAKA_HOLDOUT',json.dumps(row),flush=True)
 out={'kind':'leave-waka-out-fixed-probability-v1','training_datasets':list(TRAIN_IDS),'test_dataset':TEST_ID,'training_fraction':TRAIN_FRAC,'test_fractions':list(TEST_FRACS),'model':'fixed MLP probability model; weights fit without Waka','important':'Diagnostic ideal arithmetic rate; not yet a materialized arithmetic stream. No Waka values/statistics used in fitting or normalization.','train_tiles':meta,'rows':rows,'weighted_ideal_gain_vs_sz3':sum(q['sz3_bytes'] for q in rows)/sum(q['ideal_fixed_model_bytes_plus_128_header'] for q in rows)}
 Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--out',required=True);main(ap.parse_args())
