import json,sys
import h5py,numpy as np
import imperial_compact_nova_container as x


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);arb=x.g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,search=x.reproduce_best(X,eps)
    ob,_,OD,odetail=x.ca.causal_frame(D);old=x.c.validate(X,eps,h,Q,OD,dts,dcs,co,intercept,ob,'old_framed_causal',odetail)
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);defect,ddetail=x.compact_defect(D);stream=bytes([x.VERSION])+model+defect
    pos=0
    if stream[pos]!=x.VERSION:raise RuntimeError('version')
    pos+=1
    rank2=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids2=x.unrank_combination(rank2,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):q,pos=x.get_svar(stream,pos);co2.append(q)
    inter2,pos=x.get_svar(stream,pos);ddt2=np.asarray([x.OFFS[i][0] for i in ids2],np.int16);ddc2=np.asarray([x.OFFS[i][1] for i in ids2],np.int16);dco2=np.asarray(co2,np.int32)
    DD,pos=x.decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream):raise RuntimeError(('container trailing',pos,len(stream)))
    if not np.array_equal(DD,D):raise RuntimeError('compact defect mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,ddt2,ddc2,dco2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('compact Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=len(stream);result={'bytes':total,'bps':8*total/X.size,'maxerr':me,'model_bytes':len(model),'defect_bytes':len(defect),'version_bytes':1,'gain_vs_ar32':arb['bytes']/total,'gain_vs_sz3':szb/total,'delta_vs_ar32':total-arb['bytes'],'delta_vs_old':total-old['bytes']}
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'public_codec_config':{'h_factor':1.5,'scale_q12':x.g.SCALE,'ntaps':x.K,'tap_grammar_size':x.NGRAM,'shape_external':True,'epsilon_external':True},'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'old':old,'compact':result,'model_detail':md,'defect_detail':ddetail,'search':search,'scope':'Fully materialized compact NOVA container on the exact PR543 best hard-Imperial legal reconstruction. Shape and epsilon remain external decoder arguments exactly as in the matched SZ3 benchmark API. Fixed public codec configuration includes h=1.5*epsilon, Q12 scale, tap count and the 112-tap candidate grammar. The 20 selected taps are represented by an exact combinatorial rank; coefficients/intercept use signed varints. Causal defect planes use one compact selector/tail-bit byte plus a varint payload length. The literal stream is parsed from byte zero to EOF, the model and defect are independently recovered, exact Q is causally replayed, and source hard error is verified. No ideal or unmaterialized rate is counted.'}
    json.dump(out,open('imperial_compact_nova_container.json','w'),indent=2);print(json.dumps({'summary':{'old':old['bytes'],'compact':total,'ar32':arb['bytes'],'sz3':int(szb),'delta_ar32':total-arb['bytes'],'gain_ar32':arb['bytes']/total,'model':len(model),'defect':len(defect),'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
