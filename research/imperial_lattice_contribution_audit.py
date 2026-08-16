import json,sys
import h5py,numpy as np
import imperial_address_lattice_search as x
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps)
 h,lo,hi,Q,D,dt,dc,co,it,gchg=x.build(X,eps,1.90)
 fr=m.encode_k(D);legacy=c.validate(X,eps,h,Q,np.asarray(fr[2],np.int32),dt,dc,co,it,int(fr[0]),'legacy_'+fr[1])
 rank,_=x.frame(X,eps,h,Q,D,dt,dc,co,it,'restricted_rank')
 lc=a.logcomb_table(X.size);Q2,D2,cnt,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES);D2=np.ascontiguousarray(g._all_defects(Q2,dt,dc,co,it,g.SCALE))
 fr2=m.encode_k(D2);legacy2=c.validate(X,eps,h,Q2,np.asarray(fr2[2],np.int32),dt,dc,co,it,int(fr2[0]),'legacy_after_search_'+fr2[1])
 rank2,_=x.frame(X,eps,h,Q2,D2,dt,dc,co,it,'rank_after_search')
 rows=[legacy,rank,legacy2,rank2]
 for r in rows:r['gain_ar32']=ar['bytes']/r['bytes'];r['gain_sz3']=sz/r['bytes']
 out={'rows':rows,'ar32':ar,'sz3':{'bytes':int(sz),'orientation':ori},'hfac':1.9,'generator_changes':gchg,'address_changes':int(achg)};json.dump(out,open('imperial_lattice_contribution_audit.json','w'),indent=2)
 for r in rows:print(json.dumps({'rep':r['rep'],'bytes':r['bytes'],'gain_ar32':r['gain_ar32'],'gain_sz3':r['gain_sz3']},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
