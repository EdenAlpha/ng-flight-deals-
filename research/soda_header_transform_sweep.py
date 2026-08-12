import json,os,struct,sys
import numpy as np
import segyio

# Reuse the exact lossless backend menu already audited in PR #161/#171.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

GROUPS=(1,2,4,8,12,16,20,24,30,40,60,80,120,240)

def pack_words(V,bits):
    V=np.asarray(V,np.uint64);nb=bits//8;out=np.empty(V.shape+(nb,),np.uint8)
    for j in range(nb):out[...,j]=((V>>(8*(nb-1-j)))&255).astype(np.uint8)
    return out.reshape(V.shape[0],-1)

def unpack_words(H,bits):
    H=np.asarray(H,np.uint8);nb=bits//8;A=H.reshape(H.shape[0],-1,nb).astype(np.uint64);V=np.zeros(A.shape[:2],np.uint64)
    for j in range(nb):V=(V<<8)|A[...,j]
    return V

def delta_words(H,bits,order):
    mod=1<<bits;mask=mod-1;V=unpack_words(H,bits);D=V.copy()
    D[1:]=(V[1:]-V[:-1])&mask
    if order==2:
        E=D.copy();E[1:]=(D[1:]-D[:-1])&mask;D=E
    return pack_words(D,bits)

def undelta_words(D,bits,order):
    mod=1<<bits;mask=mod-1;V=unpack_words(D,bits)
    if order==2:
        A=np.empty_like(V);A[0]=V[0]
        for i in range(1,len(V)):A[i]=(A[i-1]+V[i])&mask
        V=A
    A=np.empty_like(V);A[0]=V[0]
    for i in range(1,len(V)):A[i]=(A[i-1]+V[i])&mask
    return pack_words(A,bits)

def xor_words(H,bits,order):
    V=unpack_words(H,bits);D=V.copy();D[1:]=V[1:]^V[:-1]
    if order==2:
        E=D.copy();E[1:]=D[1:]^D[:-1];D=E
    return pack_words(D,bits)

def unxor_words(D,bits,order):
    V=unpack_words(D,bits)
    if order==2:
        A=np.empty_like(V);A[0]=V[0]
        for i in range(1,len(V)):A[i]=A[i-1]^V[i]
        V=A
    A=np.empty_like(V);A[0]=V[0]
    for i in range(1,len(V)):A[i]=A[i-1]^V[i]
    return pack_words(A,bits)

def transform(H,name):
    if name=='raw':return H.copy()
    typ,bits,ord0=name.split('_');bits=int(bits);order=int(ord0[1:])
    return delta_words(H,bits,order) if typ=='delta' else xor_words(H,bits,order)

def inverse(T,name):
    if name=='raw':return T.copy()
    typ,bits,ord0=name.split('_');bits=int(bits);order=int(ord0[1:])
    return undelta_words(T,bits,order) if typ=='delta' else unxor_words(T,bits,order)

def encode_planes(T,g):
    P=np.ascontiguousarray(T.T);chunks=[];payloads=[];methods=[]
    for a in range(0,240,g):
        raw=np.ascontiguousarray(P[a:min(240,a+g)]).tobytes();best,_=best_comp(raw);n,m,b=best
        if decomp_one(b,m)!=raw:raise RuntimeError(('backend roundtrip',a,g,m))
        payloads.append(b);methods.append(int(m));chunks.append((a,min(240,a+g),len(raw),len(b),METHOD_NAMES[m]))
    # Realistic self-described header blob cost when combined with the already
    # measured 693-byte global-header payload: 24-byte fixed header + 5 bytes
    # per trace-header chunk (method id + uint32 length) + all payloads.
    trace_payload=sum(map(len,payloads));header_blob=24+5*len(payloads)+693+trace_payload
    # Exact transform roundtrip from compressed bytes.
    rr=[]
    for b,m,(a,z,rawlen,clen,mn) in zip(payloads,methods,chunks):
        x=decomp_one(b,m)
        if len(x)!=rawlen:raise RuntimeError('chunk raw length')
        rr.append(np.frombuffer(x,np.uint8).reshape(z-a,T.shape[0]))
    RT=np.concatenate(rr,axis=0).T.copy();return header_blob,trace_payload,chunks,RT

def main(path):
    raw=open(path,'rb').read()
    with segyio.open(path,'r',ignore_geometry=True) as f:ntr=f.tracecount;ns=len(f.samples)
    stride=240+4*ns
    if len(raw)!=3600+ntr*stride:raise RuntimeError(('layout',len(raw),ntr,ns,stride))
    H=np.empty((ntr,240),np.uint8)
    for i in range(ntr):H[i]=np.frombuffer(raw,np.uint8,count=240,offset=3600+i*stride)
    names=['raw']+[f'{typ}_{bits}_o{o}' for typ in ('delta','xor') for bits in (8,16,32) for o in (1,2)]
    rows=[]
    for name in names:
        T=transform(H,name)
        for g in GROUPS:
            hb,tp,ch,RT=encode_planes(T,g);RH=inverse(RT,name)
            if not np.array_equal(RH,H):raise RuntimeError(('header transform decode',name,g))
            rows.append({'transform':name,'group_planes':g,'chunks':len(ch),'trace_payload_bytes':tp,'header_blob_bytes':hb,'saving_vs_pr171_header_blob':5775-hb,'chunk_detail':ch})
    rows.sort(key=lambda r:r['header_blob_bytes']);out={'file':os.path.basename(path),'ntr':ntr,'ns':ns,'baseline_pr171_header_blob_bytes':5775,'best':rows[0],'top20':rows[:20]}
    print(json.dumps({'best':rows[0],'top5':rows[:5]},indent=2),flush=True);json.dump(out,open('soda_header_transform_sweep.json','w'),indent=2)

main(sys.argv[1])
