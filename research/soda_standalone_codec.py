import json, os, struct, sys
import numpy as np
import segyio, zstandard as zstd
# Reuse the already audited geometry and sparse-array codec definitions.
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())

FILE_MAGIC=b'SEGCv001'; FILE_HDR='<8sBIIIQQQ'; FHS=struct.calcsize(FILE_HDR)
HEAD_MAGIC=b'HDRCv001'; HEAD_HDR='<8sIIQQ'; HHS=struct.calcsize(HEAD_HDR)
SAMP_MAGIC=b'STOPv001'; SAMP_HDR='<8sdQQ'; SHS2=struct.calcsize(SAMP_HDR)

# Frozen sample codec discovered on F4746R1 and validated without retuning on F1750R1/F7741R1.
MAIN_PERM=(1,2,0,3)  # line, station, component, time
MAIN_REP=1            # sparse support + values
MAIN_LEVEL=22
OUT_PERM=(0,1,2,3)
OUT_REP=0             # raw legal lattice integers
OUT_LEVEL=22


def split_headers(raw,ntr,ns):
    stride=240+4*ns
    if len(raw)!=3600+ntr*stride: raise RuntimeError('prototype supports standard IEEE-float SEG-Y with no extended payload')
    gh=raw[:3600];H=np.empty((ntr,240),np.uint8)
    for i in range(ntr):H[i]=np.frombuffer(raw,dtype=np.uint8,count=240,offset=3600+i*stride)
    return gh,H


def encode_headers(gh,H):
    ntr=H.shape[0];zc=zstd.ZstdCompressor(level=22)
    D=H.copy();D[1:]=((H[1:].astype(np.int16)-H[:-1].astype(np.int16))%256).astype(np.uint8)
    gz=zc.compress(gh);dz=zc.compress(np.ascontiguousarray(D.T).tobytes())
    return struct.pack(HEAD_HDR,HEAD_MAGIC,ntr,240,len(gz),len(dz))+gz+dz


def decode_headers(blob):
    if len(blob)<HHS:raise RuntimeError('short header blob')
    magic,ntr,w,lg,ld=struct.unpack(HEAD_HDR,blob[:HHS]);
    if magic!=HEAD_MAGIC or w!=240:raise RuntimeError('bad header blob')
    p=HHS;gz=blob[p:p+lg];p+=lg;dz=blob[p:p+ld];p+=ld
    if p!=len(blob):raise RuntimeError('header blob length')
    gh=zstd.ZstdDecompressor().decompress(gz);D=np.frombuffer(zstd.ZstdDecompressor().decompress(dz),np.uint8,count=ntr*240).reshape(240,ntr).T.copy()
    H=D.copy()
    for i in range(1,ntr):H[i]=((D[i].astype(np.uint16)+H[i-1].astype(np.uint16))%256).astype(np.uint8)
    if len(gh)!=3600:raise RuntimeError('global header length')
    return gh,H


def coords_from_headers(H):
    ox=int(segyio.TraceField.GroupX)-1;oy=int(segyio.TraceField.GroupY)-1
    gx=np.empty(H.shape[0],np.int64);gy=np.empty(H.shape[0],np.int64)
    for i in range(H.shape[0]):
        gx[i]=int.from_bytes(H[i,ox:ox+4].tobytes(),'big',signed=True)
        gy[i]=int.from_bytes(H[i,oy:oy+4].tobytes(),'big',signed=True)
    return gx,gy


def encode_samples(X,gx,gy,eps):
    step=2.0*eps;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    mb=encode_array(K,MAIN_PERM,MAIN_REP,MAIN_LEVEL);ob=encode_out_sparse(O,OUT_PERM,OUT_REP,OUT_LEVEL)
    return struct.pack(SAMP_HDR,SAMP_MAGIC,float(eps),len(mb),len(ob))+mb+ob,geom


def decode_samples(blob,ntr,ns,gx,gy):
    if len(blob)<SHS2:raise RuntimeError('short sample blob')
    magic,eps,lm,lo=struct.unpack(SAMP_HDR,blob[:SHS2]);
    if magic!=SAMP_MAGIC:raise RuntimeError('bad sample blob')
    p=SHS2;mb=blob[p:p+lm];p+=lm;ob=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('sample blob length')
    RK=decode_array(mb);RG=undelta(RK,3);RO=decode_out_sparse(ob)
    dummy=np.empty((ntr,ns),np.float32);_,tm,outids,geom=geometry_map(dummy,gx,gy)
    Y=np.empty((ntr,ns),np.float32)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*eps)
    Y[outids]=RO.astype(np.float32)*np.float32(2*eps)
    return Y,float(eps),geom


