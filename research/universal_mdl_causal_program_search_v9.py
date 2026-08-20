#!/usr/bin/env python3
from __future__ import annotations
import json,math,struct,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as e
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

BASE_BYTES=22382
STEP=u.STEP
TOP=14
THRS=(1,2,4,8)

# Tiny public primitive grammar. Each tuple is fully described by a small opcode + integer lags.
PRIMS=[('base',0,0),('textrap',1,0),('textrap2',2,0),('sextrap',0,-1)]
for dt in (1,2,3,4,6,8,12,16,24,32):
    for dc in (0,-1,1,-2,2,-4,4):
        PRIMS.append(('inc',dt,dc))
PRIMS=list(dict.fromkeys(PRIMS))


def rv(R,c,t,dt,dc):
    tt=t-dt;cc=c+dc
    if tt<0 or cc<0 or cc>=R.shape[0] or (dt==0 and dc>=0):return None
    return int(R[cc,tt])


def prim_pred(name,dt,dc,R,c,t,baseco,baseoffs):
    b=u.sample_pred(R,c,t,baseco,baseoffs)
    if name=='base':return b
    if name=='textrap':
        a=rv(R,c,t,1,0);q=rv(R,c,t,2,0)
        return b if a is None or q is None else 2*a-q
    if name=='textrap2':
        a=rv(R,c,t,1,0);q=rv(R,c,t,2,0);r=rv(R,c,t,3,0)
        return b if a is None or q is None or r is None else int(round(2.5*a-2*q+0.5*r))
    if name=='sextrap':
        a=rv(R,c,t,0,-1);q=rv(R,c,t,0,-2)
        return b if a is None or q is None else 2*a-q
    # Transfer a causal historical/local increment onto the current trace's previous state.
    a=rv(R,c,t,dt,dc);q=rv(R,c,t,dt+1,dc);cur=rv(R,c,t,1,0)
    if a is None or q is None or cur is None:return b
    return cur+(a-q)


def program_pred(prog,R,c,t,co,offs):
    kind=prog['kind'];pa=prim_pred(*prog['a'],R,c,t,co,offs)
    if kind=='single':return pa
    pb=prim_pred(*prog['b'],R,c,t,co,offs)
    if kind=='avg':return int(round((pa+pb)/2.0))
    if kind=='median_base':
        bb=u.sample_pred(R,c,t,co,offs);return int(np.median(np.asarray([pa,pb,bb],np.int64)))
    if kind=='near_prev':
        ref=rv(R,c,t,1,0)
        if ref is None:return pa
        return pa if abs(pa-ref)<=abs(pb-ref) else pb
    if kind=='near_left':
        ref=rv(R,c,t,0,-1)
        if ref is None:return pa
        return pa if abs(pa-ref)<=abs(pb-ref) else pb
    if kind=='activity_gate':
        x=rv(R,c,t,1,0);y=rv(R,c,t,2,0)
        active=0 if x is None or y is None else abs(x-y)
        return pb if active>prog['thr']*STEP else pa
    if kind=='agreement_gate':
        return int(round((pa+pb)/2.0)) if abs(pa-pb)<=prog['thr']*STEP else pa
    raise ValueError(kind)


def build(X,prog,co,offs,Kgiven=None):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=program_pred(prog,R,c,t,co,offs)
            k=int(Kgiven[c,t]) if Kgiven is not None else int(np.rint((float(X[c,t])-p)/STEP))
            K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def prim_id(p):return PRIMS.index(tuple(p))

def program_blob(prog):
    kinds={'single':0,'avg':1,'median_base':2,'near_prev':3,'near_left':4,'activity_gate':5,'agreement_gate':6}
    b=bytearray([kinds[prog['kind']],prim_id(prog['a'])])
    if prog['kind']!='single':b.append(prim_id(prog['b']))
    if 'thr' in prog:b.append(int(prog['thr']))
    return bytes(b)


def screen(X,prog,co,offs):
    R,K=build(X,prog,co,offs);legacy=int(m.encode_k(K)[0]);pb=program_blob(prog)
    return legacy+len(pb),R,K,pb


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,shist=u.search_sample(X);_,_,_,mb,ob,cod=sbest
    singles=[]
    for p in PRIMS:
        prog={'kind':'single','a':list(p)};q=screen(X,prog,cod,offs);singles.append((q[0],p,prog,q))
    singles.sort(key=lambda z:z[0]);top=singles[:TOP]
    candidates=[z[2] for z in top]
    # Compose only the best primitives; MDL discourages bloated programs automatically.
    for i in range(min(10,len(top))):
        for j in range(i+1,min(10,len(top))):
            a=list(top[i][1]);b=list(top[j][1])
            for kind in ('avg','median_base','near_prev','near_left'):
                candidates.append({'kind':kind,'a':a,'b':b})
            for th in THRS:
                candidates.append({'kind':'activity_gate','a':a,'b':b,'thr':th})
                candidates.append({'kind':'activity_gate','a':b,'b':a,'thr':th})
                candidates.append({'kind':'agreement_gate','a':a,'b':b,'thr':th})
    screened=[]
    for prog in candidates:
        q=screen(X,prog,cod,offs);screened.append((q[0],prog,q))
    screened.sort(key=lambda z:z[0])
    # Exact-materialized finalist ranking using the improved #750 entropy coder.
    rows=[]
    for sc,prog,q in screened[:16]:
        _,R,K,pb=q;field,Kd,detail=e.super_frame(K);Rd,Kcheck=build(X,prog,cod,offs,Kgiven=Kd)
        if not np.array_equal(Kcheck,K) or not np.array_equal(Rd,R):raise RuntimeError(('program replay',prog))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps,prog))
        total=fair.COMMON_HEADER+1+len(ob)+len(mb)+len(pb)+field
        row={'program':prog,'program_bytes':len(pb),'bytes':int(total),'field_bytes':int(field),'screen_score':int(sc),'maxerr':me,
             'gain_vs_sz3':float(szb/total),'gain_vs_base':float(BASE_BYTES/total),'k_zero_fraction':float(np.mean(K==0))}
        rows.append(row);print('EXACT',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-mdl-causal-program-search-v9','shape':list(X.shape),'eps':eps,'step':STEP,'base_bytes':BASE_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,
         'base_offsets':[list(x) for x in offs],'primitive_count':len(PRIMS),'candidate_count':len(candidates),'best':best,'rows':rows,
         'principle':'Search a tiny generic causal program language, not just a linear stencil. Programs can transfer historical increments, extrapolate, average/median experts, or switch experts from decoder-known activity/agreement. Rank by physical program-description bytes plus physical residual bytes; replay the serialized program and residual exactly.'}
    json.dump(out,open('universal_mdl_causal_program_search_v9.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
