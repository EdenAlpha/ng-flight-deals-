import json,sys
import h5py,numpy as np
import imperial_h2_rich_causal_headtohead as h2
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

P=32;STEP=267;VERSION=14

def full_ar(X,eps):
    co=car.ar.fit_shared(X,P);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=car.ar.predict_hist(R,c0,t,co,P,'shared');k=int(np.rint((float(X[c0,t])-pred)/STEP));R[c0,t]=pred+STEP*k;K[c0,t]=k
    model,mname=car.encode_model(co);field,detail=rc.compact_rich_defect(K);stream=bytes([VERSION])+model+field
    pos=1;cod,pos=car.decode_model(stream,pos,P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('full AR field replay')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,P,'shared')+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('full AR reconstruction replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('full AR hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())},detail

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);nova,_,nd=h2.encode_nova(X,eps);ar,ad=full_ar(X,eps);nova['delta_vs_fullfit_ar32']=nova['bytes']-ar['bytes'];nova['gain_vs_fullfit_ar32']=ar['bytes']/nova['bytes'];nova['gain_vs_sz3']=szb/nova['bytes']
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'nova_h2':nova,'fullfit_ar32':ar,'nova_detail':nd,'ar_detail':ad,'scope':'Fast fairness confirmation. NOVA is the exact h=2epsilon rich-causal stream from PR590. Comparator is the same shared AR32/step267 algorithm, but its float32 coefficients are fitted on the full target tile rather than only the historical first-256 prefix. Final model bits are losslessly serialized and charged. Both NOVA defect and AR32 K use the identical rich causal coder; both literal streams are parsed/replayed and hard-error verified.'}
    json.dump(out,open('imperial_h2_vs_fullfit_ar32.json','w'),indent=2);print(json.dumps({'summary':{'NOVA':nova['bytes'],'fullfit_AR32':ar['bytes'],'delta':nova['delta_vs_fullfit_ar32'],'gain_ar32':nova['gain_vs_fullfit_ar32'],'NOVA_field':nova['field_bytes'],'AR_field':ar['field_bytes'],'NOVA_model':nova['model_bytes'],'AR_model':ar['model_bytes'],'SZ3':int(szb)}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
