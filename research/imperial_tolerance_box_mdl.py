import json,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();T=1024;C=128;SAFETY=1-1e-5
HF=[1.0,0.5,0.25]

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
def legal(X,bound,h):
 lo=np.ceil((X-bound)/h).astype(np.int32);hi=np.floor((X+bound)/h).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal set')
 q=np.rint(X/h).astype(np.int32);return lo,hi,np.minimum(np.maximum(q,lo),hi)
def choose(kind,lo,hi,q0):
 q=q0.copy();nc,nt=q.shape
 if kind=='nearest':return q
 if kind=='time_sticky':
  for t in range(1,nt):q[:,t]=np.minimum(np.maximum(q[:,t-1],lo[:,t]),hi[:,t])
  return q
 if kind=='space_sticky':
  for c in range(1,nc):q[c]=np.minimum(np.maximum(q[c-1],lo[c]),hi[c])
  return q
 if kind=='lorenzo_projected':
  for c in range(1,nc):
   for t in range(1,nt):
    p=q[c-1,t]+q[c,t-1]-q[c-1,t-1];q[c,t]=min(max(p,int(lo[c,t])),int(hi[c,t]))
  return q
 if kind in ('median4','laplace4'):
  for _ in range(10):
   n=np.stack([q[:-2,1:-1],q[2:,1:-1],q[1:-1,:-2],q[1:-1,2:]],axis=0).astype(np.float64)
   v=np.median(n,axis=0) if kind=='median4' else np.mean(n,axis=0)
   v=np.rint(v).astype(np.int32);v=np.minimum(np.maximum(v,lo[1:-1,1:-1]),hi[1:-1,1:-1]);q[1:-1,1:-1]=v
  return q
 raise ValueError(kind)
def reps(q):
 out={'raw':q.copy()};dt=q.copy();dt[:,1:]-=q[:,:-1];out['dt']=dt;dc=q.copy();dc[1:]-=q[:-1];out['dc']=dc
 L=q.copy();L[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1];out['lorenzo']=L
 return out
def encode_int(a):
 mn=int(a.min());mx=int(a.max());dt=np.dtype('<i2') if -32768<=mn and mx<=32767 else np.dtype('<i4');b=Z.compress(np.ascontiguousarray(a).astype(dt).tobytes());return b,dt.str
def decode_rep(blob,dtypestr,shape,rep):
 a=np.frombuffer(D.decompress(blob),dtype=np.dtype(dtypestr),count=int(np.prod(shape))).astype(np.int32).reshape(shape)
 if rep=='raw':return a
 if rep=='dt':return np.cumsum(a,axis=1,dtype=np.int32)
 if rep=='dc':return np.cumsum(a,axis=0,dtype=np.int32)
 if rep=='lorenzo':
  q=a.copy()
  for c in range(1,q.shape[0]):
   for t in range(1,q.shape[1]):q[c,t]=a[c,t]+q[c-1,t]+q[c,t-1]-q[c-1,t-1]
  return q
 raise ValueError(rep)
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];mu,std=stats(d);pub=.1*std;bound=pub*SAFETY;tpos=[0,14488,28976];cpos=[0,3392,6784];tiles=[];rows=[]
  for ti,t0 in enumerate(tpos):
   for ci,c0 in enumerate(cpos):
    X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;raw=X.size*2;sb=szrun(X,pub);tiles.append({'id':f't{ti}c{ci}','raw':raw,'sz3':sb})
    for fac in HF:
     h=fac*bound;lo,hi,q0=legal(X,bound,h);freedom=float(np.mean(hi-lo+1))
     for kind in ['nearest','time_sticky','space_sticky','lorenzo_projected','median4','laplace4']:
      q=choose(kind,lo,hi,q0);R=q.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
      if me>pub*(1+5e-6):raise RuntimeError(('legal',fac,kind,me,pub))
      best=None
      for rn,a in reps(q).items():
       blob,ds=encode_int(a);qq=decode_rep(blob,ds,q.shape,rn)
       if not np.array_equal(qq,q):raise RuntimeError(('decode',rn))
       b=len(blob)+24
       if best is None or b<best[0]:best=(b,rn,ds)
      rows.append({'tile':f't{ti}c{ci}','h_over_eps':fac,'selector':kind,'mean_legal_states':freedom,'bytes':best[0],'rep':best[1],'dtype':best[2],'ratio_raw':raw/best[0],'gain_vs_sz3':sb/best[0],'maxerr':me,'q_change_time':float(np.mean(q[:,1:]!=q[:,:-1])),'q_change_space':float(np.mean(q[1:]!=q[:-1]))})
  combos=[]
  for fac in HF:
   for kind in ['nearest','time_sticky','space_sticky','lorenzo_projected','median4','laplace4']:
    rr=[r for r in rows if r['h_over_eps']==fac and r['selector']==kind];b=sum(r['bytes'] for r in rr);s=sum(t['sz3'] for t in tiles);raw=sum(t['raw'] for t in tiles)
    combos.append({'h_over_eps':fac,'selector':kind,'bytes':b,'sz3':s,'ratio_raw':raw/b,'gain_vs_sz3':s/b,'median_legal_states':float(np.median([r['mean_legal_states'] for r in rr])),'median_time_change':float(np.median([r['q_change_time'] for r in rr])),'median_space_change':float(np.median([r['q_change_space'] for r in rr])),'reps':[r['rep'] for r in rr],'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'max_tile_gain':max(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':pub,'bound':bound,'tiles':tiles,'combos':combos,'rows':rows,'scope':'9-tile exact legal-codeword projection screen; reconstruction states are deliberately moved within tolerance to reduce 2-D syndrome complexity; all state bytes counted'}
  print(json.dumps({'best':combos[:10]},indent=2));json.dump(out,open('imperial_tolerance_box_mdl.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
