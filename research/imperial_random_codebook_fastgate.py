import json,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from research.imperial_random_codebook_mass import stats,choose_phase,nearest,build_model,mass_single,mass_pair,summarize,SAFETY

HFACTORS=(1.5,1.0,0.75);N=16;STARTS=(0,2304,4606,6910);STRIDE=4

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;bound=eps*SAFETY;target=(8*86361271/(30000*6912))/2;rows=[]
  for hf in HFACTORS:
   h=hf*bound;_,phi,pidx=choose_phase(ds[:2],h);sr=[];pr=[]
   for c in STARTS:
    pseq=[nearest(np.asarray(ds[k][:,c],np.float64),h,phi) for k in (0,1)];sm=build_model(pseq);tx=np.asarray(ds[2][:,c],np.float64);B=tx[:len(tx)//N*N].reshape(-1,N)[::STRIDE]
    for b in B:
     lm=mass_single(b,sm,bound,h,phi);sr.append((-lm/math.log(2)/N) if math.isfinite(lm) else math.inf)
    pq=[]
    for k in (0,1):
     a=nearest(np.asarray(ds[k][:,c:c+2],np.float64),h,phi);pq.append([tuple(map(int,r)) for r in a])
    pm=build_model(pq);X=np.asarray(ds[2][:,c:c+2],np.float64);PB=X[:len(X)//N*N].reshape(-1,N,2)[::STRIDE]
    for b in PB:
     lm=mass_pair(b,pm,bound,h,phi);pr.append((-lm/math.log(2)/(2*N)) if math.isfinite(lm) else math.inf)
   rows.append({'h_over_eps_approx':hf,'phase_index':pidx,'single':summarize(sr,target),'adjacent_pair':summarize(pr,target)})
  out={'pairs':list(STARTS),'block_time':N,'block_stride':STRIDE,'std':std,'eps':eps,'fullfile_sz3_bps':2*target,'strict_2x_target_bps':target,'rows':rows,'scope':'Fast directional gate for PR242 using the identical previous-record first-order stochastic generator and exact legal-box probability-mass DP. Four deterministic cable positions, 16-sample blocks, every fourth block only. No parameter/model changes.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_random_codebook_fastgate.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
