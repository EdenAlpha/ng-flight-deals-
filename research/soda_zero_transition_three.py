import json,os,struct,sys
import numpy as np
import segyio,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
OUTER='<BBQ'; OHS=struct.calcsize(OUTER)

def pack_int(a):
    a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0
    code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
    return code,ZC.compress(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())
def unpack_int(b,code,n):
    a=np.frombuffer(ZD.decompress(b),dtype=IDT[code],count=n)
    if a.size!=n:raise RuntimeError('integer length mismatch')
    return a.astype(np.int32,copy=False)
def d1(a,axis):
    o=a.copy();s1=[slice(None)]*2;s0=[slice(None)]*2;s1[axis]=slice(1,None);s0[axis]=slice(None,-1);o[tuple(s1)]=a[tuple(s1)]-a[tuple(s0)];return o

def leb128(u):
    out=bytearray()
    for x in np.asarray(u,dtype=np.uint64).ravel():
        x=int(x)
        while x>=128:out.append((x&127)|128);x>>=7
        out.append(x)
    return bytes(out)
def unleb128(b,n):
    out=np.empty(n,np.uint64);i=j=0
    while i<n:
        x=shift=0
        while True:
            if j>=len(b):raise RuntimeError('truncated varint')
            v=b[j];j+=1;x|=(v&127)<<shift
            if v<128:break
            shift+=7
        out[i]=x;i+=1
    if j!=len(b):raise RuntimeError('varint trailing data')
    return out

def dense_payload(K):
    dc,b=pack_int(K);h=struct.pack('<BQ',dc,len(b));return h+b,{'kind':'dense','dtype':dc,'payload':len(b)}
def decode_dense(pay,shape):
    hs=struct.calcsize('<BQ');dc,L=struct.unpack('<BQ',pay[:hs]);b=pay[hs:hs+L]
    if hs+L!=len(pay):raise RuntimeError('dense length mismatch')
    return unpack_int(b,dc,int(np.prod(shape))).reshape(shape)

def sparse_payload(K,order='C',xor_rows=False):
    M=K!=0
    if xor_rows:
        T=M.copy();T[1:]=np.logical_xor(M[1:],M[:-1]);mask=T
    else:mask=M
    mb=ZC.compress(np.packbits(mask.ravel(order=order),bitorder='little').tobytes());vals=K[M];dc,vb=pack_int(vals)
    h=struct.pack('<BBBQQ',0 if order=='C' else 1,int(xor_rows),dc,len(mb),len(vb))
    return h+mb+vb,{'kind':'mask','order':order,'xor_rows':xor_rows,'dtype':dc,'mask_bytes':len(mb),'value_bytes':len(vb),'events':int(vals.size)}
def decode_sparse(pay,shape):
    hs=struct.calcsize('<BBBQQ');ordc,xr,dc,lm,lv=struct.unpack('<BBBQQ',pay[:hs]);p=hs;mb=pay[p:p+lm];p+=lm;vb=pay[p:p+lv];p+=lv
    if p!=len(pay):raise RuntimeError('sparse length mismatch')
    n=int(np.prod(shape));order='C' if ordc==0 else 'F';T=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little',count=n).astype(bool).reshape(shape,order=order)
    if xr:
        M=T.copy()
        for i in range(1,shape[0]):M[i]=np.logical_xor(T[i],M[i-1])
    else:M=T
    vals=unpack_int(vb,dc,int(M.sum()));K=np.zeros(shape,np.int32);K[M]=vals;return K

