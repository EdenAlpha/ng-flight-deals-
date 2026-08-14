import json,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import research.imperial_valley_frozen_brady_transfer as B
NS=[256,512,1024,2048,4096,8192,16384]
T=1024;C=128

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=x.sum();ss+=(x*x).sum();n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))
def szrun(x,eps):
 best=None
 for tr in [False,True]:
  a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
  if best is None or int(b.size)<best:best=int(b.size)
 return best
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];mu,std=stats(d);pub=.1*std;internal=pub*B.SAFETY;tpos=[0,14488,28976];cpos=[0,3392,6784];tiles=[];rows=[]
  for ti,t0 in enumerate(tpos):
   for ci,c0 in enumerate(cpos):
    W=np.asarray(d[t0:t0+T,c0:c0+C]).T.astype(np.float32);raw=W.nbytes;sb=szrun(W,pub);tiles.append({'id':f't{ti}c{ci}','raw':raw,'sz3':sb})
    for n in NS:
     B.NKEEP=n;blob,me,diag=B.encode_tile(W,internal);R=B.decode_tile(blob,internal);me2=float(np.max(np.abs(W-R)))
     if me2>pub*(1+5e-6):raise RuntimeError(('hard',n,me2,pub))
     rows.append({'tile':f't{ti}c{ci}','N':n,'bytes':len(blob),'raw':raw,'sz3':sb,'ratio':raw/len(blob),'gain_vs_sz3':sb/len(blob),'model_bytes':diag['model_bytes'],'correction_bytes':diag['correction_bytes'],'correction_nonzero_fraction':diag['correction_nonzero_fraction'],'mode':diag['mode'],'maxerr':me2})
  combos=[]
  for n in NS:
   rr=[r for r in rows if r['N']==n];b=sum(r['bytes'] for r in rr);s=sum(t['sz3'] for t in tiles);raw=sum(t['raw'] for t in tiles)
   combos.append({'N':n,'bytes':b,'sz3':s,'ratio':raw/b,'gain_vs_sz3':s/b,'median_model_bytes':float(np.median([r['model_bytes'] for r in rr])),'median_correction_bytes':float(np.median([r['correction_bytes'] for r in rr])),'median_correction_density':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'max_tile_gain':max(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':pub,'tiles':tiles,'combos':combos,'rows':rows,'scope':'9-tile exact capacity sweep of PR206 spectral+certified-correction architecture; all model/correction bytes self-decoding and counted'}
  print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_dense_spectral_budget.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
