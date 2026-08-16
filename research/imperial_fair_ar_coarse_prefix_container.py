import json,sys
import h5py,numpy as np
import imperial_ar1_coarse_prefix_address as cp
import imperial_dyadic_shared_resonator as ar
import imperial_compact_ar32_audit as car
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

# importing cp installs the richer + coarse-prefix decoder-shared grammar into cp.a
A=cp.a
STEP=267
COMMON_HEADER=32
CANDS=((1,'prefix64'),(1,'full'),(8,'full'),(16,'full'),(24,'full'),(32,'full'))


def fit(X,p,scope):
    if scope=='prefix64': return ar.fit_shared(X[:,:64],p)
    if scope=='full': return ar.fit_shared(X,p)
    raise ValueError(scope)


def build(X,p,coef):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared')
            k=int(np.rint((float(X[c,t])-pred)/STEP))
            R[c,t]=pred+STEP*k;K[c,t]=k
    return R,K


def one(X,eps,cid,p,scope):
    co=fit(X,p,scope)
    model,mname=car.encode_model(co)
    # model decoder knows order from the charged public candidate selector
    cod,pos=car.decode_model(model,0,p+1)
    if pos!=len(model): raise RuntimeError(('model trailing',p,scope,pos,len(model)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):
        raise RuntimeError(('model replay',p,scope))
    R,K=build(X,p,cod)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6): raise RuntimeError(('encode hard',p,scope,me,eps))
    field,_,Kd,detail=A.hybrid_frame(K)
    if not np.array_equal(Kd,K): raise RuntimeError(('K replay',p,scope))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            Rd[c,t]=ar.predict_hist(Rd,c,t,cod,p,'shared')+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R): raise RuntimeError(('R replay',p,scope))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6): raise RuntimeError(('decode hard',p,scope,mer,eps))
    # Exact common accounting: one 32-byte container header + one public candidate selector
    # + physically serialized compact model + physically serialized coarse-prefix K field.
    total=COMMON_HEADER+1+len(model)+int(field)
    return {'selector':cid,'order':p,'fit_scope':scope,'bytes':int(total),
            'common_header_bytes':COMMON_HEADER,'selector_bytes':1,
            'model_bytes':len(model),'model_rep':mname,'field_bytes':int(field),
            'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),
            'field_detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);rows=[]
    for cid,(p,scope) in enumerate(CANDS):
        r=one(X,eps,cid,p,scope);r['gain_vs_sz3']=szb/r['bytes'];rows.append(r)
        print(json.dumps({k:v for k,v in r.items() if k!='field_detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,
         'candidates':[list(x) for x in CANDS],'common_header_bytes':COMMON_HEADER,
         'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,
         'scope':'Strict common-container fairness audit after PR620. Every AR candidate uses the identical physical accounting and address language: a fixed 32-byte common container header, one-byte public candidate selector, the same compact reversible float32 model serialization, and the same rich+coarse-prefix decoder-shared K address. AR1/train64, AR1/full and full-fit AR8/16/24/32 compete. Every model and K field is physically decoded, the complete causal reconstruction is replayed and the unchanged source hard error is checked. This removes the previous mismatch between AR1 older model/header framing and the strong-AR compact container.'}
    json.dump(out,open('imperial_fair_ar_coarse_prefix_container.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_scope':best['fit_scope'],
          'best_bytes':best['bytes'],'model_bytes':best['model_bytes'],'field_bytes':best['field_bytes'],
          'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__': main(sys.argv[1])
