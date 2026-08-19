#!/usr/bin/env python3
"""Deep 128-trace bilateral hierarchy diagnostic on native 16x128 Waka.

The direct 16x128 gate showed that SZ3 gains far more than our left-to-right
probability coder from horizontal width. This experiment attacks that measured
failure directly. For every row, decode only x=0 and x=127 as coarse anchors,
then recursively decode interval midpoints. Each midpoint is predicted from the
two already-decoded interval endpoints plus its own decoded temporal history.
Thus almost the whole 128-trace row receives legal two-sided spatial context;
no future sample is read by the decoder and no per-trace selector is transmitted.

Two non-overlapping Waka regions (.01,.08) fit a fixed hierarchy-aware probability
model. The .05 region is held out. Locations use SEG-Y headers only. Matched SZ3
receives the identical 16x128 held-out samples and epsilon.

Ideal probability-rate diagnostic only: learned probability weights/static tables
are not serialized or charged, and the arithmetic stream is not materialized.
"""
from __future__ import annotations
import argparse,json,math,gc
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_crosssurvey_prob_screen as b
from general_seismic_numeric_io import matched_sz3

DATASET='marine_waka_3d';TRAIN_FRACS=(.01,.08);TEST_FRAC=.05
NY=16;NX=128;WINDOWS=(60000,120000,240000);MAX_PER_TILE=180000;EPOCHS=7
HEADER_BYTES=128;HIDDEN=(192,144,96);SEED=20260819

def hierarchy(nx):
    xs=[];ls=[];rs=[];alphas=[];levs=[];cur=[(0,nx-1)];lev=0
    while cur:
        nxt=[]
        for l,r in cur:
            if r-l<=1:continue
            m=(l+r)//2;a=(m-l)/(r-l);xs.append(m);ls.append(l);rs.append(r);alphas.append(a);levs.append(lev)
            if m-l>1:nxt.append((l,m))
            if r-m>1:nxt.append((m,r))
        cur=nxt;lev+=1
    if len(xs)!=nx-2 or len(set(xs))!=nx-2:raise RuntimeError(('bad hierarchy',nx,len(xs)))
    return np.asarray(xs,np.int16),np.asarray(ls,np.int16),np.asarray(rs,np.int16),np.asarray(alphas,np.float64),np.asarray(levs,np.int8),lev
XS,LS,RS,ALPHAS,LEVS,NLEVEL=hierarchy(NX)
TOPO=np.zeros(NX,np.int8)
for x,l in zip(XS,LEVS):TOPO[int(x)]=int(l)+1

def extract(manifest,epsj,frac):
    r=large.r;ds=next(d for d in manifest['datasets'] if d['id']==DATASET);eps=float(epsj['datasets'][DATASET]['epsilon']);oo=[r.obj(u) for u in ds['objects']];rr=r.S3ConcatSequential(r.S3,oo,block_bytes=8*1024*1024)
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
        if chosen is None:raise RuntimeError(('no native 16x128 hierarchy tile',frac,WINDOWS))
        window,geom,gi,block,minlen,nrows=chosen;X,ids=large.read_tile(rr,s,block,minlen,NX);md={'fraction':float(frac),'geometry_mode':geom['mode'],'group_index':int(gi),'trace_first':int(ids[0]),'trace_last':int(ids[-1]),'shape':list(map(int,X.shape)),'header_window':int(window),'valid_rows_in_window':int(nrows),'location_selection_uses_sample_values':False};print('HIER_RAW',json.dumps(md),flush=True);return np.ascontiguousarray(X),eps,md
    finally:rr.close()

def state(X,eps):
    step=2*float(eps)*.9999;X=np.asarray(X,np.float64);ny,nx,nt=X.shape;Y=np.empty(X.shape,np.float64);R=np.empty(X.shape,np.int32)
    for y in range(ny):
        # Two sparse endpoints are the only horizontal anchors.
        for x in (0,nx-1):
            for t in range(nt):
                if y>0:p=b.A*Y[y-1,x,t]+(Y[y,x,t-1]-b.A*Y[y-1,x,t-1] if t else 0.)
                elif t:p=Y[y,x,t-1]
                else:p=0.
                q=int(np.rint((X[y,x,t]-p)/step));R[y,x,t]=q;Y[y,x,t]=p+q*step
        for x,l,r,a in zip(XS,LS,RS,ALPHAS):
            x=int(x);l=int(l);r=int(r);a=float(a)
            for t in range(nt):
                sp=(1-a)*Y[y,l,t]+a*Y[y,r,t];ps=((1-a)*Y[y,l,t-1]+a*Y[y,r,t-1]) if t else 0.
                p=b.A*sp+(Y[y,x,t-1]-b.A*ps if t else 0.)
                q=int(np.rint((X[y,x,t]-p)/step));R[y,x,t]=q;Y[y,x,t]=p+q*step
    return Y/step,R

