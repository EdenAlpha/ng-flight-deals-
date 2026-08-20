#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

STEP=u.STEP;V1_BYTES=22390
L=4;MAXLAG=96
THRESHOLDS=((1,8),(1,4),(1,2),(1,1),(2,1),(4,1))
MODES=('same','cross')


def inc_context(R,c,t):
    if t<=L:return None
    return [int(R[c,j])-int(R[c,j-1]) for j in range(t-L,t)]


def analog_candidate(R,c,t,mode):
    cur=inc_context(R,c,t)
    if cur is None:return None,None,None
    scale=1+sum(abs(x) for x in cur);best=None
    lo=max(L+1,t-MAXLAG)
    # Same-channel historical analogs.
    for s in range(lo,t):
        ctx=[int(R[c,j])-int(R[c,j-1]) for j in range(s-L,s)]
        d=sum(abs(a-b) for a,b in zip(cur,ctx));nxt=int(R[c,s])-int(R[c,s-1])
        row=(d,abs(nxt),s,c,nxt)
        if best is None or row<best:best=row
    if mode=='cross':
        # Same-time already-decoded left channels and short-lag nearby channels.
        for dc in (1,2,4,8):
            cc=c-dc
            if cc>=0:
                ctx=[int(R[cc,j])-int(R[cc,j-1]) for j in range(t-L,t)]
                d=sum(abs(a-b) for a,b in zip(cur,ctx));nxt=int(R[cc,t])-int(R[cc,t-1])
                row=(d,abs(nxt),t,cc,nxt)
                if best is None or row<best:best=row
            for cc in (c-dc,c+dc):
                if cc<0 or cc>=R.shape[0]:continue
                for lag in (1,2,4,8,16,32):
                    s=t-lag
                    if s<=L:continue
                    ctx=[int(R[cc,j])-int(R[cc,j-1]) for j in range(s-L,s)]
                    d=sum(abs(a-b) for a,b in zip(cur,ctx));nxt=int(R[cc,s])-int(R[cc,s-1])
                    row=(d,abs(nxt),s,cc,nxt)
                    if best is None or row<best:best=row
    if best is None:return None,None,None
    p=int(R[c,t-1])+best[4]
    return p,best[0],scale


def build(X,base_co,base_offs,mode,thr,Kgiven=None):
    num,den=thr;R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);used=0
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            pb=u.sample_pred(R,c,t,base_co,base_offs)
            pa,d,s=analog_candidate(R,c,t,mode)
            use=pa is not None and d*den<=num*s
            p=pa if use else pb
            if use:used+=1
            k=int(Kgiven[c,t]) if Kgiven is not None else int(np.rint((float(X[c,t])-p)/STEP))
            K[c,t]=k;R[c,t]=int(p+STEP*k)
    return R,K,used


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,shist=u.search_sample(X);_,_,_,mb,ob,cod=sbest
    rows=[]
    for mode in MODES:
        for thr in THRESHOLDS:
            R,K,used=build(X,cod,offs,mode,thr)
            field,Kd,detail=u.exact_field(K)
            Rd,Kcheck,usedd=build(X,cod,offs,mode,thr,Kgiven=Kd)
            if not np.array_equal(Kcheck,K) or not np.array_equal(Rd,R) or usedd!=used:raise RuntimeError(('replay',mode,thr))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
            total=fair.COMMON_HEADER+1+len(ob)+len(mb)+1+field
            row={'mode':mode,'threshold':list(thr),'bytes':int(total),'field_bytes':field,'analog_uses':used,
                 'analog_fraction':float(used/K.size),'maxerr':me,'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total)}
            rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-causal-analog-predictor-v4','shape':list(X.shape),'eps':eps,'step':STEP,'context_length':L,'max_lag':MAXLAG,
         'base_discovered_offsets':[list(x) for x in offs],'v1_bytes':V1_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,'best':best,'rows':rows,
         'principle':'Use the rate-discovered linear predictor as a floor, but when an already-decoded waveform-increment context closely matches an earlier causal context, copy that earlier continuation. The confidence gate is decoder-known and costs only one selector byte.'}
    json.dump(out,open('universal_causal_analog_predictor_v4.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
