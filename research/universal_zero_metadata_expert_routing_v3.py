#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from collections import deque
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

STEP=u.STEP
V1_BYTES=22390
BANKS=((1,8),(1,3,8),(1,2,4,8),(1,2,3,5,8))
WINDOWS=(2,4,8,16,32,64,128)
MODES=('global','channel')
COSTS=('mag','prefix')


def pred(R,c,t,co,offs):
    return u.sample_pred(R,c,t,co,offs)


def loss_cost(r,p,kind):
    q=abs(int(np.rint((float(r)-float(p))/STEP)))
    if kind=='mag': return q
    if q==0:return 0
    return 1+2*q.bit_length()


def route_build(X,experts,window,mode,cost_kind,Kgiven=None):
    nc,nt=X.shape;ne=len(experts)
    R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    picks=np.zeros((nc,nt),np.uint8)
    if mode=='global':
        sums=np.zeros(ne,np.int64);hist=[deque() for _ in range(ne)]
    else:
        sums=np.zeros((nc,ne),np.int64);hist=[[deque() for _ in range(ne)] for _ in range(nc)]
    for t in range(nt):
        for c in range(nc):
            ps=[pred(R,c,t,co,offs) for offs,co in experts]
            ss=sums if mode=='global' else sums[c]
            e=int(np.argmin(ss));p=ps[e];picks[c,t]=e
            if Kgiven is None:k=int(np.rint((float(X[c,t])-p)/STEP))
            else:k=int(Kgiven[c,t])
            K[c,t]=k;r=int(p+STEP*k);R[c,t]=r
            for j,pj in enumerate(ps):
                z=loss_cost(r,pj,cost_kind)
                if mode=='global':
                    h=hist[j];h.append(z);sums[j]+=z
                    if len(h)>window:sums[j]-=h.popleft()
                else:
                    h=hist[c][j];h.append(z);sums[c,j]+=z
                    if len(h)>window:sums[c,j]-=h.popleft()
    return R,K,picks


def model_bank(X,selected,prefixes):
    cols=u.feature_matrix(X,u.SAMPLE_POOL);experts=[];model_bytes=0;meta=[]
    for n in prefixes:
        offs=selected[:n];co=u.fit_cols(X,cols,offs,True);mb,_,cod=u.model_rt(co)
        model_bytes+=len(mb);experts.append((offs,cod));meta.append({'prefix':n,'model_bytes':len(mb),'coefficients':cod.tolist()})
    return experts,model_bytes,meta


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    selected,_,_,shist=u.search_sample(X)
    full_ob,selected_rt=u.offset_rt(selected)
    if selected_rt!=selected:raise RuntimeError('offset bank replay')
    rows=[]
    for bank in BANKS:
        prefixes=tuple(sorted(set(min(n,len(selected)) for n in bank),reverse=True))
        if len(prefixes)<2:continue
        experts,mb,emeta=model_bank(X,selected,prefixes)
        # One offset list, one byte/expert prefix, and three public selector bytes
        metadata=len(full_ob)+len(prefixes)+mb+3
        for mode in MODES:
            for cost in COSTS:
                for w in WINDOWS:
                    R,K,picks=route_build(X,experts,w,mode,cost)
                    field,Kd,detail=u.exact_field(K)
                    Rd,Kcheck,picks_d=route_build(X,experts,w,mode,cost,Kgiven=Kd)
                    if not np.array_equal(Kcheck,K) or not np.array_equal(Rd,R) or not np.array_equal(picks_d,picks):
                        raise RuntimeError(('router replay',prefixes,mode,cost,w))
                    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
                    total=fair.COMMON_HEADER+1+metadata+field
                    counts=np.bincount(picks.reshape(-1),minlength=len(experts)).tolist()
                    row={'prefixes':list(prefixes),'mode':mode,'cost':cost,'window':w,'bytes':int(total),
                         'field_bytes':field,'metadata_bytes':metadata,'model_bytes':mb,'maxerr':me,
                         'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total),'pick_counts':counts}
                    rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-zero-metadata-expert-routing-v3','shape':list(X.shape),'eps':eps,'step':STEP,
         'discovered_offsets':[list(x) for x in selected],'v1_bytes':V1_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,
         'best':best,'rows':rows,
         'principle':'Fit a small bank of rate-discovered causal predictors, then choose the current winner entirely from decoder-known rolling reconstructed-error history. The router changes experts without transmitting per-sample or per-region selector bits.'}
    json.dump(out,open('universal_zero_metadata_expert_routing_v3.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
