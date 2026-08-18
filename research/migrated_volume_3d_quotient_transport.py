#!/usr/bin/env python3
"""Self-synchronizing quotient/transport predictor for migrated seismic volumes.

Hypothesis
----------
Much of the apparent spatial innovation in a migrated cube is not new amplitude
information; it is an already-seen waveform transported in time/depth, mildly
rescaled, and offset. A point predictor therefore manufactures a dense residual
when reflectors dip or warp between neighboring traces.

This experiment quotients out that nuisance transformation. For each temporal
segment of a trace, encoder and decoder independently infer the SAME transport
model from already reconstructed history only:
  * choose an already decoded fast- or slow-axis neighboring trace;
  * choose an integer time/depth lag from a fixed symmetric menu;
  * infer a small frozen amplitude scale and an affine offset;
  * optionally mix transported prediction with the current trace's causal
    previous sample.

Crucially, the transport choices are NOT serialized. They are functions only of
previously reconstructed samples, so the decoder re-derives the local warp field
for free. Only the hard-error-bounded quantized innovation is coded.

This is a research gate, not a production claim. If it cannot substantially
reduce innovation activity/entropy, the quotient-field hypothesis is rejected.
"""
from __future__ import annotations
import math, struct
from collections import Counter
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

MAGIC=b"MVQTR001"
HDR="<8sddIIIHHI"
HSZ=struct.calcsize(HDR)
SEGMENT=96
LAG_MAX=12
SCALES=np.asarray((0.625,0.75,0.875,1.0,1.125,1.25,1.375),np.float64)
MIXES=np.asarray((0.75,1.0),np.float64)
MIN_FIT=16
# Require a real historical improvement before enabling transport; otherwise
# use the robust temporal fallback for the next segment.
TRANSPORT_GATE=0.985


def _entropy_bits(R):
    _,cnt=np.unique(np.asarray(R,np.int32),return_counts=True)
    p=cnt.astype(np.float64)/float(np.sum(cnt))
    return float(-np.sum(p*np.log2(p)))


def _choose_model(Y,y,x,t0,segment,lag_max):
    """Infer next-segment model from PREVIOUS reconstructed segment only.

    Return None for temporal fallback, otherwise
    (source, lag, scale, mix, offset, train_mae, temporal_mae).
    source 0 = fast-axis predecessor, 1 = slow-axis predecessor.
    """
    if t0 < segment or (x<=0 and y<=0):
        return None
    h0=max(0,int(t0)-int(segment));h1=int(t0)
    cur=np.asarray(Y[y,x,h0:h1],np.float64)
    if cur.size<MIN_FIT:
        return None
    temporal=float(np.mean(np.abs(cur[1:]-cur[:-1]))) if cur.size>1 else float('inf')
    if not np.isfinite(temporal) or temporal<=1e-30:
        return None
    sources=[]
    if x>0:sources.append((0,Y[y,x-1]))
    if y>0:sources.append((1,Y[y-1,x]))
    base=np.arange(h0,h1,dtype=np.int64)
    best=None;best_score=float('inf')
    for src,N in sources:
        N=np.asarray(N,np.float64)
        for lag in range(-int(lag_max),int(lag_max)+1):
            jj=base-int(lag);good=(jj>=0)&(jj<N.size)
            ids=np.flatnonzero(good)
            if ids.size<MIN_FIT:continue
            cc=cur[ids];nn=N[jj[ids]]
            cm=float(np.mean(cc));nm=float(np.mean(nn));dn=nn-nm;dc=cc-cm
            den=float(np.dot(dn,dn))
            raw_a=1.0 if den<=1e-30 else float(np.dot(dc,dn)/den)
            a=float(SCALES[int(np.argmin(np.abs(SCALES-raw_a)))])
            b=float(cm-a*nm)
            # Score only points whose previous current sample is also in the
            # historical fit region, matching the causal mixture used forward.
            valid=ids[ids>0]
            if valid.size<MIN_FIT:continue
            valid=valid[good[valid-1]]
            if valid.size<MIN_FIT:continue
            warp=a*N[base[valid]-int(lag)]+b
            prev=cur[valid-1]
            truth=cur[valid]
            for mix in MIXES:
                mm=float(mix);pred=mm*warp+(1.0-mm)*prev
                score=float(np.mean(np.abs(truth-pred)))
                if score<best_score:
                    best_score=score;best=(int(src),int(lag),a,mm,b,score,temporal)
    if best is None or best_score>=TRANSPORT_GATE*temporal:
        return None
    return best


def _predict_one(Y,y,x,t,model):
    if model is None:
        if t>0:return float(Y[y,x,t-1])
        if x>0:return float(Y[y,x-1,t])
        if y>0:return float(Y[y-1,x,t])
        return 0.0
    src,lag,a,mix,b,_score,_temporal=model
    N=Y[y,x-1] if src==0 else Y[y-1,x]
    j=int(t)-int(lag)
    if 0<=j<N.size:
        warp=float(a)*float(N[j])+float(b)
        prev=float(Y[y,x,t-1]) if t>0 else warp
        return float(mix)*warp+(1.0-float(mix))*prev
    return float(Y[y,x,t-1]) if t>0 else 0.0


