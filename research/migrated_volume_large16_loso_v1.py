#!/usr/bin/env python3
"""Four-survey 16x32 LOSO probability diagnostic with full causal replay.

Tests whether the tiny 4-row research geometry understates the general codec.
For each held-out survey, train the proven larger 320/240/160 probability model
on three fixed 16x32 regions from each of the other three surveys (nine source
tiles). The target survey is absent from fitting/normalization. Every target
chunk is charged before adaptation; replay uses only already-decoded target
samples. Geometry/location selection is header-only and fixed before amplitudes
are inspected. Ideal probability rate only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,copy,gc,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_large_native_screen as large
import migrated_volume_quick_adapter_loso_v1 as q
import migrated_volume_quick_adapter_loso_v3 as g
from general_seismic_numeric_io import matched_sz3

SURVEYS=q.SURVEYS
FRACS=(.15,.50,.85)
NY=16;NX=32;WINDOWS=(60000,120000,240000)
MAX_TRAIN=720000;EPOCHS=8;HIDDEN=(320,240,160);HEADER_BYTES=128
CHUNK=4096;ADAPT_LR=3e-4;WEIGHT_DECAY=1e-5;FIRST_CHUNK_STEPS=2;LATER_CHUNK_STEPS=1
REPLAY_PER_TILE=6000;REPLAY_CAP=12000;REPLAY_STEPS=2
PROTOCOL='large16x32-9tile-capacity-full-replay-v1'

def extract16(ds,manifest,epsj,frac):
    r=large.r;eps=float(epsj['datasets'][ds]['epsilon']);d=next(z for z in manifest['datasets'] if z['id']==ds)
    objects=[r.obj(u) for u in d['objects']];stream,local_frac,oi=g._stream_for_fraction(d,objects,frac)
    rr=r.S3ConcatSequential(r.S3,stream,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if s.total_traces is None or not s.binary_stride_exact:raise RuntimeError(('fixed stride required',ds,frac,oi,s.ns_policy))
        total=int(s.total_traces);target=int(round(local_frac*max(0,total-1)));chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),target-window//2));n=min(window,total-st)
            H=large.read_header_window(rr,s,st,n);geom=g._geom(H,r)
            if geom is None:continue
            rows=[(a+st,z+st) for a,z in geom['segments'] if z-a>=NX]
            if len(rows)<NY:continue
            cand=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);cand.append((abs(mid-target),i,block))
            _,gi,block=min(cand,key=lambda z:(z[0],z[1]));chosen=(window,geom,gi,block,min(z-a for a,z in block),len(rows));break
        if chosen is None:raise RuntimeError(('no header-derived 16x32 block',ds,frac,oi,WINDOWS))
        window,geom,gi,block,minlen,nrows=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX)
        md={'dataset':ds,'fraction':float(frac),'local_fraction':float(local_frac),'object_index':int(oi),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(nrows),'selection_uses_sample_values':False}
        print('LARGE16_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()

def build_subsample(X,eps,cap):
    A,T,I,R=q.b.build(X,eps);n=min(int(cap),len(T));ii=np.linspace(0,len(T)-1,n,dtype=np.int64);As=A[ii].copy();Ts=T[ii].copy();counts=np.bincount(q.b.cls(R.reshape(-1)),minlength=q.b.NCLASS).astype(np.float64);del A,T,I,R;gc.collect();return As,Ts,counts

def fit_base(train_tiles,seed):
    per=max(1,MAX_TRAIN//len(train_tiles));parts=[];targets=[];counts=np.zeros(q.b.NCLASS,np.float64)
    for i,(X,eps) in enumerate(train_tiles):
        A,T,c=build_subsample(X,eps,per);parts.append(A);targets.append(T);counts+=c;print('LARGE16_TRAIN_FEATURES',i,A.shape,flush=True)
    A=np.concatenate(parts);T=np.concatenate(targets);del parts,targets;gc.collect();mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A-=mu;A/=sd;Y=q.b.cls(T);counts+=1.;static=-np.log2(counts/counts.sum())
    h1,h2,h3=HIDDEN
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();self.trunk=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU());self.head=nn.Linear(h3,q.b.NCLASS)
        def latent(self,x):return self.trunk(x)
        def forward(self,x):return self.head(self.latent(x))
    torch.manual_seed(seed);np.random.seed(seed);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=1.5e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for s in range(0,len(perm),bs):
            j=perm[s:s+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('LARGE16_FIT',seed,ep,tot/len(Xt),flush=True)
    net.eval();
    for p in net.parameters():p.requires_grad_(False)
    return net,mu,sd,static

def boundary_bits(static,R,I):
    mask=np.zeros(R.shape,bool)
    for y,x,t in I:mask[int(y),int(x),int(t)]=True
    rb=R[~mask];return float(static[q.b.cls(rb)].sum()+q.b.gamma_bits(np.maximum(np.abs(rb)-q.b.LIM,0)).sum())

def prepare_target(X,eps,mu,sd,static):
    A,T,I,R=q.b.build(X,eps);A-=mu;A/=sd;Y=q.b.cls(T);bb=boundary_bits(static,R,I);tail=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum());return A,T,Y,R,bb,tail

def class_bits(net,A,Y):
    bits=0.;net.eval();XE=torch.from_numpy(A);YY=torch.from_numpy(Y)
    with torch.no_grad():
        for s in range(0,len(XE),16384):
            yy=YY[s:s+16384];lp=F.log_softmax(net(XE[s:s+16384]),1)/math.log(2);bits+=float((-lp[torch.arange(len(yy)),yy]).sum())
    return bits

def row_from_bits(meta,X,eps,bits):
    sb,sme=matched_sz3(X,eps);ours=int(math.ceil(bits/8))+HEADER_BYTES;return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/X.size),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme)}

def enable_adapt(net):
    for p in net.parameters():p.requires_grad_(True)
    return torch.optim.AdamW(net.parameters(),lr=ADAPT_LR,weight_decay=WEIGHT_DECAY)

def update(net,opt,X,Y,steps=1):
    if len(X)==0:return
    net.train()
    for _ in range(int(steps)):
        opt.zero_grad(set_to_none=True);loss=F.cross_entropy(net(X),Y);loss.backward();opt.step()
    net.eval()

def replay(net,opt,reservoir):
    if not reservoir:return
    X=torch.cat([z[0] for z in reservoir],0);Y=torch.cat([z[1] for z in reservoir],0)
    for _ in range(REPLAY_STEPS):
        for s in range(0,len(X),CHUNK):update(net,opt,X[s:s+CHUNK],Y[s:s+CHUNK],1)

def adapt_bits(net,opt,A,Y,first_tile):
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=0.;chunks=[]
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        xx=XE[s:s+CHUNK];yy=YY[s:s+CHUNK];net.eval()
        with torch.no_grad():lp=F.log_softmax(net(xx),1)/math.log(2);cb=float((-lp[torch.arange(len(yy)),yy]).sum())
        bits+=cb;chunks.append(cb/max(1,len(yy)));update(net,opt,xx,yy,FIRST_CHUNK_STEPS if first_tile and ci==0 else LATER_CHUNK_STEPS)
    return bits,chunks,XE,YY

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw={ds:{} for ds in SURVEYS}
    for ds in SURVEYS:
        for f in FRACS:raw[ds][f]=extract16(ds,m,e,f)
    targets=[]
    for ti,target in enumerate(SURVEYS):
        train_ids=tuple(ds for ds in SURVEYS if ds!=target);train=[(raw[ds][f][0],raw[ds][f][1]) for ds in train_ids for f in FRACS]
        net,mu,sd,static=fit_base(train,20261319+ti);adapt=copy.deepcopy(net);opt=enable_adapt(adapt);reservoir=[];base_rows=[];adapt_rows=[]
        for pi,f in enumerate(FRACS):
            X,eps,md=raw[target][f];A,T,Y,R,bb,tail=prepare_target(X,eps,mu,sd,static);base_bits=class_bits(net,A,Y)+tail+bb;base_rows.append(row_from_bits(md,X,eps,base_bits))
            if pi>0:replay(adapt,opt,reservoir)
            cb,chunks,XE,YY=adapt_bits(adapt,opt,A,Y,pi==0);row=row_from_bits(md,X,eps,cb+tail+bb);row['modeled_chunk_bps_first']=float(chunks[0]);row['modeled_chunk_bps_last']=float(chunks[-1]);adapt_rows.append(row);print('LARGE16_REPLAY',json.dumps(row),flush=True)
            take=min(REPLAY_PER_TILE,len(XE));ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
            while sum(len(z[0]) for z in reservoir)>REPLAY_CAP:reservoir.pop(0)
            del A,T,Y,R,XE,YY;gc.collect()
        bg=sum(z['sz3_bytes'] for z in base_rows)/sum(z['ideal_bytes_plus_header'] for z in base_rows);ag=sum(z['sz3_bytes'] for z in adapt_rows)/sum(z['ideal_bytes_plus_header'] for z in adapt_rows)
        targets.append({'test_dataset':target,'training_datasets':list(train_ids),'base_rows':base_rows,'adapt_rows':adapt_rows,'base_weighted_gain_vs_sz3':float(bg),'full_replay_weighted_gain_vs_sz3':float(ag),'gain_ratio_full_replay_over_base':float(ag/bg)});del net,adapt,opt,mu,sd,static;gc.collect()
    allb=[r for t in targets for r in t['base_rows']];alla=[r for t in targets for r in t['adapt_rows']]
    out={'kind':'four-survey-large16x32-capacity-full-replay-loso-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','protocol':PROTOCOL,'shape':[NY,NX],'source_tiles_per_loso_split':9,'source_training_fractions':list(FRACS),'target_fractions':list(FRACS),'max_train_examples':MAX_TRAIN,'source_training_epochs':EPOCHS,'hidden':list(HIDDEN),'held_out_survey_used_in_base_training':False,'location_and_geometry_use_sample_values':False,'test_positions_all_charged':True,'full_model_updates_only_after_scoring_decoded_chunks':True,'replay_uses_only_already_decoded_target_samples':True,'targets':targets,'base_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in allb)/sum(z['ideal_bytes_plus_header'] for z in allb)),'full_replay_overall_byte_weighted_gain_vs_sz3':float(sum(z['sz3_bytes'] for z in alla)/sum(z['ideal_bytes_plus_header'] for z in alla)),'all_full_replay_positions_beat_sz3':bool(all(z['gain_vs_sz3_ideal']>=1 for z in alla)),'note':'Realistic 16x32 cross-survey scale diagnostic. Model weights and arithmetic stream are not yet serialized/charged.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('LARGE16_FINAL',json.dumps({k:v for k,v in out.items() if k!='targets'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
