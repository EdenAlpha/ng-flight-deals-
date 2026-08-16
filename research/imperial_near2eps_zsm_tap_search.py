import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_near2eps_full_hard_128x30000 as f
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

q.f.q_decode=sc.q_decode
TAPS=(8,12,16,20,24,28,32,40,48)
FAC=1.99995

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,f.C0:f.C0+q.C],np.float64).T
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0)
    meanlegal=float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))
    if int(np.max(hi-lo+1))!=1:raise RuntimeError(('expected unique near2 lattice',meanlegal,int(np.max(hi-lo+1))))
    screens=[];states={}
    for ntaps in TAPS:
        dts,dcs,co,intercept=f.fit_model(Q,ntaps=ntaps)
        D=np.ascontiguousarray(g._all_defects(Q,dts,dcs,co,intercept,f.SCALE))
        mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
        best=None
        for W in q.WINDOWS:
            bb,nb=q.encode_zsm(D,W,q.SCREEN);score=int(mb)+len(bb)
            rec={'ntaps':ntaps,'W':int(W),'screen_total':score,'screen_payload':len(bb),'model_bytes':int(mb),'screen_bits':int(nb),'zero_fraction':float(np.mean(D[:,:q.SCREEN]==0)),'screen_std':float(D[:,:q.SCREEN].astype(np.float64).std())}
            screens.append(rec);print(json.dumps({'screen':rec}),flush=True)
            if best is None or score<best[0]:best=(score,int(W))
        states[ntaps]=(dts,dcs,co,intercept,D,int(mb),mrep,best[1])
    bytap=[]
    for ntaps in TAPS:
        rows=[r for r in screens if r['ntaps']==ntaps];r=min(rows,key=lambda z:z['screen_total']);bytap.append(r)
    bytap.sort(key=lambda z:z['screen_total'])
    # Prefix screening is the public model-search rule; materialize the top three to audit ranking robustness.
    finalists=[r['ntaps'] for r in bytap[:3]]
    full=[]
    for ntaps in finalists:
        dts,dcs,co,intercept,D,mb,mrep,W=states[ntaps]
        bb,nbit=q.encode_zsm(D,W,q.NT);Dd=q.decode_zsm(bb,nbit,W,D.shape)
        if not np.array_equal(Dd,D):raise RuntimeError(('defect decode',ntaps,W))
        _,_,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
        Qd=q.f.q_decode(Dd,ddt,ddc,dco,dinter,f.SCALE)
        if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',ntaps,W))
        me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',ntaps,me,eps))
        total=int(mb)+len(bb)+q.HEADER+1
        rec={'ntaps':int(ntaps),'W':int(W),'bytes':total,'model_bytes':int(mb),'payload_bytes':len(bb),'arithmetic_bits':int(nbit),'maxerr':me,'zero_fraction':float(np.mean(D==0)),'defect_std':float(D.astype(np.float64).std())}
        full.append(rec);print(json.dumps({'full':rec}),flush=True)
    full.sort(key=lambda z:z['bytes']);best=full[0];hist=2478995;sz3=2767977
    out={'shape':[q.C,q.NT],'samples':int(X.size),'eps':eps,'hfac':FAC,'mean_legal_states':meanlegal,'tap_candidates':list(TAPS),'screens':screens,'materialized_taps':finalists,'full':full,'best':best,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/best['bytes'],'matched_sz3_bytes':sz3,'gain_vs_sz3':sz3/best['bytes'],'scope':'Full-hard charged generator-capacity search under the historical ZSM entropy language. At public h=1.99995epsilon the legal lattice is unique, so Q is fixed and there is no hidden reconstruction optimization. For each public tap count 8..48 the deterministic OMP generator is fitted, quantized, physically model-framed and its exact defect field is computed. W=4/8/64 and tap count are screened only on the first 4096 time samples using model bytes plus actual ZSM prefix bytes. The top three prefix candidates are fully ZSM encoded/decoded as an audit; the best complete physical stream is reported. Every full candidate decodes the identical defect, regenerates exact Q from its charged model and verifies hard source error. No uncharged model or ideal entropy is counted.'}
    json.dump(out,open('imperial_near2eps_zsm_tap_search.json','w'),indent=2)
    print(json.dumps({'summary':{'best_ntaps':best['ntaps'],'W':best['W'],'bytes':best['bytes'],'historical':hist,'gain_historical':out['gain_vs_historical_ar32_zsm'],'sz3':sz3,'gain_sz3':out['gain_vs_sz3']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
