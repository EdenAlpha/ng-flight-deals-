#!/usr/bin/env python3
"""Fast four-survey leave-one-out probability-transfer gate.

Discovery gate, not a promoted codec.  For each migrated survey in
{Waka,Kahu,Opunake,Tui}, fit the *same fixed architecture/hyperparameters* only
on the other three surveys, then score three deterministic positions from the
held-out survey.  No held-out values, statistics, epsilon, survey id, or result
participates in fitting/normalization/model selection.

The reported byte count is an ideal arithmetic-rate estimate plus a fixed
header.  It is intentionally labelled diagnostic.  If a target crosses 2x here
we must next materialize the arithmetic stream and charge the frozen model in
the software/release, not declare a codec win from this file alone.
"""
from __future__ import annotations
import argparse, gc, json, math
from pathlib import Path
import numpy as np
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

SURVEYS=('marine_waka_3d','marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
TRAIN_FRAC=.50
TEST_FRACS=(.15,.50,.85)
MAX_TRAIN=240000
EPOCHS=3
HIDDEN=(160,112,80)
HEADER_BYTES=128
# Use a fixed central 4x24 subset for the fast gate.  The choice is made before
# reading samples and is identical for every survey/position.
XKEEP=24

def crop(X):
    X=np.asarray(X)
    if X.shape[1] <= XKEEP:return np.ascontiguousarray(X)
    x0=(X.shape[1]-XKEEP)//2
    return np.ascontiguousarray(X[:,x0:x0+XKEEP,:])

def deterministic_subsample(A,T,cap):
    n=len(T)
    if n<=cap:return A,T
    # Uniform deterministic positions; no target/value-based selection.
    idx=np.linspace(0,n-1,cap,dtype=np.int64)
    return A[idx],T[idx]

def fit_model(train_tiles,seed):
    import torch, torch.nn as nn, torch.nn.functional as F
    AA=[];TT=[];RR=[]
    for X,eps in train_tiles:
        A,T,_,R=b.build(crop(X),eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR)
    A,T=deterministic_subsample(A,T,MAX_TRAIN)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T)
    sh=np.bincount(b.cls(fullR),minlength=b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh)
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();h1,h2,h3=HIDDEN
            self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(seed);np.random.seed(seed)
    net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4)
    X=torch.from_numpy(A);Y=torch.from_numpy(Y);idx=torch.arange(len(X));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(X[j]),Y[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('FIT',seed,'epoch',ep,'ce_nats',tot/len(X),flush=True)
    return net,mu,sd,static

def score(net,mu,sd,static,X,eps,meta):
    import torch, torch.nn.functional as F
    X=crop(X);A,T,I,R=b.build(X,eps);A=(A-mu)/sd;Y=b.cls(T);bits=0.
    net.eval();XE=torch.from_numpy(A);YY=torch.from_numpy(Y)
    with torch.no_grad():
        for i in range(0,len(XE),16384):
            lp=F.log_softmax(net(XE[i:i+16384]),1)/math.log(2);yy=YY[i:i+16384]
            bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
    tail=np.maximum(np.abs(T)-b.LIM,0);bits+=float(b.gamma_bits(tail).sum())
    mask=np.zeros(R.shape,bool)
    for y,x,t in I:mask[int(y),int(x),int(t)]=True
    rb=R[~mask];bits+=float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum())
    sb,sme=matched_sz3(X,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES
    return {**meta,'shape':list(map(int,X.shape)),'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/X.size),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/X.size),'crosses_2x_ideal':bool(sb/ours>=2.0),'sz3_maxerr':float(sme)}

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps))
    # Cache only raw tiles (~small); feature matrices are freed target-by-target.
    raw={}
    for ds in SURVEYS:
        raw[ds]={}
        for frac in sorted(set((TRAIN_FRAC,)+TEST_FRACS)):
            X,ep,md=b.extract(ds,m,e,frac);raw[ds][frac]=(crop(X),ep,md)
            print('RAW',ds,frac,crop(X).shape,flush=True)
    targets=[]
    for ti,target in enumerate(SURVEYS):
        train_ids=tuple(q for q in SURVEYS if q!=target)
        train=[(raw[q][TRAIN_FRAC][0],raw[q][TRAIN_FRAC][1]) for q in train_ids]
        net,mu,sd,static=fit_model(train,20260818+ti)
        rows=[]
        for frac in TEST_FRACS:
            X,ep,md=raw[target][frac]
            row=score(net,mu,sd,static,X,ep,{'dataset':target,'fraction':frac,'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode')})
            rows.append(row);print('LOSO',json.dumps(row),flush=True)
        weighted=sum(q['sz3_bytes'] for q in rows)/sum(q['ideal_bytes_plus_header'] for q in rows)
        targets.append({'test_dataset':target,'training_datasets':list(train_ids),'rows':rows,'weighted_ideal_gain_vs_sz3':float(weighted),'min_ideal_gain_vs_sz3':float(min(q['gain_vs_sz3_ideal'] for q in rows)),'median_ideal_gain_vs_sz3':float(np.median([q['gain_vs_sz3_ideal'] for q in rows])),'positions_crossing_2x':int(sum(q['crosses_2x_ideal'] for q in rows))})
        del net,mu,sd,static;gc.collect()
    allrows=[r for t in targets for r in t['rows']]
    out={'kind':'fast-four-survey-leave-one-out-probability-v1','status':'diagnostic_not_serialized_codec','surveys':list(SURVEYS),'training_rule':'for each target, same model trained only on the other three surveys','train_fraction':TRAIN_FRAC,'test_fractions':list(TEST_FRACS),'epochs':EPOCHS,'max_train_examples':MAX_TRAIN,'spatial_shape_rule':'fixed central 4x24 after native geometry extraction','held_out_survey_used_in_training':False,'targets':targets,'overall_byte_weighted_ideal_gain_vs_sz3':float(sum(q['sz3_bytes'] for q in allrows)/sum(q['ideal_bytes_plus_header'] for q in allrows)),'surveys_weighted_ge_2x':int(sum(t['weighted_ideal_gain_vs_sz3']>=2 for t in targets)),'all_positions_ge_1x':bool(all(q['gain_vs_sz3_ideal']>=1 for q in allrows))}
    Path(a.out).write_text(json.dumps(out,indent=2));print('FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
