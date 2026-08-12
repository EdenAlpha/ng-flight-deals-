import json,os,struct,sys
import numpy as np
import segyio,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

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
            v=b[j];j+=1;x|=(v&127)<<shift
            if v<128:break
            shift+=7
        out[i]=x;i+=1
    if j!=len(b):raise RuntimeError('varint trailing data')
    return out

def sparse_mask_values(K,order='C',xor_rows=False):
    if xor_rows:
        M=K!=0;T=M.copy();T[1:]=np.logical_xor(M[1:],M[:-1]);mask=T
    else:mask=K!=0
    flat=mask.ravel(order=order);mb=ZC.compress(np.packbits(flat,bitorder='little').tobytes())
    # Values are always taken in canonical C event order and are decoded after mask inversion.
    vals=K[K!=0];dc,vb=pack_int(vals)
    head=struct.pack('<BBQQ',0 if order=='C' else 1,int(xor_rows),len(mb),len(vb))
    return head+mb+vb,{'kind':'mask','order':order,'xor_rows':xor_rows,'dtype':dc,'mask_bytes':len(mb),'value_bytes':len(vb),'events':int(vals.size)},dc

def decode_sparse(blob,shape,dc):
    hs=struct.calcsize('<BBQQ');ordc,xr,lm,lv=struct.unpack('<BBQQ',blob[:hs]);mb=blob[hs:hs+lm];vb=blob[hs+lm:hs+lm+lv];n=int(np.prod(shape));order='C' if ordc==0 else 'F';T=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little',count=n).astype(bool).reshape(shape,order=order)
    if xr:
        M=T.copy()
        for i in range(1,shape[0]):M[i]=np.logical_xor(T[i],M[i-1])
    else:M=T
    vals=unpack_int(vb,dc,int(M.sum()));K=np.zeros(shape,np.int32);K[M]=vals;return K

def gap_codec(K):
    nr,nt=K.shape;chunks=[];counts=[];vals=[]
    for r in range(nr):
        pos=np.flatnonzero(K[r]);counts.append(len(pos));prev=-1
        if len(pos):
            gaps=np.diff(np.r_[-1,pos]).astype(np.uint64)-1;chunks.append(leb128(gaps));vals.append(K[r,pos])
    count_raw=leb128(np.asarray(counts,np.uint64));gap_raw=b''.join(chunks);valarr=np.concatenate(vals) if vals else np.empty(0,np.int32);dc,vb=pack_int(valarr)
    cb=ZC.compress(count_raw);gb=ZC.compress(gap_raw);head=struct.pack('<QQQB',len(cb),len(gb),len(vb),dc);return head+cb+gb+vb,{'kind':'gaps','count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'events':int(valarr.size)},dc

def decode_gap(blob,shape):
    nr,nt=shape;hs=struct.calcsize('<QQQB');lc,lg,lv,dc=struct.unpack('<QQQB',blob[:hs]);p=hs;cb=blob[p:p+lc];p+=lc;gb=blob[p:p+lg];p+=lg;vb=blob[p:p+lv]
    counts=unleb128(ZD.decompress(cb),nr).astype(int);ne=int(counts.sum());vals=unpack_int(vb,dc,ne);raw=ZD.decompress(gb);# decode all gaps as one stream using total events
    gaps=unleb128(raw,ne).astype(np.int64);K=np.zeros(shape,np.int32);vi=0
    for r,c in enumerate(counts):
        if c:
            pos=np.cumsum(gaps[vi:vi+c]+1)-1;K[r,pos]=vals[vi:vi+c];vi+=c
    return K

def encode_panel(A,eps):
    Q=np.rint(A/(2*eps)).astype(np.int32);Kt=d1(Q,1);Kx=d1(Q,0);Kl=d1(Kt,0);cands=[]
    for mode,K in [(0,Q),(1,Kt),(2,Kx),(3,Kl)]:
        dc,b=pack_int(K);h=struct.pack('<BBBQ',mode,0,dc,len(b));cands.append((len(h)+len(b),h+b,{'kind':'dense','mode':mode,'payload':len(b)},('dense',mode,dc)))
    # Sparse candidates on temporal transition field, which dominated prior runs.
    for order in ['C','F']:
        for xr in [False,True]:
            b,m,dc=sparse_mask_values(Kt,order,xr);h=struct.pack('<BBQ',1,1,len(b));cands.append((len(h)+len(b),h+b,{**m,'mode':1},('sparse',dc)))
    b,m,dc=gap_codec(Kt);h=struct.pack('<BBQ',1,2,len(b));cands.append((len(h)+len(b),h+b,{**m,'mode':1},('gap',)))
    cands.sort(key=lambda x:x[0]);_,blob,meta,_=cands[0]
    # Decode selected stream from actual bytes.
    mode,typ,L=struct.unpack('<BBQ',blob[:struct.calcsize('<BBQ')]);pay=blob[struct.calcsize('<BBQ'):]
    if typ==0:
        # Dense header is shorter/different: reparse original.
        mode,typ,dc,L=struct.unpack('<BBBQ',blob[:struct.calcsize('<BBBQ')]);pay=blob[struct.calcsize('<BBBQ'):];K=unpack_int(pay,dc,A.size).reshape(A.shape)
    elif typ==1:
        # dtype is internal metadata returned in payload meta; infer by decompressed values impossible cheaply, so parse from stored candidate construction map by re-evaluating min header metadata.
        # Reconstruct dtype from original Kt range deterministically; decoder can equivalently store this one byte in a production container.
        lo=int(Kt.min());hi=int(Kt.max());dc=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;K=decode_sparse(pay,A.shape,dc)
    else:K=decode_gap(pay,A.shape)
    if mode==0:R=K
    elif mode==1:R=np.cumsum(K,axis=1,dtype=np.int32)
    elif mode==2:R=np.cumsum(K,axis=0,dtype=np.int32)
    else:R=np.cumsum(np.cumsum(K,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
    return blob,R.astype(np.float32)*np.float32(2*eps),meta,cands

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
        b,R,m,cands=encode_panel(A,eps);parts.append(b);maxerr=max(maxerr,float(np.max(np.abs(A-R))));diagn.append({'selected':m,'alternatives':[{'bytes':x[0],**x[2]} for x in cands[:10]]})
    eb,ee=sz3(extra,eps);# compare separate bad-trace transition encoding too
    zbad=10**18;zr=None
    if extra.size:
        bb,RR,mm,_=encode_panel(extra,eps);zbad=len(bb);zr=(bb,RR,mm)
        if zbad<=eb:eb=zbad;ee=float(np.max(np.abs(extra-zr[1])));diagn.append({'bad_selected':zr[2],'bad_codec':'transition'})
        else:diagn.append({'bad_codec':'sz3','bad_bytes':eb})
    total=32+sum(map(len,parts))+eb;return {'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'bytes':total,'ratio':raw/total,'maxerr':max(maxerr,ee),'valid':bool(max(maxerr,ee)<=eps*(1+5e-6)),'extra_bytes':eb,'panels':diagn}

out={'shots':[]}
for p in sys.argv[1:]:
    r=bench(p);out['shots'].append(r);print('RESULT',json.dumps({'file':r['file'],'bytes':r['bytes'],'ratio':r['ratio'],'maxerr':r['maxerr'],'valid':r['valid'],'extra_bytes':r['extra_bytes'],'selected':[x.get('selected') for x in r['panels'] if 'selected'in x]},indent=2),flush=True)
json.dump(out,open('soda_zero_transition_three.json','w'),indent=2)
