import json,sys,os
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from research.imperial_entropy_shaped_codeword import stats,szrun,legal,traversals,synthesize

SAFETY=1-1e-5;C=128;T=1024

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY
  # medium center and hard high-entropy edge region, both middle in time
  specs=[('medium',14488,3392),('hard',14488,6784)]
  rows=[]
  pathdict=dict(traversals(C,T))
  for name,t0,c0 in specs:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);raw=X.size*2
   lo,hi,q0=legal(X,bound,bound)
   for pname in ('channel_snake','morton'):
    order=pathdict[pname]
    for seed in ('empirical','laplace4','spike'):
     stat,qpath=synthesize(lo,hi,q0,order,seed)
     qflat=np.empty(qpath.size,np.int32);qflat[order]=qpath;q=qflat.reshape(C,T)
     me=float(np.max(np.abs(X-q.astype(np.float64)*bound)))
     if me>eps*(1+5e-6):raise RuntimeError(('hard error',name,pname,seed,me,eps))
     rows.append({'tile':name,'path':pname,'seed':seed,'sz3_bytes':sb,'raw_bytes':raw,'ideal_bytes':stat['ideal_bytes_with_model'],'zstd_bytes':stat['zstd_bytes'],'ideal_bps':8*stat['ideal_bytes_with_model']/X.size,'zstd_bps':8*stat['zstd_bytes']/X.size,'gain_vs_sz3_ideal':sb/stat['ideal_bytes_with_model'],'gain_vs_sz3_zstd':sb/stat['zstd_bytes'],'zero_fraction':stat['zero_fraction'],'delta_entropy_bps':stat['H_delta_bps'],'round':stat['round'],'maxerr':me})
  rows.sort(key=lambda x:x['ideal_bps'])
  out={'std':std,'eps':eps,'two_x_sz3_target_bps':1.8859028760018859,'rows':rows,'best':rows[:8],'scope':'Fast two-tile gate using the identical entropy-shaped legal-codeword mechanism from PR222. Diagnostic only.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_entropy_shaped_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
