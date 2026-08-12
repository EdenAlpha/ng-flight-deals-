import itertools,json,os,struct,sys
import numpy as np,segyio,zstandard as zstd
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())

MAG=b'SSMCv001';HDR='<8sBBBBB4IQQQQ';HS=struct.calcsize(HDR)
# mask transform bits: 1 station xor, 2 line xor, 4 component xor. Applied C,L,S,T in that order; inverted reverse.
def xor_mask(M,flags):
 X=M.copy()
 if flags&4:X[1:,:,:,:]^=M[:-1,:,:,:]
 A=X.copy()
 if flags&2:A[:,1:,:,:]^=X[:,:-1,:,:]
 X=A.copy()
 if flags&1:X[:,:,1:,:]^=A[:,:,:-1,:]
 return X
def unxor_mask(X,flags):
 M=X.copy()
 if flags&1:
  for s in range(1,M.shape[2]):M[:,:,s,:]^=M[:,:,s-1,:]
 if flags&2:
  for l in range(1,M.shape[1]):M[:,l,:,:]^=M[:,l-1,:,:]
 if flags&4:
  for c in range(1,M.shape[0]):M[c,:,:,:]^=M[c-1,:,:,:]
 return M

def encode(K,perm,mflags,level):
 zc=zstd.ZstdCompressor(level=level);P=np.transpose(K,perm);M=P!=0;origM=M
 # Transform support in original C,L,S,T coordinate system before traversal, then transpose.
 M4=K!=0;TM=xor_mask(M4,mflags);TP=np.transpose(TM,perm);mb=zc.compress(np.packbits(TP.ravel(),bitorder='little').tobytes())
 vals=P[origM].astype(np.int32);sign=(vals<0);ab=np.abs(vals);sb=zc.compress(np.packbits(sign,bitorder='little').tobytes())
 exc=ab!=1;eb=zc.compress(np.packbits(exc,bitorder='little').tobytes());mags=(ab[exc]-2).astype(np.int32)
 dc=dtype_code(mags);vb=zc.compress(mags.astype(DT[dc],copy=False).tobytes()) if mags.size else b''
 pc=int(perm[0]|(perm[1]<<2)|(perm[2]<<4)|(perm[3]<<6));h=struct.pack(HDR,MAG,1,pc,mflags,dc,level,*K.shape,len(mb),len(sb),len(eb),len(vb));return h+mb+sb+eb+vb,{'mask':len(mb),'sign':len(sb),'exc_mask':len(eb),'mag':len(vb),'events':int(vals.size),'exceptions':int(exc.sum())}
def decode(blob):
 vals=struct.unpack(HDR,blob[:HS]);magic,ver,pc,mflags,dc,level,d0,d1,d2,d3,lm,ls,le,lv=vals
 if magic!=MAG or ver!=1:raise RuntimeError('header')
 p=HS;mb=blob[p:p+lm];p+=lm;sb=blob[p:p+ls];p+=ls;eb=blob[p:p+le];p+=le;vb=blob[p:p+lv];p+=lv
 shape=(d0,d1,d2,d3);perm=tuple((pc>>(2*i))&3 for i in range(4));pshape=tuple(shape[i] for i in perm);n=int(np.prod(shape));zd=zstd.ZstdDecompressor()
 TMp=np.unpackbits(np.frombuffer(zd.decompress(mb),np.uint8),bitorder='little',count=n).reshape(pshape).astype(bool);invp=np.argsort(perm);TM=np.transpose(TMp,invp);M4=unxor_mask(TM,mflags);Mp=np.transpose(M4,perm);ne=int(Mp.sum())
 signs=np.unpackbits(np.frombuffer(zd.decompress(sb),np.uint8),bitorder='little',count=ne).astype(bool);exc=np.unpackbits(np.frombuffer(zd.decompress(eb),np.uint8),bitorder='little',count=ne).astype(bool);mags=np.ones(ne,np.int32)
 if exc.any():mags[exc]=np.frombuffer(zd.decompress(vb),dtype=DT[dc],count=int(exc.sum())).astype(np.int32)+2
 vv=np.where(signs,-mags,mags);P=np.zeros(pshape,np.int32);P[Mp]=vv;return np.transpose(P,invp)

path=sys.argv[1]
with segyio.open(path,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
eps=.1*float(X.astype(np.float64).std());step=2*eps;raw=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
# Give main coder a broad deterministic mode search. Outliers use best existing adaptive candidate search.
rows=[]
perms=list(itertools.permutations(range(4)))
for level in [19,22]:
 for perm in perms:
  for mf in range(8):
   b,parts=encode(K,perm,mf,level);R=decode(b)
   if not np.array_equal(R,K):raise RuntimeError('main decode mismatch')
   rows.append({'level':level,'perm':list(perm),'mask_xor_flags':mf,'bytes':len(b),'parts':parts})
rows.sort(key=lambda r:r['bytes'])
# Existing outlier modes from audited sparse script.
outrows=[]
outperms=[(0,1,2,3),(3,1,2,0)]
for td in [0,1]:
 A=delta(O,1) if td else O
 for level in [19,22]:
  for perm in outperms:
   for rep in [0,1,2]:
    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
    if not np.array_equal(RR,O):raise RuntimeError('out decode')
    outrows.append({'tdiff':bool(td),'level':level,'perm':list(perm),'rep':['raw','sparse','ternary'][rep],'bytes':len(b)})
outrows.sort(key=lambda r:r['bytes'])
br=rows[0];bo=outrows[0];mb,_=encode(K,tuple(br['perm']),br['mask_xor_flags'],br['level']);OA=delta(O,1) if bo['tdiff'] else O;repid={'raw':0,'sparse':1,'ternary':2}[bo['rep']];ob=encode_out_sparse(OA,tuple(bo['perm']),repid,bo['level']);top=struct.pack('<8sdQQ',b'SSMTOP01',eps,len(mb),len(ob))+mb+ob
# decode full and verify hard error
p=struct.calcsize('<8sdQQ');_,ee,lm,lo=struct.unpack('<8sdQQ',top[:p]);RK=decode(top[p:p+lm]);ROA=decode_out_sparse(top[p+lm:p+lm+lo]);RG=undelta(RK,3);RO=undelta(ROA,1) if bo['tdiff'] else ROA;Y=np.empty_like(X)
for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)));szb,sze=sz3_bytes(X,eps)
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_candidates':rows[:20],'outlier_candidates':outrows[:12],'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_over_sz3':(raw/len(top))/(raw/szb)}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_support_signmag.json','w'),indent=2)
