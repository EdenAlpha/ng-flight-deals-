import json,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5;PHASES=8;POLS=(1,-1)
Z=zstd.ZstdCompressor(level=19)

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(x,eps):
 best=None
 for tr in (False,True):
  a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
  if best is None or int(b.size)<best:best=int(b.size)
 return best

def encode_int(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;c=[]
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
   c.append((len(Z.compress(np.ascontiguousarray(a).astype(dt).tobytes()))+24,'signed_'+dt.str));break
 zz=((a.astype(np.int64)<<1)^(a.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if zz.size else 0
 for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
  if mz<=np.iinfo(dt).max:
   c.append((len(Z.compress(np.ascontiguousarray(zz).astype(dt).tobytes()))+24,'zigzag_'+dt.str));break
 nz=a!=0;sup=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());v=a[nz];vmn=int(v.min()) if v.size else 0;vmx=int(v.max()) if v.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if vmn>=np.iinfo(dt).min and vmx<=np.iinfo(dt).max:
   c.append((len(sup)+len(Z.compress(np.ascontiguousarray(v).astype(dt).tobytes()))+48,'sparse_'+dt.str));break
 return min(c)

def reps(a):
 a=np.asarray(a,dtype=np.int32);c=[]
 def add(name,x):
  b,r=encode_int(x);c.append((b+16,name+'_'+r))
 add('raw',a)
 if a.ndim==2:
  d0=a.copy();d0[1:]-=a[:-1];add('d0',d0)
  d1=a.copy();d1[:,1:]-=a[:,:-1];add('d1',d1)
  L=a.copy();L[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];add('lorenzo',L)
 return min(c),sorted(c)

def solve(X,bound,phase,pol):
 h=2*bound;phi=h*phase/PHASES
 cs=np.r_[np.arange(0,C,2,dtype=np.int32),C-1];co=np.arange(1,C-1,2,dtype=np.int32)
 ts=np.r_[np.arange(0,T,2,dtype=np.int32),T-1];to=np.arange(1,T-1,2,dtype=np.int32)
 sign=np.ones(T,np.float64)
 if pol==-1:sign[1::2]=-1.0
 Y=X*sign[None,:]
 Q=np.rint((Y[np.ix_(cs,ts)]-phi)/h).astype(np.int32)
 CY=phi+h*Q
 P=np.empty_like(X)
 # controls
 P[np.ix_(cs,ts)]=CY*sign[ts][None,:]
 # even/control channels, missing odd times: interpolate in demodulated coordinate then remodulate.
 PYt=0.5*(CY[:,:-2]+CY[:,1:-1])
 P[np.ix_(cs,to)]=PYt*sign[to][None,:]
 # missing odd channels at control times
 PYs=0.5*(CY[:-2,:]+CY[1:-1,:])
 P[np.ix_(co,ts)]=PYs*sign[ts][None,:]
 # missing both: bilinear interpolation of four controls in demodulated space
 PYd=0.25*(CY[:-2,:-2]+CY[1:-1,:-2]+CY[:-2,1:-1]+CY[1:-1,1:-1])
 P[np.ix_(co,to)]=PYd*sign[to][None,:]
 # Controls are already legal by nearest lattice. Missing locations get exact full-step hard-error correction.
 Kt=np.rint((X[np.ix_(cs,to)]-P[np.ix_(cs,to)])/h).astype(np.int32)
 Ks=np.rint((X[np.ix_(co,ts)]-P[np.ix_(co,ts)])/h).astype(np.int32)
 Kd=np.rint((X[np.ix_(co,to)]-P[np.ix_(co,to)])/h).astype(np.int32)
 R=P.copy();R[np.ix_(cs,to)]+=h*Kt;R[np.ix_(co,ts)]+=h*Ks;R[np.ix_(co,to)]+=h*Kd
 me=float(np.max(np.abs(X-R)))
 qr,qall=reps(Q);tr,tall=reps(Kt);sr,sall=reps(Ks);dr,dall=reps(Kd)
 total=qr[0]+tr[0]+sr[0]+dr[0]+128
 miss=Kt.size+Ks.size+Kd.size;nz=int(np.count_nonzero(Kt)+np.count_nonzero(Ks)+np.count_nonzero(Kd))
 return {'phase':phase,'temporal_polarity':pol,'bytes':total,'control_bytes':qr[0],'time_correction_bytes':tr[0],'space_correction_bytes':sr[0],'diagonal_correction_bytes':dr[0],'control_rep':qr[1],'time_rep':tr[1],'space_rep':sr[1],'diagonal_rep':dr[1],'control_fraction':Q.size/X.size,'missing_correction_nonzero_fraction':nz/miss,'time_correction_nonzero':float(np.mean(Kt!=0)),'space_correction_nonzero':float(np.mean(Ks!=0)),'diagonal_correction_nonzero':float(np.mean(Kd!=0)),'maxerr':me,'all_control_reps':qall,'all_time_reps':tall,'all_space_reps':sall,'all_diagonal_reps':dall}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY
  specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392)];rows=[];tiles=[]
  for name,t0,c0 in specs:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);tiles.append({'tile':name,'sz3':sb,'raw':X.size*2})
   for ph in range(PHASES):
    for pol in POLS:
     r=solve(X,bound,ph,pol)
     if r['maxerr']>eps*(1+5e-6):raise RuntimeError(('hard',name,r['maxerr'],eps))
     r.update({'tile':name,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
  combos=[]
  for ph in range(PHASES):
   for pol in POLS:
    rr=[r for r in rows if r['phase']==ph and r['temporal_polarity']==pol];b=sum(r['bytes'] for r in rr);s=sum(t['sz3'] for t in tiles)
    combos.append({'phase':ph,'temporal_polarity':pol,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'control_fraction':float(np.median([r['control_fraction'] for r in rr])),'median_missing_correction_nonzero':float(np.median([r['missing_correction_nonzero_fraction'] for r in rr])),'control_bytes':sum(r['control_bytes'] for r in rr),'time_correction_bytes':sum(r['time_correction_bytes'] for r in rr),'space_correction_bytes':sum(r['space_correction_bytes'] for r in rr),'diagonal_correction_bytes':sum(r['diagonal_correction_bytes'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'bound':bound,'combos':combos,'rows':rows,'scope':'Quarter-density 2D control mesh. Only even-channel/even-time controls plus final boundaries are transmitted; all other samples are deterministically generated by temporal/spatial/bilinear interpolation in either raw or implicit (-1)^t coordinates, then exact 2eps parity-class corrections are serialized separately. Coarse controls use nearest legal 2eps lattice; all bytes counted and final hard error verified. One fixed phase/polarity across four tiles.'}
  print(json.dumps({'best':combos[:8]},indent=2),flush=True);json.dump(out,open('imperial_2d_control_mesh.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
