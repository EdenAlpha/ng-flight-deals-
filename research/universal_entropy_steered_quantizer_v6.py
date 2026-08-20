#!/usr/bin/env python3
from __future__ import annotations
import json,math,sys
from collections import defaultdict
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

V1_BYTES=22390
FACTORS=(1.0,2.0/3.0,0.5)
MODES=('temporal','vote','bits','adaptive')


def zz(k):
    k=int(k);return 2*k if k>=0 else -2*k-1


def pop(x):return int(x).bit_count()

def clipk(k):return max(-15,min(15,int(k)))


def choose(cands,x,p,step,K,c,t,mode,counts):
    prev=int(K[c,t-1]) if t>0 else 0
    prev2=int(K[c,t-2]) if t>1 else prev
    left=int(K[c-1,t]) if c>0 else prev
    diag=int(K[c-1,t-1]) if c>0 and t>0 else prev
    def err(k):return abs(float(x)-(float(p)+step*int(k)))
    if mode=='temporal':
        return min(cands,key=lambda k:(4*(k!=prev)+2*(k!=left)+abs(k),err(k),abs(k),k))
    if mode=='vote':
        qs=(prev,prev2,left,diag)
        return min(cands,key=lambda k:(3*sum(k!=q for q in qs)+abs(k),err(k),abs(k),k))
    if mode=='bits':
        return min(cands,key=lambda k:(3*pop(zz(k)^zz(prev))+2*pop(zz(k)^zz(left))+pop(zz(k)^zz(diag))+zz(k).bit_length(),err(k),abs(k),k))
    ctx=(clipk(prev),clipk(left),clipk(diag))
    d=counts[ctx]
    return min(cands,key=lambda k:(-d.get(int(k),0),2*(k!=prev)+(k!=left),abs(k),err(k),k))


def encode_steered(X,eps,step,co,offs,mode):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);counts=defaultdict(dict)
    choices=0
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=u.sample_pred(R,c,t,co,offs);x=float(X[c,t])
            lo=int(math.ceil((x-eps-p)/step-1e-12));hi=int(math.floor((x+eps-p)/step+1e-12))
            if lo>hi:raise RuntimeError(('no admissible code',c,t,lo,hi,x,p,step,eps))
            cands=list(range(lo,hi+1));choices+=len(cands)
            k=int(choose(cands,x,p,step,K,c,t,mode,counts));K[c,t]=k;R[c,t]=int(p+step*k)
            if mode=='adaptive':
                prev=int(K[c,t-1]) if t>0 else 0;left=int(K[c-1,t]) if c>0 else prev;diag=int(K[c-1,t-1]) if c>0 and t>0 else prev
                ctx=(clipk(prev),clipk(left),clipk(diag));d=counts[ctx];d[k]=d.get(k,0)+1
    return R,K,choices/K.size


def decode_k(K,step,co,offs):
    R=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):R[c,t]=u.sample_pred(R,c,t,co,offs)+step*int(K[c,t])
    return R


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,_,sbest,shist=u.search_sample(X);_,_,_,mb,ob,cod=sbest
    rows=[]
    for fac in FACTORS:
        step=max(1,int(round(eps*fac)))
        for mode in MODES:
            R,K,avg_choices=encode_steered(X,eps,step,cod,offs,mode)
            field,Kd,detail=u.exact_field(K);Rd=decode_k(Kd,step,cod,offs)
            if not np.array_equal(Rd,R):raise RuntimeError(('replay',fac,mode))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps,fac,mode))
            total=fair.COMMON_HEADER+1+len(ob)+len(mb)+3+field
            row={'factor':fac,'step':step,'mode':mode,'bytes':int(total),'field_bytes':field,'avg_admissible_codes':avg_choices,
                 'k_zero_fraction':float(np.mean(K==0)),'maxerr':me,'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total)}
            rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-entropy-steered-quantizer-v6','shape':list(X.shape),'eps':eps,'base_offsets':[list(x) for x in offs],
         'v1_bytes':V1_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,'best':best,'rows':rows,
         'principle':'Use a finer internal reconstruction lattice so each sample has multiple admissible codes inside the same hard error bound, then choose among those valid codes to make the causal residual field easier to entropy-code. Decoder only receives the chosen K field plus step/config metadata.'}
    json.dump(out,open('universal_entropy_steered_quantizer_v6.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
