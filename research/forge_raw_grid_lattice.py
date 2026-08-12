import json,os,struct,sys,itertools
from collections import defaultdict
import numpy as np,segyio,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
ZC=zstd.ZstdCompressor(level=22);ZD=zstd.ZstdDecompressor();DT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
MAG=b'FGLCv001';HDR='<8sBBBB4I5Q';HS=struct.calcsize(HDR)

def dc(A):
 lo=int(A.min()) if A.size else 0;hi=int(A.max()) if A.size else 0
 return 1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3

def delta(A,axis):
 B=A.copy();sl=[slice(None)]*A.ndim;pr=[slice(None)]*A.ndim;sl[axis]=slice(1,None);pr[axis]=slice(None,-1);B[tuple(sl)]=A[tuple(sl)]-A[tuple(pr)];return B

def undelta(A,axis):return np.cumsum(A,axis=axis,dtype=np.int32)

def geometry(X,gx,gy):
 coord=defaultdict(list)
 for i,k in enumerate(zip(gx.tolist(),gy.tolist())):coord[k].append(i)
 keys=[k for k,v in coord.items() if len(v)==1];pts=np.asarray(keys,float);N=len(pts)
 d=pts[:,None,:]-pts[None,:,:];ds=np.sum(d*d,2);ds[ds==0]=np.inf;j=np.argmin(ds,1);v=pts[j]-pts;v=np.where(((v[:,0]<0)|((v[:,0]==0)&(v[:,1]<0)))[:,None],-v,v);lens=np.linalg.norm(v,axis=1);sp=float(np.median(lens));vv=v[(lens>.8*sp)&(lens<1.2*sp)];u=np.median(vv,0);u=u/np.linalg.norm(u);perp=np.array([-u[1],u[0]]);a=pts@u;b=pts@perp
 order=np.argsort(b);cuts=np.where(np.diff(b[order])>.2*sp)[0]+1;groups=np.split(order,cuts);main=[g for g in groups if len(g)>=10];main=sorted(main,key=lambda g:float(np.mean(b[g])));main_idx=np.concatenate(main);amin=float(a[main_idx].min());best=None
 for scale in np.linspace(.995,1.005,101):
  s=sp*scale;mods=np.mod(a[main_idx]-amin,s)
  for phase in np.quantile(mods,[0,.1,.25,.5,.75,.9]):
   qi=np.rint((a[main_idx]-amin-phase)/s).astype(int);pred=amin+phase+qi*s;res=np.abs(a[main_idx]-pred);span=int(qi.max()-qi.min()+1);occ=len(main_idx)/(len(main)*span);score=float(np.median(res)+np.quantile(res,.95)+s*(1-occ)*.05)
   if best is None or score<best[0]:best=(score,s,float(phase),int(qi.min()),int(qi.max()),float(np.median(res)),float(np.quantile(res,.95)))
 _,s,phase,jmin,jmax,medres,p95=best;L=len(main);S=jmax-jmin+1;T=X.shape[1];G=np.zeros((1,L,S,T),np.int32);used=set();tm=[];cells=set()
 for li,g in enumerate(main):
  for q in g.tolist():
   tid=coord[keys[q]][0];st=int(round((a[q]-amin-phase)/s))-jmin
   if not (0<=st<S):continue
   if (li,st) in cells:continue
   cells.add((li,st));tm.append((tid,0,li,st));used.add(tid)
 outids=np.asarray([i for i in range(X.shape[0]) if i not in used],np.int64)
 geom={'all_traces':int(X.shape[0]),'unique_sites':int(len(coord)),'singleton_sites':N,'line_count':L,'station_count':S,'main_traces':len(tm),'grid_occupancy':len(tm)/(L*S),'outlier_traces':int(outids.size),'along_spacing':s,'nearest_spacing':sp,'station_residual_median':medres,'station_residual_p95':p95,'along_axis':u.tolist()}
 return G,tm,outids,geom

def encode4(A,tdiff,perm,rep):
 K=delta(A,3) if tdiff else A;P=np.transpose(K,perm);pc=int(perm[0]|(perm[1]<<2)|(perm[2]<<4)|(perm[3]<<6));streams=[];dtype=1
 if rep==0:
  dtype=dc(P);streams=[ZC.compress(np.ascontiguousarray(P.astype(DT[dtype],copy=False)).tobytes()),b'',b'',b'',b'']
 elif rep==1:
  M=P!=0;vals=P[M].astype(np.int32);dtype=dc(vals);streams=[ZC.compress(np.packbits(M.ravel(),bitorder='little').tobytes()),ZC.compress(vals.astype(DT[dtype],copy=False).tobytes()),b'',b'',b'']
 elif rep==2:
  M=P!=0;vals=P[M].astype(np.int32);sign=vals<0;ab=np.abs(vals);exc=ab!=1;mag=(ab[exc]-2).astype(np.int32);dtype=dc(mag);streams=[ZC.compress(np.packbits(M.ravel(),bitorder='little').tobytes()),ZC.compress(np.packbits(sign,bitorder='little').tobytes()),ZC.compress(np.packbits(exc,bitorder='little').tobytes()),ZC.compress(mag.astype(DT[dtype],copy=False).tobytes()) if mag.size else b'',b'']
 else:raise ValueError(rep)
 h=struct.pack(HDR,MAG,1,int(tdiff),pc,rep,*A.shape,*[len(x) for x in streams]);return h+b''.join(streams),{'tdiff':bool(tdiff),'perm':list(perm),'rep':['raw','sparse','signmag'][rep],'dtype':dtype,'parts':[len(x) for x in streams]}

