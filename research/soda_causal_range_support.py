import itertools,json,os,struct,sys
import numpy as np,segyio,zstandard as zstd,constriction
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())

MAG=b'CRNGv001';HDR='<8sBBBB4I5Q';HS=struct.calcsize(HDR)

def context_for(M,c,l,s,spec):
 T=M.shape[-1];ctx=np.zeros(T,np.uint8)
 if s>0:
  p=M[c,l,s-1]
  if spec==0:ctx|=p.astype(np.uint8)
  else:
   pm=np.zeros(T,np.uint8);pp=np.zeros(T,np.uint8);pm[1:]=p[:-1];pp[:-1]=p[1:];ctx|=pm;ctx|=(p.astype(np.uint8)<<1);ctx|=(pp<<2)
 if spec>=2 and l>0:ctx|=(M[c,l-1,s].astype(np.uint8)<<3)
 if spec>=3 and c>0:ctx|=(M[c-1,l,s].astype(np.uint8)<<4)
 return ctx

def fit_freq(M,spec):
 nctx=[2,8,16,32][spec];cnt=np.zeros((nctx,2),np.int64)
 C,L,S,T=M.shape
 for c in range(C):
  for l in range(L):
   for s in range(S):
    ctx=context_for(M,c,l,s,spec);cur=M[c,l,s].astype(np.int64);j=ctx.astype(np.int64)*2+cur;bc=np.bincount(j,minlength=nctx*2).reshape(nctx,2);cnt+=bc
 p=(cnt[:,1]+1.0)/(cnt.sum(1)+2.0);freq=np.clip(np.rint(p*65535),1,65534).astype(np.uint16);return freq,cnt

def prob_table(freq):
 f=freq.astype(np.float32);p1=f/np.float32(65535.0);return np.stack([1.0-p1,p1],1).astype(np.float32)

def encode_support(M,spec):
 freq,cnt=fit_freq(M,spec);pt=prob_table(freq);fam=constriction.stream.model.Categorical(perfect=False);enc=constriction.stream.queue.RangeEncoder();C,L,S,T=M.shape
 for c in range(C):
  for l in range(L):
   for s in range(S):
    ctx=context_for(M,c,l,s,spec);enc.encode(M[c,l,s].astype(np.int32),fam,pt[ctx])
 arr=np.asarray(enc.get_compressed(),dtype='<u4');return freq.tobytes(),arr.tobytes(),cnt

def decode_support(freqb,rangeb,shape,spec):
 nctx=[2,8,16,32][spec];freq=np.frombuffer(freqb,'<u2',count=nctx);pt=prob_table(freq);fam=constriction.stream.model.Categorical(perfect=False);dec=constriction.stream.queue.RangeDecoder(np.frombuffer(rangeb,'<u4'));C,L,S,T=shape;M=np.zeros(shape,bool)
 for c in range(C):
  for l in range(L):
   for s in range(S):
    ctx=context_for(M,c,l,s,spec);M[c,l,s]=np.asarray(dec.decode(fam,pt[ctx]),dtype=np.int32).astype(bool)
 return M

def encode_values(K,M,order,level):
 zc=zstd.ZstdCompressor(level=level);P=np.transpose(K,order+(3,));MP=np.transpose(M,order+(3,));vals=P[MP].astype(np.int32);sign=vals<0;ab=np.abs(vals);exc=ab!=1;sb=zc.compress(np.packbits(sign,bitorder='little').tobytes());eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mag=(ab[exc]-2).astype(np.int32);dc=dtype_code(mag);vb=zc.compress(mag.astype(DT[dc],copy=False).tobytes()) if mag.size else b'';return sb,eb,vb,dc,{'sign':len(sb),'exc':len(eb),'mag':len(vb),'events':int(vals.size),'exceptions':int(exc.sum())}
