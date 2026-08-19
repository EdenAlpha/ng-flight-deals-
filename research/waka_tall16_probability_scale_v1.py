#!/usr/bin/env python3
"""Paired 16x32 vs 16x128 learned-probability scale diagnostic on Waka.

At each fixed location, select a native 16x128 block from SEG-Y header geometry
only. The 16x32 comparison is the exact central 32-trace crop of that same block.
Training fractions .01 and .08 are deliberately separated from the held-out .05
region so the physically large native blocks do not overlap. Matched SZ3 receives
identical samples/epsilon at each shape.

To keep 16x128 memory bounded while preserving the exact causal predictor, this
script materializes only reconstructed state/residual arrays, samples training
features deterministically from the full state, and scores held-out features in
batches. The feature definition is exactly the one in
migrated_volume_crosssurvey_prob_screen.build.

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

DATASET='marine_waka_3d'; TRAIN_FRACS=(.01,.08); TEST_FRAC=.05
NY=16; WIDE=128; SMALL=32; WINDOWS=(60000,120000,240000)
MAX_PER_TILE=180000; EPOCHS=7; HEADER_BYTES=128; HIDDEN=(192,144,96); SEED=20260819

def extract16x128(manifest,epsj,frac):
    r=large.r; ds=next(d for d in manifest['datasets'] if d['id']==DATASET)
    eps=float(epsj['datasets'][DATASET]['epsilon']); oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None: raise RuntimeError(('fixed stride required',s.ns_policy))
        total=int(s.total_traces); center=int(round(float(frac)*max(0,total-1))); chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),center-window//2)); n=min(window,total-st)
            H=large.read_header_window(rr,s,st,n); geom,_=r.choose_geometry(H)
            seg=[(a+st,z+st) for a,z in geom['segments']]; rows=[q for q in seg if q[1]-q[0]>=WIDE]
            if len(rows)<NY:
                print('COMBINED_WINDOW_REJECT',frac,window,geom['mode'],len(rows),flush=True); continue
            cand=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY]; mid=.5*(block[0][0]+block[-1][1]); cand.append((abs(mid-center),i,block))
            _,gi,block=min(cand,key=lambda q:(q[0],q[1])); minlen=min(z-a for a,z in block)
            chosen=(window,geom,gi,block,minlen,len(rows)); break
        if chosen is None: raise RuntimeError(('too few 16x128 rows after deterministic header expansion',frac,WINDOWS))
        window,geom,gi,block,minlen,row_count=chosen
        X,ids=large.read_tile(rr,s,block,minlen,WIDE)
        md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(row_count),'location_selection_uses_sample_values':False}
        print('COMBINED_RAW',json.dumps(md),flush=True); return np.ascontiguousarray(X),eps,md
    finally: rr.close()

def crop32(X):
    x0=(X.shape[1]-SMALL)//2; return np.ascontiguousarray(X[:,x0:x0+SMALL,:])

def residual_state(X,eps):
    step=2*float(eps)*.9999; X=np.asarray(X,np.float64); ny,nx,nt=X.shape
    R=np.empty(X.shape,np.int32); Y=np.empty(X.shape,np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        sp=b.W*Y[y,x-1,t]+(1-b.W)*Y[y-1,x,t]
                        ps=b.W*Y[y,x-1,t-1]+(1-b.W)*Y[y-1,x,t-1] if t else 0.
                    else:
                        sp=Y[y,x-1,t]; ps=Y[y,x-1,t-1] if t else 0.
                    p=b.A*sp+(Y[y,x,t-1]-b.A*ps if t else 0.)
                elif y>0:
                    p=b.A*Y[y-1,x,t]+(Y[y,x,t-1]-b.A*Y[y-1,x,t-1] if t else 0.)
                elif t: p=Y[y,x,t-1]
                else: p=0.
                q=int(np.rint((X[y,x,t]-p)/step)); R[y,x,t]=q; Y[y,x,t]=p+q*step
    return Y/step,R

def feature_batch(S,R,flat):
    ny,nx,nt=S.shape; ntm=nt-b.RAD-15
    flat=np.asarray(flat,np.int64); q0=flat//ntm; t=14+(flat%ntm); x=1+(q0%(nx-1)); y=q0//(nx-1)
    n=len(flat); cols=[]; ar=np.arange(n)
    # Current waveform history relative to the immediately previous decoded sample.
    prev=S[y,x,t-1]
    for o in range(-10,0): cols.append(S[y,x,t+o]-prev)
    x2=np.where(x>1,x-2,x-1); ym=np.maximum(y-1,0); has=(y>0)
    def wave(kind,o):
        if kind==0:return S[y,x-1,t+o]
        if kind==1:return S[y,x2,t+o]
        if kind==2:return np.where(has,S[ym,x,t+o],0.)
        return np.where(has,S[ym,x-1,t+o],0.)
    centers=[wave(k,0) for k in range(4)]
    for k in range(4):
        c=centers[k]
        for o in range(-b.RAD,b.RAD+1): cols.append(wave(k,o)-c)
    def resid(kind,o):
        if kind==0:return R[y,x-1,t+o]
        if kind==1:return R[y,x2,t+o]
        if kind==2:return np.where(has,R[ym,x,t+o],0)
        return np.where(has,R[ym,x-1,t+o],0)
    for k in range(4):
        for o in range(-b.RAD,b.RAD+1): cols.append(resid(k,o))
    for o in range(-b.HIST,0): cols.append(R[y,x,t+o])
    l=centers[0]; l2=centers[1]; u=centers[2]; ul=centers[3]
    cols += [l,l2,u,ul,l-l2,l-u,S[y,x,t-1]-S[y,x-1,t-1],S[y,x,t-1]-np.where(has,S[ym,x,t-1],0.)]
    F=np.stack(cols,axis=1).astype(np.float32,copy=False); T=R[y,x,t].astype(np.int32,copy=False)
    return F,T

def modeled_count(shape):
    ny,nx,nt=shape; return int(ny*(nx-1)*(nt-b.RAD-15))

def training_features(X,eps,cap):
    S,R=residual_state(X,eps); n=modeled_count(X.shape); take=min(int(cap),n)
    ii=np.linspace(0,n-1,take,dtype=np.int64); F,T=feature_batch(S,R,ii)
    counts=np.bincount(b.cls(R.reshape(-1)),minlength=b.NCLASS).astype(np.float64)
    del S,R; gc.collect(); return F,T,counts

def fit_model(train_tiles,eps,width):
    import torch,torch.nn as nn,torch.nn.functional as F
    AA=[];TT=[];counts=np.zeros(b.NCLASS,np.float64)
    for k,X in enumerate(train_tiles):
        A,T,c=training_features(X,eps,MAX_PER_TILE); AA.append(A);TT.append(T);counts+=c;print('COMBINED_TRAIN_FEATURES',width,k,A.shape,flush=True)
    A=np.concatenate(AA);T=np.concatenate(TT); del AA,TT; gc.collect()
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.; A=(A-mu)/sd; Y=b.cls(T); counts+=1.; static=-np.log2(counts/counts.sum())
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();h1,h2,h3=HIDDEN;self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(SEED+int(width));np.random.seed(SEED+int(width));torch.set_num_threads(min(8,torch.get_num_threads()))
    net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('COMBINED_FIT',width,ep,tot/len(Xt),flush=True)
    return net,mu,sd,static

def score_model(net,mu,sd,static,X,eps,width):
    import torch,torch.nn.functional as F
    S,R=residual_state(X,eps); nmod=modeled_count(X.shape); bits=0.; tailbits=0.; net.eval(); batch=16384
    with torch.no_grad():
        for s in range(0,nmod,batch):
            ii=np.arange(s,min(nmod,s+batch),dtype=np.int64); A,T=feature_batch(S,R,ii); A=(A-mu)/sd; yy=torch.from_numpy(b.cls(T)); xx=torch.from_numpy(A)
            lp=F.log_softmax(net(xx),1)/math.log(2); bits+=float((-lp[torch.arange(len(yy)),yy]).sum()); tailbits+=float(b.gamma_bits(np.maximum(np.abs(T)-b.LIM,0)).sum())
    mask=np.zeros(R.shape,bool); mask[:,1:,14:R.shape[2]-b.RAD-1]=True; rb=R[~mask]
    boundary=float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum()); total=bits+tailbits+boundary
    sb,sme=matched_sz3(X,eps);ours=int(math.ceil(total/8))+HEADER_BYTES;ns=int(X.size)
    del S,R;gc.collect()
    return {'width':int(width),'shape':list(map(int,X.shape)),'samples':ns,'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/ns),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/ns),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/ns),'gap_to_2x_bps':float(8*ours/ns-4*sb/ns),'boundary_bps':float(boundary/ns),'sz3_maxerr':float(sme),'model_weights_charged':False,'serialized_arithmetic_stream':False}

def run_shape(train_tiles,test_tile,eps,width):
    net,mu,sd,static=fit_model(train_tiles,eps,width); out=score_model(net,mu,sd,static,test_tile,eps,width); del net,mu,sd,static;gc.collect();return out

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw=[];meta=[];ep=None
    for f in TRAIN_FRACS+(TEST_FRAC,): X,ep,md=extract16x128(m,e,f);raw.append(X);meta.append(md)
    ranges=[(q['trace_first'],q['trace_last']) for q in meta]
    for i in range(len(ranges)):
        for j in range(i):
            if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]): raise RuntimeError(('training/test trace overlap',i,j,ranges))
    wide=run_shape(raw[:2],raw[2],ep,WIDE); small=run_shape([crop32(q) for q in raw[:2]],crop32(raw[2]),ep,SMALL)
    out={'kind':'waka-paired-learned-probability-scale-16x32-vs-16x128-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','dataset':DATASET,'epsilon':float(ep),'training_fractions':list(TRAIN_FRACS),'test_fraction':TEST_FRAC,'locations':meta,'same_native_16x128_regions_for_both_shapes':True,'small_is_central_32_trace_crop':True,'all_regions_nonoverlapping':True,'max_train_examples_per_training_tile':MAX_PER_TILE,'epochs':EPOCHS,'hidden':list(HIDDEN),'shape16x32':small,'shape16x128':wide,'gain_ratio_128_over_32':float(wide['gain_vs_sz3_ideal']/small['gain_vs_sz3_ideal']),'bps_reduction_128_vs_32':float(small['ideal_bps']-wide['ideal_bps']),'crosses_2x_at_16x128':bool(wide['gain_vs_sz3_ideal']>=2.0)}
    Path(a.out).write_text(json.dumps(out,indent=2)); print('COMBINED_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
