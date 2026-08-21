#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair
STEP=267;WINDOWS=(8,16,32,64,128,256);RANKS=(1,2,4,8)
def integ(E):return np.cumsum(E.astype(np.float64),axis=0)
def diff(Y):
 X=np.empty_like(Y);X[0]=Y[0];X[1:]=Y[1:]-Y[:-1];return X
def local(Y,w,r):
 L=np.zeros_like(Y)
 for t0 in range(0,Y.shape[1],w):
  Z=Y[:,t0:min(t0+w,Y.shape[1])];U,s,Vt=np.linalg.svd(Z,full_matrices=False);k=min(r,len(s));L[:,t0:t0+Z.shape[1]]=(U[:,:k]*s[:k])@Vt[:k]
 return L
def rec(X,offs,cod,C):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for t in range(X.shape[1]):
  for c in range(X.shape[0]):
   p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]));q=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=q;R[c,t]=p+STEP*q
 return R,K
def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,_=m.szrun(X,eps);offs,co,sbest,_=u.search_sample(X);_,R0,K0,mb,ob,cod=sbest;P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);Y=integ(X-P0);oh=fair.COMMON_HEADER+1+len(ob)+len(mb)+16;rows=[]
 for w in WINDOWS:
  for r in RANKS:
   if r>=min(32,w):continue
   R,K=rec(X,offs,cod,diff(local(Y,w,r)));b=int(m.encode_k(K)[0])+oh;row={'window':w,'rank':r,'bytes':b,'gain_vs_sz3':szb/b,'crosses_2x_free_oracle':bool(b<=szb/2),'zero_fraction':float(np.mean(K==0))};rows.append(row);print(json.dumps(row),flush=True)
 rows.sort(key=lambda x:x['bytes']);out={'sz3_bytes':int(szb),'target':szb/2,'best':rows[0],'best_rank_le4':min((x for x in rows if x['rank']<=4),key=lambda x:x['bytes']),'rows':rows,'warning':'FREE ORACLE SCREEN ONLY. Local SVD basis and coefficients cost zero.'};json.dump(out,open('imperial_local_subspace_screen_v19.json','w'),indent=2);print('FINAL',json.dumps(out['best_rank_le4']),flush=True)
if __name__=='__main__':main(sys.argv[1])
