import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_phase_automaton_fast as f

C=f.C;NT=f.NT;C0=f.C0;STEP=f.STEP

def main(path):
  with h5py.File(path,'r') as hf:
    d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
  Xi=np.rint(X).astype(np.int64);_,co=ah.fits(X);_,cod=cg.model_frame(co)
  z=np.zeros(16,np.int16);R0,K0=f.full_numba(Xi,cod,z,16,3,0);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64);N=Xi-P0;base=f.proxy(K0)
  rows=[]
  for i,(S,a,b) in enumerate(f.SPECS):
    tab=np.zeros(S,np.int16);hist=[]
    for it in range(2):
      K,states,vals=f.approx_numba(N,P0,tab,S,a,b,f.TRAIN,True);pr=f.proxy(K);hist.append({'iter':it,'proxy_bps':pr})
      nt=f.refit(states,vals,tab)
      if np.array_equal(nt,tab):break
      tab=nt
    R,K=f.full_numba(Xi,cod,tab,S,a,b);sb=f.side(i,tab);pr=f.proxy(K);charged=pr+8*len(sb)/(C*NT)
    row={'spec_id':i,'states':S,'a':a,'p_weight':b,'proxy_bps':pr,'charged_proxy_bps':charged,'gain_vs_uniform_proxy_bps':base-charged,'side_bytes':len(sb),'nonzero_phases':int(np.count_nonzero(tab)),'maxerr':float(np.max(np.abs(X-R.astype(np.float64)))),'train':hist};rows.append(row);print(json.dumps(row),flush=True)
  best=min(rows,key=lambda r:r['charged_proxy_bps']);out={'baseline_uniform_proxy_bps':base,'best':best,'rows':rows,'eps':eps,'note':'Proxy-only compiled finite-state screen; no serialized codec bytes. Positive gain is required before physical coding.'}
  json.dump(out,open('imperial_gca_phase_automaton_screen.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
