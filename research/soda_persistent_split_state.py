import json,os,struct,sys
import numpy as np
import zstandard as zstd
# Reuse audited loader + legal-state path construction, but not its old mixed value stream.
src=open('research/soda_persistent_legal_state.py').read().split('\ndef encode_panel')[0]
exec(compile(src,'soda_persistent_legal_state.py','exec'),globals())
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
FACTORS=[2.0,1.5,1.0,0.75,0.5,0.375,0.25,0.125]

def packi(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dc=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;return dc,ZC.compress(np.ascontiguousarray(a.astype(IDT[dc],copy=False)).tobytes())
def unpacki(b,dc,n):
 a=np.frombuffer(ZD.decompress(b),dtype=IDT[dc],count=n)
 if a.size!=n:raise RuntimeError('int length')
 return a.astype(np.int32,copy=False)
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

def signmag(v):
 v=np.asarray(v,np.int32);neg=v<0;mag=np.abs(v);exc=mag!=1;sb=ZC.compress(np.packbits(neg,bitorder='little').tobytes());mb=ZC.compress(np.packbits(exc,bitorder='little').tobytes());extra=(mag[exc]-2).astype(np.uint64);eb=ZC.compress(leb(extra));h=struct.pack('<QQQ',len(sb),len(mb),len(eb));return h+sb+mb+eb,{'sign_bytes':len(sb),'exception_mask_bytes':len(mb),'exception_value_bytes':len(eb),'nonunit_fraction':float(exc.mean()) if len(v) else 0.0}
def unsignmag(blob,n):
 hs=struct.calcsize('<QQQ');ls,lm,le=struct.unpack('<QQQ',blob[:hs]);p=hs;sb=blob[p:p+ls];p+=ls;mb=blob[p:p+lm];p+=lm;eb=blob[p:p+le];p+=le
 if p!=len(blob):raise RuntimeError('signmag length')
 neg=np.unpackbits(np.frombuffer(ZD.decompress(sb),np.uint8),bitorder='little',count=n).astype(bool);exc=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little',count=n).astype(bool);mag=np.ones(n,np.int32);mag[exc]=unleb(ZD.decompress(eb),int(exc.sum())).astype(np.int32)+2;return np.where(neg,-mag,mag).astype(np.int32)

def encode_panel(A,eps,factor):
 delta=float(eps*factor*(1.0-3e-7));nr,nt=A.shape;Q=np.empty(A.shape,np.int32);segments=0
 for r in range(nr):Q[r],n=legal_path(A[r],eps,delta);segments+=n
 init=Q[:,0].copy();# choose direct or spatial-delta initial-state stream
 imodes=[]
 for mode,iv in [(0,init),(1,np.r_[init[0],np.diff(init)])]:
  dc,b=packi(iv);imodes.append((len(b)+2,mode,dc,b))
 _,imode,idc,ib=min(imodes,key=lambda x:x[0])
 K=np.zeros_like(Q);K[:,1:]=Q[:,1:]-Q[:,:-1];mask=K!=0;counts=mask.sum(axis=1).astype(np.uint64);graw=[];vals=[]
 for r in range(nr):
  pos=np.flatnonzero(mask[r]);g=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);graw.append(leb(g));vals.append(K[r,pos])
 cb=ZC.compress(leb(counts));gb=ZC.compress(b''.join(graw));vv=np.concatenate(vals) if vals else np.empty(0,np.int32);vdc,vint=packi(vv);vsm,smeta=signmag(vv)
 if len(vsm)<len(vint)+1:vtype=1;vb=vsm
 else:vtype=0;vb=struct.pack('<B',vdc)+vint
 h=struct.pack('<dBBBQQQQ',delta,imode,idc,vtype,len(ib),len(cb),len(gb),len(vb));blob=h+ib+cb+gb+vb
 # Decode only bytes + panel shape.
 hs=struct.calcsize('<dBBBQQQQ');dd,im,idc2,vt,li,lc,lg,lv=struct.unpack('<dBBBQQQQ',blob[:hs]);p=hs;ibr=blob[p:p+li];p+=li;cbr=blob[p:p+lc];p+=lc;gbr=blob[p:p+lg];p+=lg;vbr=blob[p:p+lv];p+=lv
 if p!=len(blob):raise RuntimeError('container length')
 ii=unpacki(ibr,idc2,nr)
 if im==1:ii=np.cumsum(ii,dtype=np.int32)
 cc=unleb(ZD.decompress(cbr),nr).astype(int);ne=int(cc.sum());gg=unleb(ZD.decompress(gbr),ne).astype(np.int64)
 if vt==0:dc=vbr[0];dv=unpacki(vbr[1:],dc,ne)
 else:dv=unsignmag(vbr,ne)
 QQ=np.empty((nr,nt),np.int32);q=0
 for r,c in enumerate(cc):
  kk=np.zeros(nt,np.int32)
  if c:
   po=np.cumsum(gg[q:q+c]+1)-1;kk[po]=dv[q:q+c];q+=c
  QQ[r]=ii[r]+np.cumsum(kk,dtype=np.int32)
 if not np.array_equal(QQ,Q):raise RuntimeError('state roundtrip')
 R=QQ.astype(np.float32)*np.float32(dd);me=float(np.max(np.abs(A-R)))
 return blob,R,{'factor':factor,'events':ne,'segments':segments,'event_fraction':ne/A.size,'init_bytes':len(ib),'init_mode':imode,'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'value_type':'signmag' if vtype else 'int','delta_nonunit_fraction':smeta['nonunit_fraction'],'bytes':len(blob),'maxerr':me}

def run(path):
 X,panels,extra,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);rows=[]
 for f in FACTORS:
  total=40;ms=[];me=0.
  for A in panels+[extra]:
   if not A.size:continue
   b,R,m=encode_panel(A,eps,f);total+=len(b);ms.append(m);me=max(me,float(np.max(np.abs(A-R))))
  row={'factor':f,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'events':sum(m['events'] for m in ms),'segments':sum(m['segments'] for m in ms),'init_bytes':sum(m['init_bytes'] for m in ms),'count_bytes':sum(m['count_bytes'] for m in ms),'gap_bytes':sum(m['gap_bytes'] for m in ms),'value_bytes':sum(m['value_bytes'] for m in ms),'event_fraction':sum(m['events'] for m in ms)/X.size,'value_types':[m['value_type'] for m in ms],'nonunit':[m['delta_nonunit_fraction'] for m in ms]};rows.append(row);print('ROW',json.dumps(row),flush=True)
 rows.sort(key=lambda x:x['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'rows':rows};json.dump(out,open('soda_persistent_split_state.json','w'),indent=2);print('BEST',json.dumps(rows,indent=2),flush=True)
run(sys.argv[1])
