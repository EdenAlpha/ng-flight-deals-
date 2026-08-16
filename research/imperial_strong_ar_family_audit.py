import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_compact_ar32_audit as car
import imperial_causal_aware_rich_compact as rc
import imperial_compact_nova_container as x

ORDERS=(8,16,24,32,48,64,96)
SCOPES=('prefix256','full')
STEP=267
CANDS=[(p,s) for s in SCOPES for p in ORDERS]


def fit(X,p,scope):
    return ar.fit_shared(X[:,:256],p) if scope=='prefix256' else ar.fit_shared(X,p)


def build(X,p,scope):
    co=fit(X,p,scope);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c0,t,co,p,'shared');k=int(np.rint((float(X[c0,t])-pred)/STEP));R[c0,t]=pred+STEP*k;K[c0,t]=k
    return co,R,K


def materialize(X,eps,cid,p,scope):
    co,R,K=build(X,p,scope);model,mname=car.encode_model(co);field,detail=rc.compact_rich_defect(K);stream=bytes([cid])+model+field
    pos=0;cid2=int(stream[pos]);pos+=1
    if cid2!=cid:raise RuntimeError('selector')
    p2,scope2=CANDS[cid2]
    cod,pos=car.decode_model(stream,pos,p2+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError(('trailing',cid,pos,len(stream)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)) or not np.array_equal(Kd,K):raise RuntimeError(('field/model replay',p,scope))
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=ar.predict_hist(Rd,c0,t,cod,p2,'shared')+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('R replay',p,scope))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',p,scope,me,eps))
    return {'selector':cid,'order':p,'fit_scope':scope,'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me,'field_detail':detail,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);rows=[]
    for cid,(p,scope) in enumerate(CANDS):
        r=materialize(X,eps,cid,p,scope);r['gain_vs_sz3']=szb/r['bytes'];rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='field_detail'},flush=True))
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'step':STEP,'orders':list(ORDERS),'fit_scopes':list(SCOPES),'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Strong AR-family fairness audit. The incumbent is allowed the same favorable model-training principle as NOVA because all final model bits are transmitted: shared temporal AR orders 8/16/24/32/48/64/96 are fitted either on the historical first-256 prefix or the full target tile. Every candidate uses the same maximum safe integer step267, exact float32 model serialization, and the same rich decoder-shared causal bitplane coder used in the NOVA comparison. A real one-byte selector identifies order/scope. Every literal stream is parsed to EOF, exact coefficients/K/reconstruction are replayed, and unchanged hard source error is verified. The smallest actual stream is the strengthened incumbent target.'}
    json.dump(out,open('imperial_strong_ar_family_audit.json','w'),indent=2)
    print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_order':best['order'],'best_scope':best['fit_scope'],'model':best['model_bytes'],'field':best['field_bytes'],'sz3':int(szb),'maxerr':best['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