def encode_segy(inp,outp):
    raw=open(inp,'rb').read();fmt=int.from_bytes(raw[3224:3226],'big');ns_bin=int.from_bytes(raw[3220:3222],'big')
    if fmt!=5:raise RuntimeError(f'prototype requires SEG-Y format 5 IEEE float, got {fmt}')
    with segyio.open(inp,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
    ntr,ns=X.shape
    if ns_bin not in (0,ns):raise RuntimeError('binary-header sample count mismatch')
    eps=.1*float(X.astype(np.float64).std());gh,H=split_headers(raw,ntr,ns);hb=encode_headers(gh,H);sb,geom=encode_samples(X,gx,gy,eps)
    blob=struct.pack(FILE_HDR,FILE_MAGIC,1,ntr,ns,fmt,len(raw),len(hb),len(sb))+hb+sb;open(outp,'wb').write(blob)
    return {'input_bytes':len(raw),'container_bytes':len(blob),'ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(sb),'eps':eps,'geometry':geom}


def decode_segc(inp,outp):
    blob=open(inp,'rb').read();
    if len(blob)<FHS:raise RuntimeError('short file container')
    magic,ver,ntr,ns,fmt,orig,lh,ls=struct.unpack(FILE_HDR,blob[:FHS]);
    if magic!=FILE_MAGIC or ver!=1 or fmt!=5:raise RuntimeError('bad file container')
    p=FHS;hb=blob[p:p+lh];p+=lh;sb=blob[p:p+ls];p+=ls
    if p!=len(blob):raise RuntimeError('file container length')
    gh,H=decode_headers(hb);gx,gy=coords_from_headers(H);Y,eps,geom=decode_samples(sb,ntr,ns,gx,gy)
    out=bytearray();out.extend(gh)
    for i in range(ntr):out.extend(H[i].tobytes());out.extend(Y[i].astype('>f4',copy=False).tobytes())
    if len(out)!=orig:raise RuntimeError(f'output size {len(out)} != original {orig}')
    open(outp,'wb').write(out)
    return {'output_bytes':len(out),'eps':eps,'geometry':geom,'ntr':ntr,'ns':ns}


def verify(original,container,reconstructed):
    raw=open(original,'rb').read();out=open(reconstructed,'rb').read()
    with segyio.open(original,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();ntr=f.tracecount;ns=len(f.samples)
    with segyio.open(reconstructed,'r',ignore_geometry=True) as f:Y=np.asarray(f.trace.raw[:],np.float32).copy();ntr2=f.tracecount;ns2=len(f.samples)
    # Check every non-sample byte (3600-byte global header + every 240-byte trace header) exactly.
    headers_exact=(raw[:3600]==out[:3600]);stride=240+4*ns
    for i in range(ntr):
        a=3600+i*stride;headers_exact=headers_exact and (raw[a:a+240]==out[a:a+240])
    maxerr=float(np.max(np.abs(X-Y)));eps=.1*float(X.astype(np.float64).std())
    return {'headers_exact':bool(headers_exact),'trace_count_match':ntr==ntr2,'samples_per_trace_match':ns==ns2,'maxerr':maxerr,'eps':eps,'valid':bool(maxerr<=eps*(1+3e-6)),'original_file_bytes':len(raw),'compressed_file_bytes':os.path.getsize(container),'whole_file_ratio':len(raw)/os.path.getsize(container)}


if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: soda_standalone_codec.py input.sgy output.segc reconstructed.sgy')
    enc=encode_segy(sys.argv[1],sys.argv[2]);dec=decode_segc(sys.argv[2],sys.argv[3]);ver=verify(sys.argv[1],sys.argv[2],sys.argv[3]);res={'encode':enc,'decode':dec,'verify':ver};print(json.dumps(res,indent=2),flush=True);json.dump(res,open('soda_standalone_result.json','w'),indent=2)
