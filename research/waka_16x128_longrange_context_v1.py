#!/usr/bin/env python3
"""Long-range causal waveform context on native 16x128 Waka.

The paired 16x32/16x128 gate proved that SZ3 extracts substantially more benefit
from horizontal width than our current left-to-right probability model. This
experiment preserves the exact direct residual representation and adds only
already-decoded horizontal waveform context at distances 4, 8, 16 and 32 traces.
No point predictor, quantizer, hierarchy or target-selection rule changes.

Two non-overlapping Waka regions (.01,.08) train the same 192/144/96 probability
network; .05 is held out. Every held-out modeled symbol is scored. Matched SZ3
receives the identical 16x128 held-out samples and epsilon.

Ideal probability-rate diagnostic only: learned weights are not serialized or
charged and the arithmetic stream is not materialized.
"""
from __future__ import annotations
import argparse,json,math,gc
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

DATASET='marine_waka_3d';TRAIN_FRACS=(.01,.08);TEST_FRAC=.05
NY=16;NX=128;WINDOWS=(60000,120000,240000);MAX_PER_TILE=180000
EPOCHS=7;HEADER_BYTES=128;HIDDEN=(192,144,96);SEED=20260819
DIST=(4,8,16,32)
DIRECT_REF_BPS=0.914296875
DIRECT_REF_GAIN=1.5792019140391353