def gap_payload(K):
    nr,nt=K.shape;chunks=[];counts=[];vals=[]
    for r in range(nr):
        pos=np.flatnonzero(K[r]);counts.append(len(pos))
        if len(pos):
            gaps=np.diff(np.r_[-1,pos]).astype(np.uint64)-1;chunks.append(leb128(gaps));vals.append(K[r,pos])
    count_raw=leb128(np.asarray(counts,np.uint64));gap_raw=b''.join(chunks);valarr=np.concatenate(vals) if vals else np.empty(0,np.int32);dc,vb=pack_int(valarr);cb=ZC.compress(count_raw);gb=ZC.compress(gap_raw)
    h=struct.pack('<BQQQ',dc,len(cb),len(gb),len(vb));return h+cb+gb+vb,{'kind':'gaps','dtype':dc,'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'events':int(valarr.size)}
def decode_gap(pay,shape):
    nr,nt=shape;hs=struct.calcsize('<BQQQ');dc,lc,lg,lv=struct.unpack('<BQQQ',pay[:hs]);p=hs;cb=pay[p:p+lc];p+=lc;gb=pay[p:p+lg];p+=lg;vb=pay[p:p+lv];p+=lv
    if p!=len(pay):raise RuntimeError('gap length mismatch')
    counts=unleb128(ZD.decompress(cb),nr).astype(int);ne=int(counts.sum());vals=unpack_int(vb,dc,ne);gaps=unleb128(ZD.decompress(gb),ne).astype(np.int64);K=np.zeros(shape,np.int32);vi=0
    for r,c in enumerate(counts):
        if c:
            pos=np.cumsum(gaps[vi:vi+c]+1)-1
            if pos[-1]>=nt:raise RuntimeError('gap position out of range')
            K[r,pos]=vals[vi:vi+c];vi+=c
    return K

def wrap(mode,typ,pay):return struct.pack(OUTER,mode,typ,len(pay))+pay
def decode_candidate(blob,shape):
    mode,typ,L=struct.unpack(OUTER,blob[:OHS]);pay=blob[OHS:OHS+L]
    if OHS+L!=len(blob):raise RuntimeError('outer length mismatch')
    K=decode_dense(pay,shape) if typ==0 else decode_sparse(pay,shape) if typ==1 else decode_gap(pay,shape)
    if mode==0:Q=K
    elif mode==1:Q=np.cumsum(K,axis=1,dtype=np.int32)
    elif mode==2:Q=np.cumsum(K,axis=0,dtype=np.int32)
    elif mode==3:Q=np.cumsum(np.cumsum(K,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
    else:raise RuntimeError('bad mode')
    return Q

def encode_panel(A,eps):
    Q=np.rint(A/(2*eps)).astype(np.int32);Kt=d1(Q,1);Kx=d1(Q,0);Kl=d1(Kt,0);cands=[]
    for mode,K in [(0,Q),(1,Kt),(2,Kx),(3,Kl)]:
        pay,m=dense_payload(K);b=wrap(mode,0,pay);cands.append((len(b),b,{**m,'mode':mode}))
    for order in ['C','F']:
        for xr in [False,True]:
            pay,m=sparse_payload(Kt,order,xr);b=wrap(1,1,pay);cands.append((len(b),b,{**m,'mode':1}))
    pay,m=gap_payload(Kt);b=wrap(1,2,pay);cands.append((len(b),b,{**m,'mode':1}))
    cands.sort(key=lambda x:x[0]);_,blob,meta=cands[0];QQ=decode_candidate(blob,A.shape)
    if not np.array_equal(Q,QQ):raise RuntimeError('integer roundtrip mismatch')
    R=QQ.astype(np.float32)*np.float32(2*eps)
    return blob,R,meta,cands

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={};bad=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:bad.append(i);continue
        groups.setdefault((int(x),int(y)),[]).append(i)
    keys=sorted(groups);counts=np.asarray([len(groups[k]) for k in keys]);C=int(np.bincount(counts).argmax());panels=[]
    for c in range(C):panels.append(np.stack([X[groups[k][c]] for k in keys if len(groups[k])>c]))
    extras=X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32)
    return X,panels,extras,{'receiver_groups':len(keys),'components':C,'bad_traces':len(bad)}

def sz3(A,eps):
    if not A.size:return 0,0.
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(b,np.float32,A.shape);return int(b.size),float(np.max(np.abs(A-R)))

def bench(path):
    X,panels,extra,geom=load(path);raw=int(X.nbytes);eps=.1*float(X.astype(np.float64).std());parts=[];maxerr=0.;diagn=[]
    for A in panels:
        b,R,m,cands=encode_panel(A,eps);parts.append(b);maxerr=max(maxerr,float(np.max(np.abs(A-R))));diagn.append({'selected':m,'alternatives':[{'bytes':x[0],**x[2]} for x in cands]})
    eb,ee=sz3(extra,eps)
    if extra.size:
        bb,RR,mm,_=encode_panel(extra,eps)
        if len(bb)<eb:eb=len(bb);ee=float(np.max(np.abs(extra-RR)));diagn.append({'bad_selected':mm,'bad_codec':'transition'})
        else:diagn.append({'bad_codec':'sz3','bad_bytes':eb})
    total=32+sum(map(len,parts))+eb;mx=max(maxerr,ee)
    return {'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'bytes':total,'ratio':raw/total,'maxerr':mx,'valid':bool(mx<=eps*(1+5e-6)),'extra_bytes':eb,'panels':diagn}

out={'shots':[]}
for p in sys.argv[1:]:
    r=bench(p);out['shots'].append(r);print('RESULT',json.dumps({'file':r['file'],'bytes':r['bytes'],'ratio':r['ratio'],'maxerr':r['maxerr'],'valid':r['valid'],'extra_bytes':r['extra_bytes'],'selected':[x.get('selected') for x in r['panels'] if 'selected'in x]},indent=2),flush=True)
json.dump(out,open('soda_zero_transition_three.json','w'),indent=2)
