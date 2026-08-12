import itertools, json, os, struct, sys
import numpy as np
# Reuse audited geometry/lattice functions without executing its CLI main.
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())

SMAG=b'SPARv001'; SH='<8sBBBB4IQ'; SHS=struct.calcsize(SH)
# rep: 0 raw integer stream, 1 packed nonzero mask + values, 2 packed 2-bit {-1,0,+1,exception} + exception values

def pack2(codes):
    n=codes.size; pad=(-n)%4
    if pad:codes=np.pad(codes,(0,pad))
    q=codes.reshape(-1,4).astype(np.uint8)
    return (q[:,0]|(q[:,1]<<2)|(q[:,2]<<4)|(q[:,3]<<6)).tobytes()

def unpack2(b,n):
    q=np.frombuffer(b,np.uint8);c=np.empty(q.size*4,np.uint8);c[0::4]=q&3;c[1::4]=(q>>2)&3;c[2::4]=(q>>4)&3;c[3::4]=(q>>6)&3
    return c[:n]

def encode_array(A,perm,rep,level=19):
    P=np.transpose(A,perm); flat=np.ascontiguousarray(P).ravel(); zc=zstd.ZstdCompressor(level=level)
    dc=dtype_code(flat); chunks=[]
    if rep==0:
        chunks=[zc.compress(flat.astype(DT[dc],copy=False).tobytes())]
    elif rep==1:
        mask=flat!=0; mb=np.packbits(mask,bitorder='little').tobytes(); vals=flat[mask]; vdc=dtype_code(vals); dc=vdc
        chunks=[zc.compress(mb),zc.compress(vals.astype(DT[vdc],copy=False).tobytes())]
    elif rep==2:
        codes=np.zeros(flat.size,np.uint8);codes[flat==1]=1;codes[flat==-1]=2;exc=(flat!=0)&(flat!=1)&(flat!=-1);codes[exc]=3;vals=flat[exc];vdc=dtype_code(vals);dc=vdc
        chunks=[zc.compress(pack2(codes)),zc.compress(vals.astype(DT[vdc],copy=False).tobytes())]
    else:raise ValueError(rep)
    # Store permutation as four 2-bit axis ids in one byte.
    pc=int(perm[0]|(perm[1]<<2)|(perm[2]<<4)|(perm[3]<<6));h=struct.pack(SH,SMAG,1,rep,dc,pc,*A.shape,len(chunks));lens=b''.join(struct.pack('<Q',len(x)) for x in chunks)
    return h+lens+b''.join(chunks)

def decode_array(blob):
    magic,ver,rep,dc,pc,d0,d1,d2,d3,nc=struct.unpack(SH,blob[:SHS]);
    if magic!=SMAG or ver!=1:raise RuntimeError('sparse header')
    perm=tuple((pc>>(2*i))&3 for i in range(4));shape=(d0,d1,d2,d3);pshape=tuple(shape[i] for i in perm);n=int(np.prod(shape));p=SHS;lens=[]
    for _ in range(nc):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    fs=[]
    for L in lens:fs.append(blob[p:p+L]);p+=L
    if rep==0:flat=np.frombuffer(ZD.decompress(fs[0]),dtype=DT[dc],count=n).astype(np.int32)
    elif rep==1:
        mask=np.unpackbits(np.frombuffer(ZD.decompress(fs[0]),np.uint8),bitorder='little',count=n).astype(bool);vals=np.frombuffer(ZD.decompress(fs[1]),dtype=DT[dc],count=int(mask.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[mask]=vals
    elif rep==2:
        codes=unpack2(ZD.decompress(fs[0]),n);exc=codes==3;vals=np.frombuffer(ZD.decompress(fs[1]),dtype=DT[dc],count=int(exc.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[codes==1]=1;flat[codes==2]=-1;flat[exc]=vals
    else:raise RuntimeError('rep')
    P=flat.reshape(pshape);invp=np.argsort(perm);return np.transpose(P,invp)

OMAG=b'OSPRv001'; OH2='<8sBBBB2IQ'; OHS=struct.calcsize(OH2)
def encode_out_sparse(A,perm,rep,level=19):
    # Promote 2-D outlier matrix to 4-D singleton array to reuse exact codec; charge a tiny wrapper and strip singleton dimensions on decode.
    B=A.reshape(A.shape[0],1,1,A.shape[1]);return encode_array(B,perm,rep,level)
def decode_out_sparse(blob):return decode_array(blob)[:,0,0,:]

path=sys.argv[1];X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes
G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
vals,counts=np.unique(K,return_counts=True);order=np.argsort(counts)[::-1];topvals=[{'v':int(vals[i]),'count':int(counts[i])} for i in order[:12]]
perms=list(itertools.permutations(range(4)));rows=[]
for level in [19,22]:
  for pi,perm in enumerate(perms):
    for rep in [0,1,2]:
      b=encode_array(K,perm,rep,level);R=decode_array(b)
      if not np.array_equal(R,K):raise RuntimeError('main sparse decode')
      rows.append({'level':level,'perm':list(perm),'rep':['raw','sparse','ternary'][rep],'bytes':len(b)})
rows.sort(key=lambda r:r['bytes'])
outrows=[]
outperms=[(0,1,2,3),(3,1,2,0)]
for td in [False,True]:
 A=delta(O,1) if td else O
 for level in [19,22]:
  for perm in outperms:
   for rep in [0,1,2]:
    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
    if not np.array_equal(RR,O):raise RuntimeError('out sparse decode')
    outrows.append({'tdiff':td,'level':level,'perm':list(perm),'rep':['raw','sparse','ternary'][rep],'bytes':len(b)})
outrows.sort(key=lambda r:r['bytes'])
def repid(s):return {'raw':0,'sparse':1,'ternary':2}[s]
br=rows[0];bo=outrows[0];mb=encode_array(K,tuple(br['perm']),repid(br['rep']),br['level']);OA=delta(O,1) if bo['tdiff'] else O;ob=encode_out_sparse(OA,tuple(bo['perm']),repid(bo['rep']),bo['level']);top=struct.pack('<8sdQQ',b'STOPv001',eps,len(mb),len(ob))+mb+ob
# Full byte decode and independent hard-error verification.
p=struct.calcsize('<8sdQQ');_,ee,lm,lo=struct.unpack('<8sdQQ',top[:p]);RK=decode_array(top[p:p+lm]);ROA=decode_out_sparse(top[p+lm:p+lm+lo]);RG=undelta(RK,3);RO=undelta(ROA,1) if bo['tdiff'] else ROA
recon=np.empty_like(X)
for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
recon[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps)
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'K_top_values':topvals,'main_candidates':rows[:20],'outlier_candidates':outrows[:12],'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze}}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_grid_sparse.json','w'),indent=2)
