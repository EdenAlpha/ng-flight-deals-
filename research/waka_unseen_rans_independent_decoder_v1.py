#!/usr/bin/env python3
"""Independent probability-regenerating decoder gate on one unseen Waka block.

This is the next promotion step after the finite-CDF rANS gate.  Encoder and
decoder begin from identical source-trained model weights but do NOT share target
CDFs.  Each side independently derives causal features from its own residual /
reconstructed-waveform state, evaluates the neural probability models one symbol
at a time, quantizes to the same 15-bit CDF, and applies the same 1024-symbol
post-charge model update schedule.  The decoder receives only the rANS byte stream
and frozen model/normalization state.  A single CDF divergence should corrupt the
stream, so exact residual and reconstructed-sample checks are strict.

The first promotion gate deliberately uses only the first charged Waka 16x32
position (fraction .15) to validate mechanics before scaling the independent
decoder to the complete multi-position stream.
"""
from __future__ import annotations
import argparse,copy,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import waka_unseen_fast_boundary_mlp_v1 as bm
import waka_unseen_boundary_mlp_rans_v1 as rr

TARGET_FRAC=.15
HEADER_BYTES=128


def class_of(v):
    v=int(v);return 17 if v<-q.b.LIM else (18 if v>q.b.LIM else v+q.b.LIM)


def predict_s(S,y,x,t):
    if x>0:
        if y>0:
            sp=q.b.W*S[y,x-1,t]+(1-q.b.W)*S[y-1,x,t]
            ps=q.b.W*S[y,x-1,t-1]+(1-q.b.W)*S[y-1,x,t-1] if t else 0.
        else:
            sp=S[y,x-1,t];ps=S[y,x-1,t-1] if t else 0.
        return q.b.A*sp+(S[y,x,t-1]-q.b.A*ps if t else 0.)
    if y>0:return q.b.A*S[y-1,x,t]+(S[y,x,t-1]-q.b.A*S[y-1,x,t-1] if t else 0.)
    if t:return S[y,x,t-1]
    return 0.


def state_from_residuals(R):
    R=np.asarray(R);S=np.zeros(R.shape,np.float64);ny,nx,nt=R.shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):S[y,x,t]=predict_s(S,y,x,t)+int(R[y,x,t])
    return S


def pad_window(z,t,r=q.b.RAD):
    n=len(z);a=t-r;b=t+r+1;o=np.zeros(2*r+1,np.float64);aa=max(0,a);bb=min(n,b);o[aa-a:bb-a]=z[aa:bb];return o


def centered_history(z,t,n):
    o=np.zeros(n,np.float64);a=max(0,t-n);v=np.asarray(z[a:t],np.float64);o[n-len(v):]=v
    if len(v):o-=v[-1]
    return o


def boundary_feature(S,R,y,x,t):
    nt=S.shape[2];Z=np.zeros(nt,np.float64);cur=S[y,x];cr=R[y,x]
    l=S[y,x-1] if x else Z;lr=R[y,x-1] if x else Z
    u=S[y-1,x] if y else Z;ur=R[y-1,x] if y else Z
    ul=S[y-1,x-1] if y and x else Z;ulr=R[y-1,x-1] if y and x else Z
    f=[];f.extend(centered_history(cur,t,q.b.HIST).tolist());f.extend(centered_history(cr,t,q.b.HIST).tolist())
    for z in (l,u,ul):
        w=pad_window(z,t);f.extend((w-z[t]).tolist())
    for z in (lr,ur,ulr):f.extend(pad_window(z,t).tolist())
    x0=1.0 if x==0 else 0.0;st=1.0 if x>0 and t<14 else 0.0;en=1.0 if x>0 and t>=nt-q.b.RAD-1 else 0.0
    f += [float(cur[t-1]) if t else 0.,float(l[t]),float(u[t]),float(ul[t]),float(cur[t-1]-l[t-1]) if t and x else 0.,float(cur[t-1]-u[t-1]) if t and y else 0.,x0,st,en,t/13.0 if st else 0.0,(t-(nt-q.b.RAD-1))/q.b.RAD if en else 0.0,1.0 if y==0 else 0.0,min(y,15)/15.0]
    return np.asarray(f,np.float32)


