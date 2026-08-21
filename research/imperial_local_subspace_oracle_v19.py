#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair
STEP=267;WINDOWS=(8,16,32,64,128,256);RANKS=(1,2,4,8,12,16);TOP=5;FREE_HEADER=16

def integ(E):return np.cumsum(E.astype(np.float64),axis=0)
def diff(Y):
 X=np.empty_like(Y);X[0]=Y[0];X[1:]=Y[1:]-Y[:-1];return X

def local_lowrank(Y,w,r):
 L=np.zeros_like(Y);en=tot=0.0
 for t0 in range(0,Y.shape[1],w):
  Z=Y[:,t0:min(t0+w,Y.shape[1])];U,s,Vt=np.linalg.svd(Z,full_matrices=False);k=min(r,len(s));L[:,t0:t0+Z.shape[1]]=(U[:,:k]*s[:k])@Vt[:k];en+=float(np.dot(s[:k],s[:k]));tot+=float(np.dot(s,s))
 return L,en/max(tot,1e-30)

def rec(X,offs,cod,C):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for t in range(X.shape[1]):
  for c in range(X.shape[0]):
   p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]));k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def entropy(K):
 _,n=np.unique(K,return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);target=szb/2;offs,co,sbest,_=u.search_sample(X);base,R0,K0,mb,ob,cod=sbest
 P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);Y=integ(X-P0);oh=fair.COMMON_HEADER+1+len(ob)+len(mb)+FREE_HEADER;rows=[]
 for w in WINDOWS:
  for r in RANKS:
   if r>min(32,w):continue
   L,en=local_lowrank(Y,w,r);R,K=rec(X,offs,cod,diff(L));me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+5e-6):raise RuntimeError(('hard',w,r,me))
   fast=int(m.encode_k(K)[0])+oh;row={'window':w,'rank':r,'integrated_energy_fraction':en,'fast_bytes':fast,'fast_gain_vs_sz3':szb/fast,'zero_fraction':float(np.mean(K==0)),'k_entropy':entropy(K),'maxerr':me};rows.append((fast,row,L,K,R));print('SCREEN',json.dumps(row),flush=True)
 exact=[]
 for ii in np.argsort([x[0] for x in rows])[:TOP]:
  _,row,L,K,R=rows[int(ii)];fb,Kd,_=v7.super_frame(K)
  if not np.array_equal(Kd,K):raise RuntimeError('K replay')
  C=diff(L);Rd=np.zeros_like(K)
  for t in range(K.shape[1]):
   for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+int(np.rint(C[c,t]))+STEP*int(Kd[c,t])
  if not np.array_equal(Rd,R):raise RuntimeError('source replay')
  total=oh+fb;z={**row,'field_bytes':int(fb),'exact_bytes':int(total),'gain_vs_sz3':szb/total,'crosses_2x':bool(total<=target)};exact.append(z);print('EXACT',json.dumps(z),flush=True)
 best=min(exact,key=lambda z:z['exact_bytes']);out={'kind':'imperial-local-subspace-oracle-v19','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'strict_2x_target_bytes':target,'base_bytes':int(base),'best':best,'exact':exact,'screens':[x[1] for x in rows],'scope':'FREE ORACLE diagnostic, not a codec claim. The space-integrated causal prediction-error field is split into fixed temporal windows and each window receives a free exact rank-r SVD approximation. Only the remaining step-267 correction field is physically encoded. Purpose: determine whether the global rank-28 clue is merely near-full target leakage or whether Imperial is locally low-dimensional with a moving subspace. Any promising case must next serialize or causally learn every local basis/coefficient byte.'};json.dump(out,open('imperial_local_subspace_oracle_v19.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
