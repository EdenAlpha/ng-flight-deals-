import json,sys,math
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_address_aware_legal_search as q


def reproduce_causal_best(X,eps):
    h,Q,D,dts,dcs,co,intercept,prior=x.ca.build_pair_state(X,eps);lo,hi=x.g.legal_q(X,eps,h)
    lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(q.NBITS,np.float64);Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy())
    Q,D,cnt,ch,sc=q.causal_search(Q,lo,hi,D,dts,dcs,co,intercept,x.g.SCALE,q.MODES,lf,w,q.PASSES)
    Dr=x.g._all_defects(Q,dts,dcs,co,intercept,x.g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('causal-aware exact defect mismatch')
    return h,Q,D,dts,dcs,co,intercept,{'prior':prior,'causal_changes':int(ch),'causal_surrogate_bits':float(sc)}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);arb=x.g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,search=reproduce_causal_best(X,eps)
    ob,_,OD,odetail=x.ca.causal_frame(D);old=x.c.validate(X,eps,h,Q,OD,dts,dcs,co,intercept,ob,'causal_aware_framed',odetail)
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);defect,ddetail=x.compact_defect(D);stream=bytes([x.VERSION])+model+defect
    pos=0
    if stream[pos]!=x.VERSION:raise RuntimeError('version')
    pos+=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=x.decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('compact parse/defect mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('compact Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=len(stream);r={'bytes':total,'bps':8*total/X.size,'model_bytes':len(model),'defect_bytes':len(defect),'version_bytes':1,'maxerr':me,'gain_vs_ar32':arb['bytes']/total,'gain_vs_sz3':szb/total,'delta_vs_ar32':total-arb['bytes'],'delta_vs_framed':total-old['bytes']}
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'public_codec_config':{'h_factor':1.5,'scale_q12':x.g.SCALE,'ntaps':x.K,'tap_grammar_size':x.NGRAM,'shape_external':True,'epsilon_external':True},'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'framed':old,'compact':r,'model_detail':md,'defect_detail':ddetail,'search':search,'scope':'Compact self-decoding NOVA container applied to the exact causal-address-aware legal reconstruction from PR546. Shape and epsilon are external decoder arguments under the same benchmark API convention used for matched SZ3. The public fixed codec defines h=1.5epsilon, Q12 scale, tap count and grammar. Tap set is exact combinatorial rank, coefficients/intercept are signed varints, and causal planes use compact selectors/lengths. The literal stream is parsed to EOF, its exact defect and Q are independently replayed, and the source hard-error bound is verified. Only physical stream length counts.'};json.dump(out,open('imperial_causal_aware_compact_nova.json','w'),indent=2)
    print(json.dumps({'summary':{'framed':old['bytes'],'compact':total,'ar32':arb['bytes'],'sz3':int(szb),'delta_ar32':total-arb['bytes'],'gain_ar32':arb['bytes']/total,'model':len(model),'defect':len(defect),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
