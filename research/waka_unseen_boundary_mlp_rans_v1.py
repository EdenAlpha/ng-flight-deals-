#!/usr/bin/env python3
"""Finite-CDF real rANS stream gate for the strict unseen-Waka 2x stack.

Reproduces the source-only interior + boundary probability models from PR #711
and the 1024-symbol post-charge adaptation schedule.  Floating probabilities are
quantized to deterministic 15-bit integer CDFs.  Every residual class and every
Elias-gamma tail bit is then written to an actual byte-oriented rANS stream.
The stream is decoded immediately and the integer residual lattice must match
bit-for-bit.

This gate intentionally reuses the encoder-computed CDF sequence during the
round-trip check.  Therefore it validates finite probability quantization,
actual entropy-stream bytes, tail serialization, and rANS round-trip integrity,
but NOT yet independent decoder-side regeneration of neural probabilities.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import waka_unseen_fast_boundary_mlp_v1 as bm

SCALE_BITS=15
TOTAL=1<<SCALE_BITS
RANS_L=1<<23
HEADER_BYTES=128
BINARY_CDF=np.asarray([0,TOTAL//2,TOTAL],dtype=np.int64)
REFERENCE_IDEAL_GAIN=2.02973807935449


def class_of(v:int)->int:
    return 17 if v < -q.b.LIM else (18 if v > q.b.LIM else v+q.b.LIM)


def gamma_bits_values(v:int):
    if v<=0:raise ValueError(('gamma needs positive integer',v))
    b=bin(int(v))[2:]
    return [0]*(len(b)-1)+[1 if c=='1' else 0 for c in b]


def quantized_cdfs(probs:np.ndarray)->np.ndarray:
    """Deterministic positive frequencies summing exactly to 2^15."""
    p=np.asarray(probs,np.float64)
    f=np.maximum(1,np.floor(p*TOTAL+0.5).astype(np.int64))
    delta=TOTAL-f.sum(axis=1)
    imax=np.argmax(f,axis=1)
    f[np.arange(len(f)),imax]+=delta
    if np.any(f<=0) or np.any(f.sum(axis=1)!=TOTAL):raise RuntimeError('bad finite frequency table')
    c=np.empty((len(f),q.b.NCLASS+1),dtype=np.uint16);c[:,0]=0;c[:,1:]=np.cumsum(f,axis=1,dtype=np.int64).astype(np.uint16)
    return c


def rans_encode(starts,freqs):
    state=RANS_L;out=bytearray()
    for i in range(len(starts)-1,-1,-1):
        st=int(starts[i]);frq=int(freqs[i])
        xmax=((RANS_L>>SCALE_BITS)<<8)*frq
        while state>=xmax:
            out.append(state&255);state>>=8
        state=((state//frq)<<SCALE_BITS)+(state%frq)+st
    if state>=1<<32:raise RuntimeError(('final rANS state overflow',state))
    out+=int(state).to_bytes(4,'little')
    return bytes(out)


class RansDecoder:
    def __init__(self,data:bytes):
        if len(data)<4:raise RuntimeError('short rANS stream')
        self.data=data;self.state=int.from_bytes(data[-4:],'little');self.pos=len(data)-5
    def decode(self,cdf):
        xm=self.state&(TOTAL-1);c=np.asarray(cdf,dtype=np.int64);sym=int(np.searchsorted(c,xm,side='right')-1)
        if sym<0 or sym>=len(c)-1:raise RuntimeError(('bad decoded cumulative',xm,sym))
        st=int(c[sym]);frq=int(c[sym+1]-c[sym]);self.state=frq*(self.state>>SCALE_BITS)+(xm-st)
        while self.state<RANS_L:
            if self.pos<0:raise RuntimeError('rANS underflow')
            self.state=(self.state<<8)|self.data[self.pos];self.pos-=1
        return sym


def boundary_coords(shape):
    ny,nx,nt=shape;out=[]
    for y in range(ny):
        for t in range(nt):out.append((y,0,t))
        for x in range(1,nx):
            for t in range(14):out.append((y,x,t))
            for t in range(nt-q.b.RAD-1,nt):out.append((y,x,t))
    return out


def boundary_cdfs(R):
    A,T=bm.boundary_features_from_R(R);A=(A-bm._BMU)/bm._BSD;X=torch.from_numpy(A);parts=[];bm._BMODEL.eval()
    with torch.no_grad():
        for i in range(0,len(X),16384):parts.append(quantized_cdfs(torch.softmax(bm._BMODEL(X[i:i+16384]),1).cpu().numpy()))
    return np.concatenate(parts,axis=0),T


def prepare_main_cdfs_and_adapt(net,mu,sd,X,eps,state,reservoir,first_tile):
    A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;XE=torch.from_numpy(A);YY=torch.from_numpy(q.b.cls(T));C=np.empty((len(T),q.b.NCLASS+1),dtype=np.uint16)
    finite_class_bits=0.
    for ci,st in enumerate(range(0,len(XE),fr.CHUNK)):
        en=min(len(XE),st+fr.CHUNK);xx=XE[st:en];yy=YY[st:en];net.eval()
        with torch.no_grad():probs=torch.softmax(net(xx),1).cpu().numpy()
        cdf=quantized_cdfs(probs);C[st:en]=cdf
        y=yy.cpu().numpy();lo=cdf[np.arange(len(y)),y].astype(np.int64);hi=cdf[np.arange(len(y)),y+1].astype(np.int64);finite_class_bits+=float((-np.log2((hi-lo)/TOTAL)).sum())
        fr._update(net,xx,yy,state,fr.FIRST_CHUNK_STEPS if (first_tile and ci==0) else fr.LATER_CHUNK_STEPS)
    take=min(fr.REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>fr.REPLAY_CAP:reservoir.pop(0)
    return C,T,I,R,finite_class_bits


def encode_tile(net,mu,sd,X,eps,state,reservoir,first_tile):
    mainC,T,I,R,main_fbits=prepare_main_cdfs_and_adapt(net,mu,sd,X,eps,state,reservoir,first_tile)
    bC,bT=boundary_cdfs(R);bcoords=boundary_coords(R.shape)
    if len(bcoords)!=len(bT):raise RuntimeError(('boundary coordinate mismatch',len(bcoords),len(bT)))
    starts=[];freqs=[];finite_bits=0.;mp=0;bp=0;ny,nx,nt=R.shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                raw=int(R[y,x,t]);is_boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1)
                if is_boundary:
                    if tuple(bcoords[bp])!=(y,x,t) or int(bT[bp])!=raw:raise RuntimeError(('boundary traversal mismatch',bp,(y,x,t),bcoords[bp],raw,int(bT[bp])))
                    cdf=bC[bp];bp+=1
                else:
                    if tuple(map(int,I[mp]))!=(y,x,t) or int(T[mp])!=raw:raise RuntimeError(('interior traversal mismatch',mp,(y,x,t),tuple(map(int,I[mp])),raw,int(T[mp])))
                    cdf=mainC[mp];mp+=1
                c=class_of(raw);lo=int(cdf[c]);hi=int(cdf[c+1]);starts.append(lo);freqs.append(hi-lo);finite_bits+=-math.log2((hi-lo)/TOTAL)
                if c in (17,18):
                    excess=abs(raw)-q.b.LIM
                    for bit in gamma_bits_values(excess):starts.append(0 if bit==0 else TOTAL//2);freqs.append(TOTAL//2);finite_bits+=1.
    if mp!=len(T) or bp!=len(bT):raise RuntimeError(('stream pointers incomplete',mp,len(T),bp,len(bT)))
    stream=rans_encode(starts,freqs)
    # Decode using the exact finite CDF sequence to validate actual entropy stream and tails.
    dec=RansDecoder(stream);R2=np.empty_like(R);mp=0;bp=0
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                is_boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1);cdf=bC[bp] if is_boundary else mainC[mp]
                c=dec.decode(cdf)
                if is_boundary:bp+=1
                else:mp+=1
                if c<=16:raw=c-q.b.LIM
                else:
                    zeros=0
                    while dec.decode(BINARY_CDF)==0:zeros+=1
                    v=1
                    for _ in range(zeros):v=(v<<1)|dec.decode(BINARY_CDF)
                    raw=-(q.b.LIM+v) if c==17 else q.b.LIM+v
                R2[y,x,t]=raw
    if not np.array_equal(R,R2):
        at=np.argwhere(R!=R2)[0];idx=tuple(map(int,at));raise RuntimeError(('rANS residual roundtrip mismatch',idx,int(R[idx]),int(R2[idx])))
    if dec.pos!=-1:raise RuntimeError(('rANS unread renormalization bytes',dec.pos))
    return {'rans_payload_bytes':len(stream),'header_bytes':HEADER_BYTES,'actual_total_bytes':len(stream)+HEADER_BYTES,'actual_bps':float(8*(len(stream)+HEADER_BYTES)/R.size),'finite_cdf_ideal_bits':float(finite_bits),'finite_cdf_ideal_bps':float(finite_bits/R.size),'rans_overhead_bits_vs_finite_ideal':float(8*len(stream)-finite_bits),'residual_roundtrip_exact':True,'events':len(starts),'main_modeled_symbols':len(T),'boundary_symbols':len(bT)}


def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[];source_meta=[]
    for ds in s.SOURCE_IDS:
        for frac in s.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=s.central24(X);source.append((X,ep));source_meta.append({'dataset':ds,'fraction':float(frac),'shape':list(map(int,X.shape))});print('RANS_SOURCE',ds,frac,X.shape,flush=True)
    targets=[]
    for frac in s.TARGET_FRACS:
        X,ep,md=s.extract_waka16(m,e,frac);targets.append((X,ep,md))
    q.crop=lambda X:np.ascontiguousarray(X);fr.CHUNK=1024;fr._orig_fit=bm.patched_fit
    net,mu,sd,static=fr.fit_base(source,20261319);state,u1,u2=fr.new_adapter(98000);reservoir=[];rows=[]
    for pi,(frac,(X,ep,md)) in enumerate(zip(s.TARGET_FRACS,targets)):
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        enc=encode_tile(net,mu,sd,X,ep,state,reservoir,pi==0);sb,sme=q.matched_sz3(X,ep);enc.update({'position':pi,'fraction':float(frac),'samples':int(X.size),'sz3_bytes':int(sb),'gain_vs_sz3_actual_rans':float(sb/enc['actual_total_bytes']),'sz3_maxerr':float(sme),'shape':list(map(int,X.shape))});rows.append(enc);print('RANS_WAKA',json.dumps(enc),flush=True)
    actual_gain=float(sum(z['sz3_bytes'] for z in rows)/sum(z['actual_total_bytes'] for z in rows));samples=sum(z['samples'] for z in rows);sz=sum(z['sz3_bytes'] for z in rows);actual=sum(z['actual_total_bytes'] for z in rows)
    out={'kind':'unseen-waka-finite-cdf-real-rans-v1','status':'actual_entropy_stream_with_precomputed_cdf_decoder_check_not_full_probability-regenerating_decoder','training_datasets':list(s.SOURCE_IDS),'source_training_tiles':len(source),'waka_used_in_probability_training':False,'target_positions_all_charged':True,'adaptation_chunk':fr.CHUNK,'cdf_precision_bits':SCALE_BITS,'tails_serialized_inside_rans_as_equiprobable_gamma_bits':True,'residual_stream_roundtrip_exact':bool(all(z['residual_roundtrip_exact'] for z in rows)),'rows':rows,'actual_rans_weighted_gain_vs_sz3':actual_gain,'actual_weighted_gap_to_2x_bps':float((actual-.5*sz)*8/samples),'reference_ideal_probability_gain':REFERENCE_IDEAL_GAIN,'important':'Actual finite-CDF rANS payload bytes and exact residual-symbol roundtrip. Decoder in this gate reuses encoder-computed CDFs; independent decoder-side probability regeneration remains the next promotion gate.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('RANS_FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