def decode4(blob):
 q=struct.unpack(HDR,blob[:HS]);magic,ver,tdiff,pc,rep,d0,d1,d2,d3,l0,l1,l2,l3,l4=q
 if magic!=MAG or ver!=1:raise RuntimeError('header')
 perm=tuple((pc>>(2*i))&3 for i in range(4));shape=(d0,d1,d2,d3);pshape=tuple(shape[i] for i in perm);p=HS;lens=[l0,l1,l2,l3,l4];ss=[]
 for L in lens:ss.append(blob[p:p+L]);p+=L
 # dtype is inferred from decompressed byte length and event count only for prototype candidates; raw/sign values are expected int8 in this FORGE tolerance regime, otherwise fall back by length tests.
 n=int(np.prod(shape));inv=np.argsort(perm)
 if rep==0:
  raw=ZD.decompress(ss[0]);item=len(raw)//n;dt={1:np.int8,2:'<i2',4:'<i4'}[item];P=np.frombuffer(raw,dt,count=n).astype(np.int32).reshape(pshape)
 elif rep==1:
  M=np.unpackbits(np.frombuffer(ZD.decompress(ss[0]),np.uint8),bitorder='little',count=n).reshape(pshape).astype(bool);ne=int(M.sum());raw=ZD.decompress(ss[1]);item=(len(raw)//ne if ne else 1);dt={1:np.int8,2:'<i2',4:'<i4'}[item];vals=np.frombuffer(raw,dt,count=ne).astype(np.int32);P=np.zeros(pshape,np.int32);P[M]=vals
 else:
  M=np.unpackbits(np.frombuffer(ZD.decompress(ss[0]),np.uint8),bitorder='little',count=n).reshape(pshape).astype(bool);ne=int(M.sum());sign=np.unpackbits(np.frombuffer(ZD.decompress(ss[1]),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(ZD.decompress(ss[2]),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
  if exc.any():
   raw=ZD.decompress(ss[3]);item=len(raw)//int(exc.sum());dt={1:np.int8,2:'<i2',4:'<i4'}[item];ab[exc]=np.frombuffer(raw,dt,count=int(exc.sum())).astype(np.int32)+2
  vals=np.where(sign,-ab,ab);P=np.zeros(pshape,np.int32);P[M]=vals
 A=np.transpose(P,inv);return undelta(A,3) if tdiff else A

def best_encode(A):
 rows=[];perms=[(1,2,0,3),(2,1,0,3),(3,1,2,0),(0,1,2,3)]
 for td in [0,1]:
  for perm in perms:
   for rep in [0,1,2]:
    b,m=encode4(A,td,perm,rep);R=decode4(b)
    if not np.array_equal(R,A):raise RuntimeError('codec mismatch')
    rows.append((len(b),b,m))
 rows.sort(key=lambda x:x[0]);return rows[0],rows

def sz3(X,eps):
 cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(b,np.float32,X.shape);return int(b.size),float(np.max(np.abs(X-R)))

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True,endian='little') as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=int(X.nbytes);G,tm,outids,geom=geometry(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32).reshape(1,1,len(outids),X.shape[1]);(lm,mb,mm),mainrows=best_encode(G);(lo,ob,mo),outrows=best_encode(O);top=struct.pack('<8sdQQ',b'FGTOP001',eps,lm,lo)+mb+ob;p=struct.calcsize('<8sdQQ');_,ee,a,b=struct.unpack('<8sdQQ',top[:p]);RG=decode4(top[p:p+a]);RO=decode4(top[p+a:p+a+b]).reshape(len(outids),X.shape[1]);Y=np.empty_like(X)
for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));sb,se=sz3(X,eps);ratio=raw/len(top);szr=raw/sb
K=delta(G,3)
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_best':{'bytes':lm,**mm},'outlier_best':{'bytes':lo,**mo},'container_bytes':len(top),'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':sb,'ratio':szr,'maxerr':se},'gain_over_sz3':ratio/szr,'main_top':[{'bytes':n,**m} for n,_,m in mainrows[:12]],'out_top':[{'bytes':n,**m} for n,_,m in outrows[:12]]}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('forge_raw_grid_lattice.json','w'),indent=2)