def nmodeled(shape):return int(shape[0]*len(XS)*(shape[2]-b.RAD-15))
def coords(flat,nt):
    ntm=nt-b.RAD-15;flat=np.asarray(flat,np.int64);q0=flat//ntm;t=14+(flat%ntm);pi=q0%len(XS);y=q0//len(XS);return y,pi,t

def features(S,R,flat):
    ny,nx,nt=S.shape;y,pi,t=coords(flat,nt);x=XS[pi].astype(np.int64);l=LS[pi].astype(np.int64);r=RS[pi].astype(np.int64);a=ALPHAS[pi];lev=LEVS[pi].astype(np.float32);ym=np.maximum(y-1,0);has=(y>0);cols=[]
    prev=S[y,x,t-1]
    for o in range(-10,0):cols.append(S[y,x,t+o]-prev)
    def wav(k,o):
        if k==0:return S[y,l,t+o]
        if k==1:return S[y,r,t+o]
        if k==2:return np.where(has,S[ym,x,t+o],0.)
        return np.where(has,(1-a)*S[ym,l,t+o]+a*S[ym,r,t+o],0.)
    centers=[wav(k,0) for k in range(4)]
    for k in range(4):
        c=centers[k]
        for o in range(-b.RAD,b.RAD+1):cols.append(wav(k,o)-c)
    def res(k,o):
        if k==0:return R[y,l,t+o]
        if k==1:return R[y,r,t+o]
        if k==2:return np.where(has,R[ym,x,t+o],0)
        return np.where(has,(1-a)*R[ym,l,t+o]+a*R[ym,r,t+o],0.)
    for k in range(4):
        for o in range(-b.RAD,b.RAD+1):cols.append(res(k,o))
    for o in range(-b.HIST,0):cols.append(R[y,x,t+o])
    interp=(1-a)*centers[0]+a*centers[1];interp_prev=(1-a)*S[y,l,t-1]+a*S[y,r,t-1]
    span=(r-l).astype(np.float32);cols += [centers[0],centers[1],centers[2],interp,centers[1]-centers[0],prev-interp_prev,a.astype(np.float32),np.log2(span).astype(np.float32)/7.0,lev/max(1,NLEVEL-1),has.astype(np.float32)]
    return np.stack(cols,axis=1).astype(np.float32,copy=False),R[y,x,t].astype(np.int32,copy=False),lev.astype(np.int64)

def static_counts(R):
    out=np.ones((NLEVEL+1,b.NCLASS),np.float64)
    for x in range(NX):out[int(TOPO[x])]+=np.bincount(b.cls(R[:,x,:].reshape(-1)),minlength=b.NCLASS)
    return out

def train_features(X,eps):
    S,R=state(X,eps);n=nmodeled(X.shape);take=min(MAX_PER_TILE,n);ii=np.linspace(0,n-1,take,dtype=np.int64);A,T,L=features(S,R,ii);C=static_counts(R);del S,R;gc.collect();return A,T,L,C

