import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_full_hard_128x30000 as f
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
q.f.q_decode=sc.q_decode
FACS=(1.970,1.980,1.990,1.995,1.999,1.9995,1.9999,1.99995)
SCREEN=4096

def legal_round(X,eps,h):
 Q=np.rint(X/h).astype(np.int32);me=float(np.max(np.abs(X-Q.astype(np.float64)*h)))
 if me>eps*(1+2e-12):raise RuntimeError(('round not legal',h,me,eps))
 return Q,me

def fit_and_prefix(Q):
 dt,dc,co,it=f.fit_model(Q,ntaps=20)
 D=g._all_defects(np.ascontiguousarray(Q[:,:SCREEN],np.int32),dt,dc,co,it,f.SCALE)
 mb,mrep,_,_,_,_=g.model_frame(dt,dc,co,it);best=None
 for W in q.WINDOWS:
  bb,nb=q.encode_zsm(D,W,SCREEN);score=int(mb)+len(bb)
  if best is None or score<best[0]:best=(score,int(W),len(bb),int(nb))
 return dt,dc,co,it,int(mb),mrep,best

def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,f.C0:f.C0+f.C],np.float64).T
 screens=[];states={}
 for fac in FACS:
  h=float(eps*fac);Q,rounderr=legal_round(X,eps,h);dt,dc,co,it,mb,mrep,b=fit_and_prefix(Q)
  rec={'hfac':fac,'h':h,'screen_total':b[0],'W':b[1],'screen_payload':b[2],'screen_bits':b[3],'model_bytes':mb,'round_maxerr':rounderr,'q_std':float(Q.astype(np.float64).std())};screens.append(rec);states[fac]=(h,Q,dt,dc,co,it,mb,mrep,b[1]);print(json.dumps({'screen':rec}),flush=True)
 screens.sort(key=lambda z:z['screen_total']);finalists=[r['hfac'] for r in screens[:3]];full=[]
 for fac in finalists:
  h,Q,dt,dc,co,it,mb,mrep,W=states[fac];D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,f.SCALE));bb,nb=q.encode_zsm(D,W,q.NT);Dd=q.decode_zsm(bb,nb,W,D.shape)
  if not np.array_equal(Dd,D):raise RuntimeError(('defect decode',fac))
  _,_,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it);Qd=q.f.q_decode(Dd,ddt,ddc,dco,dit,f.SCALE)
  if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',fac))
  me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
  if me>eps*(1+5e-6):raise RuntimeError(('hard',fac,me,eps))
  total=int(mb)+len(bb)+q.HEADER+2
  rec={'hfac':fac,'W':W,'bytes':total,'model_bytes':mb,'payload_bytes':len(bb),'arithmetic_bits':int(nb),'maxerr':me,'defect_zero_fraction':float(np.mean(D==0)),'defect_std':float(D.astype(np.float64).std())};full.append(rec);print(json.dumps({'full':rec}),flush=True)
 full.sort(key=lambda z:z['bytes']);best=full[0];hist=2478995;old=2486110;sz3=2767977;bestbytes=min(old,best['bytes'])
 out={'factors':list(FACS),'screens':screens,'materialized_factors':finalists,'full':full,'best_new':best,'best_learned_bytes':bestbytes,'historical_learned_bytes':old,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/bestbytes,'matched_sz3_bytes':sz3,'gain_vs_sz3':sz3/bestbytes,'scope':'Full-hard NOVA coordinate-spacing search scored directly by historical ZSM rate. A fixed public near-2epsilon factor menu is tested on the canonical 128x30000 hard block. For each factor Q is the deterministic nearest legal lattice reconstruction, the 20-tap charged sparse generator is relearned, and W=4/8/64 is screened only on the first 4096 times using model bytes plus actual ZSM prefix bytes. A charged factor byte and window byte are included. The top three prefix candidates are fully materialized, exact ZSM decoded, used with the transmitted model to regenerate identical Q, and hard-error validated. Final learned result is min(this new menu and the historical #551 learned baseline), compared against the untouched 2,478,995-byte historical AR32+ZSM champion.'};json.dump(out,open('imperial_near2eps_zsm_lattice_search.json','w'),indent=2);print(json.dumps({'summary':{'best_factor':best['hfac'],'new_bytes':best['bytes'],'learned_best':bestbytes,'ar32_zsm':hist,'gain':hist/bestbytes,'sz3':sz3}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