def forward(X,eps,segment=SEGMENT,lag_max=LAG_MAX):
    X=np.asarray(X,np.float64)
    if X.ndim!=3:raise ValueError(X.shape)
    ny,nx,nt=X.shape;internal=float(eps)*float(c.MARGIN);step=2.0*internal
    R=np.empty((ny,nx,nt),np.int32);Y=np.empty((ny,nx,nt),np.float64)
    source=Counter();lags=Counter();scales=Counter();mixes=Counter();used=0;fallback=0;fit_improve=[]
    for y in range(ny):
        for x in range(nx):
            for t0 in range(0,nt,int(segment)):
                model=_choose_model(Y,y,x,t0,segment,lag_max)
                if model is None:fallback+=1
                else:
                    used+=1;src,lag,a,mix,_b,score,temp=model
                    source['fast' if src==0 else 'slow']+=1;lags[str(lag)]+=1;scales[f'{a:g}']+=1;mixes[f'{mix:g}']+=1
                    fit_improve.append(float(temp/max(score,1e-30)))
                t1=min(nt,t0+int(segment))
                for t in range(t0,t1):
                    pred=_predict_one(Y,y,x,t,model)
                    q=int(np.rint((float(X[y,x,t])-pred)/step))
                    if q<np.iinfo(np.int32).min or q>np.iinfo(np.int32).max:raise OverflowError('transport residual int32')
                    R[y,x,t]=q;Y[y,x,t]=pred+float(q)*step
    diag={
        'segment':int(segment),'lag_max':int(lag_max),'segments_transport':int(used),'segments_fallback':int(fallback),
        'transport_fraction':float(used/max(1,used+fallback)),'source_counts':dict(source),'lag_counts':dict(lags),
        'scale_counts':dict(scales),'mix_counts':dict(mixes),
        'median_historical_fit_improvement':float(np.median(fit_improve)) if fit_improve else 1.0,
        'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),
        'residual_entropy_bits_per_sample':_entropy_bits(R),
        'encoder_reconstruction_maxerr':float(c.hard(X,Y)),
    }
    return R,Y,internal,diag


def inverse(R,internal,segment=SEGMENT,lag_max=LAG_MAX):
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;step=2.0*float(internal)
    Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
        for x in range(nx):
            for t0 in range(0,nt,int(segment)):
                model=_choose_model(Y,y,x,t0,segment,lag_max)
                t1=min(nt,t0+int(segment))
                for t in range(t0,t1):
                    pred=_predict_one(Y,y,x,t,model)
                    Y[y,x,t]=pred+float(R[y,x,t])*step
    return Y


def encode(X,eps,segment=SEGMENT,lag_max=LAG_MAX):
    R,Y,internal,diag=forward(X,eps,segment,lag_max)
    payload,nbp=pq._pack_bitplanes(R)
    ny,nx,nt=R.shape
    hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),int(ny),int(nx),int(nt),int(segment),int(lag_max),len(payload))
    blob=hdr+payload
    diag.update({'payload_bytes':len(payload),'header_bytes':HSZ,'container_bytes':len(blob),'bitplanes':int(nbp),'side_map_bytes':0,'model':'self_synchronizing_affine_transport'})
    return blob,diag


def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short quotient transport stream')
    magic,eps,internal,ny,nx,nt,segment,lag_max,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC:raise RuntimeError('bad quotient transport magic')
    if len(blob)!=HSZ+int(npay):raise RuntimeError(('transport length',len(blob),HSZ,npay))
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)))
    Y=inverse(R,float(internal),int(segment),int(lag_max))
    return Y,{'shape':[int(ny),int(nx),int(nt)],'eps':float(eps),'segment':int(segment),'lag_max':int(lag_max),'model':'self_synchronizing_affine_transport'}


def sanity():
    rng=np.random.default_rng(20260818);ny,nx,nt=3,12,577;t=np.arange(nt,dtype=np.float64)
    base=70*np.sin(t/19.0)+23*np.sin(t/6.3)+8*np.sin(t/41.0)
    X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):
            shift=2*x+y
            X[y,x]=(np.roll(base,shift)*(1.0+0.015*x)+3*y+rng.normal(0,1.2,nt)).astype(np.float32)
    eps=3.0;b,d=encode(X,eps);Y,m=decode(b);me=float(c.hard(X,Y))
    if me>eps*(1+3e-6):raise RuntimeError(('transport sanity hard',me,eps))
    # Encoder and decoder must reproduce the exact same floating reconstruction
    # in this reference implementation.
    R,Ye,_,_=forward(X,eps)
    if not np.array_equal(Y,Ye):raise RuntimeError(('transport replay mismatch',float(np.max(np.abs(Y-Ye)))))
    print('MV_QUOTIENT_TRANSPORT_SANITY_OK',{'bytes':len(b),'nonzero':d['nonzero_fraction'],'entropy':d['residual_entropy_bits_per_sample'],'maxerr':me},flush=True)

if __name__=='__main__':sanity()
