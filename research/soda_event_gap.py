import itertools,json,os,struct,sys
import numpy as np,segyio,zstandard as zstd
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())

MAG=b'EGAPv001';HDR='<8sBBBB4I5Q';HS=struct.calcsize(HDR)
# order is a permutation of spatial axes C,L,S. Time remains event-position dimension.
def leb128_u(values):
 out=bytearray()
 for vv in values:
  v=int(vv)
  while v>=128:out.append((v&127)|128);v>>=7
  out.append(v)
 return bytes(out)
def leb128_decode(data,n):
 out=np.empty(n,np.int32);j=0;v=0;shift=0
 for b in data:
  v|=(b&127)<<shift
  if not (b&128):
   if j>=n:raise RuntimeError('too many varints')
   out[j]=v;j+=1;v=0;shift=0
  else:shift+=7
 if j!=n or shift:raise RuntimeError('varint count')
 return out

def encode(K,order,valmode,level):
 zc=zstd.ZstdCompressor(level=level);P=np.transpose(K,order+(3,));sh=P.shape;tr=P.reshape(-1,sh[-1]);counts=np.count_nonzero(tr,axis=1).astype(np.uint16);gaps=[];vals=[]
 for row in tr:
  pos=np.flatnonzero(row)
  if pos.size:
   g=np.empty(pos.size,np.int32);g[0]=pos[0]+1
   if pos.size>1:g[1:]=np.diff(pos)
   gaps.extend(g.tolist());vals.extend(row[pos].astype(np.int32).tolist())
 gaps=np.asarray(gaps,np.int32);vals=np.asarray(vals,np.int32);cb=zc.compress(counts.astype('<u2',copy=False).tobytes());gb=zc.compress(leb128_u(gaps));v1=v2=v3=b'';dc=1
 if valmode==0:
  dc=dtype_code(vals);v1=zc.compress(vals.astype(DT[dc],copy=False).tobytes())
 else:
  sign=vals<0;ab=np.abs(vals);exc=ab!=1;v1=zc.compress(np.packbits(sign,bitorder='little').tobytes());v2=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);v3=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else b''
 oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(HDR,MAG,1,oc,valmode,dc,*K.shape,len(cb),len(gb),len(v1),len(v2),len(v3));parts={'counts':len(cb),'gaps':len(gb),'v1':len(v1),'v2':len(v2),'v3':len(v3),'events':int(vals.size),'raw_varint_bytes':len(leb128_u(gaps))};return h+cb+gb+v1+v2+v3,parts

