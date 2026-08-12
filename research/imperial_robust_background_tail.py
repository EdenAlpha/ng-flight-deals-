import json,sys,struct
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();T=1024;C=128
KS=[0.75,1.0,1.25,1.5,2.0,3.0,4.0,6.0]
def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=x.sum();ss+=(x*x).sum();n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))
def szrun(x,eps):
 best=None
 for tr in [False,True]:
  a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);r=r.T if tr else r
  me=float(np.max(np.abs(x.astype(np.float32)-r)));q=(int(b.size),r,me,tr)
  if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
  if best is None or q[0]<best[0]:best=q
 return best
def tailpack(r):
 m=r!=0;mb=Z.compress(np.packbits(m.ravel(),bitorder='little').tobytes());v=r[m].astype(np.int32)
 vb=Z.compress(v.astype('<i4').tobytes()) if v.size else b''
 return len(mb)+len(vb)+12,mb,vb,int(v.size)
def metrics(x):
 x=x.astype(np.float64);xc=x-x.mean();
 ac=float(np.corrcoef(x[:-1].ravel(),x[1:].ravel())[0,1]) if x.shape[0]>1 else 0
 tc=float(np.corrcoef(x[:,:-1].ravel(),x[:,1:].ravel())[0,1]) if x.shape[1]>1 else 0
 s=np.linalg.svd(xc,compute_uv=False);sv=float((s[:16]@s[:16])/(s@s)) if np.any(s) else 1
 F=np.fft.fft(np.fft.rfft(xc,axis=1),axis=0).ravel();e=np.abs(F)**2;n=min(256,e.size);sp=float(np.partition(e,-n)[-n:].sum()/e.sum()) if e.sum() else 1
 return {'adj_corr':ac,'time_corr':tc,'svd16':sv,'spec256':sp}
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];mu,std=stats(d);eps=.1*std;tpos=[0,14488,28976];cpos=[0,3392,6784];rows=[];tiles=[]
  for ti,t0 in enumerate(tpos):
   for ci,c0 in enumerate(cpos):
    X=np.asarray(d[t0:t0+T,c0:c0+C],np.int32).T;raw=X.size*2;db,dr,dme,dtr=szrun(X,eps);med=float(np.median(X));mad=float(np.median(np.abs(X-med)));rs=max(1.0,1.4826*mad);tiles.append({'id':f't{ti}c{ci}','direct_sz3':db,'raw':raw,'median':med,'robust_sigma':rs,'raw_metrics':metrics(X)})
    for k in KS:
     lo=int(np.floor(med-k*rs));hi=int(np.ceil(med+k*rs));W=np.clip(X,lo,hi).astype(np.int32);R=(X-W).astype(np.int32);tb,mb,vb,nz=tailpack(R);bb,wr,bme,tr=szrun(W,eps);Y=wr.astype(np.float64)+R.astype(np.float64);me=float(np.max(np.abs(X.astype(np.float64)-Y)))
     if me>eps*(1+5e-6):raise RuntimeError(('final',me,eps))
     total=bb+tb+28;rows.append({'tile':f't{ti}c{ci}','k':k,'lo':lo,'hi':hi,'tail_fraction':nz/X.size,'background_sz3_bytes':bb,'tail_bytes':tb,'bytes':total,'direct_sz3':db,'gain_vs_direct_sz3':db/total,'ratio_raw':raw/total,'background_metrics':metrics(W),'maxerr':me})
  combos=[]
  for k in KS:
   rr=[r for r in rows if r['k']==k];b=sum(r['bytes'] for r in rr);s=sum(r['direct_sz3'] for r in rr);raw=sum(t['raw'] for t in tiles)
   combos.append({'k':k,'bytes':b,'direct_sz3':s,'gain_vs_direct_sz3':s/b,'ratio_raw':raw/b,'median_tail_fraction':float(np.median([r['tail_fraction'] for r in rr])),'median_svd16_before':float(np.median([t['raw_metrics']['svd16'] for t in tiles])),'median_svd16_after':float(np.median([r['background_metrics']['svd16'] for r in rr])),'median_spec256_before':float(np.median([t['raw_metrics']['spec256'] for t in tiles])),'median_spec256_after':float(np.median([r['background_metrics']['spec256'] for r in rr])),'min_tile_gain':min(r['gain_vs_direct_sz3'] for r in rr),'max_tile_gain':max(r['gain_vs_direct_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'tiles':tiles,'combos':combos,'rows':rows,'scope':'9-tile exact screen: integer winsorized background compressed at same epsilon plus exact sparse tail; all tail bytes counted'}
  print(json.dumps({'best':combos[:8]},indent=2));json.dump(out,open('imperial_robust_background_tail.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
