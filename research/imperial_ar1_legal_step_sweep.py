import json,sys
import h5py,numpy as np
import imperial_ar1_legal_trajectory_address as lt
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(240,248,252,256,260,264,266,267)
OBJECTIVES=('lowbits','causal_bits','symbol_causal','zero_mag')
FORCE_LEGAL={248,256,260,264,266,267}


def build_step(X,coef,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared')
            k=int(np.rint((float(X[c,t])-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    return R,K


def replay_step(X,coef,K,eps,step):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared');R[c,t]=pred+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',step,me,eps))
    return R,me


def exact_row(K,X,coef,eps,step,objective,model_bytes,extra=None):
    fb,_,Kd,detail=lt.A.hybrid_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('K decode',step,objective))
    _,me=replay_step(X,coef,Kd,eps,step)
    total=fair.COMMON_HEADER+1+model_bytes+int(fb)
    r={'step':step,'objective':objective,'bytes':int(total),'field_bytes':int(fb),'model_bytes':model_bytes,'maxerr':me,'field_detail':detail}
    if extra:r.update(extra)
    return r


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    co=fair.fit(X,1,'prefix64');model,mname=fair.encode_model(co);coef,pos=fair.decode_model(model,0,2)
    if pos!=len(model):raise RuntimeError('model trailing')
    baselines=[];cache={}
    for step in STEPS:
        R,K=build_step(X,coef,step);me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('baseline hard',step,me,eps))
        row=exact_row(K,X,coef,eps,step,'nearest_baseline',len(model),{'changed_k':0,'ambiguity_ratio_est':max(0.0,2*eps/step-1.0)})
        baselines.append(row);cache[step]=(K,R);print(json.dumps({k:v for k,v in row.items() if k!='field_detail'},indent=2),flush=True)
    # Exact baseline rate screens the spacing, but force several slack-rich steps so a
    # worse nearest stream cannot hide a much better legal-trajectory solution.
    ranked=sorted(baselines,key=lambda r:r['bytes']);selected=set(r['step'] for r in ranked[:3])|FORCE_LEGAL
    rows=list(baselines)
    for step in STEPS:
        if step not in selected:continue
        K0,_=cache[step];C=lt.cost_model(K0);lt.STEP=step
        for kind in OBJECTIVES:
            K,R,me,diag=lt.optimize(X,coef,K0,eps,kind,C)
            row=exact_row(K,X,coef,eps,step,kind,len(model),diag);rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='field_detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];base267=next(r for r in baselines if r['step']==267)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'steps':list(STEPS),'selected_for_legal_search':sorted(selected),
         'objectives':list(OBJECTIVES),'beam':lt.BEAM,'order':1,'fit_scope':'prefix64','model_bytes':len(model),'model_rep':mname,
         'common_header_bytes':fair.COMMON_HEADER,'sz3':{'bytes':int(szb),'orientation':ori},'baseline267_bytes':base267['bytes'],'rows':rows,'best':best,
         'scope':'Lattice-slack GCA sweep on the strict AR1/prefix64 model. Step size is treated as a charged public configuration rather than fixed at the maximal 267. Smaller steps create overlap between adjacent hard-error-valid reconstruction cells, increasing the number of legal decoder trajectories. Every step is first measured with its exact nearest legal K stream. The best baseline steps plus forced slack-rich spacings are then beam-searched over every hard-error-legal neighboring K using encoder-only rate proxies. Search paths/proxies are not transmitted. Only the final exact K stream, one public step/config selector, compact model and common header count. Every candidate is physically K-decoded, recursively AR1-replayed and checked against the unchanged source error; winner is actual bytes only.'}
    json.dump(out,open('imperial_ar1_legal_step_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline267':base267['bytes'],'best':best['bytes'],'step':best['step'],'objective':best['objective'],'delta_vs_267':best['bytes']-base267['bytes'],'changed_k':best.get('changed_k',0),'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
