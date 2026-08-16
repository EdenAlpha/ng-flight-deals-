import json,sys
import h5py,numpy as np
import imperial_address_aware_pair_search as p
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy())
    Q,D,counts1,single_changes=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,a.PASSES)
    D1=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(D1,D):
        D=D1
        counts1=a.init_counts(D,p.NBITS)
    rb1,_,RE1,detail1=rr.restricted_rank_frame(D)
    single=c.validate(X,eps,h,Q,RE1,dts,dcs,co,intercept,rb1,'single_address_search',detail1)
    before_pair_obj=float(a.total_cost(counts1,logc))

    Q2,Dcache,counts_cache,pair_changes,tested,rejected=p.pair_search(
        np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),
        dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,p.PAIR_PASSES)

    # Ground truth is always rebuilt from the final legal Q trajectory.
    D2=g._all_defects(Q2,dts,dcs,co,intercept,g.SCALE)
    counts2=a.init_counts(D2,p.NBITS)
    exact_obj=float(a.total_cost(counts2,logc))
    if exact_obj>before_pair_obj+1e-9:
        raise RuntimeError(('pair exact objective regressed',before_pair_obj,exact_obj))
    rb2,_,RE2,detail2=rr.restricted_rank_frame(D2)
    pair=c.validate(X,eps,h,Q2,RE2,dts,dcs,co,intercept,rb2,'pair_address_search',detail2)
    for r in (single,pair):
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes']
        print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    mismatch=int(np.count_nonzero(Dcache!=D2))
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,
         'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,
         'single':single,'pair':pair,
         'search':{'base_projection_changes':int(base_changes),'single_changes':int(single_changes),
                   'pair_changes':int(pair_changes),'pair_candidates_tested':int(tested),
                   'pair_nominations_rejected_by_full_exact_check':int(rejected),
                   'before_pair_global_rank_bits':before_pair_obj,
                   'after_pair_global_rank_bits':exact_obj,
                   'cached_defect_mismatch_cells':mismatch,
                   'before_pair_counts':[int(x) for x in counts1],
                   'after_pair_counts':[int(x) for x in counts2]},
         'scope':'Safety-fixed paired NOVA address search. Pair proposals are still accepted only after the original full exact defect recomputation proves a lower global combinatorial address objective. The final reported stream no longer trusts the incremental defect cache at all: it rebuilds every defect from the final Q field, recomputes exact counts/objective, rejects any global regression, physically serializes with PR512 restricted ranking, independently decodes, regenerates Q with the charged learned generator and checks the unchanged source hard-error bound. Only those fresh exact final bytes count.'}
    json.dump(out,open('imperial_address_aware_pair_search_fixed.json','w'),indent=2)
    print(json.dumps({'summary':{'single':single['bytes'],'pair':pair['bytes'],'ar32':arb['bytes'],'sz3':int(szb),
                                 'pair_changes':int(pair_changes),'tested':int(tested),'rejected_exact':int(rejected),
                                 'cache_mismatch_cells':mismatch,'gain_vs_single':single['bytes']/pair['bytes'],
                                 'gain_vs_ar32':arb['bytes']/pair['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
