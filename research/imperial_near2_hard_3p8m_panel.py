import json,sys
import h5py,numpy as np
import imperial_address_lattice_search as x
import imperial_address_aware_legal_search as a
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAC=1.9995
C0S=(512,544,576,608)
T0S=tuple(range(0,29696,1024))


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        rows=[];ours_total=ar_total=sz_total=0;wins_ar=wins_sz=0
        maxerr=0.0
        for c0 in C0S:
            for t0 in T0S:
                X=np.asarray(d[t0:t0+g.T,c0:c0+g.C],np.float64).T
                if X.shape!=(g.C,g.T):raise RuntimeError(('shape',c0,t0,X.shape))
                sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps)
                h,lo,hi,Q,D,dt,dc,co,it,gchg=x.build(X,eps,FAC)
                lc=a.logcomb_table(X.size)
                Q,D,_,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES)
                D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
                ours,_=x.frame(X,eps,h,Q,D,dt,dc,co,it,'near2_boundary_rank')
                ob=int(ours['bytes']);ab=int(ar['bytes']);sb=int(sz)
                rec={'c0':int(c0),'t0':int(t0),'ours':ob,'ar32':ab,'sz3':sb,
                     'gain_ar32':ab/ob,'gain_sz3':sb/ob,'maxerr':float(ours['maxerr']),
                     'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),
                     'generator_changes':int(gchg),'address_changes':int(achg)}
                rows.append(rec);ours_total+=ob;ar_total+=ab;sz_total+=sb
                wins_ar+=ob<ab;wins_sz+=ob<sb;maxerr=max(maxerr,float(ours['maxerr']))
                print(json.dumps(rec),flush=True)
        agg={'ours':ours_total,'ar32':ar_total,'sz3':sz_total,
             'gain_ar32':ar_total/ours_total,'gain_sz3':sz_total/ours_total,
             'wins_ar32':wins_ar,'wins_sz3':wins_sz,'tiles':len(rows),
             'samples':len(rows)*g.C*g.T,'channels':128,'time_samples':29696,
             'coverage_fraction_of_30000':29696/30000,'maxerr':maxerr}
        out={'hfac':FAC,'eps':eps,'cases':rows,'aggregate':agg,
             'scope':'Large non-overlapping Imperial hard-region validation. Covers channels 512:640 and time samples 0:29696 as 4 x 29 independent 32x1024 tiles = 3,801,088 source samples (98.9867% of the 30,000-sample hard time span). Every tile independently learns and fully charges its sparse causal generator, uses fixed public h=1.9995epsilon, performs hard-error-legal address search, physically serializes exact restricted-rank bytes, independently decodes Q and verifies the unchanged source error. AR32 and SZ3 are rerun on the identical tile. Aggregate is literal sum of complete per-tile streams; there is no overlap and no dataset-name routing.'}
        json.dump(out,open('imperial_near2_hard_3p8m_panel.json','w'),indent=2)
        print(json.dumps({'summary':agg},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
