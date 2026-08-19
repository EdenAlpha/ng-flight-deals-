#!/usr/bin/env python3
"""Tall Waka learned-probability diagnostic with deeper causal vertical context.

The native 16x32 regions and residual representation are unchanged from the
paired tall-scale gate.  This extension compares the existing probability
features against a model that additionally sees already-decoded rows y-2 and
y-4.  No future row, sample-value location selection, or test-region tuning is
allowed.  Matched SZ3 receives the identical held-out 16x32 samples/epsilon.

Ideal probability-rate diagnostic only; model weights and arithmetic stream are
not yet charged/materialized.
"""
from __future__ import annotations
import argparse,json,math,gc
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

DATASET='marine_waka_3d';TRAIN_FRACS=(.01,.08);TEST_FRAC=.05
NY=16;NX=32;WINDOWS=(60000,120000,240000);MAX_PER_TILE=180000
EPOCHS=7;HEADER_BYTES=128;HIDDEN=(192,144,96);SEED=20260819
DEEP_ROWS=(2,4)

def extract16x32(manifest,epsj,frac):
 r=large.r;ds=next(d for d in manifest['datasets'] if d['id']==DATASET);eps=float(epsj['datasets'][DATASET]['epsilon']);oo=[r.obj(u) for u in ds['objects']];rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr)
  if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('fixed stride required',s.ns_policy))
  total=int(s.total_traces);center=int(round(float(frac)*max(0,total-1)));chosen=None
  for window in WINDOWS:
   st=max(0,min(max(0,total-window),center-window//2));n=min(window,total-st);H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,z+st) for a,z in geom['segments']];rows=[q for q in seg if q[1]-q[0]>=NX]
   if len(rows)<NY:
    print('TALL_WINDOW_REJECT',frac,window,geom['mode'],len(rows),flush=True);continue
   cand=[]
   for i in range(len(rows)-NY+1):
    block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);cand.append((abs(mid-center),i,block))
   _,gi,block=min(cand,key=lambda q:(q[0],q[1]));minlen=min(z-a for a,z in block);chosen=(window,geom,gi,block,minlen,len(rows));break
  if chosen is None:raise RuntimeError(('too few 16x32 rows after deterministic header expansion',frac,WINDOWS))
  window,geom,gi,block,minlen,row_count=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX);md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(row_count),'location_selection_uses_sample_values':False};print('TALL_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
 finally:rr.close()

def reconstructed_state(R,eps):
 step=2*float(eps)*.9999;R=np.asarray(R);ny,nx,nt=R.shape;Y=np.empty(R.shape,np.float64)
 for y in range(ny):
  for x in range(nx):
   for t in range(nt):
    if x>0:
     if y>0:
      sp=b.W*Y[y,x-1,t]+(1-b.W)*Y[y-1,x,t];ps=b.W*Y[y,x-1,t-1]+(1-b.W)*Y[y-1,x,t-1] if t else 0.
     else:sp=Y[y,x-1,t];ps=Y[y,x-1,t-1] if t else 0.
     p=b.A*sp+(Y[y,x,t-1]-b.A*ps if t else 0.)
    elif y>0:p=b.A*Y[y-1,x,t]+(Y[y,x,t-1]-b.A*Y[y-1,x,t-1] if t else 0.)
    elif t:p=Y[y,x,t-1]
    else:p=0.
    Y[y,x,t]=p+int(R[y,x,t])*step
 return Y/step

def build_features(X,eps,deep=False):
 A,T,I,R=b.build(X,eps)
 if not deep:return A,T,I,R
 S=reconstructed_state(R,eps);extra=[];rad=b.RAD
 for y,x,t in I:
  y=int(y);x=int(x);t=int(t);row=[]
  upper=S[y-1,x,t] if y else 0.
  for dy in DEEP_ROWS:
   if y>=dy:
    z=S[y-dy,x];zr=R[y-dy,x]
    row.extend((z[t-rad:t+rad+1]-z[t]).tolist())
    row.extend(np.asarray(zr[t-rad:t+rad+1],dtype=np.float64).tolist())
    row.extend([float(z[t]),float(z[t]-upper),1.0])
   else:
    row.extend([0.0]*(2*(2*rad+1)+3))
  extra.append(row)
 return np.concatenate([A,np.asarray(extra,np.float32)],axis=1),T,I,R

def subsample(A,T,cap):
 if len(T)<=cap:return A,T
 ii=np.linspace(0,len(T)-1,cap,dtype=np.int64);return A[ii],T[ii]

def fit_and_score(train_tiles,test_tile,eps,deep,label):
 import torch,torch.nn as nn,torch.nn.functional as F
 AA=[];TT=[];RR=[]
 for X in train_tiles:
  A,T,I,R=build_features(X,eps,deep=deep);A,T=subsample(A,T,MAX_PER_TILE);AA.append(A);TT.append(T);RR.append(R.reshape(-1));del I;gc.collect()
 A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR);mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T);cnt=np.bincount(b.cls(fullR),minlength=b.NCLASS).astype(np.float64)+1.;static=-np.log2(cnt/cnt.sum())
 class M(nn.Module):
  def __init__(self,d):
   super().__init__();h1,h2,h3=HIDDEN;self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
  def forward(self,x):return self.net(x)
 torch.manual_seed(SEED+16);np.random.seed(SEED+16);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
 for ep in range(EPOCHS):
  net.train();perm=idx[torch.randperm(len(idx))];tot=0.
  for i in range(0,len(perm),bs):
   j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
  print('VERT_FIT',label,ep,tot/len(Xt),flush=True)
 A0,T0,I0,R0=build_features(test_tile,eps,deep=deep);A0=(A0-mu)/sd;XE=torch.from_numpy(A0);YT=torch.from_numpy(b.cls(T0));bits=0.;net.eval()
 with torch.no_grad():
  for i in range(0,len(XE),16384):
   lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);yy=YT[i:i+16384];bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
 bits+=float(b.gamma_bits(np.maximum(np.abs(T0)-b.LIM,0)).sum());mask=np.zeros(R0.shape,bool)
 for y,x,t in I0:mask[int(y),int(x),int(t)]=True
 rb=R0[~mask];boundary=float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum());bits+=boundary;sb,sme=matched_sz3(test_tile,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES;n=int(test_tile.size)
 return {'label':label,'deep_rows':list(DEEP_ROWS) if deep else [],'feature_count':int(A.shape[1]),'shape':list(map(int,test_tile.shape)),'samples':n,'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/n),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/n),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/n),'gap_to_2x_bps':float(8*ours/n-4*sb/n),'boundary_bps':float(boundary/n),'sz3_maxerr':float(sme),'model_weights_charged':False,'serialized_arithmetic_stream':False}

def main(a):
 m=json.load(open(a.manifest));e=json.load(open(a.eps));raw=[];meta=[];ep=None
 for f in TRAIN_FRACS+(TEST_FRAC,):X,ep,md=extract16x32(m,e,f);raw.append(X);meta.append(md)
 ranges=[(q['trace_first'],q['trace_last']) for q in meta]
 for i in range(len(ranges)):
  for j in range(i):
   if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]):raise RuntimeError(('training/test trace overlap',i,j,ranges))
 base=fit_and_score(raw[:2],raw[2],ep,False,'baseline');deep=fit_and_score(raw[:2],raw[2],ep,True,'yminus2_yminus4')
 out={'kind':'waka-tall16-deep-vertical-context-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','dataset':DATASET,'epsilon':float(ep),'training_fractions':list(TRAIN_FRACS),'test_fraction':TEST_FRAC,'locations':meta,'same_residual_representation':True,'heldout_region_used_in_training_or_normalization':False,'deep_context_is_already_decoded_rows_only':True,'max_train_examples_per_training_tile':MAX_PER_TILE,'epochs':EPOCHS,'hidden':list(HIDDEN),'baseline':base,'deep_vertical':deep,'bps_change_deep_minus_base':float(deep['ideal_bps']-base['ideal_bps']),'gain_ratio_deep_over_base':float(deep['gain_vs_sz3_ideal']/base['gain_vs_sz3_ideal']),'crosses_2x':bool(deep['gain_vs_sz3_ideal']>=2.0)}
 Path(a.out).write_text(json.dumps(out,indent=2));print('VERT_FINAL',json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
