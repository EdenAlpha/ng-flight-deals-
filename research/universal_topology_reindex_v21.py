#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

TIME_LAGS=(1,2,4,6,8,16,32)
CMODES=('identity','half_interleave','even_odd','bit_reverse','reverse','graph')
TOP_EXACT=6


def time_order(n,L):
    return np.concatenate([np.arange(r,n,L,dtype=np.int32) for r in range(L)]) if L>1 else np.arange(n,dtype=np.int32)


def graph_order(X):
    A=X-X.mean(axis=1,keepdims=True);s=np.linalg.norm(A,axis=1);s=np.where(s>1e-12,s,1.0);A=A/s[:,None]
    C=np.abs(A@A.T);np.fill_diagonal(C,0)
    start=int(np.argmax(C.sum(axis=1)));path=[start];unused=set(range(X.shape[0]));unused.remove(start)
    while unused:
        cur=path[-1];j=max(unused,key=lambda q:float(C[cur,q]));path.append(int(j));unused.remove(j)
    # 2-opt on path edge score.
    improved=True
    while improved:
        improved=False;base=sum(float(C[path[i],path[i+1]]) for i in range(len(path)-1))
        for i in range(1,len(path)-2):
            for j in range(i+1,len(path)-1):
                q=path[:i]+path[i:j+1][::-1]+path[j+1:]
                sc=sum(float(C[q[k],q[k+1]]) for k in range(len(q)-1))
                if sc>base+1e-9:path=q;base=sc;improved=True
    return np.asarray(path,np.int32)


def bitrev(n=32):
    bits=int(np.ceil(np.log2(n)));return np.asarray(sorted(range(n),key=lambda x:int(f'{x:0{bits}b}'[::-1],2)),np.int32)


def channel_order(X,mode):
    n=X.shape[0]
    if mode=='identity':return np.arange(n,dtype=np.int32),0
    if mode=='half_interleave':
        h=n//2;return np.asarray([z for i in range(h) for z in (i,i+h)],np.int32),0
    if mode=='even_odd':return np.r_[np.arange(0,n,2),np.arange(1,n,2)].astype(np.int32),0
    if mode=='bit_reverse':return bitrev(n),0
    if mode=='reverse':return np.arange(n-1,-1,-1,dtype=np.int32),0
    if mode=='graph':return graph_order(X),32
    raise ValueError(mode)


def invert_order(order):
    inv=np.empty_like(order);inv[order]=np.arange(len(order));return inv


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);target=szb/2.0;rows=[]
    for cm in CMODES:
        co,extra=channel_order(X,cm)
        for L in TIME_LAGS:
            to=time_order(X.shape[1],L);Xp=X[co][:,to]
            offs,search_total,sbest,hist=u.search_sample(Xp);base,R,K,mb,ob,cod=sbest
            me=float(np.max(np.abs(Xp-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard',cm,L,me,eps))
            fast=int(m.encode_k(K)[0]);order_bytes=2+extra;total=fair.COMMON_HEADER+1+len(ob)+len(mb)+order_bytes+fast
            row={'channel_mode':cm,'time_polyphase':L,'order_bytes':order_bytes,'offsets':[list(x) for x in offs],'fast_field_bytes':fast,'fast_total_bytes':int(total),'fast_gain_vs_sz3':float(szb/total),'zero_fraction':float(np.mean(K==0)),'maxerr':me}
            rows.append((total,row,co,to,R,K,mb,ob,cod,offs));print('SCREEN',json.dumps(row),flush=True)
    order=np.argsort([x[0] for x in rows])[:TOP_EXACT];exact=[]
    for ii in order:
        _,row,co,to,R,K,mb,ob,cod,offs=rows[int(ii)];fb,Kd,detail=v7.super_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError('K replay')
        Rd=np.zeros_like(K)
        for t in range(K.shape[1]):
            for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+u.STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R):raise RuntimeError(('permuted source replay',row['channel_mode'],row['time_polyphase']))
        ci=invert_order(co);ti=invert_order(to);Xhat=Rd[ci][:,ti]
        me=float(np.max(np.abs(X-Xhat.astype(np.float64))))
        total=fair.COMMON_HEADER+1+len(ob)+len(mb)+row['order_bytes']+int(fb)
        z={**row,'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':float(szb/total),'crosses_2x':bool(total<=target),'maxerr':me};exact.append(z);print('EXACT',json.dumps(z),flush=True)
    best=min(exact,key=lambda z:z['bytes'])
    out={'kind':'universal-topology-reindex-v21','shape':list(X.shape),'eps':eps,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'best':best,'exact':exact,'screens':[x[1] for x in rows],
         'principle':'Before the ordinary SZ-style predictor/quantizer/entropy pipeline, search a tiny reversible coordinate reindexing family that turns nonlocal dependencies into local neighbours. Time is optionally grouped into polyphase sequences at public lags 2/4/6/8/16/32. Channels use public fixed permutations or a source-discovered correlation path whose full 32-byte permutation is charged. The selected IDs/permutation, predictor metadata and actual residual bytes are all charged. Decoder restores the original channel/time order after exact reconstruction.'}
    json.dump(out,open('universal_topology_reindex_v21.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
