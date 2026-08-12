import json, os, struct, sys
import numpy as np
import segyio
import soda_standalone_codec as base

# Leave 0.01% of the public hard-error budget for the final SEG-Y sample-format rounding.
SAFETY=0.9999


def ieee_to_ibm32_bytes(x):
    """Vectorized native float -> big-endian IBM 32-bit float bytes (SEG-Y format 1)."""
    a=np.asarray(x,dtype=np.float64)
    if not np.all(np.isfinite(a)):raise RuntimeError('non-finite samples not supported by prototype')
    flat=a.ravel();out=np.zeros(flat.size,np.uint32);nz=flat!=0
    if np.any(nz):
        v=flat[nz];sign=(v<0).astype(np.uint32);av=np.abs(v)
        # IBM value = fraction * 16**(exp-64), normalized with 1/16 <= fraction < 1.
        e=np.floor(np.log(av)/np.log(16.0)).astype(np.int64)+1
        frac=av/np.power(16.0,e)
        mant=np.rint(frac*(1<<24)).astype(np.int64)
        carry=mant>=(1<<24)
        if np.any(carry):
            e[carry]+=1;mant[carry]=(1<<20)
        ef=e+64
        if np.any((ef<=0)|(ef>=128)):raise RuntimeError('IBM float exponent out of range')
        words=(sign<<31)|(ef.astype(np.uint32)<<24)|mant.astype(np.uint32)
        out[nz]=words
    return out.astype('>u4',copy=False).tobytes()


def encode_segy(inp,outp):
    raw=open(inp,'rb').read();fmt=int.from_bytes(raw[3224:3226],'big');ns_bin=int.from_bytes(raw[3220:3222],'big')
    if fmt not in (1,5):raise RuntimeError(f'prototype supports SEG-Y formats 1/5, got {fmt}')
    with segyio.open(inp,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64)
    ntr,ns=X.shape
    if ns_bin not in (0,ns):raise RuntimeError('binary-header sample count mismatch')
    public_eps=.1*float(X.astype(np.float64).std());internal_eps=public_eps*SAFETY
    gh,H=base.split_headers(raw,ntr,ns);hb=base.encode_headers(gh,H);sb,geom=base.encode_samples(X,gx,gy,internal_eps)
    blob=struct.pack(base.FILE_HDR,base.FILE_MAGIC,1,ntr,ns,fmt,len(raw),len(hb),len(sb))+hb+sb;open(outp,'wb').write(blob)
    return {'input_bytes':len(raw),'container_bytes':len(blob),'ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(sb),'public_eps':public_eps,'internal_eps':internal_eps,'sample_format':fmt,'geometry':geom}


def decode_segc(inp,outp):
    blob=open(inp,'rb').read();
    if len(blob)<base.FHS:raise RuntimeError('short file container')
    magic,ver,ntr,ns,fmt,orig,lh,ls=struct.unpack(base.FILE_HDR,blob[:base.FHS])
    if magic!=base.FILE_MAGIC or ver!=1 or fmt not in (1,5):raise RuntimeError('bad file container')
    p=base.FHS;hb=blob[p:p+lh];p+=lh;sb=blob[p:p+ls];p+=ls
    if p!=len(blob):raise RuntimeError('file container length')
    gh,H=base.decode_headers(hb);gx,gy=base.coords_from_headers(H);Y,internal_eps,geom=base.decode_samples(sb,ntr,ns,gx,gy)
    out=bytearray();out.extend(gh)
    for i in range(ntr):
        out.extend(H[i].tobytes())
        if fmt==1:out.extend(ieee_to_ibm32_bytes(Y[i]))
        else:out.extend(Y[i].astype('>f4',copy=False).tobytes())
    if len(out)!=orig:raise RuntimeError(f'output size {len(out)} != original {orig}')
    open(outp,'wb').write(out)
    return {'output_bytes':len(out),'internal_eps':internal_eps,'sample_format':fmt,'geometry':geom,'ntr':ntr,'ns':ns}


def verify(original,container,reconstructed):
    raw=open(original,'rb').read();out=open(reconstructed,'rb').read()
    with segyio.open(original,'r',ignore_geometry=True) as f:X=np.asarray(f.trace.raw[:],np.float32).copy();ntr=f.tracecount;ns=len(f.samples)
    with segyio.open(reconstructed,'r',ignore_geometry=True) as f:Y=np.asarray(f.trace.raw[:],np.float32).copy();ntr2=f.tracecount;ns2=len(f.samples)
    headers_exact=(raw[:3600]==out[:3600]);stride=240+4*ns
    for i in range(ntr):
        a=3600+i*stride;headers_exact=headers_exact and (raw[a:a+240]==out[a:a+240])
    maxerr=float(np.max(np.abs(X-Y)));public_eps=.1*float(X.astype(np.float64).std())
    return {'headers_exact':bool(headers_exact),'trace_count_match':ntr==ntr2,'samples_per_trace_match':ns==ns2,'maxerr':maxerr,'public_eps':public_eps,'valid':bool(maxerr<=public_eps*(1+3e-6)),'original_file_bytes':len(raw),'compressed_file_bytes':os.path.getsize(container),'whole_file_ratio':len(raw)/os.path.getsize(container)}


if __name__=='__main__':
    if len(sys.argv)!=4:raise SystemExit('usage: soda_standalone_codec_v2.py input.sgy output.segc reconstructed.sgy')
    enc=encode_segy(sys.argv[1],sys.argv[2]);dec=decode_segc(sys.argv[2],sys.argv[3]);ver=verify(sys.argv[1],sys.argv[2],sys.argv[3]);res={'encode':enc,'decode':dec,'verify':ver};print(json.dumps(res,indent=2),flush=True);json.dump(res,open('soda_standalone_result.json','w'),indent=2)
