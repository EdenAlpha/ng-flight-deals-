import itertools,json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse the audited geometry, legal lattice, generic sparse codec and outlier codec.
src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())
s2=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(s2,'soda_grid_sparse.py','exec'),globals())

VMAG=b'VEC3v001'
VH='<8sBBBBBIIIIQQQQQ'
VHS=struct.calcsize(VH)

def pack_fixed(a,bits):
    a=np.asarray(a,np.uint8).ravel();out=bytearray((a.size*bits+7)//8);acc=0;nb=0;j=0
    for vv in a.tolist():
        acc|=int(vv)<<nb;nb+=bits
        while nb>=8:
            out[j]=acc&255;j+=1;acc>>=8;nb-=8
    if nb:out[j]=acc&255
    return bytes(out)

def unpack_fixed(b,n,bits):
    out=np.empty(n,np.uint8);acc=0;nb=0;j=0;k=0
    bb=memoryview(b)
    while k<n:
        while nb<bits:
            acc|=int(bb[j])<<nb;j+=1;nb+=8
        out[k]=acc&((1<<bits)-1);acc>>=bits;nb-=bits;k+=1
    return out

def perm_code(p):return int(p[0]|(p[1]<<2)|(p[2]<<4))
def perm_decode(pc):return tuple((pc>>(2*i))&3 for i in range(3))

def vectorize(K,p):
    # p indexes physical L/S/T axes as 0/1/2. Component remains a 3-vector.
    P=K.transpose((0,)+(tuple(x+1 for x in p)))
    return np.moveaxis(P,0,-1).reshape(-1,K.shape[0])

def unvectorize(V,C,L,S,T,p):
    dims=(L,S,T);pd=tuple(dims[x] for x in p);P=np.moveaxis(V.reshape(pd+(C,)),-1,0)
    inv=np.argsort(np.asarray(p));return P.transpose((0,)+tuple((inv+1).tolist()))

def encode_vector(K,p,level,packed_codes):
    if K.shape[0]!=3:raise RuntimeError('expected 3 components')
    V=vectorize(K,p);U=np.any(V!=0,axis=1);A=V[U]
    base=np.sign(A).astype(np.int8)
    codes=((base[:,0].astype(np.int16)+1)+3*(base[:,1].astype(np.int16)+1)+9*(base[:,2].astype(np.int16)+1)).astype(np.uint8)
    exc=np.abs(A)>1;has=np.any(exc,axis=1);E=exc[has]
    emask=(E[:,0].astype(np.uint8)|(E[:,1].astype(np.uint8)<<1)|(E[:,2].astype(np.uint8)<<2)) if E.size else np.empty(0,np.uint8)
    extras=(np.abs(A[has])[E]-1).astype(np.int32) if E.size else np.empty(0,np.int32)
    dc=dtype_code(extras);zc=zstd.ZstdCompressor(level=level)
    ub=np.packbits(U,bitorder='little').tobytes();cb=pack_fixed(codes,5) if packed_codes else codes.tobytes();hb=np.packbits(has,bitorder='little').tobytes();eb=pack_fixed(emask,3);xb=extras.astype(DT[dc],copy=False).tobytes()
    frames=[zc.compress(ub),zc.compress(cb),zc.compress(hb),zc.compress(eb),zc.compress(xb)]
    h=struct.pack(VH,VMAG,1,int(level),int(packed_codes),dc,perm_code(p),*K.shape,*[len(x) for x in frames])
    blob=h+b''.join(frames)
    active_counts=np.sum(A!=0,axis=1) if A.size else np.empty(0,np.int64)
    diag={'bytes':len(blob),'perm':list(p),'level':level,'packed_codes':bool(packed_codes),'union_events':int(U.sum()),'component_events':int(np.count_nonzero(V)),'support_overlap_factor':float(np.count_nonzero(V)/max(1,int(U.sum()))),'active_components_hist':{str(k):int(np.sum(active_counts==k)) for k in (1,2,3)},'exception_vectors':int(has.sum()),'exception_components':int(exc.sum()),'frame_bytes':{'union':len(frames[0]),'vector_code':len(frames[1]),'exception_support':len(frames[2]),'exception_component_mask':len(frames[3]),'exception_magnitude':len(frames[4])}}
    return blob,diag

def decode_vector(blob):
    if len(blob)<VHS:raise RuntimeError('short vector blob')
    vals=struct.unpack(VH,blob[:VHS]);magic,ver,level,packed,dc,pc,C,L,S,T,*lens=vals
    if magic!=VMAG or ver!=1 or C!=3:raise RuntimeError('vector header')
    p=VHS;fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('vector length')
    D=zstd.ZstdDecompressor();N=L*S*T
    U=np.unpackbits(np.frombuffer(D.decompress(fs[0]),np.uint8),bitorder='little',count=N).astype(bool);M=int(U.sum())
    cr=D.decompress(fs[1]);codes=unpack_fixed(cr,M,5) if packed else np.frombuffer(cr,np.uint8,count=M).copy()
    c=codes.astype(np.int16);b0=(c%3)-1;c//=3;b1=(c%3)-1;c//=3;b2=(c%3)-1
    A=np.stack([b0,b1,b2],axis=1).astype(np.int32)
    H=np.unpackbits(np.frombuffer(D.decompress(fs[2]),np.uint8),bitorder='little',count=M).astype(bool);nh=int(H.sum())
    er=D.decompress(fs[3]);em=unpack_fixed(er,nh,3) if nh else np.empty(0,np.uint8)
    ne=int(sum(((int(x)&1)>0)+((int(x)&2)>0)+((int(x)&4)>0) for x in em.tolist()))
    extra=np.frombuffer(D.decompress(fs[4]),dtype=DT[dc],count=ne).astype(np.int32) if ne else np.empty(0,np.int32)
    rows=np.flatnonzero(H);q=0
    for j,r in enumerate(rows.tolist()):
        m=int(em[j])
        for cc in range(3):
            if m&(1<<cc):
                s=int(A[r,cc]);
                if s==0:raise RuntimeError('exception sign missing')
                A[r,cc]=s*(1+int(extra[q]));q+=1
    if q!=ne:raise RuntimeError('exception count')
    V=np.zeros((N,3),np.int32);V[U]=A
    return unvectorize(V,C,L,S,T,perm_decode(pc))

def best_outlier(O):
    rows=[]
    for td in (False,True):
        A=delta(O,1) if td else O
        for level in (19,22):
            for perm in ((0,1,2,3),(3,1,2,0)):
                for rep in (0,1,2):
                    b=encode_out_sparse(A,perm,rep,level);R=decode_out_sparse(b);RR=undelta(R,1) if td else R
                    if not np.array_equal(RR,O):raise RuntimeError('outlier decode')
                    rows.append((len(b),td,level,perm,rep,b))
    return min(rows,key=lambda x:x[0])

def current_main(K):
    rows=[]
    for level in (19,22):
        for p in itertools.permutations(range(4)):
            for rep in (0,1,2):
                b=encode_array(K,p,rep,level);R=decode_array(b)
                if not np.array_equal(R,K):raise RuntimeError('current decode')
                rows.append((len(b),level,p,rep,b))
    return min(rows,key=lambda x:x[0])

def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    cur=current_main(K);bo=best_outlier(O)
    candidates=[]
    for level in (19,22):
        for p in itertools.permutations(range(3)):
            for packed in (False,True):
                b,d=encode_vector(K,p,level,packed);R=decode_vector(b)
                if not np.array_equal(R,K):raise RuntimeError(('vector integer decode',p,level,packed))
                candidates.append((len(b),b,d))
    candidates.sort(key=lambda x:x[0]);vb,mainblob,vdiag=candidates[0]
    fmt='<8sdBQQ';top=struct.pack(fmt,b'V3TOP001',eps,1,len(mainblob),len(bo[5]))+mainblob+bo[5]
    hs=struct.calcsize(fmt);magic,ee,mode,lm,lo=struct.unpack(fmt,top[:hs]);RK=decode_vector(top[hs:hs+lm]);ROA=decode_out_sparse(top[hs+lm:hs+lm+lo]);RO=undelta(ROA,1) if bo[1] else ROA;RG=undelta(RK,3)
    recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    recon[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps)
    current_total=struct.calcsize('<8sdQQ')+cur[0]+bo[0]
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'current_best':{'main_bytes':cur[0],'outlier_bytes':bo[0],'estimated_top_bytes':current_total,'ratio':raw/current_total,'main_level':cur[1],'main_perm':list(cur[2]),'main_rep':['raw','sparse','ternary'][cur[3]]},'vector_best':vdiag,'vector_candidates':[x[2] for x in candidates[:12]],'outlier':{'bytes':bo[0],'tdiff':bo[1],'level':bo[2],'perm':list(bo[3]),'rep':['raw','sparse','ternary'][bo[4]]},'container_bytes':len(top),'ratio':raw/len(top),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze},'gain_vs_sz3':szb/len(top)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_3c_vector_events.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
