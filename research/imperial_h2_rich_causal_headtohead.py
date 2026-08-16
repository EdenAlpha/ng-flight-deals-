import json,sys
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

HFAC=2.0
VERSION_N=9
VERSION_A=10


def build_h2(X,eps):
    h=float(HFAC*eps);lo,hi=x.g.legal_q(X,eps,h)
    if np.any(lo!=hi):raise RuntimeError(('h2 not unique',int(np.max(hi-lo+1)),float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))))
    Q=np.ascontiguousarray(lo.copy(),np.int32)
    dts,dcs,co,intercept=x.g.fit_model(Q)
    D=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
    return h,Q,D,dts,dcs,co,intercept


def encode_nova(X,eps):
    h,Q,D,dts,dcs,co,intercept=build_h2(X,eps)
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);field,detail=rc.compact_rich_defect(D);stream=bytes([VERSION_N])+model+field
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('NOVA field replay')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('NOVA Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('NOVA hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'maxerr':me,'h':h,'h_factor':HFAC},md,detail


def encode_ar32(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);field,detail=rc.compact_rich_defect(K);stream=bytes([VERSION_A])+model+field
    pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('AR field replay')
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('AR coef replay')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR R replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'model_rep':mname,'maxerr':me},detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);nova,md,nd=encode_nova(X,eps);ar32,ad=encode_ar32(X,eps)
    nova['delta_vs_ar32']=nova['bytes']-ar32['bytes'];nova['gain_vs_ar32']=ar32['bytes']/nova['bytes'];nova['gain_vs_sz3']=szb/nova['bytes']
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'nova_h2':nova,'ar32_rich':ar32,'nova_model_detail':md,'nova_field_detail':nd,'ar32_field_detail':ad,'scope':'Symmetric fair head-to-head prompted by PR573. NOVA uses the maximum universally hard-error-safe lattice spacing h=2epsilon, which gives exactly one legal lattice state per source sample on this object; there is therefore no encoder legal-state search. A charged learned sparse generator is fit to that deterministic Q field. Both the NOVA defect field and frozen AR32 innovation K are then encoded with the exact same richer decoder-shared causal bitplane grammar and packed framing. Each literal stream is parsed to EOF, its model/field/reconstruction is reproduced exactly, and the unchanged source hard-error bound is checked. Only physical bytes count.'}
    json.dump(out,open('imperial_h2_rich_causal_headtohead.json','w'),indent=2)
    print(json.dumps({'summary':{'NOVA_h2':nova['bytes'],'AR32_rich':ar32['bytes'],'delta':nova['delta_vs_ar32'],'gain_ar32':nova['gain_vs_ar32'],'NOVA_model':nova['model_bytes'],'NOVA_field':nova['field_bytes'],'AR_model':ar32['model_bytes'],'AR_field':ar32['field_bytes'],'SZ3':int(szb),'maxerr':nova['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
