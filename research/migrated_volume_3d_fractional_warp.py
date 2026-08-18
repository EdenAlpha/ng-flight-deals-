#!/usr/bin/env python3
"""Zero-side-information fractional-delay warp predictor.

This extends the causal warp idea below one sample.  A seismic event can move by
fractions of a sample between adjacent traces; ordinary point prediction then
creates a dense correction even though the physical waveform is nearly the same.
The delay, reference axis, affine gain and offset are inferred from already
reconstructed history only.  Delays live on a fixed half-sample lattice and
linear interpolation is deterministic at the decoder, so no warp map is sent.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_predictive_v3 as pq

MAGIC=b"MVFWARP1"
HDR="<8sddIIIHHI";HSZ=struct.calcsize(HDR)
# tid: (half-sample radius, history, segment, smooth penalty, differential)
PARAMS={45:(12,96,32,0.02,False),46:(16,128,64,0.02,False),47:(12,96,32,0.02,True)}
NAMES={45:'causal_fractional_warp_r6_h96_s32',46:'causal_fractional_warp_r8_h128_s64',47:'causal_fractional_warp_diff_r6_h96_s32'}

def _fit(x,z):
    x=np.asarray(x,np.float64);z=np.asarray(z,np.float64)
    if x.size<8:return 1.,0.
    xm=float(x.mean());zm=float(z.mean());dz=z-zm;den=float(np.dot(dz,dz))
    if den<=1e-24:return 0.,xm
    a=max(-2.,min(2.,float(np.dot(dz,x-xm)/den)));return a,xm-a*zm

def _interp_scalar(ref,q2):
    # q2 is coordinate in half samples.
    i=q2//2
    if q2&1:
        if i<0 or i+1>=ref.size:return None
        return 0.5*(float(ref[i])+float(ref[i+1]))
    if i<0 or i>=ref.size:return None
    return float(ref[i])

def _interp_vec(ref,start,n,d2):
    # output ref[start:start+n] evaluated at +d2/2.
    q2=2*np.arange(start,start+n,dtype=np.int64)+int(d2);i=np.floor_divide(q2,2);odd=(q2&1)!=0
    if i.size==0 or int(i.min())<0 or int(i.max())>=ref.size or (np.any(odd) and int(i[odd].max())+1>=ref.size):return None
    z=ref[i].astype(np.float64,copy=True)
    if np.any(odd):z[odd]=0.5*(ref[i[odd]].astype(np.float64)+ref[i[odd]+1].astype(np.float64))
    return z

def _select(cur,refs,t,r2,h,prev_d2,penalty):
    lo=max(0,t-h);n=t-lo
    if n<8:return None
    x=cur[lo:t];best=None
    for ri,ref in enumerate(refs):
        for d2 in range(-r2,r2+1):
            z=_interp_vec(ref,lo,n,d2)
            if z is None:continue
            a,b=_fit(x,z);e=x-(a*z+b);score=float(np.mean(e*e))
            if penalty and prev_d2 is not None:
                scale=float(np.mean(x*x))+1e-12;score+=float(penalty)*scale*((d2-prev_d2)/max(1,r2))**2
            key=(score,abs(d2),ri,d2)
            if best is None or key<best[0]:best=(key,ri,d2,a,b)
    return None if best is None else best[1:]

def _forward(X,eps,tid):
    r2,h,seg,penalty,diff=PARAMS[int(tid)];X=np.asarray(X,np.float64);ny,nx,nt=X.shape
    internal=float(eps)*float(c.MARGIN);step=2*internal;R=np.empty((ny,nx,nt),np.int32);Y=np.empty((ny,nx,nt),np.float64);ds=[]
    for y in range(ny):
      for x in range(nx):
        cur=Y[y,x];refs=[]
        if x>0:refs.append(Y[y,x-1])
        if y>0:refs.append(Y[y-1,x])
        prev=None
        for s in range(0,nt,seg):
          e=min(nt,s+seg);ch=_select(cur,refs,s,r2,h,prev,penalty) if refs and s>=8 else None
          if ch is None:
            for t in range(s,e):
              p=float(cur[t-1]) if t else 0.;q=int(np.rint((float(X[y,x,t])-p)/step));R[y,x,t]=q;cur[t]=p+q*step
          else:
            ri,d2,a,b=ch;ref=refs[ri];prev=int(d2);ds.append(int(d2))
            for t in range(s,e):
              rv=_interp_scalar(ref,2*t+d2)
              if rv is None:p=float(cur[t-1]) if t else 0.
              elif diff and t>0:
                rp=_interp_scalar(ref,2*(t-1)+d2);p=float(cur[t-1])+a*(rv-rp) if rp is not None else a*rv+b
              else:p=a*rv+b
              q=int(np.rint((float(X[y,x,t])-p)/step));R[y,x,t]=q;cur[t]=p+q*step
    return R,Y,internal,{'nonzero_fraction':float(np.mean(R!=0)),'mean_abs_residual':float(np.mean(np.abs(R.astype(np.int64)))),'delay_mean_abs_samples':float(np.mean(np.abs(ds))/2) if ds else 0.,'fractional_delay_fraction':float(np.mean((np.asarray(ds)&1)!=0)) if ds else 0.,'delay_nonzero_fraction':float(np.mean(np.asarray(ds)!=0)) if ds else 0.}

def _inverse(R,internal,tid):
    r2,h,seg,penalty,diff=PARAMS[int(tid)];R=np.asarray(R,np.int32);ny,nx,nt=R.shape;step=2*float(internal);Y=np.empty((ny,nx,nt),np.float64)
    for y in range(ny):
      for x in range(nx):
        cur=Y[y,x];refs=[]
        if x>0:refs.append(Y[y,x-1])
        if y>0:refs.append(Y[y-1,x])
        prev=None
        for s in range(0,nt,seg):
          e=min(nt,s+seg);ch=_select(cur,refs,s,r2,h,prev,penalty) if refs and s>=8 else None
          if ch is None:
            for t in range(s,e):p=float(cur[t-1]) if t else 0.;cur[t]=p+int(R[y,x,t])*step
          else:
            ri,d2,a,b=ch;ref=refs[ri];prev=int(d2)
            for t in range(s,e):
              rv=_interp_scalar(ref,2*t+d2)
              if rv is None:p=float(cur[t-1]) if t else 0.
              elif diff and t>0:
                rp=_interp_scalar(ref,2*(t-1)+d2);p=float(cur[t-1])+a*(rv-rp) if rp is not None else a*rv+b
              else:p=a*rv+b
              cur[t]=p+int(R[y,x,t])*step
    return Y

def candidate(X,eps,tid):
    R,Y,internal,d=_forward(X,eps,int(tid));payload,nbp=pq._pack_bitplanes(R);ny,nx,nt=R.shape
    blob=struct.pack(HDR,MAGIC,float(eps),float(internal),ny,nx,nt,int(tid),int(nbp),len(payload))+payload;Z,_=decode(blob);me=float(c.hard(X,Z))
    if me>float(eps)*(1+3e-6):raise RuntimeError(('fractional warp hard',tid,me,eps))
    d.update({'tid':int(tid),'name':NAMES[int(tid)],'bytes':len(blob),'payload_bytes':len(payload),'header_bytes':HSZ,'bitplanes':int(nbp),'maxerr':me});return d,blob

def decode(blob):
    if len(blob)<HSZ:raise RuntimeError('short fractional warp')
    magic,eps,internal,ny,nx,nt,tid,nbp,npay=struct.unpack(HDR,blob[:HSZ])
    if magic!=MAGIC or int(tid) not in PARAMS or len(blob)!=HSZ+int(npay):raise RuntimeError('bad fractional warp')
    R=pq._unpack_bitplanes(blob[HSZ:],(int(ny),int(nx),int(nt)));return _inverse(R,float(internal),int(tid)),{'tid':int(tid),'name':NAMES[int(tid)]}

def sanity():
    rng=np.random.default_rng(18);ny,nx,nt=3,8,320;t=np.arange(nt,dtype=np.float64);X=np.empty((ny,nx,nt),np.float32)
    for y in range(ny):
      for x in range(nx):
        u=t+0.5*x+1.5*y;X[y,x]=(90*np.sin(u/16)+22*np.sin(u/5.5)+rng.normal(0,1,nt)).astype(np.float32)
    for tid in PARAMS:
      d,b=candidate(X,3.,tid);print('FWARP_SANITY',tid,d['bytes'],d['nonzero_fraction'],d['fractional_delay_fraction'],flush=True)
if __name__=='__main__':sanity()
