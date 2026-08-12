import json,os,struct,sys,math
import numpy as np
import segyio,zstandard as zstd
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
MAGIC=b'ZTPHASE1';HDR='<8sddIIHQQQQBB';HS=struct.calcsize(HDR)

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
   if j>=len(b):raise RuntimeError('varint trunc')
   v=b[j];j+=1;x|=(v&127)<<sh
   if v<128:break
   sh+=7
  a[i]=x;i+=1
 if j!=len(b):raise RuntimeError('varint trailing')
 return a
def packi(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dc=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;return dc,Z.compress(np.ascontiguousarray(a.astype(IDT[dc],copy=False)).tobytes())
def unpacki(b,dc,n):
 a=np.frombuffer(D.decompress(b),dtype=IDT[dc],count=n)
 if a.size!=n:raise RuntimeError('int len')
 return a.astype(np.int32,copy=False)
def packphase(idx,M):
 if M==1:return b''
 bits=int(math.log2(M));a=np.asarray(idx,np.uint16);raw=np.packbits(((a[:,None]>>np.arange(bits,dtype=np.uint16))&1).astype(np.uint8).ravel(),bitorder='little').tobytes();return Z.compress(raw)
def unpackphase(b,n,M):
 if M==1:return np.zeros(n,np.int32)
 bits=int(math.log2(M));bb=np.unpackbits(np.frombuffer(D.decompress(b),np.uint8),bitorder='little',count=n*bits).reshape(n,bits);return np.sum(bb.astype(np.int32)*(1<<np.arange(bits,dtype=np.int32)),axis=1)

def signmag(v,counts,order,alt):
 v=np.asarray(v,np.int32);neg=v<0;mag=np.abs(v);exc=mag!=1;em=Z.compress(np.packbits(exc,bitorder='little').tobytes());eb=Z.compress(leb((mag[exc]-2).astype(np.uint64)))
 if alt:
  res=np.zeros(len(v),bool);p=0
  for i in order:
   n=int(counts[i])
   for j in range(n):
    pred=False if j==0 else (not bool(neg[p+j-1]));res[p+j]=(bool(neg[p+j])!=pred)
   p+=n
  sb=Z.compress(np.packbits(res,bitorder='little').tobytes());typ=2
 else:sb=Z.compress(np.packbits(neg,bitorder='little').tobytes());typ=1
 return struct.pack('<BQQQ',typ,len(sb),len(em),len(eb))+sb+em+eb,{'type':typ,'sign_bytes':len(sb),'exception_mask_bytes':len(em),'exception_bytes':len(eb),'nonunit_fraction':float(exc.mean()) if len(v) else 0.0}
def unsignmag(blob,n,counts,order):
 hs=struct.calcsize('<BQQQ');typ,ls,lm,le=struct.unpack('<BQQQ',blob[:hs]);p=hs;sb=blob[p:p+ls];p+=ls;mb=blob[p:p+lm];p+=lm;eb=blob[p:p+le];p+=le
 if p!=len(blob):raise RuntimeError('value len')
 bits=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=n).astype(bool);exc=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little',count=n).astype(bool);mag=np.ones(n,np.int32);mag[exc]=unleb(D.decompress(eb),int(exc.sum())).astype(np.int32)+2
 if typ==1:neg=bits
 else:
  neg=np.zeros(n,bool);q=0
  for i in order:
   c=int(counts[i])
   for j in range(c):
    pred=False if j==0 else (not neg[q+j-1]);neg[q+j]=pred^bits[q+j]
   q+=c
 return np.where(neg,-mag,mag).astype(np.int32)

def choose_phase(A,eps,M):
 step=2.0*eps*(1-2e-7);nr,nt=A.shape
 if M==1:return np.zeros(nr,np.int32),np.rint(A/step).astype(np.int32),step
 phases=step*np.arange(M,dtype=np.float64)/M;idx=np.zeros(nr,np.int32);Q=np.empty((nr,nt),np.int32)
 for r,a in enumerate(A):
  best=None
  for k,p in enumerate(phases):
   q=np.rint((a.astype(np.float64)-p)/step).astype(np.int32);d=np.r_[q[0],np.diff(q)];score=(int(np.count_nonzero(d)),int(np.abs(d).sum()),k)
   if best is None or score<best[0]:best=(score,k,q)
  idx[r]=best[1];Q[r]=best[2]
 return idx,Q,step

