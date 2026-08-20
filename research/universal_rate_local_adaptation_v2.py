#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as v1
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=v1.A;STEP=v1.STEP
CHUNKS=(32,64,128,256,512)
CURRENT_BEST=22390


def fit_local(X,offs,t0,t1):
    rows=[];yy=[]
    for t in range(t0,t1):
        if t==0:continue
        for c in range(X.shape[0]):
            rows.append([v1.off_value(X,c,t,o) for o in offs]+[1.0]);yy.append(float(X[c,t]))
    if not rows:return np.zeros(len(offs)+1,np.float16)
    co=np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(yy,np.float64),rcond=1e-7)[0]
    return co.astype(np.float16)


def build_piecewise(X,offs,chunk,table):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        co=table[min(t//chunk,len(table)-1)].astype(np.float64)
        for c in range(X.shape[0]):
            if t==0:p=0
            else:
                s=float(co[-1])
                for j,o in enumerate(offs):s+=float(co[j])*v1.off_value(R,c,t,o)
                p=int(np.rint(s))
            k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def rt_coeffs(table):
    b=np.asarray(table,dtype='<f2').tobytes();d=np.frombuffer(b,dtype='<f2').reshape(np.asarray(table).shape).copy()
    if not np.array_equal(np.asarray(table,dtype=np.float16).view(np.uint16),d.view(np.uint16)):raise RuntimeError('coeff replay')
    return b,d


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,history=v1.search_sample(X)
    # exact global v1 comparator
    _,R0,K0,smb,sob,scod=sbest
    f0,_,_=v1.exact_field(K0);global_total=fair.COMMON_HEADER+1+len(sob)+len(smb)+f0
    rows=[]
    for chunk in CHUNKS:
        table=[]
        for t0 in range(0,X.shape[1],chunk):table.append(fit_local(X,offs,t0,min(X.shape[1],t0+chunk)))
        cb,decoded=rt_coeffs(table);ob,od=v1.offset_rt(offs)
        R,K=build_piecewise(X,od,chunk,decoded);field,Kd,detail=v1.exact_field(K)
        if not np.array_equal(Kd,K):raise RuntimeError('field replay')
        Rd,_=build_piecewise(X,od,chunk,decoded)
        if not np.array_equal(Rd,R):raise RuntimeError('R replay')
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('hard error',chunk,me,eps))
        # 4 bytes: chunk length + number of coefficient vectors. Offsets serialized once.
        meta=4+len(ob)+len(cb)
        total=fair.COMMON_HEADER+1+meta+field
        row={'chunk':chunk,'chunks':len(table),'bytes':int(total),'field_bytes':field,'metadata_bytes':meta,'coeff_bytes':len(cb),
             'gain_vs_sz3':float(szb/total),'gain_vs_global_v1':float(global_total/total),'maxerr':me,'k_zero_fraction':float(np.mean(K==0))}
        rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-rate-local-adaptation-v2','shape':list(X.shape),'eps':eps,'step':STEP,'auto_discovered_offsets':[list(x) for x in offs],
         'global_v1_bytes':int(global_total),'prior_current_best':CURRENT_BEST,'sz3_bytes':int(szb),'sz3_orientation':ori,'rows':rows,'best':best,
         'principle':'Discover one generic causal graph by rate, then allow the same graph coefficients to change locally. Float16 coefficient tables are fully serialized and decoder replayed; no seismic-type labels or hand-picked final offsets.'}
    json.dump(out,open('universal_rate_local_adaptation_v2.json','w'),indent=2)
    print('FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
