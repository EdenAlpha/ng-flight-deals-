import json, os, struct, sys
import numpy as np, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

# Reuse the already-validated raw Utah parser, receiver-order dictionary, and exact
# integer representation container without executing the benchmark main body.
src=open('research/forge_raw_lattice.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'forge_raw_lattice.py','exec'),globals())

FILE_MAGIC=b'FSEGC001'; FILE_HDR='<8sBIIIBQQQ'; FHS=struct.calcsize(FILE_HDR)
HEAD_MAGIC=b'FHDRC001'; HEAD_HDR='<8sIIQQ'; HHS=struct.calcsize(HEAD_HDR)
SAMP_MAGIC=b'FSTPv001'; SAMP_HDR='<8sddQ'; SHS=struct.calcsize(SAMP_HDR)
BASE_MAGIC=b'FSZ3v001'; BASE_HDR='<8sBIIdBQQ'; BHS=struct.calcsize(BASE_HDR)


def split_headers(raw,ntr,ns):
    stride=240+4*ns
    if len(raw)!=3600+ntr*stride:raise RuntimeError(('prototype fixed-layout mismatch',len(raw),3600+ntr*stride))
    gh=raw[:3600];H=np.empty((ntr,240),np.uint8)
    for i in range(ntr):H[i]=np.frombuffer(raw,dtype=np.uint8,count=240,offset=3600+i*stride)
    return gh,H


def encode_headers(gh,H):
    zc=zstd.ZstdCompressor(level=22);D=H.copy();D[1:]=((H[1:].astype(np.int16)-H[:-1].astype(np.int16))%256).astype(np.uint8)
    gz=zc.compress(gh);dz=zc.compress(np.ascontiguousarray(D.T).tobytes())
    return struct.pack(HEAD_HDR,HEAD_MAGIC,H.shape[0],240,len(gz),len(dz))+gz+dz


def decode_headers(blob):
    magic,ntr,w,lg,ld=struct.unpack(HEAD_HDR,blob[:HHS])
    if magic!=HEAD_MAGIC or w!=240:raise RuntimeError('bad header blob')
    p=HHS;gz=blob[p:p+lg];p+=lg;dz=blob[p:p+ld];p+=ld
    if p!=len(blob):raise RuntimeError('header length')
    D=np.frombuffer(zstd.ZstdDecompressor().decompress(dz),np.uint8,count=ntr*240).reshape(240,ntr).T.copy();H=D.copy()
    for i in range(1,ntr):H[i]=((D[i].astype(np.uint16)+H[i-1].astype(np.uint16))%256).astype(np.uint8)
    gh=zstd.ZstdDecompressor().decompress(gz)
    if len(gh)!=3600:raise RuntimeError('global header length')
    return gh,H


def fields_from_headers(H):
    n=H.shape[0];gx=np.empty(n);gy=np.empty(n);sx=np.empty(n);sy=np.empty(n);offs=np.empty(n,np.int64)
    for i in range(n):
        th=H[i].tobytes();sc=i16(th,70);sx[i]=scaled(i32(th,72),sc);sy[i]=scaled(i32(th,76),sc);gx[i]=scaled(i32(th,80),sc);gy[i]=scaled(i32(th,84),sc);offs[i]=i32(th,36)
    return gx,gy,sx,sy,offs


def encode_samples(X,gx,gy,sx,sy,offs,public_eps):
    internal_eps=public_eps*(1-1e-4);step=2*internal_eps;Q=np.rint(X.astype(np.float64)/step).astype(np.int32);K=np.empty_like(Q);K[:,0]=Q[:,0];K[:,1:]=Q[:,1:]-Q[:,:-1]
    ordlist,_=orders(gx,gy,sx,sy,offs);rows=[]
    for oc,(name,o) in enumerate(ordlist):
        KO=K[o]
        for orient in (0,1):
            for rep in (1,2):
                b=encode_rep(KO,oc,orient,rep,19);roc,ro,R=decode_rep(b)
                if roc!=oc or ro!=orient or not np.array_equal(R,KO):raise RuntimeError('integer candidate decode')
                rows.append((len(b),name,oc,orient,rep,b))
    for oc in range(min(3,len(ordlist))):
        name,o=ordlist[oc];KO=K[o]
        for orient in (0,1):
            b=encode_rep(KO,oc,orient,0,19);roc,ro,R=decode_rep(b)
            if not np.array_equal(R,KO):raise RuntimeError('dense integer candidate decode')
            rows.append((len(b),name,oc,orient,0,b))
    best=min(rows,key=lambda q:q[0]);inner=best[-1]
    return struct.pack(SAMP_HDR,SAMP_MAGIC,float(public_eps),float(internal_eps),len(inner))+inner,{'order':best[1],'order_code':best[2],'orient':'trace_time' if best[3]==0 else 'time_trace','rep':('raw' if best[4]==0 else 'sparse' if best[4]==1 else 'ternary'),'inner_bytes':len(inner),'K_nonzero_fraction':float(np.mean(K!=0))}


def decode_samples(blob,ntr,ns,gx,gy,sx,sy,offs):
    magic,public_eps,internal_eps,li=struct.unpack(SAMP_HDR,blob[:SHS]);
    if magic!=SAMP_MAGIC or SHS+li!=len(blob):raise RuntimeError('bad sample blob')
    oc,orient,KO=decode_rep(blob[SHS:]);ordlist,_=orders(gx,gy,sx,sy,offs)
    if oc>=len(ordlist):raise RuntimeError('bad order code')
    o=ordlist[oc][1];K=np.empty((ntr,ns),np.int32);K[o]=KO;Q=np.cumsum(K,axis=1,dtype=np.int32);Y=Q.astype(np.float32)*np.float32(2*internal_eps)
    return Y,float(public_eps),float(internal_eps),{'order':ordlist[oc][0],'order_code':oc,'orient':'trace_time' if orient==0 else 'time_trace'}


def encode_segc(inp,outp):
    raw=open(inp,'rb').read();X,gx,gy,sx,sy,offs,layout=load_segy(inp);ntr,ns=X.shape
    public_eps=.1*float(X.astype(np.float64).std());gh,H=split_headers(raw,ntr,ns);hb=encode_headers(gh,H);sb,smeta=encode_samples(X,gx,gy,sx,sy,offs,public_eps)
    blob=struct.pack(FILE_HDR,FILE_MAGIC,1,ntr,ns,int(layout['dt_us']),5,len(raw),len(hb),len(sb))+hb+sb;open(outp,'wb').write(blob)
    return {'input_bytes':len(raw),'container_bytes':len(blob),'whole_file_ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(sb),'public_eps':public_eps,'sample':smeta,'layout':layout}


def decode_segc(inp,outp):
    blob=open(inp,'rb').read();magic,ver,ntr,ns,dt,fmt,orig,lh,ls=struct.unpack(FILE_HDR,blob[:FHS])
    if magic!=FILE_MAGIC or ver!=1 or fmt!=5:raise RuntimeError('bad file container')
    p=FHS;hb=blob[p:p+lh];p+=lh;sb=blob[p:p+ls];p+=ls
    if p!=len(blob):raise RuntimeError('file length')
    gh,H=decode_headers(hb);gx,gy,sx,sy,offs=fields_from_headers(H);Y,public_eps,internal_eps,smeta=decode_samples(sb,ntr,ns,gx,gy,sx,sy,offs)
    out=bytearray(gh)
    for i in range(ntr):out.extend(H[i].tobytes());out.extend(Y[i].astype('<f4',copy=False).tobytes())
    if len(out)!=orig:raise RuntimeError((len(out),orig))
    open(outp,'wb').write(out)
    return {'output_bytes':len(out),'public_eps':public_eps,'internal_eps':internal_eps,'sample':smeta}


def best_sz3_blob(X,gx,gy,sx,sy,offs,eps):
    ordlist,_=orders(gx,gy,sx,sy,offs);rows=[];cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    for oc,(name,o) in enumerate(ordlist):
        A=np.ascontiguousarray(X[o]);b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);rows.append((int(b.size),name,oc,np.ascontiguousarray(b).tobytes(),float(np.max(np.abs(A-R)))))
    return min(rows,key=lambda q:q[0]),ordlist


def encode_sz3_container(inp,outp):
    raw=open(inp,'rb').read();X,gx,gy,sx,sy,offs,layout=load_segy(inp);eps=.1*float(X.astype(np.float64).std());gh,H=split_headers(raw,*X.shape);hb=encode_headers(gh,H);best,ordlist=best_sz3_blob(X,gx,gy,sx,sy,offs,eps);bb=best[3]
    blob=struct.pack(BASE_HDR,BASE_MAGIC,1,X.shape[0],X.shape[1],float(eps),best[2],len(hb),len(bb))+hb+bb;open(outp,'wb').write(blob)
    return {'container_bytes':len(blob),'whole_file_ratio':len(raw)/len(blob),'header_blob_bytes':len(hb),'sample_blob_bytes':len(bb),'order':best[1],'order_code':best[2],'maxerr_ordered':best[4]}


def decode_sz3_container(inp,outp,orig_size):
    blob=open(inp,'rb').read();magic,ver,ntr,ns,eps,oc,lh,ls=struct.unpack(BASE_HDR,blob[:BHS]);
    if magic!=BASE_MAGIC or ver!=1:raise RuntimeError('bad baseline container')
    p=BHS;hb=blob[p:p+lh];p+=lh;bb=blob[p:p+ls];p+=ls
    if p!=len(blob):raise RuntimeError('baseline length')
    gh,H=decode_headers(hb);gx,gy,sx,sy,offs=fields_from_headers(H);ordlist,_=orders(gx,gy,sx,sy,offs);o=ordlist[oc][1]
    R,_=sz.decompress(np.frombuffer(bb,np.uint8),np.float32,(ntr,ns));Y=np.empty((ntr,ns),np.float32);Y[o]=R
    out=bytearray(gh)
    for i in range(ntr):out.extend(H[i].tobytes());out.extend(Y[i].astype('<f4',copy=False).tobytes())
    if len(out)!=orig_size:raise RuntimeError((len(out),orig_size))
    open(outp,'wb').write(out)


def verify(original,reconstructed,eps):
    raw=open(original,'rb').read();out=open(reconstructed,'rb').read();X,*_=load_segy(original);Y,*_=load_segy(reconstructed);ntr,ns=X.shape;stride=240+4*ns
    headers=(raw[:3600]==out[:3600])
    for i in range(ntr):
        a=3600+i*stride;headers=headers and raw[a:a+240]==out[a:a+240]
    me=float(np.max(np.abs(X-Y)))
    return {'headers_exact':bool(headers),'sample_maxerr':me,'eps':float(eps),'valid':bool(headers and me<=eps*(1+3e-6)),'output_size_match':len(raw)==len(out)}


def main(inp):
    enc=encode_segc(inp,'utah.segc');dec=decode_segc('utah.segc','utah_recon.sgy');ver=verify(inp,'utah_recon.sgy',enc['public_eps']);base=encode_sz3_container(inp,'utah_sz3.segz');decode_sz3_container('utah_sz3.segz','utah_sz3_recon.sgy',enc['input_bytes']);bver=verify(inp,'utah_sz3_recon.sgy',enc['public_eps'])
    res={'lattice':enc,'lattice_decode':dec,'lattice_verify':ver,'sz3':base,'sz3_verify':bver,'whole_file_size_gain':base['container_bytes']/enc['container_bytes']};print(json.dumps(res,indent=2),flush=True);json.dump(res,open('forge_standalone_result.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
