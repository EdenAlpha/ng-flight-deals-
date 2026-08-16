import json,sys
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

STEP=267
VERSION_N=12
VERSION_A=13


def build_spacetime(X):
    # Fully target-fitted sparse causal generator; final model is transmitted and charged.
    dts,dcs,co,intercept=x.g.fit_model(X,ntaps=x.K)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    # time-major ordering makes same-time negative-channel taps decoder-known.
    for t in range(X.shape[1]):
        for c0 in range(X.shape[0]):
            pred=x.g._pred(R,c0,t,dts,dcs,co,intercept,x.g.SCALE)
            k=int(np.rint((float(X[c0,t])-pred)/STEP));R[c0,t]=pred+STEP*k;K[c0,t]=k
    return dts,dcs,co,intercept,R,K


def encode_nova(X,eps):
    dts,dcs,co,intercept,R,K=build_spacetime(X);model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);field,detail=rc.compact_rich_defect(K);stream=bytes([VERSION_N])+model+field
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('NOVA K replay')
    Rd=np.zeros_like(R)
    for t in range(X.shape[1]):
        for c0 in range(X.shape[0]):Rd[c0,t]=x.g._pred(Rd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('NOVA R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('NOVA hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())},md,detail


def encode_ar32(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);field,detail=rc.compact_rich_defect(K);stream=bytes([VERSION_A])+model+field;pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('AR K replay')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())},detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);nova,md,nd=encode_nova(X,eps);ar32,ad=encode_ar32(X,eps);nova['delta_vs_ar32']=nova['bytes']-ar32['bytes'];nova['gain_vs_ar32']=ar32['bytes']/nova['bytes'];nova['gain_vs_sz3']=szb/nova['bytes']
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'step':STEP,'sz3':{'bytes':int(szb),'orientation':ori},'spacetime_nova':nova,'ar32':ar32,'nova_model_detail':md,'nova_field_detail':nd,'ar32_field_detail':ad,'scope':'Decoder-real shared-generator comparison using the incumbent predictive-quantization mechanism. NOVA fits a fully charged 20-tap sparse causal space-time generator from the full target tile, then uses its decoder-known prediction to shift a step267 lattice independently at every sample; only exact K is transmitted with the same rich causal lossless coder as AR32. Same-time negative-channel taps are valid because encoding/decoding is time-major. AR32 is frozen historical prefix-fit shared AR(32), also with step267 and the identical rich K coder. Both literal streams parse/replay exact K and recursive reconstruction and pass the unchanged hard source error. This tests generator quality without legal-set or fixed-lattice confounds.'}
    json.dump(out,open('imperial_spacetime_predictive_quantizer.json','w'),indent=2);print(json.dumps({'summary':{'spacetime_NOVA':nova['bytes'],'AR32':ar32['bytes'],'delta':nova['delta_vs_ar32'],'gain_ar32':nova['gain_vs_ar32'],'NOVA_model':nova['model_bytes'],'NOVA_field':nova['field_bytes'],'AR_model':ar32['model_bytes'],'AR_field':ar32['field_bytes'],'SZ3':int(szb),'maxerr':nova['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
