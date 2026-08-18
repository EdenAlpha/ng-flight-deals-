#!/usr/bin/env python3
"""Self-synchronizing adaptive operator quotient v2.

A local FIR operator is inferred from reconstructed history, then evolves inside
the segment using only decoder-visible reconstruction error.  Both sides thus
maintain the same hidden transport operator without transmitting coefficients.
This combines blockwise identification with fixed-point normalized-LMS tracking,
allowing continuous sub-sample phase/delay and wavelet-shape drift.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

MAGIC=b"MVOPQ02\0";HDR="<8sddIIIHHI";HSZ=struct.calcsize(HDR)
# tid: rad, history, segment, coeff denominator, NLMS mu
PARAMS={54:(2,96,32,1024,0.05),55:(2,96,32,1024,0.10),56:(2,96,32,1024,0.20),57:(3,128,32,1024,0.10)}
NAMES={k:f'adaptive_operator_quotient_r{r}_h{h}_s{s}_mu{mu:g}' for k,(r,h,s,q,mu) in PARAMS.items()}

def _design(refs,lo,hi,rad):
    return np.stack([ref[lo+k:hi+k] for ref in refs for k in range(-rad,rad+1)],axis=1).astype(np.float64,copy=False)

def _fit(cur,refs,t,h,rad,step,qden):
    lo=max(rad,t-h);hi=min(t,cur.size-rad)
    if hi-lo<max(16,2*(2*rad+1)):return None
    y=np.asarray(cur[lo:hi],np.float64);X=_design(refs,lo,hi,rad);xm=X.mean(0);ym=float(y.mean());A=X-xm;yc=y-ym
    G=A.T@A;scale=float(np.trace(G)/max(1,G.shape[0]))+1e-18
    try:w=np.linalg.solve(G+(1e-3*scale)*np.eye(G.shape[0]),A.T@yc)
    except np.linalg.LinAlgError:return None
    w=np.rint(np.clip(w,-2.,2.)*qden)/qden;b=ym-float(xm@w);bq=max(step/64.,1e-18);b=np.rint(b/bq)*bq
    e=y-(X@w+b);score=float(np.mean(e*e))+1e-4*(float(np.mean((y-ym)**2))+1e-18)*len(w)
    return score,w,float(b)

def _select(cur,left,up,t,h,rad,step,qden):
    specs=[]
    if left is not None:specs.append((0,[left]))
    if up is not None:specs.append((1,[up]))
    if left is not None and up is not None:specs.append((2,[left,up]))
    best=None
    for kind,refs in specs:
        f=_fit(cur,refs,t,h,rad,step,qden)
        if f is None:continue
        score,w,b=f;key=(score,kind)
        if best is None or key<best[0]:best=(key,kind,refs,w,b)
    return None if best is None else best[1:]

def _vector(refs,t,rad):
    v=[]
    for ref in refs:
        for k in range(-rad,rad+1):
            j=t+k
            if j<0 or j>=ref.size:return None
            v.append(float(ref[j]))
    return np.asarray(v,np.float64)

def _adapt(w,b,v,visible_err,step,qden,mu):
    # Separate normalized updates for FIR and intercept. Quantize state after
    # every update, making the hidden operator exactly decoder-reproducible.
    den=float(np.dot(v,v))+1e-18
    w=w+(float(mu)*float(visible_err)/den)*v
    w=np.rint(np.clip(w,-2.,2.)*qden)/qden
    bq=max(step/64.,1e-18);b=b+float(mu)*float(visible_err);b=float(np.rint(b/bq)*bq)
    return w,b

def _run(X_or_R,eps_or_internal,tid,decode_mode=False):
    rad,h,seg,qden,mu=PARAMS[int(tid)]
    if decode_mode:
        R=np.asarray(X_or_R,np.int32);ny,nx,nt=R.shape;internal=float(eps_or_internal);step=2*internal;X=None
    else:
        X=np.asarray(X_or_R,np.float64);ny,nx,nt=X.shape;internal=float(eps_or_internal)*float(c.MARGIN);step=2*internal;R=np.empty((ny,nx,nt),np.int32)
    Y=np.empty((ny,nx,nt),np.float64);kinds=[];updates=0
    for y in range(ny):
      for x in range(nx):
        cur=Y[y,x];left=Y[y,x-1] if x>0 else None;up=Y[y-1,x] if y>0 else None
        for s in range(0,nt,seg):
          e=min(nt,s+seg);ch=_select(cur,left,up,s,h,rad,step,qden) if s>=max(16,rad+1) else None
          if ch is None:
            for t in range(s,e):
              pred=float(cur[t-1]) if t else 0.
              if decode_mode:q=int(R[y,x,t])
              else:q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q
              cur[t]=pred+q*step
          else:
            kind,refs,w,b=ch;kinds.append(int(kind))
            for t in range(s,e):
              v=_vector(refs,t,rad)
              if v is None:pred=float(cur[t-1]) if t else 0.
              else:pred=float(np.dot(v,w)+b)
              if decode_mode:q=int(R[y,x,t])
              else:q=int(np.rint((float(X[y,x,t])-pred)/step));R[y,x,t]=q
              cur[t]=pred+q*step
              if v is not None:
                  visible=float(cur[t]-pred);w,b=_adapt(w,b,v,visible,step,qden,mu);updates+=1
    d={'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),'adaptive_updates':int(updates),'operator_segments':int(len(kinds)),'joint_model_fraction':float(np.mean(np.asarray(kinds)==2)) if kinds else 0.0}
    return R,Y,internal,d

def candidate(X,eps,tid):
    R,Y,internal,d=_run(X,eps,int(tid),False);payload,nbp=pq._pack_bitplanes(R);ny,nx,nt=R.shape
    blob=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),int(nbp),len(payload))+payload;Z,_=decode(blob);me=float(c.hard(X,Z))
    if me>float(eps)*(1+3e-6):raise RuntimeError(('adaptive operator hard',tid,me,eps))
    d.update({'tid':int(tid),'name':NAMES[int(tid)],'bytes':len(blob),'payload_bytes':len(payload),'header_bytes':HSZ,'bitplanes':int(nbp),'maxerr':me});return d,blob

def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short adaptive operator')
    magic,eps,internal,ny,nx,nt,tid,nbp,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or int(tid) not in PARAMS or len(blob)!=HSZ+int(npay):raise RuntimeError('bad adaptive operator')
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)));_,Y,_,_=_run(R,float(internal),int(tid),True);return Y,{'tid':int(tid),'name':NAMES[int(tid)]}

def sanity():
    rng=np.random.default_rng(20260818);ny,nx,nt=4,10,384;t=np.arange(nt,dtype=np.float64);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
      for x in range(nx):
        u=t+0.45*x+0.8*y;X[y,x]=(80*np.sin(u/17)+(22+0.7*x)*np.sin(u/6.1+0.015*y)+rng.normal(0,1.2,nt)).astype(np.float32)
    for tid in PARAMS:
      d,b=candidate(X,3.,tid);print('OPQ2_SANITY',tid,d['bytes'],d['nonzero_fraction'],d['joint_model_fraction'],flush=True)
if __name__=='__main__':sanity()
