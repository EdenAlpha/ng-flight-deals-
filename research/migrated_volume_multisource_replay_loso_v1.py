#!/usr/bin/env python3
"""Shape-matched universal 16x32 source -> unseen Waka 16x32 gate.

The strongest prior unseen-Waka result trained the universal model on 4x24 source
tiles but deployed it on native 16x32 Waka. This experiment removes that shape
mismatch while preserving every other successful rule: 15 diverse source regions
from Kahu/Opunake/Tui, 320/240/160 probability model, 10 source-training epochs,
and strict decoder-reproducible full replay.

All source and target locations are fixed by survey fraction and SEG-Y headers
before amplitudes are inspected. Multiple standalone SEG-Y objects are selected
by cumulative object bytes; true split-file assemblies remain concatenated.
Waka is completely absent from fitting and normalization. Every held-out Waka
chunk is charged before adaptation; replay uses only already-decoded Waka data.

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
import migrated_volume_large_native_screen as large

TARGET='marine_waka_3d'
SOURCE_IDS=('marine_kahu_3d','marine_opunake_3d','marine_tui_3d')
SOURCE_FRACS=(.08,.29,.50,.71,.92)
TARGET_FRACS=(.15,.50,.85)
MAX_TRAIN=1200000
EPOCHS=10
HIDDEN=(320,240,160)
NY=16;NX=32;WINDOWS=(60000,120000,240000)
PROTOCOL='shape-matched-source16-target16-general-v1'

def _stream_for_fraction(d,objects,frac):
    if d.get('assembly') or len(objects)==1:return objects,float(frac),0
    sizes=np.asarray([int(o['size']) for o in objects],np.int64);cum=np.cumsum(sizes);target=float(frac)*float(cum[-1]);oi=int(np.searchsorted(cum,target,side='right'));oi=min(oi,len(objects)-1);before=0 if oi==0 else int(cum[oi-1]);local=(target-before)/max(1,int(sizes[oi]));return [objects[oi]],min(1.,max(0.,float(local))),oi

def extract16(ds,manifest,epsj,frac):
    r=large.r;d=next(z for z in manifest['datasets'] if z['id']==ds);eps=float(epsj['datasets'][ds]['epsilon']);objects=[r.obj(u) for u in d['objects']];stream,local_frac,oi=_stream_for_fraction(d,objects,frac)
    rr=r.S3ConcatSequential(r.S3,stream,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('fixed-stride selected SEG-Y required',ds,frac,oi,s.ns_policy))
        total=int(s.total_traces);center=int(round(local_frac*max(0,total-1)));chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),center-window//2));n=min(window,total-st);H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,z+st) for a,z in geom['segments']];rows=[z for z in seg if z[1]-z[0]>=NX]
            if len(rows)<NY:
                print('SHAPE16_WINDOW_REJECT',ds,frac,window,geom['mode'],len(rows),flush=True);continue
            choices=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);choices.append((abs(mid-center),i,block))
            _,gi,block=min(choices,key=lambda z:(z[0],z[1]));chosen=(window,geom,gi,block,min(z-a for a,z in block),len(rows));break
        if chosen is None:raise RuntimeError(('no header-derived 16x32 geometry',ds,frac,oi,WINDOWS))
        window,geom,gi,block,minlen,row_count=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX)
        md={'dataset':ds,'fraction':float(frac),'local_fraction':float(local_frac),'object_index':int(oi),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(row_count),'location_selection_uses_sample_values':False};print('SHAPE16_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()

def _assert_nonoverlap(meta,label):
    by={}
    for z in meta:by.setdefault((z['dataset'],z['object_index']),[]).append(z)
    for key,rows in by.items():
        rows=sorted(rows,key=lambda z:z['trace_first'])
        for a,b0 in zip(rows,rows[1:]):
            if b0['trace_first']<=a['trace_last']:raise RuntimeError((label,'overlap',key,a['fraction'],b0['fraction'],(a['trace_first'],a['trace_last']),(b0['trace_first'],b0['trace_last'])))

def wide_fit(train_tiles,seed):
    # Memory-bounded source preparation: deterministically retain an equal share
    # of the frozen 1.2M training examples from each 16x32 source tile.
    per=max(1,MAX_TRAIN//len(train_tiles));AA=[];TT=[];counts=np.zeros(q.b.NCLASS,np.float64)
    for ti,(X,eps) in enumerate(train_tiles):
        A,T,_,R=q.b.build(X,eps);counts+=np.bincount(q.b.cls(R.reshape(-1)),minlength=q.b.NCLASS);A,T=q.deterministic_subsample(A,T,per);AA.append(A);TT.append(T);print('SHAPE16_FEATURES',ti,A.shape,flush=True);del R;gc.collect()
    A=np.concatenate(AA);T=np.concatenate(TT);del AA,TT;gc.collect();mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=q.b.cls(T);counts+=1.;static=-np.log2(counts/counts.sum());h1,h2,h3=HIDDEN
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
        print('SHAPE16_FIT',seed,ep,tot/len(Xt),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    print('SHAPE16_PARAMS',sum(p.numel() for p in net.parameters()),flush=True);return net,mu,sd,static

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    for ds in SOURCE_IDS:
        for frac in SOURCE_FRACS:
            X,ep,md=extract16(ds,m,e,frac);source.append((X,ep));source_meta.append(md)
    _assert_nonoverlap(source_meta,'source')
    targets=[];target_meta=[]
    for frac in TARGET_FRACS:
        X,ep,md=extract16(TARGET,m,e,frac);targets.append((X,ep,md));target_meta.append(md)
    _assert_nonoverlap(target_meta,'target')
    q.crop=lambda X:np.ascontiguousarray(X);fr._orig_fit=wide_fit
    net,mu,sd,static=fr.fit_base(source,20261419);state,u1,u2=fr.new_adapter(99000);reservoir=[];base_rows=[];adapt_rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(TARGET_FRACS,targets)):
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md['trace_first'],'trace_last':md['trace_last'],'geometry_mode':md['geometry_mode'],'shape':list(map(int,X.shape))}
        base_rows.append(fr.score_base(net,mu,sd,static,X,ep,meta))
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        row=fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0);adapt_rows.append(row);print('SHAPE16_WAKA_REPLAY',json.dumps(row),flush=True)
    bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows);gap=(sum(z['ideal_bytes_plus_header'] for z in adapt_rows)-.5*sum(z['sz3_bytes'] for z in adapt_rows))*8/sum(z['samples'] for z in adapt_rows)
    out={'kind':'shape-matched-source16-unseen-waka16-full-replay-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'training_datasets':list(SOURCE_IDS),'source_training_fractions':list(SOURCE_FRACS),'source_training_tiles':len(source),'source_training_shape':'16x32 native','source_training_epochs':EPOCHS,'max_train_examples':MAX_TRAIN,'hidden':list(HIDDEN),'test_dataset':TARGET,'target_shape':'16x32 native','target_fractions':list(TARGET_FRACS),'waka_used_in_base_training':False,'source_positions_nonoverlapping_within_each_object':True,'target_positions_nonoverlapping':True,'target_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_waka_samples':True,'source_meta':source_meta,'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'weighted_gap_to_2x_bps':float(gap),'all_target_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in adapt_rows)),'positions_crossing_2x':int(sum(z['gain_vs_sz3_ideal']>=2 for z in adapt_rows)),'frozen_4x24_source_reference_gain':1.9125539732547088,'note':'Only source training geometry changes relative to the frozen strongest unseen-Waka stacked gate: source surveys are now also native 16x32. Waka remains fully held out until its charged stream begins. Ideal probability rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('SHAPE16_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