def decode(blob):
 q=struct.unpack(HDR,blob[:HS]);magic,ver,oc,valmode,dc,d0,d1,d2,d3,lc,lg,l1,l2,l3=q
 if magic!=MAG or ver!=1:raise RuntimeError('header')
 order=tuple((oc>>(2*i))&3 for i in range(3));shape=(d0,d1,d2,d3);pshape=tuple(shape[i] for i in order)+(d3,);ntr=int(np.prod(pshape[:-1]));T=d3;p=HS;cb=blob[p:p+lc];p+=lc;gb=blob[p:p+lg];p+=lg;v1=blob[p:p+l1];p+=l1;v2=blob[p:p+l2];p+=l2;v3=blob[p:p+l3];p+=l3;zd=zstd.ZstdDecompressor();counts=np.frombuffer(zd.decompress(cb),'<u2',count=ntr).astype(np.int32);ne=int(counts.sum());gaps=leb128_decode(zd.decompress(gb),ne)
 if valmode==0:vals=np.frombuffer(zd.decompress(v1),dtype=DT[dc],count=ne).astype(np.int32)
 else:
  sign=np.unpackbits(np.frombuffer(zd.decompress(v1),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(v2),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
  if exc.any():ab[exc]=np.frombuffer(zd.decompress(v3),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
  vals=np.where(sign,-ab,ab)
 tr=np.zeros((ntr,T),np.int32);k=0
 for i,c in enumerate(counts):
  if c:
   g=gaps[k:k+c];pos=np.cumsum(g)-1
   if pos[-1]>=T:raise RuntimeError('position range')
   tr[i,pos]=vals[k:k+c];k+=c
 P=tr.reshape(pshape);# inverse spatial permutation, keep time last
 inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
eps=.1*float(X.astype(np.float64).std());step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);rows=[]
for order in itertools.permutations((0,1,2)):
 for vm in [0,1]:
  for level in [19,22]:
   b,parts=encode(K,order,vm,level);R=decode(b)
   if not np.array_equal(R,K):raise RuntimeError('gap decode mismatch')
   rows.append({'order':list(order),'value_mode':'signed' if vm==0 else 'signmag','level':level,'bytes':len(b),'parts':parts})
rows.sort(key=lambda r:r['bytes'])
# Also event-gap code outlier traces directly/time-differenced with a singleton geometry representation.
def encode_out_gap(O,td,vm,level):
 A=delta(O,1) if td else O;K4=A.reshape(1,1,A.shape[0],A.shape[1]);return encode(K4,(0,1,2),vm,level)
def decode_out_gap(b,td):
 A=decode(b).reshape(O.shape);return undelta(A,1) if td else A
outrows=[]
for td in [0,1]:
 for vm in [0,1]:
  for level in [19,22]:
   b,parts=encode_out_gap(O,td,vm,level);R=decode_out_gap(b,td)
   if not np.array_equal(R,O):raise RuntimeError('out gap mismatch')
   outrows.append({'tdiff':bool(td),'value_mode':'signed' if vm==0 else 'signmag','level':level,'bytes':len(b),'parts':parts})
# include prior generic outlier modes so encoder chooses cheapest legitimate form
for td in [0,1]:
 A=delta(O,1) if td else O
 for level in [19,22]:
  for perm in [(0,1,2,3),(3,1,2,0)]:
   for rep in [0,1,2]:
    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);R=undelta(R,1) if td else R
    if not np.array_equal(R,O):raise RuntimeError('generic out mismatch')
    outrows.append({'tdiff':bool(td),'value_mode':'generic-'+['raw','sparse','ternary'][rep],'level':level,'perm':list(perm),'bytes':len(b)})
outrows.sort(key=lambda r:r['bytes']);br=rows[0];bo=outrows[0];vm=0 if br['value_mode']=='signed' else 1;mb,_=encode(K,tuple(br['order']),vm,br['level'])
if bo['value_mode'].startswith('generic-'):
 A=delta(O,1) if bo['tdiff'] else O;rep={'generic-raw':0,'generic-sparse':1,'generic-ternary':2}[bo['value_mode']];ob=encode_out_sparse(A,tuple(bo['perm']),rep,bo['level']);out_decoder=('generic',bo)
else:
 vm2=0 if bo['value_mode']=='signed' else 1;ob,_=encode_out_gap(O,bo['tdiff'],vm2,bo['level']);out_decoder=('gap',bo)
top=struct.pack('<8sdQQB',b'EGTOP001',eps,len(mb),len(ob),0 if out_decoder[0]=='gap' else 1)+mb+ob;p=struct.calcsize('<8sdQQB');_,ee,lm,lo,kind=struct.unpack('<8sdQQB',top[:p]);RK=decode(top[p:p+lm]);obb=top[p+lm:p+lm+lo]
if kind==0:RO=decode_out_gap(obb,bo['tdiff'])
else:
 A=decode_out_sparse(obb);RO=undelta(A,1) if bo['tdiff'] else A
RG=undelta(RK,3);Y=np.empty_like(X)
for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps);ratio=raw/len(top);szr=raw/szb
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_candidates':rows[:20],'outlier_candidates':outrows[:20],'container_bytes':len(top),'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':szr,'maxerr':sze},'gain_over_sz3':ratio/szr}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_event_gap.json','w'),indent=2)