def main_feature(S,R,y,x,t):
    nt=S.shape[2];Z=np.zeros(nt,np.float64);cur=S[y,x];cr=R[y,x]
    l=S[y,x-1];l2=S[y,x-2] if x>1 else l;u=S[y-1,x] if y else Z;ul=S[y-1,x-1] if y else Z
    lr=R[y,x-1];l2r=R[y,x-2] if x>1 else lr;ur=R[y-1,x] if y else Z;ulr=R[y-1,x-1] if y else Z
    f=[];f.extend((cur[t-10:t]-cur[t-1]).tolist())
    for z in (l,l2,u,ul):f.extend((z[t-q.b.RAD:t+q.b.RAD+1]-z[t]).tolist())
    for z in (lr,l2r,ur,ulr):f.extend(np.asarray(z[t-q.b.RAD:t+q.b.RAD+1],np.float64).tolist())
    f.extend(np.asarray(cr[t-q.b.HIST:t],np.float64).tolist());f += [float(l[t]),float(l2[t]),float(u[t]),float(ul[t]),float(l[t]-l2[t]),float(l[t]-u[t]),float(cur[t-1]-l[t-1]),float(cur[t-1]-u[t-1])]
    return np.asarray(f,np.float32)


def single_cdf(model,feature,mu=None,sd=None):
    x=feature if mu is None else (feature-mu)/sd
    with torch.no_grad():p=torch.softmax(model(torch.from_numpy(np.asarray(x,np.float32))[None,:]),1).cpu().numpy()
    return rr.quantized_cdfs(p)[0]


def push_class_events(starts,freqs,cdf,raw):
    c=class_of(raw);lo=int(cdf[c]);hi=int(cdf[c+1]);starts.append(lo);freqs.append(hi-lo)
    if c in (17,18):
        for bit in rr.gamma_bits_values(abs(int(raw))-q.b.LIM):starts.append(0 if bit==0 else rr.TOTAL//2);freqs.append(rr.TOTAL//2)


def decode_tail(dec,c):
    if c<=16:return c-q.b.LIM
    zeros=0
    while dec.decode(rr.BINARY_CDF)==0:zeros+=1
    v=1
    for _ in range(zeros):v=(v<<1)|dec.decode(rr.BINARY_CDF)
    return -(q.b.LIM+v) if c==17 else q.b.LIM+v


def maybe_update(net,state,features,labels,chunk_index):
    if not features:return
    X=torch.from_numpy(np.stack(features).astype(np.float32));Y=torch.tensor(labels,dtype=torch.long)
    fr._update(net,X,Y,state,fr.FIRST_CHUNK_STEPS if chunk_index==0 else fr.LATER_CHUNK_STEPS)


def encode(enet,mu,sd,R,S):
    estate,u1,u2=fr.new_adapter(120001);starts=[];freqs=[];bufF=[];bufY=[];chunk_index=0;ny,nx,nt=R.shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                raw=int(R[y,x,t]);boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1)
                if boundary:cdf=single_cdf(bm._BMODEL,boundary_feature(S,R,y,x,t),bm._BMU,bm._BSD)
                else:
                    f=main_feature(S,R,y,x,t);cdf=single_cdf(enet,f,mu,sd);bufF.append(((f-mu)/sd).astype(np.float32));bufY.append(class_of(raw))
                push_class_events(starts,freqs,cdf,raw)
                if not boundary and len(bufF)==fr.CHUNK:
                    maybe_update(enet,estate,bufF,bufY,chunk_index);bufF=[];bufY=[];chunk_index+=1
    if bufF:maybe_update(enet,estate,bufF,bufY,chunk_index)
    return rr.rans_encode(starts,freqs),estate


