import json,os,sys
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
SAFETY=1-1e-4;T=1024;C=128
MODS=['none','time_alt','time_0011','time_0110']
TRANS=[('raw',0),('time_potential',2),('time_potential2',4),('space_potential',2),('space_time_potential',4)]

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=x.sum();ss+=(x*x).sum();n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0.,ss/n-m*m)))
def sign(shape,t0,c0,m):
 c,t=shape;tt=np.arange(t0,t0+t)[None,:]
 if m=='none':return np.ones(shape,np.float64)
 if m=='time_alt':return np.broadcast_to(np.where(tt%2==0,1.,-1.),shape)
 if m=='time_0011':return np.broadcast_to(np.where(tt%4<2,1.,-1.),shape)
 if m=='time_0110':return np.broadcast_to(np.where((tt+1)%4<2,1.,-1.),shape)
 raise ValueError(m)
def fwd(x,k):
 if k=='raw':return x.copy()
 if k=='time_potential':return np.cumsum(x,axis=1,dtype=np.float64)
 if k=='time_potential2':return np.cumsum(np.cumsum(x,axis=1,dtype=np.float64),axis=1,dtype=np.float64)
 if k=='space_potential':return np.cumsum(x,axis=0,dtype=np.float64)
 if k=='space_time_potential':return np.cumsum(np.cumsum(x,axis=1,dtype=np.float64),axis=0,dtype=np.float64)
 raise ValueError(k)
def d0(x,axis):
 z=np.zeros_like(np.take(x,[0],axis=axis));return np.diff(x,axis=axis,prepend=z)
def inv(p,k):
 if k=='raw':return p
 if k=='time_potential':return d0(p,1)
 if k=='time_potential2':return d0(d0(p,1),1)
 if k=='space_potential':return d0(p,0)
 if k=='space_time_potential':return d0(d0(p,0),1)
 raise ValueError(k)
def szrun(x,eb):
 best=None
 for tr in [False,True]:
  a=np.ascontiguousarray(x.T if tr else x)
  cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eb)
  b,_=sz.compress(a,cfg);r,_=sz.decompress(b,a.dtype,a.shape);r=r.T if tr else r
  me=float(np.max(np.abs(x-r)))
  if me>eb*(1+1e-5):raise RuntimeError(('potential bound',me,eb,a.dtype))
  q=(int(b.size),r,me,tr)
  if best is None or q[0]<best[0]:best=q
 return best
def e256(x):
 F=np.fft.fft(np.fft.rfft(x,axis=1),axis=0).ravel();e=np.abs(F)**2;tot=float(e.sum())
 if not tot:return 1.
 n=min(256,e.size);return float(np.partition(e,-n)[-n:].sum()/tot)
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];mu,std=stats(d);pub=.1*std
  tpos=[0,14488,28976];cpos=[0,3392,6784];tiles=[];rows=[]
  for ti,t0 in enumerate(tpos):
   for ci,c0 in enumerate(cpos):
    W=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;rawbytes=W.size*2
    db,dr,dme,dtr=szrun(W.astype(np.float32),pub);tiles.append({'id':f't{ti}c{ci}','t0':t0,'c0':c0,'direct_sz3':db,'raw':rawbytes})
    for mod in MODS:
     s=sign(W.shape,t0,c0,mod);Z=W*s
     for kind,norm in TRANS:
      P=fwd(Z,kind);eb=pub*SAFETY/(norm if norm else 1);bb,Rp,pme,tr=szrun(P,eb);R=inv(Rp,kind)*s;me=float(np.max(np.abs(W-R)))
      if me>pub*(1+2e-5):raise RuntimeError(('final bound',mod,kind,me,pub))
      rows.append({'tile':f't{ti}c{ci}','mod':mod,'kind':kind,'op_l1':norm if norm else 1,'bytes':bb+20,'direct_sz3':db,'gain_vs_direct_sz3':db/(bb+20),'ratio_raw':rawbytes/(bb+20),'potential_top256_energy':e256(P),'potential_bound':eb,'potential_maxerr':pme,'final_maxerr':me,'transpose':tr})
  combos=[]
  for mod in MODS:
   for kind,norm in TRANS:
    rr=[r for r in rows if r['mod']==mod and r['kind']==kind];b=sum(r['bytes'] for r in rr);s=sum(r['direct_sz3'] for r in rr);raw=sum(t['raw'] for t in tiles)
    combos.append({'mod':mod,'kind':kind,'bytes':b,'direct_sz3':s,'gain_vs_direct_sz3':s/b,'ratio_raw':raw/b,'median_top256_energy':float(np.median([r['potential_top256_energy'] for r in rr])),'min_tile_gain':min(r['gain_vs_direct_sz3'] for r in rr),'max_tile_gain':max(r['gain_vs_direct_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'dataset':'Imperial Valley continuous DAS','shape':list(d.shape),'std':std,'public_eps':pub,'tiles':tiles,'combos':combos,'rows':rows,'scope':'9-tile representation screen; potential encoded with matched SZ3 solely to test whether reversible anti-differentiation exposes lower-rate structure'}
  print(json.dumps({'std':std,'eps':pub,'best':combos[:8]},indent=2));json.dump(out,open('imperial_latent_potential_screen.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
