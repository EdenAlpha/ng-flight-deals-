import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_universe_shaping as u
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

CYCLES=4
BIT_PASSES=3
HIST_PASSES=3


def materialize(X,eps,h,Q,D,dts,dcs,co,intercept,label,szb,arb):
    best,reps=u.materialized_best(X,eps,h,Q,D,dts,dcs,co,intercept,label)
    best['gain_vs_sz3']=szb/best['bytes'];best['gain_vs_ar32']=arb['bytes']/best['bytes']
    return best,reps


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size);lf=np.zeros(X.size+1,np.float64);lf[1:]=np.cumsum(np.log(np.arange(1,X.size+1,dtype=np.float64)))
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy());stages=[];allreps=[]
    base,reps=materialize(X,eps,h,Q,D,dts,dcs,co,intercept,'resonant_start',szb,arb);base['stage']='start';stages.append(base);allreps.append({'stage':'start','reps':reps})
    for cyc in range(CYCLES):
        Q,D,bc,bch=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,a.NBITS,BIT_PASSES)
        Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('bit defect mismatch',cyc))
        r,reps=materialize(X,eps,h,Q,D,dts,dcs,co,intercept,f'c{cyc}_bit',szb,arb);r.update({'stage':f'c{cyc}_bit','changes':int(bch),'bit_counts':[int(x) for x in bc[:10]]});stages.append(r);allreps.append({'stage':r['stage'],'reps':reps});print(json.dumps({k:v for k,v in r.items() if k not in ('detail','bit_counts')},indent=2),flush=True)
        Q,D,hh,hch=u.shape_hist(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,lf,HIST_PASSES)
        Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('hist defect mismatch',cyc))
        r,reps=materialize(X,eps,h,Q,D,dts,dcs,co,intercept,f'c{cyc}_hist',szb,arb);r.update({'stage':f'c{cyc}_hist','changes':int(hch),'distinct':int(np.count_nonzero(hh))});stages.append(r);allreps.append({'stage':r['stage'],'reps':reps});print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
        if bch==0 and hch==0:break
    best=min(stages,key=lambda r:r['bytes'])
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'cycles':CYCLES,'bit_passes':BIT_PASSES,'hist_passes':HIST_PASSES,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'stages':stages,'all_reps':allreps,'best':best,'scope':'Decoder-real alternating restriction search. The fully charged learned generator and unchanged hard-error legal set are frozen. Encoder computation alternates two previously successful legal-state objectives on one evolving reconstruction: PR518 global combinatorial defect-bit shaping and PR529 whole-symbol multinomial-universe shaping. After every half-cycle the current defect is recomputed from scratch, physically encoded through both exact restricted ranking and the incumbent dense representation menu, independently decoded, used to regenerate exact Q and hard-error checked. Search trajectories/objective values are never counted as compression. The best actual byte stream over all visited legal reconstructions wins. This tests whether the two restriction mechanisms expose new degrees of freedom for each other rather than optimizing them independently.'}
    json.dump(out,open('imperial_alternating_restriction_search.json','w'),indent=2)
    print(json.dumps({'summary':{'best_stage':best['stage'],'best_bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes'],'trajectory':[(r['stage'],r['bytes']) for r in stages]}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
