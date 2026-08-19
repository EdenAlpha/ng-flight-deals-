#!/usr/bin/env python3
"""Paired 4x32 vs 4x128 learned-probability scale diagnostic on Waka.

Three Waka locations are frozen by fractions before amplitudes are read. Two
locations (.01,.025) train the same probability architecture; .05 is held out.
At each location a native 4x128 block is extracted from SEG-Y header geometry.
The 4x32 experiment uses the exact central 32 traces of those same 4x128 blocks.
Thus width is the only intended scale change. Matched SZ3 sees the identical
samples and public survey epsilon for each width.

Ideal probability-rate diagnostic only: learned weights are not serialized or
charged. A positive result must later be reproduced with a frozen universal
model or explicit model charge and a real arithmetic stream.
"""
from __future__ import annotations
import argparse, json, math, gc
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

DATASET='marine_waka_3d'
TRAIN_FRACS=(.01,.025)
TEST_FRAC=.05
WIDTH=128
SMALL=32
NY=4
WINDOW=60000
MAX_PER_TILE=180000
EPOCHS=7
HEADER_BYTES=128
HIDDEN=(192,144,96)
SEED=20260819


def extract128(manifest,epsj,frac):
    r=large.r;ds=next(d for d in manifest['datasets'] if d['id']==DATASET);eps=float(epsj['datasets'][DATASET]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('fixed stride required',s.ns_policy))
        total=int(s.total_traces);center=int(round(float(frac)*max(0,total-1)));st=max(0,min(max(0,total-WINDOW),center-WINDOW//2));n=min(WINDOW,total-st)
        H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,z+st) for a,z in geom['segments']]
        # Ignore one-trace separators/truncated runs: select only genuine rows
        # long enough for 128 traces, using header geometry only.
        rows=[q for q in seg if q[1]-q[0]>=WIDTH]
        if len(rows)<NY:raise RuntimeError(('too few 128-wide rows',frac,geom['mode'],rows[:20]))
        cand=[]
        for i in range(len(rows)-NY+1):
            block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);cand.append((abs(mid-center),i,block))
        _,gi,block=min(cand,key=lambda q:(q[0],q[1]));minlen=min(z-a for a,z in block);X,ids=large.read_tile(rr,s,block,minlen,WIDTH)
        md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'location_selection_uses_sample_values':False}
        print('WIDE_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()


def crop32(X):
    x0=(X.shape[1]-SMALL)//2
    return np.ascontiguousarray(X[:,x0:x0+SMALL,:])


def subsample(A,T,cap):
    if len(T)<=cap:return A,T
    ii=np.linspace(0,len(T)-1,cap,dtype=np.int64);return A[ii],T[ii]


def fit_and_score(train_tiles,test_tile,eps,width):
    import torch, torch.nn as nn, torch.nn.functional as F
    AA=[];TT=[];RR=[]
    for X in train_tiles:
        A,T,I,R=b.build(X,eps);A,T=subsample(A,T,MAX_PER_TILE);AA.append(A);TT.append(T);RR.append(R.reshape(-1));del I;gc.collect()
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T)
    cnt=np.bincount(b.cls(fullR),minlength=b.NCLASS).astype(np.float64)+1.;static=-np.log2(cnt/cnt.sum())
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();h1,h2,h3=HIDDEN
            self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(SEED+int(width));np.random.seed(SEED+int(width));torch.set_num_threads(min(8,torch.get_num_threads()))
    net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('WIDE_FIT',width,ep,tot/len(Xt),flush=True)
    A0,T0,I0,R0=b.build(test_tile,eps);A0=(A0-mu)/sd;YY=b.cls(T0);XE=torch.from_numpy(A0);YT=torch.from_numpy(YY);bits=0.;net.eval()
    with torch.no_grad():
        for i in range(0,len(XE),16384):
            lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);yy=YT[i:i+16384];bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
    bits+=float(b.gamma_bits(np.maximum(np.abs(T0)-b.LIM,0)).sum())
    mask=np.zeros(R0.shape,bool)
    for y,x,t in I0:mask[int(y),int(x),int(t)]=True
    rb=R0[~mask];boundary=float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum());bits+=boundary
    sb,sme=matched_sz3(test_tile,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES;n=int(test_tile.size)
    return {'width':int(width),'shape':list(map(int,test_tile.shape)),'samples':n,'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/n),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/n),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/n),'gap_to_2x_bps':float(8*ours/n-4*sb/n),'boundary_bps':float(boundary/n),'sz3_maxerr':float(sme),'model_weights_charged':False,'serialized_arithmetic_stream':False}


def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw=[];meta=[];ep=None
    for f in TRAIN_FRACS+(TEST_FRAC,):
        X,ep,md=extract128(m,e,f);raw.append(X);meta.append(md)
    # Explicit non-overlap sanity from trace ranges.
    ranges=[(q['trace_first'],q['trace_last']) for q in meta]
    for i in range(len(ranges)):
        for j in range(i):
            if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]):raise RuntimeError(('training/test trace overlap',i,j,ranges))
    wide=fit_and_score(raw[:2],raw[2],ep,128)
    small_train=[crop32(q) for q in raw[:2]];small_test=crop32(raw[2]);small=fit_and_score(small_train,small_test,ep,32)
    out={'kind':'waka-paired-learned-probability-scale-32-vs-128-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','dataset':DATASET,'epsilon':float(ep),'training_fractions':list(TRAIN_FRACS),'test_fraction':TEST_FRAC,'locations':meta,'same_native_4x128_regions_for_both_widths':True,'small_is_central_32_trace_crop':True,'max_train_examples_per_training_tile':MAX_PER_TILE,'epochs':EPOCHS,'hidden':list(HIDDEN),'width32':small,'width128':wide,'gain_ratio_128_over_32':float(wide['gain_vs_sz3_ideal']/small['gain_vs_sz3_ideal']),'bps_reduction_128_vs_32':float(small['ideal_bps']-wide['ideal_bps']),'crosses_2x_at_128':bool(wide['gain_vs_sz3_ideal']>=2.0)}
    Path(a.out).write_text(json.dumps(out,indent=2));print('WIDE_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
