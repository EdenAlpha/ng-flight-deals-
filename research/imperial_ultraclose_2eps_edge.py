import json,sys
import h5py,numpy as np
import imperial_near_2eps_resonance_sweep as s
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FACS=(1.991,1.993,1.995,1.997,1.998,1.999,1.9995,1.9998,1.9999,1.99995,1.99999,1.999999)


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);rows=[]
    for fac in FACS:
        z=s.build_at(X,eps,fac,0);r=s.rank_materialize(X,eps,z,f'edge_{fac}');r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'}),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'factors':list(FACS),'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'rows':rows,'best':best,'scope':'Fine legal-edge sweep after PR534. The unchanged source hard-error interval has width 2epsilon, while legal_q uses a tiny inward safety margin. Public h/epsilon values from 1.991 to 1.999999 are tested with the identical charged learned sparse generator, global legal projection, exact restricted-rank serialization, independent defect/Q replay and source hard-error verification. No epsilon relaxation or phase search is included. The purpose is only to locate the best safe fixed lattice spacing immediately below the 2epsilon boundary.'}
    json.dump(out,open('imperial_ultraclose_2eps_edge.json','w'),indent=2)
    print(json.dumps({'summary':{'fac':best['fac'],'bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes'],'maxerr':best['maxerr']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
