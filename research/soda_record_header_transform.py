import json,struct,sys
import numpy as np
import soda_record_standalone_v2 as compat

base=compat.base
HX_MAGIC=b'SRHDX001'; HX_HDR='<8sIBBBQQ'; HX_HS=struct.calcsize(HX_HDR)
MODE_NAMES={0:'byte-mod-delta-plane',1:'byte-xor-delta-plane',2:'byte-zigzag-mod-delta-plane',3:'u16-zigzag-mod-delta-plane',4:'u32-zigzag-mod-delta-plane',5:'direct-byte-plane'}


def _zz_encode_signed(d,bits):
    # d is signed int64 in the centered modular interval.
    return ((d<<1)^(d>>(bits-1)))

def _zz_decode_unsigned(u):
    u=np.asarray(u,dtype=np.int64);return (u>>1)^(-(u&1))


def transform_headers(H,mode):
    H=np.ascontiguousarray(H,np.uint8);ntr=H.shape[0]
    if H.shape[1]!=240:raise RuntimeError('trace header width')
    if mode==0:
        D=H.copy();D[1:]=((H[1:].astype(np.int16)-H[:-1].astype(np.int16))%256).astype(np.uint8);return np.ascontiguousarray(D.T).tobytes()
    if mode==1:
        D=H.copy();D[1:]=np.bitwise_xor(H[1:],H[:-1]);return np.ascontiguousarray(D.T).tobytes()
    if mode==2:
        cur=H.astype(np.int16);prev=np.zeros_like(cur);prev[1:]=cur[:-1];d=((cur-prev+128)%256)-128;u=_zz_encode_signed(d.astype(np.int64),8).astype(np.uint8);return np.ascontiguousarray(u.T).tobytes()
    if mode==3:
        V=np.frombuffer(H.tobytes(),dtype='>u2').reshape(ntr,120).astype(np.uint32);P=np.zeros_like(V);P[1:]=V[:-1];m=(V-P)&0xffff;d=np.where(m<0x8000,m.astype(np.int64),m.astype(np.int64)-0x10000);u=_zz_encode_signed(d,16).astype('<u2');return np.ascontiguousarray(u.T).tobytes()
    if mode==4:
        V=np.frombuffer(H.tobytes(),dtype='>u4').reshape(ntr,60).astype(np.uint64);P=np.zeros_like(V);P[1:]=V[:-1];m=(V-P)&np.uint64(0xffffffff);mi=m.astype(np.int64);d=np.where(m<np.uint64(0x80000000),mi,mi-(1<<32));u=_zz_encode_signed(d,32).astype('<u4');return np.ascontiguousarray(u.T).tobytes()
    if mode==5:return np.ascontiguousarray(H.T).tobytes()
    raise ValueError(mode)


def inverse_headers(raw,ntr,mode):
    if len(raw)!=ntr*240:raise RuntimeError(('header transform raw length',len(raw),ntr*240))
    if mode==0:
        D=np.frombuffer(raw,np.uint8).reshape(240,ntr).T.copy();H=D.copy()
        for i in range(1,ntr):H[i]=((D[i].astype(np.uint16)+H[i-1].astype(np.uint16))%256).astype(np.uint8)
        return H
    if mode==1:
        D=np.frombuffer(raw,np.uint8).reshape(240,ntr).T.copy();H=D.copy()
        for i in range(1,ntr):H[i]=np.bitwise_xor(D[i],H[i-1])
        return H
    if mode==2:
        u=np.frombuffer(raw,np.uint8).reshape(240,ntr).T;d=_zz_decode_unsigned(u);v=np.mod(np.cumsum(d,axis=0,dtype=np.int64),256).astype(np.uint8);return np.ascontiguousarray(v)
    if mode==3:
        u=np.frombuffer(raw,dtype='<u2').reshape(120,ntr).T;d=_zz_decode_unsigned(u.astype(np.int64));v=np.mod(np.cumsum(d,axis=0,dtype=np.int64),1<<16).astype(np.uint16);be=v.astype('>u2',copy=False);return np.frombuffer(be.tobytes(),np.uint8).reshape(ntr,240).copy()
    if mode==4:
        u=np.frombuffer(raw,dtype='<u4').reshape(60,ntr).T;d=_zz_decode_unsigned(u.astype(np.int64));# values stay safely within uint32 after modular cumulative sum
        acc=np.empty(d.shape,np.uint32);state=np.zeros(d.shape[1],np.int64)
        for i in range(ntr):state=np.mod(state+d[i],1<<32);acc[i]=state.astype(np.uint32)
        be=acc.astype('>u4',copy=False);return np.frombuffer(be.tobytes(),np.uint8).reshape(ntr,240).copy()
    if mode==5:return np.frombuffer(raw,np.uint8).reshape(240,ntr).T.copy()
    raise ValueError(mode)


def encode_headers_x(gh,H):
    gt=bytes(gh);gb=base.best_comp(gt)[0];ng,mg,bg=gb
    if base.decomp_one(bg,mg)!=gt:raise RuntimeError('global header backend')
    rows=[]
    for mode in sorted(MODE_NAMES):
        raw=transform_headers(H,mode);RH=inverse_headers(raw,H.shape[0],mode)
        if not np.array_equal(RH,H):raise RuntimeError(('header transform roundtrip',mode))
        n,m,b=base.best_comp(raw)[0]
        if base.decomp_one(b,m)!=raw:raise RuntimeError(('trace header backend',mode,m))
        rows.append((n,mode,m,b))
    rows.sort(key=lambda x:(x[0],x[1]));nd,mode,md,bd=rows[0]
    h=struct.pack(HX_HDR,HX_MAGIC,H.shape[0],mg,md,mode,len(bg),len(bd))
    diag={'global_raw_bytes':len(gt),'trace_header_raw_bytes':int(H.size),'global_method':base.METHOD_NAMES[mg],'global_bytes':len(bg),'trace_method':base.METHOD_NAMES[md],'trace_transform':MODE_NAMES[mode],'trace_bytes':len(bd),'header_header_bytes':HX_HS,'trace_candidates':[{'mode':MODE_NAMES[r[1]],'method':base.METHOD_NAMES[r[2]],'bytes':int(r[0])} for r in rows]}
    return h+bg+bd,diag


def decode_headers_x(blob):
    if len(blob)<HX_HS:raise RuntimeError('short transformed header blob')
    magic,ntr,mg,md,mode,lg,ld=struct.unpack(HX_HDR,blob[:HX_HS])
    if magic!=HX_MAGIC:raise RuntimeError('bad transformed header magic')
    p=HX_HS;bg=blob[p:p+lg];p+=lg;bd=blob[p:p+ld];p+=ld
    if p!=len(blob):raise RuntimeError('transformed header blob length')
    gh=base.decomp_one(bg,mg);raw=base.decomp_one(bd,md)
    if len(gh)!=3600:raise RuntimeError('global header raw length')
    H=inverse_headers(raw,ntr,mode);return gh,H

base.encode_headers=encode_headers_x
base.decode_headers=decode_headers_x

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    base.main(sys.argv[1],sys.argv[2],sys.argv[3])
