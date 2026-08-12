import json,os,struct,sys,math
import numpy as np
import segyio,zstandard as zstd
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
MS=[1,2,4,8,16,32,64]

def leb(u):
 o=bytearray()
 for x in np.asarray(u,dtype=np.uint64).ravel():
  x=int(x)
  while x>=128:o.append((x&127)|128);x>>=7
  o.append(x)
 return bytes(o)
def unleb(b,n):
 a=np.empty(n,np.uint64);i=j=0
 while i<n:
  x=sh=0
  while True:
   if j>=len(b):raise RuntimeError('trunc')
   v=b[j];j+=1;x|=(v&127)<<sh
   if v<128:break
   sh+=7
  a[i]=x;i+=1
 if j!=len(b):raise RuntimeError('trail')
 return a
def packi(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dc=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;return dc,Z.compress(np.ascontiguousarray(a.astype(IDT[dc],copy=False)).tobytes())
def unpacki(b,dc,n):
 a=np.frombuffer(D.decompress(b),dtype=IDT[dc],count=n)
 if a.size!=n:raise RuntimeError('int len')
 return a.astype(np.int32,copy=False)
def pack_phase(idx,M):
 if M==1:return b''
 bits=int(math.log2(M));a=np.asarray(idx,np.uint16);bb=((a[:,None]>>np.arange(bits,dtype=np.uint16))&1).astype(np.uint8).ravel();return Z.compress(np.packbits(bb,bitorder='little').tobytes())
def unpack_phase(blob,n,M):
 if M==1:return np.zeros(n,np.int32)
 bits=int(math.log2(M));bb=np.unpackbits(np.frombuffer(D.decompress(blob),np.uint8),bitorder='little',count=n*bits).reshape(n,bits);return np.sum(bb.astype(np.int32)*(1<<np.arange(bits,dtype=np.int32)),axis=1)

def choose(A,eps,M,mode):
 step=2.0*eps*(1-2e-7);nr,nt=A.shape
 if M==1:return np.zeros(nr,np.int32),np.rint(A/step).astype(np.int32),step
 phases=step*np.arange(M,dtype=np.float64)/M
 if mode=='component':
  best=None
  for k,p in enumerate(phases):
   Q=np.rint((A.astype(np.float64)-p)/step).astype(np.int32);K=Q.copy();K[:,1:]-=Q[:,:-1];score=(int(np.count_nonzero(K)),int(np.abs(K).sum()))
   if best is None or score<best[0]:best=(score,k,Q)
  return np.full(nr,best[1],np.int32),best[2],step
 idx=np.zeros(nr,np.int32);Q=np.empty((nr,nt),np.int32)
 for r,a in enumerate(A):
  best=None
  for k,p in enumerate(phases):
   q=np.rint((a.astype(np.float64)-p)/step).astype(np.int32);d=np.r_[q[0],np.diff(q)];score=(int(np.count_nonzero(d)),int(np.abs(d).sum()),k)
   if best is None or score<best[0]:best=(score,k,q)
  idx[r]=best[1];Q[r]=best[2]
 return idx,Q,step

def encode_panel(A,eps,M,mode):
 idx,Q,step=choose(A,eps,M,mode);nr,nt=A.shape;pb=pack_phase(idx,M);K=Q.copy();K[:,1:]-=Q[:,:-1];mask=K!=0;counts=mask.sum(axis=1).astype(np.uint64);graw=[];vals=[]
 for r in range(nr):
  pos=np.flatnonzero(mask[r]);g=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);graw.append(leb(g));vals.append(K[r,pos])
 cb=Z.compress(leb(counts));gb=Z.compress(b''.join(graw));vv=np.concatenate(vals) if vals else np.empty(0,np.int32);dc,vb=packi(vv);h=struct.pack('<dHBBQQQQ',step,M,0 if mode=='trace' else 1,dc,len(pb),len(cb),len(gb),len(vb));blob=h+pb+cb+gb+vb
 # Exact byte decode
 hs=struct.calcsize('<dHBBQQQQ');ss,MM,md,dc,lp,lc,lg,lv=struct.unpack('<dHBBQQQQ',blob[:hs]);p=hs;pbr=blob[p:p+lp];p+=lp;cbr=blob[p:p+lc];p+=lc;gbr=blob[p:p+lg];p+=lg;vbr=blob[p:p+lv];p+=lv
 if p!=len(blob):raise RuntimeError('length')
 ii=unpack_phase(pbr,nr,MM);cc=unleb(D.decompress(cbr),nr).astype(int);ne=int(cc.sum());gg=unleb(D.decompress(gbr),ne).astype(np.int64);vv2=unpacki(vbr,dc,ne);QQ=np.zeros((nr,nt),np.int32);q=0
 for r,c in enumerate(cc):
  kk=np.zeros(nt,np.int32)
  if c:
   po=np.cumsum(gg[q:q+c]+1)-1;kk[po]=vv2[q:q+c];q+=c
  QQ[r]=np.cumsum(kk,dtype=np.int32)
 if not np.array_equal(QQ,Q):raise RuntimeError('Q roundtrip')
 phase=ss*ii.astype(np.float64)/MM if MM>1 else np.zeros(nr);R=(QQ.astype(np.float64)*ss+phase[:,None]).astype(np.float32);me=float(np.max(np.abs(A-R)))
 return blob,R,{'M':M,'mode':mode,'events':ne,'event_fraction':ne/A.size,'phase_bytes':len(pb),'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'dtype':dc,'bytes':len(blob),'maxerr':me}

def load(path):
 with segyio.open(path,'r',ignore_geometry=True) as f:
  X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
 groups={};bad=[]
 for i,(x,y) in enumerate(zip(gx,gy)):
  if x==0 and y==0:bad.append(i);continue
  groups.setdefault((int(x),int(y)),[]).append(i)
 keys=sorted(groups);C=int(np.bincount(np.asarray([len(groups[k]) for k in keys])).argmax());panels=[np.stack([X[groups[k][c]] for k in keys]) for c in range(C)];extra=X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32);return X,panels,extra,{'receivers':len(keys),'components':C,'bad_traces':len(bad)}
def run(path):
 X,panels,extra,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);rows=[]
 for M in MS:
  for mode in (['trace'] if M==1 else ['component','trace']):
   total=40;ms=[];me=0.
   for A in panels+[extra]:
    if not A.size:continue
    b,R,m=encode_panel(A,eps,M,mode);total+=len(b);ms.append(m);me=max(me,float(np.max(np.abs(A-R))))
   row={'M':M,'mode':mode,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'events':sum(m['events'] for m in ms),'phase_bytes':sum(m['phase_bytes'] for m in ms),'count_bytes':sum(m['count_bytes'] for m in ms),'gap_bytes':sum(m['gap_bytes'] for m in ms),'value_bytes':sum(m['value_bytes'] for m in ms),'event_fraction':sum(m['events'] for m in ms)/X.size,'dtypes':[m['dtype'] for m in ms]};rows.append(row);print('ROW',json.dumps(row),flush=True)
 rows.sort(key=lambda x:x['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'rows':rows};json.dump(out,open('soda_phase_lattice.json','w'),indent=2);print('BEST',json.dumps(rows,indent=2),flush=True)
run(sys.argv[1])
