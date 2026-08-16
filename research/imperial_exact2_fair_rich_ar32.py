import json,sys,math
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_address_aware_legal_search as q
import imperial_causal_aware_rich_compact as rc
import imperial_compact_ar32_audit as car

HFAC=2.0
VERSION_COMPACT=4
VERSION_RICH=5
VERSION_AR=3


def build_exact2(X,eps):
    h=float(eps*HFAC);lo,hi=x.g.legal_q(X,eps,h);Q=x.g._initial(lo,hi,0);changes=0
    for _ in range(x.g.ROUNDS):
        dts,dcs,co,intercept=x.g.fit_model(Q)
        Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);changes+=int(ch)
    dts,dcs,co,intercept=x.g.fit_model(Q)
    Q,D,H,score,nz,ch=x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,x.g.SCALE,False,x.g.PASSES);changes+=int(ch)
    D=np.ascontiguousarray(x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE))
    lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(q.NBITS,np.float64)
    Q,D,cnt,cchg,sc=q.causal_search(np.ascontiguousarray(Q),lo,hi,D,dts,dcs,co,intercept,x.g.SCALE,q.MODES,lf,w,q.PASSES)
    Dr=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('exact2 defect mismatch')
    return h,lo,hi,np.ascontiguousarray(Q),np.ascontiguousarray(D),dts,dcs,co,intercept,changes,int(cchg),float(sc)


def decode_model(stream,pos):
    rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES
    ids=x.unrank_combination(rank,x.NGRAM,x.K);coef=[]
    for _ in range(x.K):
        v,pos=x.get_svar(stream,pos);coef.append(v)
    inter,pos=x.get_svar(stream,pos)
    dts=np.asarray([x.OFFS[i][0] for i in ids],np.int16)
    dcs=np.asarray([x.OFFS[i][1] for i in ids],np.int16)
    return dts,dcs,np.asarray(coef,np.int32),int(inter),pos


def replay_nova(X,eps,h,Q,stream,rich):
    pos=0;want=VERSION_RICH if rich else VERSION_COMPACT
    if not stream or stream[pos]!=want:raise RuntimeError('NOVA version')
    pos+=1;dts,dcs,co,intercept,pos=decode_model(stream,pos)
    if rich:D,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    else:D,pos=x.decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream):raise RuntimeError(('NOVA trailing',rich,pos,len(stream)))
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):Qd[c,t]=x.g._pred(Qd,c,t,dts,dcs,co,intercept,x.g.SCALE)+int(D[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError(('NOVA Q replay',rich))
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('NOVA hard',rich,me,eps))
    return D,me


def materialize_nova(X,eps,h,Q,D,dts,dcs,co,intercept,rich):
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept)
    if rich:defect,dd=rc.compact_rich_defect(D);version=VERSION_RICH
    else:defect,dd=x.compact_defect(D);version=VERSION_COMPACT
    stream=bytes([version])+model+defect
    Dd,me=replay_nova(X,eps,h,Q,stream,rich)
    if not np.array_equal(Dd,D):raise RuntimeError(('NOVA D replay',rich))
    return {'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'maxerr':me,'model_detail':md,'defect_detail':dd}


def rich_ar32(X,eps):
    co,R,K=car.build_ar32(X);model,mname=car.encode_model(co);kstream,kdetail=rc.compact_rich_defect(K);stream=bytes([VERSION_AR])+model+kstream
    pos=1;cod,pos=car.decode_model(stream,pos,car.P+1);Kd,pos=rc.decode_compact_rich(stream,pos,X.shape)
    if pos!=len(stream):raise RuntimeError(('AR trailing',pos,len(stream)))
    if not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('AR coef mismatch')
    if not np.array_equal(Kd,K):raise RuntimeError('AR K mismatch')
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=car.ar.predict_hist(Rd,c,t,cod,car.P,'shared')+car.STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('AR reconstruction mismatch')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'innovation_bytes':len(kstream),'model_rep':mname,'maxerr':me,'k_detail':kdetail}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps)
    h,lo,hi,Q,D,dts,dcs,co,intercept,pchg,cchg,score=build_exact2(X,eps)
    compact=materialize_nova(X,eps,h,Q,D,dts,dcs,co,intercept,False)
    rich=materialize_nova(X,eps,h,Q,D,dts,dcs,co,intercept,True)
    ar=rich_ar32(X,eps)
    for r in (compact,rich):
        r['delta_vs_rich_ar32']=r['bytes']-ar['bytes'];r['gain_vs_rich_ar32']=ar['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes']
    best=min((('compact_causal',compact),('rich_causal',rich)),key=lambda z:z[1]['bytes'])
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'h_factor':HFAC,'h':h,'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'projection_changes':pchg,'causal_changes':cchg,'causal_surrogate_bits':score,'sz3':{'bytes':int(szb),'orientation':ori},'rich_causal_ar32':ar,'exact2_compact_nova':compact,'exact2_rich_nova':rich,'best_nova_rep':best[0],'best_nova':best[1],'scope':'Single-process fair exact-2epsilon audit. The NOVA side reproduces the h=2.0*epsilon causal-lattice mechanism that won PR573, with the charged sparse causal generator and exact source hard-error contract. The identical final NOVA model/defect is materialized twice: the compact causal container used by PR573 and the richer causal bitplane grammar used by PR570. The AR32 side is independently rebuilt with its strongest known rich-causal innovation grammar. Every literal stream is parsed to EOF, exact transmitted fields are recovered, causal reconstructions are replayed, and source-domain hard error is checked. This resolves cross-run comparator ambiguity and separately measures whether richer causal coding helps the exact-2epsilon NOVA state.'}
    json.dump(out,open('imperial_exact2_fair_rich_ar32.json','w'),indent=2)
    print(json.dumps({'summary':{'exact2_compact':compact['bytes'],'exact2_rich':rich['bytes'],'rich_ar32':ar['bytes'],'sz3':int(szb),'best_nova_rep':best[0],'best_nova':best[1]['bytes'],'delta_vs_rich_ar32':best[1]['bytes']-ar['bytes'],'gain_vs_rich_ar32':ar['bytes']/best[1]['bytes'],'gain_vs_sz3':szb/best[1]['bytes'],'maxerr':best[1]['maxerr']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