def encode_matrix(A,eps,M):
 idx,Q,step=choose_phase(A,eps,M);nr,nt=A.shape;pb=packphase(idx,M);K=Q.copy();K[:,1:]-=Q[:,:-1];mask=K!=0;counts=mask.sum(axis=1).astype(np.uint64);order=sorted(range(nr),key=lambda i:(int(counts[i]),i));g=[];vals=[]
 for i in order:
  pos=np.flatnonzero(mask[i]);gg=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);g.extend(gg.tolist());vals.extend(K[i,pos].tolist())
 cb=Z.compress(leb(counts));gb=Z.compress(leb(g));v=np.asarray(vals,np.int32);dc,vi=packi(v);rawv=struct.pack('<BB',0,dc)+vi;s1,m1=signmag(v,counts,order,False);s2,m2=signmag(v,counts,order,True);_,vb,vm=min([(len(rawv),rawv,{'type':0,'dtype':dc}),(len(s1),s1,m1),(len(s2),s2,m2)],key=lambda x:x[0]);head=struct.pack(HDR,MAGIC,float(eps),float(step),nr,nt,M,len(pb),len(cb),len(gb),len(vb),1,vm['type']);blob=head+pb+cb+gb+vb
 # decode
 magic,ee,ss,nr2,nt2,MM,lp,lc,lg,lv,ordmode,vtype=struct.unpack(HDR,blob[:HS]);p=HS;pbr=blob[p:p+lp];p+=lp;cbr=blob[p:p+lc];p+=lc;gbr=blob[p:p+lg];p+=lg;vbr=blob[p:p+lv];p+=lv
 if p!=len(blob) or magic!=MAGIC:raise RuntimeError('container')
 ii=unpackphase(pbr,nr2,MM);cnt=unleb(D.decompress(cbr),nr2).astype(np.int64);ord2=sorted(range(nr2),key=lambda i:(int(cnt[i]),i));ne=int(cnt.sum());gg=unleb(D.decompress(gbr),ne).astype(np.int64)
 if vtype==0:_,dc2=struct.unpack('<BB',vbr[:2]);vv=unpacki(vbr[2:],dc2,ne)
 else:vv=unsignmag(vbr,ne,cnt,ord2)
 KK=np.zeros((nr2,nt2),np.int32);q=0
 for i in ord2:
  c=int(cnt[i])
  if c:
   pos=np.cumsum(gg[q:q+c]+1)-1;KK[i,pos]=vv[q:q+c];q+=c
 QQ=np.cumsum(KK,axis=1,dtype=np.int32)
 if not np.array_equal(QQ,Q):raise RuntimeError('integer roundtrip')
 ph=ss*ii.astype(np.float64)/MM if MM>1 else np.zeros(nr2);R=(QQ.astype(np.float64)*ss+ph[:,None]).astype(np.float32);me=float(np.max(np.abs(A-R)))
 return blob,R,{'M':M,'events':ne,'phase_bytes':len(pb),'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'value_meta':vm,'bytes':len(blob),'maxerr':me}

def load(path):
 with segyio.open(path,'r',ignore_geometry=True) as f:
  X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
 groups={};bad=[]
 for i,(x,y) in enumerate(zip(gx,gy)):
  if x==0 and y==0:bad.append(i);continue
  groups.setdefault((int(x),int(y)),[]).append(i)
 keys=sorted(groups);C=int(np.bincount(np.asarray([len(groups[k]) for k in keys])).argmax());valid=np.concatenate([np.asarray([groups[k][c] for k in keys],np.int64) for c in range(C)]);return X,X[valid],X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32),{'receivers':len(keys),'components':C,'valid_traces':len(valid),'bad_traces':len(bad)}
def run(path):
 X,A,B,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);rows=[]
 for M in [1,2,4]:
  ba,RA,ma=encode_matrix(A,eps,M);total=48+len(ba);me=float(np.max(np.abs(A-RA)));mb=None
  if B.size:bb,RB,mb=encode_matrix(B,eps,M);total+=len(bb);me=max(me,float(np.max(np.abs(B-RB))))
  row={'M':M,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'valid_stream':ma,'bad_stream':mb};rows.append(row);print('ROW',json.dumps({'M':M,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':row['valid'],'valid_stream':ma},indent=2),flush=True)
 rows.sort(key=lambda x:x['ratio'],reverse=True);return {'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'rows':rows}
out={'shots':[run(p) for p in sys.argv[1:]]};json.dump(out,open('soda_phase_count_results.json','w'),indent=2)
