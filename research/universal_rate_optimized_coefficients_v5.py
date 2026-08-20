#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

V1_BYTES=22390
ROUNDS=4


def eval_model(X,offs,co):
    mb,_,cod=u.model_rt(np.asarray(co,np.float32));ob,od=u.offset_rt(offs)
    R,K=u.build_sample(X,cod,od);field,Kd,detail=u.exact_field(K)
    Rd=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,od)+u.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('replay')
    total=fair.COMMON_HEADER+1+len(ob)+len(mb)+field
    return int(total),field,cod,len(mb),float(np.mean(K==0)),R,K


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    offs,co,sbest,shist=u.search_sample(X)
    best=eval_model(X,offs,co);cur=np.asarray(best[2],np.float32);history=[]
    start=best[0]
    for rnd in range(ROUNDS):
        changed=False
        for j in range(len(cur)):
            base=float(cur[j])
            if j==len(cur)-1:step=u.STEP*(0.5**(rnd+2))
            else:step=max(abs(base)*0.20*(0.5**rnd),0.01*(0.5**rnd))
            winner=(best[0],cur.copy(),best)
            for mult in (-2,-1,1,2):
                cand=cur.copy();cand[j]=np.float32(base+mult*step)
                q=eval_model(X,offs,cand)
                if q[0]<winner[0]:winner=(q[0],np.asarray(q[2],np.float32),q)
            if winner[0]<best[0]:
                old=best[0];cur=winner[1];best=winner[2];changed=True
                row={'round':rnd,'coef':j,'old_bytes':old,'new_bytes':best[0],'value':float(cur[j])}
                history.append(row);print('IMPROVE',json.dumps(row),flush=True)
        print('ROUND',rnd,'bytes',best[0],flush=True)
        if not changed and rnd>=1:break
    total,field,cod,mb,kz,R,K=best
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
    out={'kind':'universal-rate-optimized-coefficients-v5','shape':list(X.shape),'eps':eps,'step':u.STEP,
         'offsets':[list(x) for x in offs],'start_bytes':start,'bytes':total,'field_bytes':field,'model_bytes':mb,
         'coefficients':cod.tolist(),'improvements':history,'maxerr':me,'k_zero_fraction':kz,
         'v1_bytes':V1_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,'gain_vs_sz3':float(szb/total),'gain_vs_v1':float(V1_BYTES/total),
         'principle':'After discovering the causal stencil, optimize the same serialized predictor coefficients directly for physical compressed bytes rather than least-squares prediction error. No extra decoder model is added.'}
    json.dump(out,open('universal_rate_optimized_coefficients_v5.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k not in ('coefficients','improvements')},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
