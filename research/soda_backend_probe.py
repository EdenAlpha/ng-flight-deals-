import bz2,json,lzma,os,struct,sys,zlib
import numpy as np
import brotli,segyio,zstandard as zstd
Z19=zstd.ZstdCompressor(level=19);Z22=zstd.ZstdCompressor(level=22)

def comp(data,name):
    if name=='z19':return Z19.compress(data)
    if name=='z22':return Z22.compress(data)
    if name=='zlib':return zlib.compress(data,9)
    if name=='bz2':return bz2.compress(data,9)
    if name=='xz':return lzma.compress(data,format=lzma.FORMAT_XZ,preset=9|lzma.PRESET_EXTREME)
    if name=='br':return brotli.compress(data,quality=11,mode=brotli.MODE_GENERIC)
    raise ValueError(name)
def decomp(data,name):
    if name.startswith('z'):return zstd.ZstdDecompressor().decompress(data)
    if name=='zlib':return zlib.decompress(data)
    if name=='bz2':return bz2.decompress(data)
    if name=='xz':return lzma.decompress(data)
    if name=='br':return brotli.decompress(data)
BACK=['z19','z22','zlib','bz2','xz','br']

def choose_backend(raw):
    rows=[]
    for n in BACK:
        b=comp(raw,n)
        if decomp(b,n)!=raw:raise RuntimeError('backend roundtrip '+n)
        rows.append((len(b),n,b))
    rows.sort();return rows[0],[(n,l) for l,n,_ in rows]
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
            v=b[j];j+=1;x|=(v&127)<<sh
            if v<128:break
            sh+=7
        a[i]=x;i+=1
    if j!=len(b):raise RuntimeError('varint trailing')
    return a

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={};bad=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:bad.append(i);continue
        groups.setdefault((int(x),int(y)),[]).append(i)
    keys=sorted(groups);C=int(np.bincount(np.asarray([len(groups[k]) for k in keys])).argmax());valid=np.concatenate([np.asarray([groups[k][c] for k in keys],np.int64) for c in range(C)]);return X,X[valid],X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32)

def make_raw(A,eps,M):
    step=2*eps*(1-2e-7);phases=step*np.arange(M)/M;nr,nt=A.shape;idx=np.zeros(nr,np.uint8);Q=np.empty((nr,nt),np.int32)
    for r,a in enumerate(A):
        best=None
        for k,p in enumerate(phases):
            q=np.rint((a.astype(np.float64)-p)/step).astype(np.int32);d=np.r_[q[0],np.diff(q)];score=(int(np.count_nonzero(d)),int(np.abs(d).sum()),k)
            if best is None or score<best[0]:best=(score,k,q)
        idx[r]=best[1];Q[r]=best[2]
    K=Q.copy();K[:,1:]-=Q[:,:-1];mask=K!=0;counts=mask.sum(axis=1).astype(np.uint64);order=sorted(range(nr),key=lambda i:(int(counts[i]),i));g=[];vals=[];starts=[]
    for i in order:
        starts.append(len(vals));pos=np.flatnonzero(mask[i]);gg=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);g.extend(gg.tolist());vals.extend(K[i,pos].tolist())
    bits=int(np.log2(M));phase_raw=np.packbits(((idx[:,None]>>np.arange(bits,dtype=np.uint8))&1).astype(np.uint8).ravel(),bitorder='little').tobytes() if M>1 else b''
    count_raw=leb(counts);gap_raw=leb(g);v=np.asarray(vals,np.int32);lo=int(v.min());hi=int(v.max());dt=np.int8 if lo>=-128 and hi<=127 else np.int16 if lo>=-32768 and hi<=32767 else np.int32;direct_raw=v.astype(dt).tobytes()
    neg=v<0;mag=np.abs(v);exc=mag!=1;res=np.zeros(len(v),bool);p=0
    for i in order:
        n=int(counts[i])
        for j in range(n):
            pred=False if j==0 else (not bool(neg[p+j-1]));res[p+j]=(bool(neg[p+j])!=pred)
        p+=n
    sign_raw=np.packbits(res,bitorder='little').tobytes();exc_raw=np.packbits(exc,bitorder='little').tobytes();extra_raw=leb((mag[exc]-2).astype(np.uint64))
    return {'phase':phase_raw,'counts':count_raw,'gaps':gap_raw,'direct_values':direct_raw,'sign_resid':sign_raw,'exception_mask':exc_raw,'exception_values':extra_raw},Q,idx,step,counts,order

def encode_part(A,eps,M):
    raws,Q,idx,step,counts,order=make_raw(A,eps,M);chosen={};allrows={};total=0
    for key in ['phase','counts','gaps']:
        if not raws[key]:chosen[key]={'backend':'none','bytes':0,'blob':b''};continue
        (L,n,b),rows=choose_backend(raws[key]);chosen[key]={'backend':n,'bytes':L,'blob':b};allrows[key]=rows;total+=1+8+L
    # Direct value stream versus sign/magnitude split, each allowed independent backend per substream.
    (Ld,nd,bd),rd=choose_backend(raws['direct_values']);direct=1+8+Ld
    sm=0;smc={}
    for key in ['sign_resid','exception_mask','exception_values']:
        (L,n,b),rows=choose_backend(raws[key]);sm+=1+8+L;smc[key]=(L,n,b,rows)
    if sm<direct:
        vmode='signmag';total+=1+sm
        for key,(L,n,b,rows) in smc.items():chosen[key]={'backend':n,'bytes':L,'blob':b};allrows[key]=rows
    else:
        vmode='direct';total+=1+direct;chosen['direct_values']={'backend':nd,'bytes':Ld,'blob':bd};allrows['direct_values']=rd
    # Add a realistic part header: magic/dims/eps/step/M plus stream lengths/modes.
    total+=64
    # Validate selected backends reproduce every raw stream exactly; then use original Q for hard-error check.
    for k,v in chosen.items():
        if v['backend']!='none' and decomp(v['blob'],v['backend'])!=raws[k]:raise RuntimeError('selected backend mismatch')
    ph=step*idx.astype(np.float64)/M;R=(Q.astype(np.float64)*step+ph[:,None]).astype(np.float32);me=float(np.max(np.abs(A-R)))
    return {'bytes':total,'vmode':vmode,'selected':{k:{'backend':v['backend'],'bytes':v['bytes'],'raw_bytes':len(raws[k])} for k,v in chosen.items()},'all_backend_sizes':allrows,'events':int(counts.sum()),'maxerr':me}

def run(path):
    X,A,B=load(path);eps=.1*float(X.astype(np.float64).std());raw=X.nbytes;rows=[]
    for M in [1,2]:
        a=encode_part(A,eps,M);tot=48+a['bytes'];me=a['maxerr'];b=None
        if B.size:b=encode_part(B,eps,M);tot+=b['bytes'];me=max(me,b['maxerr'])
        rows.append({'M':M,'bytes':tot,'ratio':raw/tot,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'valid_stream':a,'bad_stream':b})
    rows.sort(key=lambda x:x['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'rows':rows};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_backend_probe.json','w'),indent=2)
run(sys.argv[1])