def decode_values(M,order,sb,eb,vb,dc):
 Pm=np.transpose(M,order+(3,));ne=int(Pm.sum());zd=zstd.ZstdDecompressor();sign=np.unpackbits(np.frombuffer(zd.decompress(sb),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);ab=np.ones(ne,np.int32)
 if exc.any():ab[exc]=np.frombuffer(zd.decompress(vb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
 vals=np.where(sign,-ab,ab);P=np.zeros(Pm.shape,np.int32);P[Pm]=vals;inv=np.argsort(order);return np.transpose(P,tuple(inv)+(3,))

def encode(K,spec,order,level):
 M=K!=0;fb,rb,cnt=encode_support(M,spec);sb,eb,vb,dc,parts=encode_values(K,M,order,level);oc=int(order[0]|(order[1]<<2)|(order[2]<<4));h=struct.pack(HDR,MAG,1,spec,oc,dc,*K.shape,len(fb),len(rb),len(sb),len(eb),len(vb));parts.update(freq=len(fb),range=len(rb),contexts=int(cnt.shape[0]));return h+fb+rb+sb+eb+vb,parts

def decode(blob):
 q=struct.unpack(HDR,blob[:HS]);magic,ver,spec,oc,dc,d0,d1,d2,d3,lf,lr,ls,le,lv=q
 if magic!=MAG or ver!=1:raise RuntimeError('header')
 p=HS;fb=blob[p:p+lf];p+=lf;rb=blob[p:p+lr];p+=lr;sb=blob[p:p+ls];p+=ls;eb=blob[p:p+le];p+=le;vb=blob[p:p+lv];shape=(d0,d1,d2,d3);order=tuple((oc>>(2*i))&3 for i in range(3));M=decode_support(fb,rb,shape,spec);return decode_values(M,order,sb,eb,vb,dc)

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
eps=.1*float(X.astype(np.float64).std());step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);M=K!=0;rows=[]
# Fit/encode each causal support model once; combine with independently searched value orders.
support_cache={}
for spec in range(4):
 fb,rb,cnt=encode_support(M,spec);R=decode_support(fb,rb,M.shape,spec)
 if not np.array_equal(R,M):raise RuntimeError('support decode mismatch')
 support_cache[spec]=(fb,rb,cnt)
 for order in itertools.permutations((0,1,2)):
  for level in [19,22]:
   sb,eb,vb,dc,parts=encode_values(K,M,order,level);K2=decode_values(M,order,sb,eb,vb,dc)
   if not np.array_equal(K2,K):raise RuntimeError('value decode mismatch')
   n=HS+len(fb)+len(rb)+len(sb)+len(eb)+len(vb);rows.append({'spec':spec,'order':list(order),'level':level,'bytes':n,'parts':{'freq':len(fb),'range':len(rb),**parts}})
rows.sort(key=lambda r:r['bytes'])
# Outlier: search existing and event-gap-style signmag temporal support using generic sparse machinery.
outrows=[]
for td in [0,1]:
 A=delta(O,1) if td else O
 for level in [19,22]:
  for perm in [(0,1,2,3),(3,1,2,0)]:
   for rep in [0,1,2]:
    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);R=undelta(R,1) if td else R
    if not np.array_equal(R,O):raise RuntimeError('out decode')
    outrows.append({'tdiff':bool(td),'level':level,'perm':list(perm),'rep':['raw','sparse','ternary'][rep],'bytes':len(b)})
outrows.sort(key=lambda r:r['bytes']);br=rows[0];bo=outrows[0];fb,rb,_=support_cache[br['spec']];sb,eb,vb,dc,_=encode_values(K,M,tuple(br['order']),br['level']);oc=int(br['order'][0]|(br['order'][1]<<2)|(br['order'][2]<<4));mb=struct.pack(HDR,MAG,1,br['spec'],oc,dc,*K.shape,len(fb),len(rb),len(sb),len(eb),len(vb))+fb+rb+sb+eb+vb;A=delta(O,1) if bo['tdiff'] else O;rep={'raw':0,'sparse':1,'ternary':2}[bo['rep']];ob=encode_out_sparse(A,tuple(bo['perm']),rep,bo['level']);top=struct.pack('<8sdQQ',b'CRTOP001',eps,len(mb),len(ob))+mb+ob;p=struct.calcsize('<8sdQQ');_,ee,lm,lo=struct.unpack('<8sdQQ',top[:p]);RK=decode(top[p:p+lm]);ROA=decode_out_sparse(top[p+lm:p+lm+lo]);RO=undelta(ROA,1) if bo['tdiff'] else ROA;RG=undelta(RK,3);Y=np.empty_like(X)
for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps);ratio=raw/len(top);szr=raw/szb
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_candidates':rows[:20],'outlier_candidates':outrows[:12],'container_bytes':len(top),'ratio':ratio,'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':szr,'maxerr':sze},'gain_over_sz3':ratio/szr}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_causal_range_support.json','w'),indent=2)
