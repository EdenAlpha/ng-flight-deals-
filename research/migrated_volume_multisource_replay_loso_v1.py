#!/usr/bin/env python3
"""Stacked unseen-Waka 16x32 generalization gate.

Combine only mechanisms that independently improved held-out compression:
- 15 diverse source tiles from Kahu/Opunake/Tui (five fixed regions each),
- a wider 320/240/160 probability model,
- 10 source-training epochs,
- full decoder-reproducible causal replay,
- native 16x32 Waka target geometry, which independently beat 4x32 scaling.

Waka is completely absent from fitting and normalization. Source tiles retain
the established central 4x24 training shape. Before target evaluation q.crop is
replaced by identity so the held-out Waka target remains a genuine 16x32 block.
Every Waka chunk is charged before it updates the model; between target tiles,
replay uses only already-decoded Waka samples.

Ideal probability-rate diagnostic only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,gc,json
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as geometry  # installs object-aware source extractor
import migrated_volume_large_native_screen as large

TARGET='marine_waka_3d'
SOURCE_IDS=('marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
SOURCE_FRACS=(.08,.29,.50,.71,.92)
TARGET_FRACS=(.15,.50,.85)
MAX_TRAIN=1200000
EPOCHS=10
HIDDEN=(320,240,160)
NY=16;NX=32;WINDOWS=(60000,120000,240000)
PROTOCOL='unseen-waka-16x32-stacked-general-v1'

def central24(X):
    X=np.asarray(X);x0=(X.shape[1]-24)//2;return np.ascontiguousarray(X[:,x0:x0+24,:])

def extract_waka16(manifest,epsj,frac):
    r=large.r;ds=next(d for d in manifest['datasets'] if d['id']==TARGET);eps=float(epsj['datasets'][TARGET]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('fixed stride Waka required',s.ns_policy))
        total=int(s.total_traces);center=int(round(float(frac)*max(0,total-1)));chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),center-window//2));n=min(window,total-st);H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,z+st) for a,z in geom['segments']];rows=[z for z in seg if z[1]-z[0]>=NX]
            if len(rows)<NY:
                print('STACKED_WAKA_WINDOW_REJECT',frac,window,geom['mode'],len(rows),flush=True);continue
            choices=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);choices.append((abs(mid-center),i,block))
            _,gi,block=min(choices,key=lambda z:(z[0],z[1]));chosen=(window,geom,gi,block,min(z-a for a,z in block),len(rows));break
        if chosen is None:raise RuntimeError(('no header-derived Waka 16x32 geometry',frac,WINDOWS))
        window,geom,gi,block,minlen,row_count=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX)
        md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(row_count),'location_selection_uses_sample_values':False}
        print('STACKED_WAKA_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()

def wide_fit(train_tiles,seed):
    AA=[];TT=[];RR=[]
    for X,eps in train_tiles:
        A,T,_,R=q.b.build(X,eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR);A,T=q.deterministic_subsample(A,T,MAX_TRAIN)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=q.b.cls(T)
    sh=np.bincount(q.b.cls(fullR),minlength=q.b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh);h1,h2,h3=HIDDEN
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();self.trunk=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU());self.head=nn.Linear(h3,q.b.NCLASS)
        def latent(self,x):return self.trunk(x)
        def forward(self,x):return self.head(self.latent(x))
    torch.manual_seed(seed);np.random.seed(seed);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=1.5e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('STACKED_SOURCE_FIT',seed,ep,tot/len(Xt),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    print('STACKED_MODEL_PARAMS',sum(p.numel() for p in net.parameters()),flush=True);return net,mu,sd,static

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    # Source training remains the established 4x24 protocol.
    for ds in SOURCE_IDS:
        for frac in SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=central24(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape)),'trace_first':md.get('trace_first')});print('STACKED_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=extract_waka16(m,e,frac);targets.append((X,ep,md))
    ranges=[(int(z[2]['trace_first']),int(z[2]['trace_last'])) for z in targets]
    for i in range(len(ranges)):
        for j in range(i):
            if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]):raise RuntimeError(('Waka target overlap',i,j,ranges))
    # From this point on, preserve the full 16x32 held-out target; fr functions
    # resolve q.crop dynamically, so identity disables the old 24-trace gate crop.
    q.crop=lambda X: np.ascontiguousarray(X)
    fr._orig_fit=wide_fit
    net,mu,sd,static=fr.fit_base(source,20261319);state,u1,u2=fr.new_adapter(98000);reservoir=[];base_rows=[];adapt_rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md['trace_first'],'trace_last':md['trace_last'],'geometry_mode':md['geometry_mode'],'shape':list(map(int,X.shape))}
        base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('STACKED_WAKA_REPLAY',json.dumps(row),flush=True)
    bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
    out={'kind':'unseen-waka-16x32-stacked-general-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'training_datasets':list(SOURCE_IDS),'source_training_fractions':list(SOURCE_FRACS),'source_training_tiles':len(source),'source_training_shape':'4x24 native crop','source_training_epochs':EPOCHS,'max_train_examples':MAX_TRAIN,'hidden':list(HIDDEN),'test_dataset':TARGET,'target_shape':'16x32 native','target_fractions':list(TARGET_FRACS),'waka_used_in_base_training':False,'target_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_waka_samples':True,'source_meta':source_meta,'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'gain_ratio_full_replay_over_base':float(ag/bg),'all_target_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in adapt_rows)),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in adapt_rows)),'note':'Stacks only mechanisms with prior independent positive evidence: source diversity, longer source fitting, wider probability capacity, native 16-row Waka geometry, and strict causal replay. Waka remains fully held out until its charged stream begins. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('STACKED_WAKA_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
