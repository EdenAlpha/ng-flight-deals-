import json,sys
import h5py,numpy as np
import imperial_address_lattice_search as x
import imperial_address_aware_legal_search as a
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
FAC=1.995
T0S=(0,4096,8192,12288,14488,16384,20480,24576,28976)
CASES=[(512,t) for t in T0S]+[(544,14488),(576,14488),(608,14488)]

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];A=R=S=0
  for c0,t0 in CASES:
   X=np.asarray(d[t0:t0+g.T,c0:c0+g.C],np.float64).T
   sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps)
   h,lo,hi,Q,D,dt,dc,co,it,gchg=x.build(X,eps,FAC);lc=a.logcomb_table(X.size)
   Q,D,cnt,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES);D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
   ours,_=x.frame(X,eps,h,Q,D,dt,dc,co,it,'near2_rank')
   rec={'c0':c0,'t0':t0,'ours':ours['bytes'],'ar32':ar['bytes'],'sz3':int(sz),'gain_ar32':ar['bytes']/ours['bytes'],'gain_sz3':sz/ours['bytes'],'maxerr':ours['maxerr'],'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'generator_changes':gchg,'address_changes':int(achg)}
   rows.append(rec);A+=ours['bytes'];R+=ar['bytes'];S+=int(sz);print(json.dumps(rec),flush=True)
 out={'hfac':FAC,'eps':eps,'cases':rows,'aggregate':{'ours':A,'ar32':R,'sz3':S,'gain_ar32':R/A,'gain_sz3':S/A,'wins_ar32':sum(r['ours']<r['ar32'] for r in rows),'wins_sz3':sum(r['ours']<r['sz3'] for r in rows),'tiles':len(rows)},'scope':'Twelve independent decoder-real hard-region tiles. Nine time windows use channels 512:544; three additional slabs cover channels 544:640 at the original hard time. Each tile independently learns and fully charges its generator, uses fixed public h=1.995epsilon, exact legal reconstruction/address search, exact restricted-rank serialization, independent Q replay and unchanged source hard-error validation. Aggregate is the literal sum of complete per-tile streams.'};json.dump(out,open('imperial_near2_hard_panel.json','w'),indent=2);print(json.dumps({'summary':out['aggregate']},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
