#!/usr/bin/env python3
"""Causal self-derived warp/affine predictor for migrated seismic volumes.

Core idea: adjacent traces may be the same seismic event under a local time warp
and mild amplitude/offset change.  The encoder and decoder infer that warp from
ALREADY RECONSTRUCTED history only, so no lag/warp map is transmitted.

For each spatial trace and time segment:
  * candidate references are causal completed spatial neighbours (fast/slow);
  * candidate lags are a fixed dataset-agnostic integer range;
  * the best lag/reference is chosen by past-window SSE only;
  * affine gain/offset are fitted from the same reconstructed past window;
  * the selected relation predicts the next segment.

The first segment of each trace falls back to causal temporal prediction.  All
residuals are quantized on the same legal 2*epsilon lattice and the resulting
stream is independently decodable under the hard max-error contract.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

MAGIC=b"MVWARP1\0"
HDR="<8sddIIIHHI"
HSZ=struct.calcsize(HDR)
# tid: (radius, history, segment, smooth_penalty, differential_mode)
PARAMS={
    41:(4,64,32,0.00,False),
    42:(8,96,32,0.02,False),
    43:(8,128,64,0.02,False),
    44:(8,96,32,0.02,True),
}
NAMES={
    41:"causal_warp_affine_r4_h64_s32",
    42:"causal_warp_affine_r8_h96_s32",
    43:"causal_warp_affine_r8_h128_s64",
    44:"causal_warp_differential_r8_h96_s32",
}

def _fit(x,z):
    """Stable affine z->x fit, fully determined by reconstructed history."""
    x=np.asarray(x,np.float64);z=np.asarray(z,np.float64)
    if x.size<8:return 1.0,0.0
    zm=float(z.mean());xm=float(x.mean());dz=z-zm
    den=float(np.dot(dz,dz))
    if den<=1e-24:return 0.0,xm
    a=float(np.dot(dz,x-xm)/den)
    # Clamp only for numerical robustness; fixed and dataset-agnostic.
    a=max(-2.0,min(2.0,a));b=xm-a*zm
    return a,b

def _history_pair(cur,ref,t,h,lag):
    lo=max(0,t-h);hi=t
    rlo=lo+lag;rhi=hi+lag
    if rlo<0 or rhi>ref.size:return None
    x=cur[lo:hi];z=ref[rlo:rhi]
    if x.size<8:return None
    return x,z

def _select(cur,refs,t,radius,h,prev_lag,penalty):
    """Choose reference, lag, affine map using only already reconstructed cur[:t]."""
    best=None
    for ri,ref in enumerate(refs):
        for lag in range(-radius,radius+1):
            pair=_history_pair(cur,ref,t,h,lag)
            if pair is None:continue
            x,z=pair;a,b=_fit(x,z);e=x-(a*z+b)
            score=float(np.mean(e*e))
            if penalty and prev_lag is not None:
                scale=float(np.mean(x*x))+1e-12
                score += float(penalty)*scale*((lag-prev_lag)/max(1,radius))**2
            key=(score,abs(lag),ri,lag)
            if best is None or key<best[0]:best=(key,ri,lag,a,b)
    return None if best is None else best[1:]

def _forward(X,eps,tid):
    radius,h,seg,penalty,diff=PARAMS[int(tid)]
    X=np.asarray(X,np.float64)
    if X.ndim!=3:raise ValueError(X.shape)
    ny,nx,nt=X.shape;internal=float(eps)*float(c.MARGIN);step=2.0*internal
    R=np.empty((ny,nx,nt),np.int32);Y=np.empty((ny,nx,nt),np.float64)
    lag_hist=[];ref_hist=[]
    for y in range(ny):
        for x in range(nx):
            cur=Y[y,x]
            refs=[]
            if x>0:refs.append(Y[y,x-1])
            if y>0:refs.append(Y[y-1,x])
            prev_lag=None
            for s in range(0,nt,seg):
                e=min(nt,s+seg)
                choice=_select(cur,refs,s,radius,h,prev_lag,penalty) if refs and s>=8 else None
                if choice is None:
                    ri=lag=0;a=1.0;b=0.0
                    for t in range(s,e):
                        pred=float(cur[t-1]) if t>0 else 0.0
                        q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q;cur[t]=pred+q*step
                else:
                    ri,lag,a,b=choice;ref=refs[ri];prev_lag=int(lag);lag_hist.append(int(lag));ref_hist.append(int(ri))
                    for t in range(s,e):
                        j=t+lag
                        if j<0 or j>=nt:
                            pred=float(cur[t-1]) if t>0 else 0.0
                        elif diff and t>0 and j>0:
                            pred=float(cur[t-1])+a*(float(ref[j])-float(ref[j-1]))
                        else:
                            pred=a*float(ref[j])+b
                        q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q;cur[t]=pred+q*step
    diag={
        'nonzero_fraction':float(np.mean(R!=0)),
        'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),
        'lag_mean_abs':float(np.mean(np.abs(lag_hist))) if lag_hist else 0.0,
        'lag_nonzero_fraction':float(np.mean(np.asarray(lag_hist)!=0)) if lag_hist else 0.0,
        'slow_ref_fraction':float(np.mean(np.asarray(ref_hist)==1)) if ref_hist else 0.0,
        'segments_warped':int(len(lag_hist)),
    }
    return R,Y,internal,diag

def _inverse(R,internal,tid):
    radius,h,seg,penalty,diff=PARAMS[int(tid)]
    R=np.asarray(R,np.int32);ny,nx,nt=R.shape;step=2.0*float(internal);Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
        for x in range(nx):
            cur=Y[y,x];refs=[]
            if x>0:refs.append(Y[y,x-1])
            if y>0:refs.append(Y[y-1,x])
            prev_lag=None
            for s in range(0,nt,seg):
                e=min(nt,s+seg);choice=_select(cur,refs,s,radius,h,prev_lag,penalty) if refs and s>=8 else None
                if choice is None:
                    for t in range(s,e):
                        pred=float(cur[t-1]) if t>0 else 0.0;cur[t]=pred+int(R[y,x,t])*step
                else:
                    ri,lag,a,b=choice;ref=refs[ri];prev_lag=int(lag)
                    for t in range(s,e):
                        j=t+lag
                        if j<0 or j>=nt:pred=float(cur[t-1]) if t>0 else 0.0
                        elif diff and t>0 and j>0:pred=float(cur[t-1])+a*(float(ref[j])-float(ref[j-1]))
                        else:pred=a*float(ref[j])+b
                        cur[t]=pred+int(R[y,x,t])*step
    return Y

def candidate(X,eps,tid):
    R,Y,internal,d=_forward(X,eps,int(tid));payload,nbp=pq._pack_bitplanes(R)
    ny,nx,nt=R.shape;hdr=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),int(nbp),len(payload));blob=hdr+payload
    Z,_=decode(blob);me=float(c.hard(X,Z))
    if me>float(eps)*(1+3e-6):raise RuntimeError(('warp hard bound',tid,me,eps))
    d.update({'tid':int(tid),'name':NAMES[int(tid)],'bytes':len(blob),'payload_bytes':len(payload),'header_bytes':HSZ,'bitplanes':int(nbp),'maxerr':me})
    return d,blob

def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short warp stream')
    magic,eps,internal,ny,nx,nt,tid,nbp,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or int(tid) not in PARAMS or len(blob)!=HSZ+int(npay):raise RuntimeError('bad warp stream')
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)))
    return _inverse(R,float(internal),int(tid)),{'eps':float(eps),'tid':int(tid),'name':NAMES[int(tid)],'bitplanes':int(nbp)}

def sanity():
    rng=np.random.default_rng(20260818);ny,nx,nt=4,10,384;t=np.arange(nt,dtype=np.float64);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
        for x in range(nx):
            sh=2*x+3*y;u=t+sh
            X[y,x]=(80*np.sin(u/17)+25*np.sin(u/6.5)+rng.normal(0,1.5,nt)).astype(np.float32)
    for tid in PARAMS:
        d,b=candidate(X,3.0,tid);Z,_=decode(b)
        if c.hard(X,Z)>3.0*(1+3e-6):raise RuntimeError(('sanity',tid))
        print('WARP_SANITY',tid,d['bytes'],d['nonzero_fraction'],d['lag_mean_abs'],flush=True)

if __name__=='__main__':sanity()
