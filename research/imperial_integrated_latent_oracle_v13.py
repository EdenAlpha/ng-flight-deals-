#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

STEP=267
RANKS=(0,1,2,4,8,12,16,20,24,28,32)
TOP_EXACT=5
FREE_ORACLE_HEADER=16

def integrate(E,axis):
    return np.cumsum(E.astype(np.float64),axis=axis)

def differentiate(Y,axis):
    X=np.empty_like(Y)
    if axis==1:
        X[:,0]=Y[:,0];X[:,1:]=Y[:,1:]-Y[:,:-1]
    else:
        X[0,:]=Y[0,:];X[1:,:]=Y[1:,:]-Y[:-1,:]
    return X

def lowrank_correction(E,axis,k):
    Y=integrate(E,axis);U,s,Vt=np.linalg.svd(Y,full_matrices=False)
    if k==0:L=np.zeros_like(Y)
    else:L=(U[:,:k]*s[:k])@Vt[:k,:]
    C=differentiate(L,axis)
    energy=float(np.dot(s[:k],s[:k])/max(np.dot(s,s),1e-30)) if k else 0.0
    return C,energy

def recursive_with_free_correction(X,offs,cod,C):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]))
            k=int(np.rint((float(X[c,t])-float(p))/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K

def entropy(K):
    _,n=np.unique(K,return_counts=True);p=n.astype(np.float64)/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);target=szb/2.0
    offs,co,sbest,shist=u.search_sample(X);base_total,R0,K0,mb,ob,cod=sbest
    # Baseline causal prediction error field before quantization. This is the structure the oracle is allowed to study.
    P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);E0=X-P0
    candidates=[]
    for axis,name in ((1,'time_integrated'),(0,'space_integrated')):
        for k in RANKS:
            C,en=lowrank_correction(E0,axis,k);R,K=recursive_with_free_correction(X,offs,cod,C)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard',name,k,me,eps))
            # Fast physical coder used only to rank finalists. Free C and its basis/coefficients are intentionally not charged.
            fast=int(m.encode_k(K)[0])+FREE_ORACLE_HEADER
            row={'axis':name,'rank':int(k),'integrated_energy_fraction':en,'fast_bytes':fast,'fast_gain_vs_sz3':float(szb/fast),'zero_fraction':float(np.mean(K==0)),'k_entropy':entropy(K),'maxerr':me}
            candidates.append((fast,row,C,K,R));print('SCREEN',json.dumps(row),flush=True)
    # Always include rank0 plus strongest unique candidates for exact modern residual coding.
    order=sorted(range(len(candidates)),key=lambda i:candidates[i][0]);pick=[]
    for i in order:
        if candidates[i][1]['rank']==0 or len(pick)<TOP_EXACT:
            if i not in pick:pick.append(i)
        if len(pick)>=TOP_EXACT and any(candidates[j][1]['rank']==0 for j in pick):break
    exact=[]
    overhead=fair.COMMON_HEADER+1+len(ob)+len(mb)+FREE_ORACLE_HEADER
    for i in pick:
        fast,row,C,K,R=candidates[i];fb,Kd,detail=v7.super_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError('K replay')
        # Re-run decoder-side recursion from the free oracle correction field.
        Rd=np.zeros_like(K)
        for t in range(K.shape[1]):
            for c in range(K.shape[0]):
                p=u.sample_pred(Rd,c,t,cod,offs)+int(np.rint(C[c,t]));Rd[c,t]=p+STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R):raise RuntimeError(('source replay',row['axis'],row['rank']))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        total=overhead+int(fb);z={**row,'field_bytes':int(fb),'exact_bytes':int(total),'gain_vs_sz3':float(szb/total),'crosses_2x':bool(total<=target),'maxerr':me};exact.append(z);print('EXACT',json.dumps(z),flush=True)
    best=min(exact,key=lambda z:z['exact_bytes'])
    out={'kind':'imperial-integrated-latent-oracle-v13','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'base_search_bytes':int(base_total),'base_offsets':[list(x) for x in offs],'best':best,'exact':exact,'screens':[x[1] for x in candidates],
         'scope':'Deliberately impossible ceiling test, NOT a compression claim. The baseline rate-discovered causal predictor is charged normally. Its source-domain prediction-error field is cumulatively integrated in time or channel, and an exact SVD is computed. For each rank k, the differentiated rank-k integrated component is handed to encoder and decoder for FREE: its basis, coefficients, and all oracle knowledge cost zero. The decoder still receives a physically serialized exact quantized correction field through the current PR750 residual coder, and source reconstruction/max-error are replayed exactly. If a small free rank cannot push actual remaining bytes near half of SZ3, integrated low-rank structure is not the missing 2x mechanism. If it can, a subsequent experiment must encode/learn the latent component causally and charge every byte.'}
    json.dump(out,open('imperial_integrated_latent_oracle_v13.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k not in ('screens','exact')},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
