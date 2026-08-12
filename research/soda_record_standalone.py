import json,os,struct,sys
import numpy as np
import segyio

# PR #161/#165 audited sample codec, decoder, geometry and backend primitives.
src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

SAFETY=0.9999
FILE_MAGIC=b'SRSEG001'; FILE_HDR='<8sBIIIQQQ'; FHS=struct.calcsize(FILE_HDR)
HEAD_MAGIC=b'SRHDR001'; HEAD_HDR='<8sIBBQQ'; HHS=struct.calcsize(HEAD_HDR)
SAMP_MAGIC=b'SRSMP001'; SAMP_HDR='<8sdBBQQ'; SHS=struct.calcsize(SAMP_HDR)


def split_headers(raw,ntr,ns):
    stride=240+4*ns
    if len(raw)!=3600+ntr*stride:raise RuntimeError(('nonstandard SEG-Y payload',len(raw),3600+ntr*stride))
    gh=raw[:3600];H=np.empty((ntr,240),np.uint8)
    for i in range(ntr):H[i]=np.frombuffer(raw,dtype=np.uint8,count=240,offset=3600+i*stride)
    return gh,H


def header_delta_plane(H):
    D=H.copy();D[1:]=((H[1:].astype(np.int16)-H[:-1].astype(np.int16))%256).astype(np.uint8)
    return np.ascontiguousarray(D.T).tobytes()


def encode_headers(gh,H):
    # Same reversible delta/byte-plane transform as PR #113, but let the already
    # audited exact backend menu choose the smallest lossless representation.
    gt=bytes(gh);dt=header_delta_plane(H);gb=best_comp(gt)[0];db=best_comp(dt)[0]
    ng,mg,bg=gb;nd,md,bd=db
    if decomp_one(bg,mg)!=gt or decomp_one(bd,md)!=dt:raise RuntimeError('header backend roundtrip')
    h=struct.pack(HEAD_HDR,HEAD_MAGIC,H.shape[0],mg,md,len(bg),len(bd))
    return h+bg+bd,{'global_raw_bytes':len(gt),'trace_header_raw_bytes':H.size,'global_method':METHOD_NAMES[mg],'global_bytes':len(bg),'trace_method':METHOD_NAMES[md],'trace_bytes':len(bd),'header_header_bytes':HHS}


def decode_headers(blob):
    if len(blob)<HHS:raise RuntimeError('short header blob')
    magic,ntr,mg,md,lg,ld=struct.unpack(HEAD_HDR,blob[:HHS])
    if magic!=HEAD_MAGIC:raise RuntimeError('bad header magic')
    p=HHS;bg=blob[p:p+lg];p+=lg;bd=blob[p:p+ld];p+=ld
    if p!=len(blob):raise RuntimeError('header blob length')
    gh=decomp_one(bg,mg);dt=decomp_one(bd,md)
    if len(gh)!=3600 or len(dt)!=ntr*240:raise RuntimeError('header raw lengths')
    D=np.frombuffer(dt,np.uint8).reshape(240,ntr).T.copy();H=D.copy()
    for i in range(1,ntr):H[i]=((D[i].astype(np.uint16)+H[i-1].astype(np.uint16))%256).astype(np.uint8)
    return gh,H


def coords_from_headers(H):
    ox=int(segyio.TraceField.GroupX)-1;oy=int(segyio.TraceField.GroupY)-1
    gx=np.empty(H.shape[0],np.int64);gy=np.empty(H.shape[0],np.int64)
    for i in range(H.shape[0]):
        gx[i]=int.from_bytes(H[i,ox:ox+4].tobytes(),'big',signed=True);gy[i]=int.from_bytes(H[i,oy:oy+4].tobytes(),'big',signed=True)
    return gx,gy


def ieee_to_ibm32_bytes(x):
    a=np.asarray(x,dtype=np.float64)
    if not np.all(np.isfinite(a)):raise RuntimeError('nonfinite samples')
    flat=a.ravel();out=np.zeros(flat.size,np.uint32);nz=flat!=0
    if np.any(nz):
        v=flat[nz];sign=(v<0).astype(np.uint32);av=np.abs(v);e=np.floor(np.log(av)/np.log(16.0)).astype(np.int64)+1;frac=av/np.power(16.0,e);mant=np.rint(frac*(1<<24)).astype(np.int64);carry=mant>=(1<<24)
        if np.any(carry):e[carry]+=1;mant[carry]=(1<<20)
        ef=e+64
        if np.any((ef<=0)|(ef>=128)):raise RuntimeError('IBM exponent')
        out[nz]=(sign<<31)|(ef.astype(np.uint32)<<24)|mant.astype(np.uint32)
    return out.astype('>u4',copy=False).tobytes()


