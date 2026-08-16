import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

HFAC=1.9995
VERSION=4


def build_near2(X,eps):
    h=eps*HFAC
    lo,hi=g.legal_q(X,eps,h)
    Q=g._initial(lo,hi,0)
    generator_changes=0
    for _ in range(g.ROUNDS):
        dt,dc,co,it=g.fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES)
        generator_changes+=int(ch)
    dt,dc,co,it=g.fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES)
    generator_changes+=int(ch)
    D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
    lc=a.logcomb_table(X.size)
    Q2,D2,counts,address_changes=a.shape_search(np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES)
    D2=np.ascontiguousarray(g._all_defects(Q2,dt,dc,co,it,g.SCALE))
    return h,lo,hi,np.ascontiguousarray(Q2),D2,dt,dc,co,it,generator_changes,int(address_changes)


def decode_compact_model_and_defect(stream,shape):
    pos=0
    if not stream or stream[pos]!=VERSION:raise RuntimeError('version')
    pos+=1
    rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES
    ids=x.unrank_combination(rank,x.NGRAM,x.K)
    co=[]
    for _ in range(x.K):
        v,pos=x.get_svar(stream,pos);co.append(v)
    inter,pos=x.get_svar(stream,pos)
    dt=np.asarray([x.OFFS[i][0] for i in ids],np.int16)
    dc=np.asarray([x.OFFS[i][1] for i in ids],np.int16)
    co=np.asarray(co,np.int32)
    D,pos=rc.decode_compact_rich(stream,pos,shape)
    if pos!=len(stream):raise RuntimeError(('nova trailing',pos,len(stream)))
    return dt,dc,co,int(inter),D


def materialize_near2_rich(X,eps,h,Q,D,dt,dc,co,it):
    model,_,_,_,_,md=x.compact_model(dt,dc,co,it)
    defect,ddetail=rc.compact_rich_defect(D)
    stream=bytes([VERSION])+model+defect
    dt2,dc2,co2,it2,D2=decode_compact_model_and_defect(stream,Q.shape)
    if not np.array_equal(D2,D):raise RuntimeError('near2 rich defect mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):
            Qd[c0,t]=g._pred(Qd,c0,t,dt2,dc2,co2,it2,g.SCALE)+int(D2[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('near2 rich Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('near2 rich hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'version_bytes':1,'maxerr':me,'model_detail':md,'defect_detail':ddetail}


def rich_ar32(X,eps):
    co,R,K=car.build_ar32(X)
    model,mname=car.encode_model(co)
    kstream,kdetail=rc.compact_rich_defect(K)
    stream=bytes([3])+model+kstream
    pos=1
    cod,pos=car.decode_model(stream,pos,car.P+1)
    Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError(('AR rich trailing',pos,len(stream)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('AR rich coef mismatch')
    if not np.array_equal(Kd,K):raise RuntimeError('AR rich K mismatch')
    Rd=np.zeros_like(R)
    for c0 in range(X.shape[0]):
        for t in range(X.shape[1]):
            Rd[c0,t]=car.ar.predict_hist(Rd,c0,t,cod,car.P,'shared')+car.STEP*int(Kd[c0,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR rich reconstruction mismatch')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR rich hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'innovation_bytes':len(kstream),'model_rep':mname,'maxerr':me,'k_detail':kdetail}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps)
    h,lo,hi,Q,D,dt,dc,co,it,gchg,achg=build_near2(X,eps)
    rb,_,RD,rdetail=rr.restricted_rank_frame(D)
    if not np.array_equal(RD,D):raise RuntimeError('restricted baseline defect replay')
    restricted=c.validate(X,eps,h,Q,RD,dt,dc,co,it,rb,'near2_restricted_rank',rdetail)
    nova=materialize_near2_rich(X,eps,h,Q,D,dt,dc,co,it)
    ar=rich_ar32(X,eps)
    nova.update({'delta_vs_rich_ar32':nova['bytes']-ar['bytes'],'gain_vs_rich_ar32':ar['bytes']/nova['bytes'],'gain_vs_sz3':szb/nova['bytes'],'delta_vs_restricted_near2':nova['bytes']-restricted['bytes']})
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'hfac':HFAC,'h':h,'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'generator_changes':gchg,'address_changes':achg,'sz3':{'bytes':int(szb),'orientation':ori},'near2_restricted':restricted,'near2_rich_compact':nova,'rich_causal_ar32':ar,'scope':'Fair decoder-real fusion gate. The reconstruction/generator side is the independently positive near-2epsilon NOVA mechanism (h=1.9995*epsilon): relearn and fully charge the sparse causal generator, select only hard-error-legal Q states, then run the exact address-aware legal search. Instead of PR563 restricted ranking, the identical final defect is serialized with the same richer decoder-shared causal bitplane grammar and compact model/plane framing that reduced AR32 to 22,739 B in PR570. The rich-AR32 comparator is rebuilt in the same process with the identical causal grammar. Both literal streams are parsed to EOF, exact transmitted fields are recovered, full reconstructions are independently replayed and the unchanged source hard-error bound is mandatory. No historical hardcoded comparator or ideal rate is used.'}
    json.dump(out,open('imperial_near2_rich_causal_compact.json','w'),indent=2)
    print(json.dumps({'summary':{'near2_restricted':restricted['bytes'],'near2_rich':nova['bytes'],'rich_ar32':ar['bytes'],'sz3':int(szb),'delta_vs_rich_ar32':nova['delta_vs_rich_ar32'],'gain_vs_rich_ar32':nova['gain_vs_rich_ar32'],'gain_vs_sz3':nova['gain_vs_sz3'],'model':nova['model_bytes'],'defect':nova['defect_bytes'],'maxerr':nova['maxerr']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