def decode(dnet,mu,sd,stream,shape):
    dstate,u1,u2=fr.new_adapter(120001);dec=rr.RansDecoder(stream);R=np.zeros(shape,np.int32);S=np.zeros(shape,np.float64);bufF=[];bufY=[];chunk_index=0;ny,nx,nt=shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1)
                if boundary:f=boundary_feature(S,R,y,x,t);cdf=single_cdf(bm._BMODEL,f,bm._BMU,bm._BSD)
                else:f=main_feature(S,R,y,x,t);cdf=single_cdf(dnet,f,mu,sd)
                c=dec.decode(cdf);raw=decode_tail(dec,c);R[y,x,t]=raw;S[y,x,t]=predict_s(S,y,x,t)+raw
                if not boundary:
                    bufF.append(((f-mu)/sd).astype(np.float32));bufY.append(c)
                    if len(bufF)==fr.CHUNK:
                        maybe_update(dnet,dstate,bufF,bufY,chunk_index);bufF=[];bufY=[];chunk_index+=1
    if bufF:maybe_update(dnet,dstate,bufF,bufY,chunk_index)
    if dec.pos!=-1:raise RuntimeError(('unread rANS renormalization bytes',dec.pos))
    return R,S,dstate


def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in s.SOURCE_IDS:
        for frac in s.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);source.append((s.central24(X),ep));print('INDEP_SOURCE',ds,frac,source[-1][0].shape,flush=True)
    q.crop=lambda X:np.ascontiguousarray(X);fr.CHUNK=1024
    net0,mu,sd,static=bm.patched_fit(source,20261319);enet=copy.deepcopy(net0);dnet=copy.deepcopy(net0)
    X,eps,md=s.extract_waka16(m,e,TARGET_FRAC);_,_,_,R0=q.b.build(X,eps);S0=state_from_residuals(R0)
    stream,estate=encode(enet,mu,sd,R0,S0);R1,S1,dstate=decode(dnet,mu,sd,stream,R0.shape)
    if not np.array_equal(R0,R1):
        at=np.argwhere(R0!=R1)[0];idx=tuple(map(int,at));raise RuntimeError(('independent residual decode mismatch',idx,int(R0[idx]),int(R1[idx])))
    state_diff=max(float((a-b).abs().max()) for a,b in zip(enet.parameters(),dnet.parameters()))
    step=2*float(eps)*.9999;Y=S1*step;maxerr=float(np.max(np.abs(np.asarray(X,np.float64)-Y)))
    if maxerr>float(eps)*(1+3e-6):raise RuntimeError(('reconstruction error',maxerr,eps))
    sb,sme=q.matched_sz3(X,eps);total=len(stream)+HEADER_BYTES
    out={'kind':'unseen-waka-independent-probability-regenerating-rans-decoder-v1','status':'single_block_end_to_end_prototype','dataset':s.TARGET,'fraction':TARGET_FRAC,'shape':list(map(int,X.shape)),'samples':int(X.size),'waka_used_in_probability_training':False,'decoder_reuses_encoder_cdfs':False,'decoder_receives_original_samples':False,'decoder_regenerates_main_and_boundary_probabilities':True,'decoder_updates_main_model_after_1024_decoded_interior_symbols':True,'cdf_precision_bits':rr.SCALE_BITS,'rans_payload_bytes':len(stream),'header_bytes':HEADER_BYTES,'actual_total_bytes':total,'actual_bps':float(8*total/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_actual_bytes':float(sb/total),'residual_roundtrip_exact':True,'max_reconstruction_error':maxerr,'epsilon':float(eps),'error_bound_valid':True,'encoder_decoder_model_max_parameter_difference':state_diff,'sz3_maxerr':float(sme),'important':'Independent decoder regenerates every finite CDF from its own decoded causal state; no encoder CDF sequence is reused. Single first target block only; multi-position replay/deployment and cross-platform determinism remain later gates.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('INDEPENDENT_DECODER_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