def encode_samples(X,gx,gy,internal_eps):
    step=2*internal_eps;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3);mb,parts=encode_main(K,(0,1,2),4);RK=decode_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('main K encode audit')
    bo=best_out(O);obb=bo[6];out_kind=0 if bo[1]=='gap' else 1;tdiff=1 if bo[2] else 0
    if out_kind==0:A=decode(obb).reshape(O.shape);RO=undelta(A,1) if tdiff else A
    else:A=decode_out_sparse(obb);RO=undelta(A,1) if tdiff else A
    if not np.array_equal(RO,O):raise RuntimeError('outlier encode audit')
    h=struct.pack(SAMP_HDR,SAMP_MAGIC,float(internal_eps),out_kind,tdiff,len(mb),len(obb))
    diag={'main_bytes':len(mb),'outlier_bytes':len(obb),'sample_header_bytes':SHS,'main_parts':parts,'outlier_kind':bo[1],'outlier_tdiff':bool(bo[2]),'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0))}
    return h+mb+obb,diag


def decode_samples(blob,ntr,ns,gx,gy):
    if len(blob)<SHS:raise RuntimeError('short sample blob')
    magic,eps,ok,td,lm,lo=struct.unpack(SAMP_HDR,blob[:SHS])
    if magic!=SAMP_MAGIC:raise RuntimeError('bad sample magic')
    p=SHS;mb=blob[p:p+lm];p+=lm;obb=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('sample blob length')
    RK=decode_main(mb);RG=undelta(RK,3);dummy=np.empty((ntr,ns),np.float32);_,tm,outids,geom=geometry_map(dummy,gx,gy);Oshape=(len(outids),ns)
    if ok==0:A=decode(obb).reshape(Oshape);RO=undelta(A,1) if td else A
    elif ok==1:A=decode_out_sparse(obb);RO=undelta(A,1) if td else A
    else:raise RuntimeError('bad outlier kind')
    Y=np.empty((ntr,ns),np.float32)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*eps)
    Y[outids]=RO.astype(np.float32)*np.float32(2*eps)
    return Y,float(eps),geom


def encode_segy(inp,outp):
    raw=open(inp,'rb').read();fmt=int.from_bytes(raw[3224:3226],'big');ns_bin=int.from_bytes(raw[3220:3222],'big')
    if fmt not in (1,5):raise RuntimeError(('unsupported SEG-Y sample format',fmt))
    with segyio.open(inp,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
    ntr,ns=X.shape
    if ns_bin not in (0,ns):raise RuntimeError(('binary ns mismatch',ns_bin,ns))
    public_eps=.1*float(X.astype(np.float64).std());internal_eps=public_eps*SAFETY;gh,H=split_headers(raw,ntr,ns);hb,hdiag=encode_headers(gh,H);sb,sdiag=encode_samples(X,gx,gy,internal_eps)
    blob=struct.pack(FILE_HDR,FILE_MAGIC,1,ntr,ns,fmt,len(raw),len(hb),len(sb))+hb+sb;open(outp,'wb').write(blob)
    return {'input_bytes':len(raw),'container_bytes':len(blob),'whole_file_ratio':len(raw)/len(blob),'file_header_bytes':FHS,'header_blob_bytes':len(hb),'header_diag':hdiag,'sample_blob_bytes':len(sb),'sample_diag':sdiag,'public_eps':public_eps,'internal_eps':internal_eps,'sample_format':fmt}


def decode_segc(inp,outp):
    blob=open(inp,'rb').read()
    if len(blob)<FHS:raise RuntimeError('short file container')
    magic,ver,ntr,ns,fmt,orig,lh,ls=struct.unpack(FILE_HDR,blob[:FHS])
    if magic!=FILE_MAGIC or ver!=1 or fmt not in (1,5):raise RuntimeError('bad file container')
    p=FHS;hb=blob[p:p+lh];p+=lh;sb=blob[p:p+ls];p+=ls
    if p!=len(blob):raise RuntimeError('file length')
    gh,H=decode_headers(hb);gx,gy=coords_from_headers(H);Y,eps,geom=decode_samples(sb,ntr,ns,gx,gy);out=bytearray(gh)
    for i in range(ntr):
        out.extend(H[i].tobytes());out.extend(ieee_to_ibm32_bytes(Y[i]) if fmt==1 else Y[i].astype('>f4',copy=False).tobytes())
    if len(out)!=orig:raise RuntimeError(('output bytes',len(out),orig))
    open(outp,'wb').write(out);return {'output_bytes':len(out),'internal_eps':eps,'sample_format':fmt,'geometry':geom,'ntr':ntr,'ns':ns}


def verify(original,container,reconstructed):
    raw=open(original,'rb').read();out=open(reconstructed,'rb').read()
    with segyio.open(original,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();ntr=f.tracecount;ns=len(f.samples)
    with segyio.open(reconstructed,'r',ignore_geometry=True) as f:Y=np.asarray(f.trace.raw[:],np.float32).copy();ntr2=f.tracecount;ns2=len(f.samples)
    exact=raw[:3600]==out[:3600];stride=240+4*ns
    for i in range(ntr):
        a=3600+i*stride
        if raw[a:a+240]!=out[a:a+240]:exact=False;break
    me=float(np.max(np.abs(X-Y)));public_eps=.1*float(X.astype(np.float64).std())
    return {'headers_exact':bool(exact),'trace_count_match':ntr==ntr2,'samples_per_trace_match':ns==ns2,'maxerr':me,'public_eps':public_eps,'valid':bool(me<=public_eps*(1+3e-6)),'original_file_bytes':len(raw),'compressed_file_bytes':os.path.getsize(container),'whole_file_ratio':len(raw)/os.path.getsize(container)}


def main(inp,container,recon):
    enc=encode_segy(inp,container);dec=decode_segc(container,recon);ver=verify(inp,container,recon);res={'encode':enc,'decode':dec,'verify':ver}
    if not ver['headers_exact'] or not ver['valid']:raise RuntimeError(('standalone verification',ver))
    print(json.dumps({'container_bytes':enc['container_bytes'],'whole_file_ratio':enc['whole_file_ratio'],'header_blob_bytes':enc['header_blob_bytes'],'sample_blob_bytes':enc['sample_blob_bytes'],'sample_format':enc['sample_format'],'maxerr':ver['maxerr'],'public_eps':ver['public_eps'],'headers_exact':ver['headers_exact'],'valid':ver['valid']},indent=2),flush=True);json.dump(res,open('soda_record_standalone.json','w'),indent=2)

if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('input.sgy output.srseg reconstructed.sgy')
    main(sys.argv[1],sys.argv[2],sys.argv[3])
