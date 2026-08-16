import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
FACS=(1.50,1.55,1.60,1.65,1.70,1.80,1.90)

def build(X,eps,fac):
 h=eps*fac;lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);chg=0
 for _ in range(g.ROUNDS):
  dt,dc,co,it=g.fit_model(Q);Q,D,H,s,n,z=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);chg+=int(z)
 dt,dc,co,it=g.fit_model(Q);Q,D,H,s,n,z=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);chg+=int(z)
 return h,lo,hi,np.ascontiguousarray(Q),np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE)),dt,dc,co,it,chg

def frame(X,eps,h,Q,D,dt,dc,co,it,name):
 b,_,E,detail=rr.restricted_rank_frame(D);r=c.validate(X,eps,h,Q,E,dt,dc,co,it,b,name,detail);return r,detail

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps);lc=a.logcomb_table(X.size);rows=[]
 for fac in FACS:
  h,lo,hi,Q,D,dt,dc,co,it,gchg=build(X,eps,fac)
  pre,_=frame(X,eps,h,Q,D,dt,dc,co,it,'pre')
  Q2,D2,cnt,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES)
  D2=np.ascontiguousarray(g._all_defects(Q2,dt,dc,co,it,g.SCALE));post,detail=frame(X,eps,h,Q2,D2,dt,dc,co,it,'address')
  r={'hfac':fac,'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'pre':pre['bytes'],'bytes':post['bytes'],'defect_bytes':post['defect_bytes'],'generator_changes':gchg,'address_changes':int(achg),'gain_sz3':sz/post['bytes'],'gain_ar32':ar['bytes']/post['bytes']};rows.append(r);print(json.dumps(r),flush=True)
 rows.sort(key=lambda x:x['bytes']);b=rows[0]
 out={'rows':rows,'best':b,'ar32':ar,'sz3':{'bytes':int(sz),'orientation':ori},'eps':eps,'scope':'Exact decoder-real address-rate lattice sweep. Each h/epsilon lattice relearns and charges the sparse generator, selects only hard-error-legal Q states, applies address-aware legal search, serializes through exact restricted ranking, independently decodes Q and verifies source hard error. Only actual bytes count.'};json.dump(out,open('imperial_address_lattice_search.json','w'),indent=2)
 print(json.dumps({'summary':{'best_hfac':b['hfac'],'bytes':b['bytes'],'ar32':ar['bytes'],'sz3':int(sz),'gap':b['bytes']-ar['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