def fit(train_tiles,eps):
    import torch,torch.nn as nn,torch.nn.functional as F
    AA=[];TT=[];CC=np.zeros((NLEVEL+1,b.NCLASS),np.float64)
    for i,X in enumerate(train_tiles):A,T,L,C=train_features(X,eps);AA.append(A);TT.append(T);CC+=C;print('HIER_TRAIN',i,A.shape,flush=True)
    A=np.concatenate(AA);T=np.concatenate(TT);del AA,TT;gc.collect();mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=b.cls(T);static=-np.log2(CC/CC.sum(1,keepdims=True))
    class M(nn.Module):
        def __init__(self,d):super().__init__();h1,h2,h3=HIDDEN;self.net=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU(),nn.Linear(h3,b.NCLASS))
        def forward(self,x):return self.net(x)
    torch.manual_seed(SEED);np.random.seed(SEED);torch.set_num_threads(min(8,torch.get_num_threads()));net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=2e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for s in range(0,len(perm),bs):j=perm[s:s+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('HIER_FIT',ep,tot/len(Xt),flush=True)
    return net,mu,sd,static

def score(net,mu,sd,static,X,eps):
    import torch,torch.nn.functional as F
    S,R=state(X,eps);n=nmodeled(X.shape);batch=16384;mode_bits=0.;level_bits=np.zeros(NLEVEL,np.float64);level_n=np.zeros(NLEVEL,np.int64);net.eval()
    with torch.no_grad():
        for s in range(0,n,batch):
            ii=np.arange(s,min(n,s+batch),dtype=np.int64);A,T,L=features(S,R,ii);xx=torch.from_numpy((A-mu)/sd);yy=torch.from_numpy(b.cls(T));lp=F.log_softmax(net(xx),1)/math.log(2);cost=(-lp[torch.arange(len(yy)),yy]).cpu().numpy()+b.gamma_bits(np.maximum(np.abs(T)-b.LIM,0));mode_bits+=float(cost.sum())
            for lv in np.unique(L):m=(L==lv);level_bits[int(lv)]+=float(cost[m].sum());level_n[int(lv)]+=int(m.sum())
    # Charge anchors completely, and temporal boundaries of every midpoint, with training-only topology distributions.
    boundary=0.
    stop=R.shape[2]-b.RAD-1
    for x in range(NX):
        topo=int(TOPO[x]);vals=R[:,x,:] if topo==0 else np.concatenate((R[:,x,:14],R[:,x,stop:]),axis=1)
        boundary+=float(static[topo,b.cls(vals.reshape(-1))].sum()+b.gamma_bits(np.maximum(np.abs(vals.reshape(-1))-b.LIM,0)).sum())
    total=mode_bits+boundary;sb,sme=matched_sz3(X,eps);ours=int(math.ceil(total/8))+HEADER_BYTES;ns=int(X.size)
    levels=[{'level':int(i),'modeled_samples':int(level_n[i]),'modeled_bps':float(level_bits[i]/max(1,level_n[i])),'trace_count':int(np.sum(LEVS==i))} for i in range(NLEVEL)]
    return {'shape':list(map(int,X.shape)),'samples':ns,'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/ns),'sz3_bytes':int(sb),'sz3_bps':float(8*sb/ns),'gain_vs_sz3_ideal':float(sb/ours),'two_x_target_bps':float(4*sb/ns),'gap_to_2x_bps':float(8*ours/ns-4*sb/ns),'boundary_bps':float(boundary/ns),'crosses_2x_ideal':bool(sb/ours>=2.0),'levels':levels,'anchor_trace_fraction':float(2/NX),'sz3_maxerr':float(sme),'model_weights_charged':False,'serialized_arithmetic_stream':False}

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));raw=[];meta=[];ep=None
    for f in TRAIN_FRACS+(TEST_FRAC,):X,ep,md=extract(m,e,f);raw.append(X);meta.append(md)
    ranges=[(z['trace_first'],z['trace_last']) for z in meta]
    for i in range(len(ranges)):
        for j in range(i):
            if max(ranges[i][0],ranges[j][0])<=min(ranges[i][1],ranges[j][1]):raise RuntimeError(('training/test overlap',i,j,ranges))
    net,mu,sd,static=fit(raw[:2],ep);res=score(net,mu,sd,static,raw[2],ep)
    out={'kind':'waka-16x128-deep-bilateral-hierarchy-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','dataset':DATASET,'epsilon':float(ep),'training_fractions':list(TRAIN_FRACS),'test_fraction':TEST_FRAC,'locations':meta,'all_regions_nonoverlapping':True,'hierarchy_levels':int(NLEVEL),'midpoint_trace_counts':[int(np.sum(LEVS==i)) for i in range(NLEVEL)],'anchors':[0,NX-1],'midpoint_predictor':'linear interpolation of two already-decoded interval endpoints plus current trace temporal correction','future_information_used':False,'result':res,'frozen_direct_16x128_reference':{'ideal_bps':0.914296875,'gain_vs_sz3_ideal':1.5792019140391353,'source_run':32273953927},'improvement_bps_vs_direct_reference':float(0.914296875-res['ideal_bps']),'crosses_2x':bool(res['gain_vs_sz3_ideal']>=2.0),'note':'Ideal rate only. Hierarchy order and endpoint identities are structural and require no selector stream. Learned probability/static model weights are not charged.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('HIER_FINAL',json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
