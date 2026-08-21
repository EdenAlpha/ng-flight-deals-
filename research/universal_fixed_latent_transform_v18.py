#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np,zstandard as zstd,brotli
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair
STEP=267;KS=(4,8,12,16,20,24,28,32);QF=(.5,1,2,4,8,16,32,64,128);TOP=4;MAGIC=b'FT18'
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def integ(E):return np.cumsum(E.astype(np.float64),axis=0)
def diff(Y):
 X=np.empty_like(Y);X[0]=Y[0];X[1:]=Y[1:]-Y[:-1];return X

def basis(n=32):
 x=np.arange(n,dtype=np.float64);k=np.arange(n,dtype=np.float64)[:,None]
 B=np.cos(np.pi*(x+.5)*k/n);B[0]*=np.sqrt(1/n);B[1:]*=np.sqrt(2/n);return B
B=basis()

def sdtype(a):
 mn=int(a.min());mx=int(a.max())
 for code,dt in enumerate((np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4'))):
  ii=np.iinfo(dt)
  if mn>=ii.min and mx<=ii.max:return code,dt
 raise RuntimeError((mn,mx))

def pack(Y,k,qstep):
 F=B@Y;energy=np.sum(F*F,axis=1);idx=np.sort(np.argsort(energy)[-k:]).astype(np.uint8)
 qs=np.float32(qstep);Q=np.rint(F[idx]/float(qs)).astype(np.int32);code,dt=sdtype(Q)
 variants=[]
 for mode,A in ((0,Q),(1,np.c_[Q[:,0],Q[:,1:]-Q[:,:-1]])):
  raw=A.astype(dt).tobytes();zz=Z.compress(raw);bb=brotli.compress(raw,quality=11)
  variants.append((len(zz),mode,0,zz));variants.append((len(bb),mode,1,bb))
 _,mode,cm,payload=min(variants,key=lambda z:z[0])
 mask=sum(1<<int(i) for i in idx)
 blob=struct.pack('<4sBBfIBI',MAGIC,k,code,float(qs),mask,(mode<<1)|cm,len(payload))+payload
 return blob,unpack(blob,Y.shape)

def unpack(blob,shape):
 magic,k,code,qs,mask,flags,n=struct.unpack_from('<4sBBfIBI',blob,0);off=19
 if magic!=MAGIC or off+n!=len(blob):raise RuntimeError('latent')
 mode=flags>>1;cm=flags&1;p=blob[off:];raw=D.decompress(p) if cm==0 else brotli.decompress(p)
 dt=(np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4'))[code];idx=np.array([i for i in range(32) if mask>>i&1],np.int32)
 A=np.frombuffer(raw,dt,count=k*shape[1]).astype(np.int32).reshape(k,shape[1])
 Q=np.cumsum(A,axis=1,dtype=np.int32) if mode else A
 F=np.zeros(shape,np.float64);F[idx]=Q.astype(np.float64)*float(qs);return B.T@F

def rec(X,offs,cod,C):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for t in range(X.shape[1]):
  for c in range(X.shape[0]):
   p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]));q=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=q;R[c,t]=p+STEP*q
 return R,K

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);target=szb/2;offs,co,sbest,_=u.search_sample(X);base,R0,K0,mb,ob,cod=sbest
 P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);Y=integ(X-P0);oh=fair.COMMON_HEADER+1+len(ob)+len(mb);rows=[]
 for k in KS:
  for qf in QF:
   blob,Yh=pack(Y,k,eps*qf);R,K=rec(X,offs,cod,diff(Yh));me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+5e-6):raise RuntimeError(('hard',k,qf,me))
   fast=int(m.encode_k(K)[0]);tot=oh+len(blob)+fast;row={'k':k,'q_factor':qf,'latent_bytes':len(blob),'fast_field_bytes':fast,'fast_total_bytes':tot,'fast_gain_vs_sz3':szb/tot,'zero_fraction':float(np.mean(K==0)),'maxerr':me};rows.append((tot,row,blob,K,R));print('SCREEN',json.dumps(row),flush=True)
 exact=[]
 for ii in np.argsort([x[0] for x in rows])[:TOP]:
  _,row,blob,K,R=rows[int(ii)];fb,Kd,_=v7.super_frame(K)
  if not np.array_equal(Kd,K):raise RuntimeError('K replay')
  C=diff(unpack(blob,Y.shape));Rd=np.zeros_like(K)
  for t in range(K.shape[1]):
   for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+int(np.rint(C[c,t]))+STEP*int(Kd[c,t])
  if not np.array_equal(Rd,R):raise RuntimeError('source replay')
  total=oh+len(blob)+fb;z={**row,'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':szb/total,'crosses_2x':bool(total<=target)};exact.append(z);print('EXACT',json.dumps(z),flush=True)
 best=min(exact,key=lambda z:z['bytes']);out={'kind':'universal-fixed-latent-transform-v18','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'strict_2x_target_bytes':target,'base_bytes':int(base),'best':best,'exact':exact,'screens':[x[1] for x in rows],'principle':'Use a public zero-model DCT basis on the space-integrated causal prediction-error field. Encoder selects a tiny transmitted mode mask, quantizes only those coefficient traces, entropy-compresses them, reconstructs the same latent at decoder, differentiates it into a predictor correction, then sends exact SZ-style correction indices. Every byte is charged; the basis itself is fixed and costs zero.'};json.dump(out,open('universal_fixed_latent_transform_v18.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
