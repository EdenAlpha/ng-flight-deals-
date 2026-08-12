import json,os,struct,sys
import numpy as np
import segyio,zstandard as zstd
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
MAGIC=b'ZTCOUNT1';HDR='<8sddIIQQQBB';HS=struct.calcsize(HDR)

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

def signmag(v,counts,order,alternating):
 v=np.asarray(v,np.int32);neg=v<0;mag=np.abs(v);exc=mag!=1;em=Z.compress(np.packbits(exc,bitorder='little').tobytes());extras=(mag[exc]-2).astype(np.uint64);eb=Z.compress(leb(extras))
 if alternating:
  res=np.zeros(len(v),bool);p=0
  for i in order:
   n=int(counts[i])
   for j in range(n):
    pred=False if j==0 else (not bool(neg[p+j-1]));res[p+j]=(bool(neg[p+j])!=pred)
   p+=n
  sb=Z.compress(np.packbits(res,bitorder='little').tobytes());typ=2
 else:
  sb=Z.compress(np.packbits(neg,bitorder='little').tobytes());typ=1
 h=struct.pack('<BQQQ',typ,len(sb),len(em),len(eb));return h+sb+em+eb,{'type':typ,'sign_bytes':len(sb),'exception_mask_bytes':len(em),'exception_bytes':len(eb),'nonunit_fraction':float(exc.mean()) if len(v) else 0.0}
def unsignmag(blob,n,counts,order):
 hs=struct.calcsize('<BQQQ');typ,ls,lm,le=struct.unpack('<BQQQ',blob[:hs]);p=hs;sb=blob[p:p+ls];p+=ls;mb=blob[p:p+lm];p+=lm;eb=blob[p:p+le];p+=le
 if p!=len(blob):raise RuntimeError('value length')
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

def encode_matrix(A,eps):
 step=2.0*eps;Q=np.rint(A/step).astype(np.int32);K=Q.copy();K[:,1:]-=Q[:,:-1];M=K!=0;counts=M.sum(axis=1).astype(np.uint64);order=sorted(range(len(A)),key=lambda i:(int(counts[i]),i));gaps=[];vals=[]
 for i in order:
  pos=np.flatnonzero(M[i]);g=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);gaps.extend(g.tolist());vals.extend(K[i,pos].tolist())
 cb=Z.compress(leb(counts));gb=Z.compress(leb(gaps));v=np.asarray(vals,np.int32);dc,vint=packi(v);rawv=struct.pack('<BB',0,dc)+vint;sm1,m1=signmag(v,counts,order,False);sm2,m2=signmag(v,counts,order,True);cands=[(len(rawv),rawv,{'type':0,'dtype':dc}),(len(sm1),sm1,m1),(len(sm2),sm2,m2)];_,vb,vm=min(cands,key=lambda x:x[0]);head=struct.pack(HDR,MAGIC,float(eps),float(step),A.shape[0],A.shape[1],len(cb),len(gb),len(vb),1,vm['type']);blob=head+cb+gb+vb
 # Decoder uses only blob.
 magic,ee,ss,nr,nt,lc,lg,lv,ordering,vtype=struct.unpack(HDR,blob[:HS]);p=HS;cbr=blob[p:p+lc];p+=lc;gbr=blob[p:p+lg];p+=lg;vbr=blob[p:p+lv];p+=lv
 if p!=len(blob) or magic!=MAGIC:raise RuntimeError('container')
 cnt=unleb(D.decompress(cbr),nr).astype(np.int64);ord2=sorted(range(nr),key=lambda i:(int(cnt[i]),i));ne=int(cnt.sum());gg=unleb(D.decompress(gbr),ne).astype(np.int64)
 if vtype==0:typ,dc2=struct.unpack('<BB',vbr[:2]);vv=unpacki(vbr[2:],dc2,ne)
 else:vv=unsignmag(vbr,ne,cnt,ord2)
 KK=np.zeros((nr,nt),np.int32);q=0
 for i in ord2:
  c=int(cnt[i])
  if c:
   pos=np.cumsum(gg[q:q+c]+1)-1;KK[i,pos]=vv[q:q+c];q+=c
 QQ=np.cumsum(KK,axis=1,dtype=np.int32)
 if not np.array_equal(QQ,Q):raise RuntimeError('integer roundtrip')
 R=QQ.astype(np.float32)*np.float32(ss);me=float(np.max(np.abs(A-R)))
 return blob,R,{'events':ne,'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'value_meta':vm,'bytes':len(blob),'maxerr':me}

def load(path):
 with segyio.open(path,'r',ignore_geometry=True) as f:
  X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
 groups={};bad=[]
 for i,(x,y) in enumerate(zip(gx,gy)):
  if x==0 and y==0:bad.append(i);continue
  groups.setdefault((int(x),int(y)),[]).append(i)
 keys=sorted(groups);counts=np.asarray([len(groups[k]) for k in keys]);C=int(np.bincount(counts).argmax());valid=np.concatenate([np.asarray([groups[k][c] for k in keys],np.int64) for c in range(C)]);A=X[valid];B=X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32);return X,A,B,{'receivers':len(keys),'components':C,'valid_traces':len(valid),'bad_traces':len(bad)}
def run(path):
 X,A,B,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);ba,RA,ma=encode_matrix(A,eps);total=48+len(ba);me=float(np.max(np.abs(A-RA)));mb=None
 if B.size:
  bb,RB,mb=encode_matrix(B,eps);total+=len(bb);me=max(me,float(np.max(np.abs(B-RB))))
 out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'valid_stream':ma,'bad_stream':mb};print(json.dumps(out,indent=2),flush=True);return out
out={'shots':[run(p) for p in sys.argv[1:]]};json.dump(out,open('soda_zero_count_sorted_results.json','w'),indent=2)
