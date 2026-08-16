import json,sys
import h5py,numpy as np
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car
import imperial_compact_nova_container as x

VERSION=3


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);standard=rc.compact_ar32_bytes(X,eps);co,R,K=car.build_ar32(X)
    model,mname=car.encode_model(co);kstream,kdetail=rc.compact_rich_defect(K);stream=bytes([VERSION])+model+kstream
    pos=0
    if stream[pos]!=VERSION:raise RuntimeError('version')
    pos+=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError(('AR rich trailing',pos,len(stream)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('AR rich coef mismatch')
    if not np.array_equal(Kd,K):raise RuntimeError('AR rich K mismatch')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR rich reconstruction mismatch')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR rich hard',me,eps))
    rich={'bytes':len(stream),'model_bytes':len(model),'innovation_bytes':len(kstream),'model_rep':mname,'maxerr':me,'delta_vs_standard_compact':len(stream)-standard['bytes'],'gain_vs_sz3':szb/len(stream)}
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'standard_compact_ar32':standard,'rich_causal_ar32':rich,'k_detail':kdetail,'scope':'Strong-incumbent audit. The AR32 predictor, exact float32 coefficients, step267 innovation K and reconstruction are unchanged. Only the lossless innovation representation is replaced by the exact same richer decoder-shared causal bitplane grammar and packed 3-byte plane framing used by the NOVA head-to-head. The AR model remains exactly lossless and charged. The literal stream is parsed to EOF, coefficient bits and K are recovered exactly, recursive AR32 reconstruction is reproduced exactly, and unchanged hard error is verified. This tests whether NOVA gains are architectural or merely a generic entropy-coder gain available to AR32 as well.'};json.dump(out,open('imperial_ar32_rich_causal_audit.json','w'),indent=2)
    print(json.dumps({'summary':{'standard_compact_ar32':standard['bytes'],'rich_causal_ar32':rich['bytes'],'delta':rich['delta_vs_standard_compact'],'model':rich['model_bytes'],'innovation':rich['innovation_bytes'],'sz3':int(szb),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
