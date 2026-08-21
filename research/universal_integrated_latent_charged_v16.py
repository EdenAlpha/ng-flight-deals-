#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np,zstandard as zstd,brotli
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_integrated_latent_oracle_v13 as o
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

STEP=267
RANKS=(8,12,16,20,24,28)
STRIDES=(1,2,4,8,16)
U_LEVELS=(127,511)
T_LEVELS=(63,127,255,511,1023)
TOP_EXACT=4
MAGIC=b'IL16'


def _dtype(levels):
    return np.int8 if levels<=127 else np.int16


def _qrows(A,levels):
    A=np.asarray(A,np.float64);mx=np.max(np.abs(A),axis=1)
    sc=np.where(mx>0,mx/float(levels),1.0).astype(np.float32)
    q=np.rint(A/sc[:,None]).clip(-levels,levels).astype(_dtype(levels))
    return q,sc


def _pack_payload(raw):
    z=zstd.ZstdCompressor(level=19).compress(raw)
    b=brotli.compress(raw,quality=11)
    if len(z)<=len(b): return 0,z
    return 1,b


def _unpack_payload(method,payload):
    return zstd.ZstdDecompressor().decompress(payload) if method==0 else brotli.decompress(payload)


def encode_latent(U,T,k,stride,ul,tl,nt):
    idx=np.arange(0,nt,stride,dtype=np.int32)
    if idx[-1]!=nt-1: idx=np.r_[idx,nt-1]
    uq,us=_qrows(U[:,:k].T,ul)  # k x 32
    tq,ts=_qrows(T[:k,idx],tl)  # k x ns
    dt=np.empty_like(tq);dt[:,0]=tq[:,0];dt[:,1:]=tq[:,1:]-tq[:,:-1]
    raw=uq.tobytes(order='C')+dt.tobytes(order='C')
    method,payload=_pack_payload(raw)
    h=struct.pack('<4sBBBBHHI',MAGIC,k,stride,0 if ul<=127 else 1,0 if tl<=127 else 1,ul,tl,len(idx))
    blob=h+us.astype('<f4').tobytes()+ts.astype('<f4').tobytes()+bytes([method])+struct.pack('<I',len(payload))+payload
    C=decode_latent(blob,nt)
    return blob,C,len(idx)


def decode_latent(blob,nt):
    off=0;magic,k,stride,ud,td,ul,tl,ns=struct.unpack_from('<4sBBBBHHI',blob,off);off+=16
    if magic!=MAGIC: raise RuntimeError('latent magic')
    us=np.frombuffer(blob,dtype='<f4',count=k,offset=off).astype(np.float64);off+=4*k
    ts=np.frombuffer(blob,dtype='<f4',count=k,offset=off).astype(np.float64);off+=4*k
    method=blob[off];off+=1;plen=struct.unpack_from('<I',blob,off)[0];off+=4
    raw=_unpack_payload(method,blob[off:off+plen]);off+=plen
    if off!=len(blob): raise RuntimeError('latent trailing')
    udt=np.int8 if ud==0 else np.int16;tdt=np.int8 if td==0 else np.int16
    nu=k*32;ub=np.dtype(udt).itemsize*nu
    uq=np.frombuffer(raw[:ub],dtype=udt,count=nu).astype(np.float64).reshape(k,32)
    dt=np.frombuffer(raw[ub:],dtype=tdt,count=k*ns).astype(np.int64).reshape(k,ns)
    tq=np.cumsum(dt,axis=1).astype(np.float64)
    Uhat=(uq*us[:,None]).T
    Ts=tq*ts[:,None]
    idx=np.arange(0,nt,stride,dtype=np.int32)
    if idx[-1]!=nt-1: idx=np.r_[idx,nt-1]
    full=np.empty((k,nt),np.float64);x=np.arange(nt)
    for j in range(k): full[j]=np.interp(x,idx,Ts[j])
    L=Uhat@full
    return o.differentiate(L,0)


def recursive(X,offs,cod,C):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]))
            q=int(np.rint((float(X[c,t])-float(p))/STEP));K[c,t]=q;R[c,t]=p+STEP*q
    return R,K


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);target=szb/2.0
    offs,co,sbest,shist=u.search_sample(X);base_total,R0,K0,mb,ob,cod=sbest
    P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);E0=X-P0
    Y=o.integrate(E0,0);U,s,Vt=np.linalg.svd(Y,full_matrices=False);T=s[:,None]*Vt
    overhead=fair.COMMON_HEADER+1+len(ob)+len(mb)
    cand=[]
    for k in RANKS:
      for stride in STRIDES:
       for ul in U_LEVELS:
        for tl in T_LEVELS:
            blob,C,ns=encode_latent(U,T,k,stride,ul,tl,X.shape[1]);R,K=recursive(X,offs,cod,C)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6): raise RuntimeError(('hard',k,stride,ul,tl,me,eps))
            fast=int(m.encode_k(K)[0]);total=overhead+len(blob)+fast
            row={'rank':k,'stride':stride,'u_levels':ul,'t_levels':tl,'latent_bytes':len(blob),'sampled_coeffs':k*ns,'fast_field_bytes':fast,'fast_total_bytes':total,'fast_gain_vs_sz3':float(szb/total),'zero_fraction':float(np.mean(K==0)),'maxerr':me}
            cand.append((total,row,blob,C,K,R));print('SCREEN',json.dumps(row),flush=True)
    order=np.argsort([x[0] for x in cand])[:TOP_EXACT]
    exact=[]
    for ii in order:
        _,row,blob,C,K,R=cand[int(ii)];fb,Kd,detail=v7.super_frame(K)
        if not np.array_equal(Kd,K): raise RuntimeError('K replay')
        Cd=decode_latent(blob,X.shape[1]);Rd=np.zeros_like(K)
        for t in range(K.shape[1]):
            for c in range(K.shape[0]):
                p=u.sample_pred(Rd,c,t,cod,offs)+int(np.rint(Cd[c,t]));Rd[c,t]=p+STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R): raise RuntimeError('source replay')
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=overhead+len(blob)+fb
        z={**row,'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':float(szb/total),'crosses_2x':bool(total<=target),'maxerr':me};exact.append(z);print('EXACT',json.dumps(z),flush=True)
    best=min(exact,key=lambda z:z['bytes'])
    out={'kind':'universal-integrated-latent-charged-v16','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'base_bytes':int(base_total),'base_offsets':[list(x) for x in offs],'best':best,'exact':exact,'screens':[x[1] for x in cand],
      'principle':'Convert the v13 free-oracle clue into a real charged two-pass codec. Integrate the source-domain prediction error across channels, factor it once, quantize the spatial basis and temporally downsampled latent coefficient tracks, physically serialize every latent byte, reconstruct that correction at the decoder, then use the unchanged SZ-style hard-error quantizer plus current exact residual coder for the remaining correction. The final stream charges basis, coefficient scales, compressed coefficient payload, predictor metadata, and correction bytes.'}
    json.dump(out,open('universal_integrated_latent_charged_v16.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