def extract(manifest,epsj,frac):
    r=large.r;ds=next(d for d in manifest['datasets'] if d['id']==DATASET);eps=float(epsj['datasets'][DATASET]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
    rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
    try:
        s=r.SegySequential(rr)
        if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('fixed stride required',s.ns_policy))
        total=int(s.total_traces);center=int(round(float(frac)*max(0,total-1)));chosen=None
        for window in WINDOWS:
            st=max(0,min(max(0,total-window),center-window//2));n=min(window,total-st);H=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(H);seg=[(a+st,z+st) for a,z in geom['segments']];rows=[q for q in seg if q[1]-q[0]>=NX]
            if len(rows)<NY:continue
            cc=[]
            for i in range(len(rows)-NY+1):
                block=rows[i:i+NY];mid=.5*(block[0][0]+block[-1][1]);cc.append((abs(mid-center),i,block))
            _,gi,block=min(cc,key=lambda z:(z[0],z[1]));chosen=(window,geom,gi,block,min(z-a for a,z in block),len(rows));break
        if chosen is None:raise RuntimeError(('no native 16x128 tile',frac,WINDOWS))
        window,geom,gi,block,minlen,nrows=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX)
        md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(nrows),'location_selection_uses_sample_values':False};print('LR_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()

def state(X,eps):
    step=2*float(eps)*.9999;X=np.asarray(X,np.float64);ny,nx,nt=X.shape;R=np.empty(X.shape,np.int32);Y=np.empty(X.shape,np.float64)
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
                q=int(np.rint((X[y,x,t]-p)/step));R[y,x,t]=q;Y[y,x,t]=p+q*step
    return Y/step,R

def nmodeled(shape):return int(shape[0]*(shape[1]-1)*(shape[2]-b.RAD-15))

def feature_batch(S,R,flat):
    ny,nx,nt=S.shape;ntm=nt-b.RAD-15;flat=np.asarray(flat,np.int64);q0=flat//ntm;t=14+(flat%ntm);x=1+(q0%(nx-1));y=q0//(nx-1);cols=[]
    prev=S[y,x,t-1]
    for o in range(-10,0):cols.append(S[y,x,t+o]-prev)
    x2=np.where(x>1,x-2,x-1);ym=np.maximum(y-1,0);has=(y>0)
    def wave(kind,o):
        if kind==0:return S[y,x-1,t+o]
        if kind==1:return S[y,x2,t+o]
        if kind==2:return np.where(has,S[ym,x,t+o],0.)
        return np.where(has,S[ym,x-1,t+o],0.)
    centers=[wave(k,0) for k in range(4)]
    for k in range(4):
        c=centers[k]
        for o in range(-b.RAD,b.RAD+1):cols.append(wave(k,o)-c)
    def resid(kind,o):
        if kind==0:return R[y,x-1,t+o]
        if kind==1:return R[y,x2,t+o]
        if kind==2:return np.where(has,R[ym,x,t+o],0)
        return np.where(has,R[ym,x-1,t+o],0)
    for k in range(4):
        for o in range(-b.RAD,b.RAD+1):cols.append(resid(k,o))
    for o in range(-b.HIST,0):cols.append(R[y,x,t+o])
    l,l2,u,ul=centers;cols += [l,l2,u,ul,l-l2,l-u,S[y,x,t-1]-S[y,x-1,t-1],S[y,x,t-1]-np.where(has,S[ym,x,t-1],0.)]
    # New information only: distant already-decoded trace waveform shapes.
    # Use the same +/-RAD local waveform window, centered on each distant trace,
    # plus availability and relation to the immediate left waveform.
    for d in DIST:
        avail=(x>=d);xd=np.maximum(0,x-d);c=S[y,xd,t]
        for o in range(-b.RAD,b.RAD+1):cols.append(np.where(avail,S[y,xd,t+o]-c,0.))
        cols.append(avail.astype(np.float64));cols.append(np.where(avail,c-l,0.));cols.append(np.where(avail,S[y,xd,t-1]-S[y,x-1,t-1],0.))
    return np.stack(cols,axis=1).astype(np.float32,copy=False),R[y,x,t].astype(np.int32,copy=False)

def train_features(X,eps):
    S,R=state(X,eps);n=nmodeled(X.shape);take=min(MAX_PER_TILE,n);ii=np.linspace(0,n-1,take,dtype=np.int64);A,T=feature_batch(S,R,ii);cnt=np.bincount(b.cls(R.reshape(-1)),minlength=b.NCLASS).astype(np.float64);del S,R;gc.collect();return A,T,cnt

def fit(train_tiles,eps):
    import torch,torch.nn as nn,torch.nn.functional as F
    AA=[];TT=[];cnt=np.zeros(b.NCLASS,np.float64)
    for i,X in enumerate(train_tiles):A,T,c=train_features(X,eps);AA.append(A);TT.append(T);cnt+=c;print('LR_TRAIN',i,A.shape,flush=True)
    A=np.concatenate(AA);T=np.concatenate(TT);del AA,TT;gc.collect();mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T);cnt+=1.;static=-np.log2(cnt/cnt.sum())
    class M(nn.Module):
        def __init__(self,d):super().__init__();h1,h2,h3=HIDDEN;self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(SEED);np.random.seed(SEED);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for s in range(0,len(perm),bs):j=perm[s:s+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('LR_FIT',ep,tot/len(Xt),flush=True)
    return net,mu,sd,static

def score(net,mu,sd,static,X,eps):
    import torch,torch.nn.functional as F
    S,R=state(X,eps);n=nmodeled(X.shape);bits=0.;tail=0.;batch=16384;net.eval()
    with torch.no_grad():
        for s in range(0,n,batch):
            ii=np.arange(s,min(n,s+batch),dtype=np.int64);A,T=feature_batch(S,R,ii);xx=torch.from_numpy((A-mu)/sd);yy=torch.from_numpy(b.cls(T));lp=F.log_softmax(net(xx),1)/math.log(2);bits+=float((-lp[torch.arange(len(yy)),yy]).sum());tail+=float(b.gamma_bits(np.maximum(np.abs(T)-b.LIM,0)).sum())
    mask=np.zeros(R.shape,bool);mask[:,1:,14:R.shape[2]-b.RAD-1]=True;rb=R[~mask];boundary=float(static[b.cls(rb)].sum()+b.gamma_bits(np.maximum(np.abs(rb)-b.LIM,0)).sum());total=bits+tail+boundary;sb,sme=matched_sz3(X,eps);ours=int(math.ceil(total/8))+HEADER_BYTES;ns=int(X.size);del S,R;gc.collect()
    return {'shape':list(map(int,X.shape)),'samples':ns,'feature_dim':int(len(mu)),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/ns),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/ns),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/ns),'gap_to_2x_bps':float(8*ours/ns-4*sb/ns),'boundary_bps':float(boundary/ns),'crosses_2x_ideal':bool(sb/ours>=2.0),'sz3_maxerr':float(sme),'model_weights_charged':False,'serialized_arithmetic_stream':False}

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw=[];meta=[];ep=None
    for f in TRAIN_FRACS+(TEST_FRAC,):X,ep,md=extract(m,e,f);raw.append(X);meta.append(md)
    ranges=[(z['trace_first'],z['trace_last']) for z in meta]
    for i in range(len(ranges)):
        for j in range(i):
            if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]):raise RuntimeError(('training/test overlap',i,j,ranges))
    net,mu,sd,static=fit(raw[:2],ep);res=score(net,mu,sd,static,raw[2],ep)
    out={'kind':'waka-16x128-longrange-causal-waveform-context-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','dataset':DATASET,'epsilon':float(ep),'training_fractions':list(TRAIN_FRACS),'test_fraction':TEST_FRAC,'locations':meta,'all_regions_nonoverlapping':True,'longrange_distances':list(DIST),'residual_representation_changed':False,'future_information_used':False,'result':res,'frozen_direct_16x128_reference':{'ideal_bps':DIRECT_REF_BPS,'gain_vs_sz3_ideal':DIRECT_REF_GAIN,'source_run':32273953927},'improvement_bps_vs_direct_reference':float(DIRECT_REF_BPS-res['ideal_bps']),'gain_ratio_vs_direct_reference':float(res['gain_vs_sz3_ideal']/DIRECT_REF_GAIN),'note':'Only causal probability features change. Direct predictor/quantizer/residual lattice and held-out samples are identical to the frozen 16x128 reference. Ideal rate only.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('LR_FINAL',json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
