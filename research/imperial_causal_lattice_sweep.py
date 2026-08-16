import json,sys,math
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_address_aware_legal_search as q
import imperial_compact_ar32_audit as car

FACS=(1.0,1.25,1.5,1.75,2.0)
VERSION=4


def build_fac(X,eps,fac):
    h=float(eps*fac);lo,hi=x.g.legal_q(X,eps,h);Q=x.g._initial(lo,hi,0);changes=0
    for _ in range(x.g.ROUNDS):
        dts,dcs,co,intercept=x.g.fit_model(Q)
        Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);changes+=int(ch)
    dts,dcs,co,intercept=x.g.fit_model(Q)
    Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);changes+=int(ch)
    return h,lo,hi,np.ascontiguousarray(Q),np.ascontiguousarray(D),dts,dcs,co,intercept,changes


def compact_stream(Q,D,dts,dcs,co,intercept,X,eps,h):
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);defect,dd=x.compact_defect(D);stream=bytes([VERSION])+model+defect
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=x.decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('compact defect parse')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('compact Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'maxerr':me,'model_detail':md,'defect_detail':dd}


def compact_ar32(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);kf,_=car.encode_k_compact(K);stream=bytes([car.VERSION])+model+kf;pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=car.decode_k_compact(stream,pos,X.shape)
    if pos!=len(stream) or not np.array_equal(Kd,K):raise RuntimeError('AR compact decode')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR compact replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError('AR hard')
    return {'bytes':len(stream),'model_bytes':len(model),'innovation_bytes':len(kf),'model_rep':mname,'maxerr':me}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);arb=compact_ar32(X,eps);lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(q.NBITS,np.float64);rows=[]
    for fac in FACS:
        h,lo,hi,Q,D,dts,dcs,co,intercept,proj_changes=build_fac(X,eps,fac)
        Q,D,cnt,ch,sc=q.causal_search(Q,lo,hi,D,dts,dcs,co,intercept,x.g.SCALE,q.MODES,lf,w,q.PASSES)
        Dr=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError((fac,'defect mismatch'))
        r=compact_stream(Q,D,dts,dcs,co,intercept,X,eps,h);r.update({'h_factor':fac,'h':h,'projection_changes':proj_changes,'causal_changes':int(ch),'causal_surrogate_bits':float(sc),'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'delta_vs_compact_ar32':r['bytes']-arb['bytes'],'gain_vs_compact_ar32':arb['bytes']/r['bytes'],'gain_vs_sz3':szb/r['bytes']});rows.append(r);print(json.dumps({k:v for k,v in r.items() if k not in ('model_detail','defect_detail')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'factors':list(FACS),'sz3':{'bytes':int(szb),'orientation':ori},'compact_ar32':arb,'rows':rows,'best':best,'scope':'Decoder-real legal-lattice spacing sweep under the final causal-address-aware search. Each public h/epsilon factor independently rebuilds its charged learned sparse generator, globally projects the reconstruction into the unchanged hard-error box, then optimizes legal Q states against the fixed decoder-shared causal objective. Final streams use exact compact NOVA model/causal framing and are parsed/replayed independently. Compact AR32 is rebuilt in the same process. This tests whether h=1.5epsilon, inherited from old residual objectives, remains optimal after computation-for-communication search.'};json.dump(out,open('imperial_causal_lattice_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_factor':best['h_factor'],'best_nova':best['bytes'],'compact_ar32':arb['bytes'],'delta':best['delta_vs_compact_ar32'],'sz3':int(szb)}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
