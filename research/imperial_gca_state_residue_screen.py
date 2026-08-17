import json,math,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_state_residue_fast as f

C=f.C;NT=f.NT;C0=f.C0

def main(path):
  with h5py.File(path,'r') as hf:
    d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
  Xi=np.rint(X).astype(np.int64);_,co=ah.fits(X);_,cod=cg.model_frame(co)
  z=np.zeros(9,np.int16);_,Kb,_,_=f.build_numba(Xi,cod,z,0,NT,False);base=f.proxy(Kb)
  rows=[]
  for fid,fam in enumerate(f.FAMILIES):
    tab=np.zeros(f.NCTX[fid],np.int16);hist=[]
    for it in range(2):
      _,K,ctxs,vals=f.build_numba(Xi,cod,tab,fid,f.TRAIN,True);pr=f.proxy(K);hist.append({'iter':it,'proxy_bps':pr})
      nt=f.refit(ctxs,vals,tab)
      if np.array_equal(nt,tab):break
      tab=nt
    R,K,_,_=f.build_numba(Xi,cod,tab,fid,NT,False);sb=f.side(fid,tab);pr=f.proxy(K);charged=pr+8*len(sb)/(C*NT)
    row={'family':fam,'proxy_bps':pr,'charged_proxy_bps':charged,'gain_vs_uniform_proxy_bps':base-charged,'side_bytes':len(sb),'nonzero_phases':int(np.count_nonzero(tab)),'maxerr':float(np.max(np.abs(X-R.astype(np.float64)))),'train':hist};rows.append(row);print(json.dumps(row),flush=True)
  best=min(rows,key=lambda r:r['charged_proxy_bps'])
  out={'baseline_uniform_proxy_bps':base,'best':best,'rows':rows,'eps':eps,'note':'Proxy-only compiled screen; no serialized codec bytes. Positive gain is required before an exact candidate is worth physical arithmetic coding.'}
  json.dump(out,open('imperial_gca_state_residue_screen.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
