import json, os, struct, sys
from collections import Counter
import numpy as np
import zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode
MAG=b'FSTATE01'; HDR='<8sdIIBQQ'; HS=struct.calcsize(HDR)
DT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}; ZC=zstd.ZstdCompressor(level=22); ZD=zstd.ZstdDecompressor()
def geti(b,o,n,bo,s=False): return int.from_bytes(b[o:o+n],bo,signed=s)
def scale_coord(v,s): return float(v)*(float(s) if s>0 else (1.0/float(-s) if s<0 else 1.0))
def load_auto_segy(path):
    size=os.path.getsize(path)
    with open(path,'rb') as f: head=f.read(3600)
    if len(head)!=3600: raise RuntimeError('short SEG-Y')
    bh=head[3200:3600]; cand=[]
    for bo in ('little','big'):
        dt=geti(bh,16,2,bo); ns=geti(bh,20,2,bo); fmt=geti(bh,24,2,bo); ext=geti(bh,304,2,bo,True)
        data0=3600+max(0,ext)*3200; stride=240+4*ns; rem=size-data0
        if fmt==5 and 0<dt<1000000 and 0<ns<1000000 and rem>0 and rem%stride==0:
            cand.append((bo,dt,ns,fmt,ext,data0,stride,rem//stride))
    if len(cand)!=1: raise RuntimeError({'endian_candidates':cand,'size':size})
    bo,dt,ns,fmt,ext,data0,stride,ntr=cand[0]; sdtype='<f4' if bo=='little' else '>f4'
    X=np.empty((ntr,ns),np.float32); gx=np.empty(ntr); gy=np.empty(ntr); sx=np.empty(ntr); sy=np.empty(ntr)
    with open(path,'rb') as f:
        f.seek(data0)
        for i in range(ntr):
            th=f.read(240); ns_t=geti(th,114,2,bo) or ns; dt_t=geti(th,116,2,bo) or dt
            if ns_t!=ns or dt_t!=dt: raise RuntimeError(f'variable trace at {i}: ns={ns_t} dt={dt_t}')
            sc=geti(th,70,2,bo,True); sx[i]=scale_coord(geti(th,72,4,bo,True),sc); sy[i]=scale_coord(geti(th,76,4,bo,True),sc); gx[i]=scale_coord(geti(th,80,4,bo,True),sc); gy[i]=scale_coord(geti(th,84,4,bo,True),sc)
            X[i]=np.frombuffer(f.read(4*ns),dtype=sdtype,count=ns).astype(np.float32)
    return X,gx,gy,sx,sy,{'file_bytes':size,'endian':bo,'data_offset':data0,'dt_us':dt,'ns':ns,'format':fmt,'trace_count':int(ntr)}
def dtype_code(a):
    lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    return 1 if lo>=-128 and hi<=127 else (2 if lo>=-32768 and hi<=32767 else 3)
def encode_frozen(X,eps):
    Q=np.rint(X/(2.0*eps)).astype(np.int32); K=Q.copy(); K[:,1:]-=Q[:,:-1]; mask=K!=0; vals=K[mask]; dc=dtype_code(vals)
    mz=ZC.compress(np.packbits(mask.ravel(),bitorder='little').tobytes()); vz=ZC.compress(np.ascontiguousarray(vals.astype(DT[dc],copy=False)).tobytes()); h=struct.pack(HDR,MAG,float(eps),X.shape[0],X.shape[1],dc,len(mz),len(vz))
    return h+mz+vz,{'K_nonzero_fraction':float(mask.mean()),'K_nonzero_count':int(mask.sum()),'dtype_code':dc,'mask_bytes':len(mz),'value_bytes':len(vz),'header_bytes':HS}
def decode_frozen(blob):
    magic,eps,ntr,ns,dc,lm,lv=struct.unpack(HDR,blob[:HS]); p=HS
    if magic!=MAG: raise RuntimeError('bad magic')
    mz=blob[p:p+lm];p+=lm;vz=blob[p:p+lv];p+=lv
    if p!=len(blob): raise RuntimeError('length')
    n=ntr*ns; mask=np.unpackbits(np.frombuffer(ZD.decompress(mz),np.uint8),bitorder='little',count=n).astype(bool); nv=int(mask.sum()); vals=np.frombuffer(ZD.decompress(vz),dtype=DT[dc],count=nv).astype(np.int32); K=np.zeros(n,np.int32);K[mask]=vals;Q=np.cumsum(K.reshape(ntr,ns),axis=1,dtype=np.int32)
    return Q.astype(np.float32)*np.float32(2*eps),float(eps)
def sz3_bench(X,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(b,np.float32,X.shape);return {'bytes':int(b.size),'ratio':float(X.nbytes/int(b.size)),'maxerr':float(np.max(np.abs(X-R)))}
def main(path):
    X,gx,gy,sx,sy,meta=load_auto_segy(path)
    if not np.isfinite(X).all(): raise RuntimeError('nonfinite samples')
    std=float(X.astype(np.float64).std());eps=.1*std;raw=int(X.nbytes);blob,state=encode_frozen(X,eps);R,_=decode_frozen(blob);me=float(np.max(np.abs(X-R)));sz3=sz3_bench(X,eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_sample_bytes':raw,'std':std,'eps':eps,'segy':meta,'state':state,'container_bytes':len(blob),'ratio':float(raw/len(blob)),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':sz3,'gain_vs_sz3':float((raw/len(blob))/sz3['ratio'])}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('forge_raw_frozen_auto.json','w'),indent=2)
main(sys.argv[1])
