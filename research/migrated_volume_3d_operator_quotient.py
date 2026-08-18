#!/usr/bin/env python3
"""Self-derived local operator quotient predictor for migrated seismic volumes.

Instead of assuming a neighbouring trace differs only by amplitude or delay,
model the causal relation as a tiny local convolutional operator.  Such an
operator can simultaneously represent integer/fractional delay, phase rotation,
wavelet-shape change and amplitude mixing.  The operator is re-estimated from
ALREADY RECONSTRUCTED history at every segment and quantized on a fixed grid;
there is no transmitted coefficient or model map.

For an interior trace, candidate models use the completed fast neighbour, the
completed slow neighbour, or both.  Model choice is based only on reconstructed
past SSE plus a fixed complexity penalty.  The chosen operator predicts the next
segment; only hard-error-bounded lattice residuals are serialized.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

MAGIC=b"MVOPQ01\0"
HDR="<8sddIIIHHI";HSZ=struct.calcsize(HDR)
# tid: (tap radius, history, segment, coefficient quantum denominator)
PARAMS={51:(2,96,32,256),52:(3,128,32,256),53:(2,128,64,512)}
NAMES={51:'operator_quotient_r2_h96_s32',52:'operator_quotient_r3_h128_s32',53:'operator_quotient_r2_h128_s64'}

def _matrix(refs,lo,hi,rad):
    n=hi-lo
    if n<=0:return None
    cols=[]
    for ref in refs:
        for k in range(-rad,rad+1):cols.append(ref[lo+k:hi+k])
    if not cols:return None
    return np.stack(cols,axis=1).astype(np.float64,copy=False)

def _fit(cur,refs,t,h,rad,step,qden):
    lo=max(rad,t-h);hi=min(t,cur.size-rad)
    if hi-lo<max(16,2*(2*rad+1)):return None
    y=np.asarray(cur[lo:hi],np.float64);X=_matrix(refs,lo,hi,rad)
    if X is None or X.shape[0]!=y.size:return None
    xm=X.mean(axis=0);ym=float(y.mean());A=X-xm;yc=y-ym
    G=A.T@A;scale=float(np.trace(G)/max(1,G.shape[0]))+1e-18
    lam=1e-3*scale
    try:coef=np.linalg.solve(G+lam*np.eye(G.shape[0]),A.T@yc)
    except np.linalg.LinAlgError:return None
    coef=np.clip(coef,-2.0,2.0);coef=np.rint(coef*float(qden))/float(qden)
    b=ym-float(xm@coef);bq=max(float(step)/64.0,1e-18);b=np.rint(b/bq)*bq
    pred=X@coef+b;e=y-pred;var=float(np.mean((y-ym)**2))+1e-18
    # Small fixed MDL-like penalty prevents a two-neighbour model from winning
    # on microscopic training SSE differences alone.
    score=float(np.mean(e*e))+1e-4*var*len(coef)
    return score,coef,float(b),lo,hi

def _select(cur,left,up,t,h,rad,step,qden):
    specs=[]
    if left is not None:specs.append((0,[left]))
    if up is not None:specs.append((1,[up]))
    if left is not None and up is not None:specs.append((2,[left,up]))
    best=None
    for kind,refs in specs:
        q=_fit(cur,refs,t,h,rad,step,qden)
        if q is None:continue
        score,coef,b,lo,hi=q;key=(score,kind)
        if best is None or key<best[0]:best=(key,kind,refs,coef,b)
    return None if best is None else best[1:]

def _predict(refs,coef,b,t,rad):
    vals=[]
    for ref in refs:
        for k in range(-rad,rad+1):
            j=t+k
            if j<0 or j>=ref.size:return None
            vals.append(float(ref[j]))
    return float(np.dot(np.asarray(vals,np.float64),coef)+b)

def _forward(X,eps,tid):
    rad,h,seg,qden=PARAMS[int(tid)];X=np.asarray(X,np.float64)
    if X.ndim!=3:raise ValueError(X.shape)
    ny,nx,nt=X.shape;internal=float(eps)*float(c.MARGIN);step=2.0*internal
    R=np.empty((ny,nx,nt),np.int32);Y=np.empty((ny,nx,nt),np.float64);kinds=[];l1=[]
    for y in range(ny):
      for x in range(nx):
        cur=Y[y,x];left=Y[y,x-1] if x>0 else None;up=Y[y-1,x] if y>0 else None
        for s in range(0,nt,seg):
          e=min(nt,s+seg);ch=_select(cur,left,up,s,h,rad,step,qden) if s>=max(16,rad+1) else None
          if ch is None:
            for t in range(s,e):
              pred=float(cur[t-1]) if t else 0.0;q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q;cur[t]=pred+q*step
          else:
            kind,refs,coef,b=ch;kinds.append(int(kind));l1.append(float(np.sum(np.abs(coef))))
            for t in range(s,e):
              pred=_predict(refs,coef,b,t,rad)
              if pred is None:pred=float(cur[t-1]) if t else 0.0
              q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q;cur[t]=pred+q*step
    kk=np.asarray(kinds,np.int8) if kinds else np.empty(0,np.int8)
    d={'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),
       'joint_model_fraction':float(np.mean(kk==2)) if kk.size else 0.0,'fast_model_fraction':float(np.mean(kk==0)) if kk.size else 0.0,
       'slow_model_fraction':float(np.mean(kk==1)) if kk.size else 0.0,'mean_operator_l1':float(np.mean(l1)) if l1 else 0.0,'operator_segments':int(len(kinds))}
    return R,Y,internal,d

def _inverse(R,internal,tid):
    rad,h,seg,qden=PARAMS[int(tid)];R=np.asarray(R,np.int32);ny,nx,nt=R.shape;step=2.0*float(internal);Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
      for x in range(nx):
        cur=Y[y,x];left=Y[y,x-1] if x>0 else None;up=Y[y-1,x] if y>0 else None
        for s in range(0,nt,seg):
          e=min(nt,s+seg);ch=_select(cur,left,up,s,h,rad,step,qden) if s>=max(16,rad+1) else None
          if ch is None:
            for t in range(s,e):pred=float(cur[t-1]) if t else 0.0;cur[t]=pred+int(R[y,x,t])*step
          else:
            kind,refs,coef,b=ch
            for t in range(s,e):
              pred=_predict(refs,coef,b,t,rad)
              if pred is None:pred=float(cur[t-1]) if t else 0.0
              cur[t]=pred+int(R[y,x,t])*step
    return Y

def candidate(X,eps,tid):
    R,Y,internal,d=_forward(X,eps,int(tid));payload,nbp=pq._pack_bitplanes(R);ny,nx,nt=R.shape
    blob=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),int(nbp),len(payload))+payload;Z,_=decode(blob);me=float(c.hard(X,Z))
    if me>float(eps)*(1+3e-6):raise RuntimeError(('operator quotient hard',tid,me,eps))
    d.update({'tid':int(tid),'name':NAMES[int(tid)],'bytes':len(blob),'payload_bytes':len(payload),'header_bytes':HSZ,'bitplanes':int(nbp),'maxerr':me});return d,blob

def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short operator quotient')
    magic,eps,internal,ny,nx,nt,tid,nbp,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or int(tid) not in PARAMS or len(blob)!=HSZ+int(npay):raise RuntimeError('bad operator quotient')
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)));return _inverse(R,float(internal),int(tid)),{'tid':int(tid),'name':NAMES[int(tid)]}

def sanity():
    rng=np.random.default_rng(20260818);ny,nx,nt=4,10,384;t=np.arange(nt,dtype=np.float64);X=np.empty((ny,nx,nt),np.float32)
    base=80*np.sin(t/17)+22*np.sin(t/6.1)
    for y in range(ny):
      for x in range(nx):
        sh=0.45*x+0.8*y;u=t+sh
        # Slight local wavelet shape change in addition to sub-sample transport.
        X[y,x]=(80*np.sin(u/17)+(22+0.7*x)*np.sin(u/6.1+0.015*y)+rng.normal(0,1.2,nt)).astype(np.float32)
    for tid in PARAMS:
      d,b=candidate(X,3.0,tid);print('OPQ_SANITY',tid,d['bytes'],d['nonzero_fraction'],d['joint_model_fraction'],flush=True)
if __name__=='__main__':sanity()
