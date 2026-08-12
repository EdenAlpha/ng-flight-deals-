import json, os, struct, sys
from collections import Counter
import numpy as np
import zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

MAG=b'FSTATE01'
HDR='<8sdIIBQQ'
HS=struct.calcsize(HDR)
DT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
ZC=zstd.ZstdCompressor(level=22)
ZD=zstd.ZstdDecompressor()

def i16(b,o): return int.from_bytes(b[o:o+2],'little',signed=True)
def u16(b,o): return int.from_bytes(b[o:o+2],'little',signed=False)
def i32(b,o): return int.from_bytes(b[o:o+4],'little',signed=True)
def scale_coord(v,s): return float(v)*(float(s) if s>0 else (1.0/float(-s) if s<0 else 1.0))

def load_little_segy(path):
    size=os.path.getsize(path)
    with open(path,'rb') as f:
        head=f.read(3600)
        if len(head)!=3600: raise RuntimeError('short SEG-Y')
        bh=head[3200:3600]
        dt=u16(bh,16); ns=u16(bh,20); fmt=u16(bh,24); ext=i16(bh,304)
        family_header_fallback=False
        if fmt!=5:
            fam_ns=16001; fam_dt=1000; fam_fmt=5; fam_ntr=1747
            fam_stride=240+4*fam_ns
            if not any(head) and size==3600+fam_ntr*fam_stride:
                ns=fam_ns; dt=fam_dt; fmt=fam_fmt; ext=0; family_header_fallback=True
            else:
                raise RuntimeError(f'expected little-endian IEEE float format 5, got {fmt}')
        data0=3600+max(0,ext)*3200
        stride=240+4*ns
        rem=size-data0
        if ns<=0 or rem<=0 or rem%stride: raise RuntimeError({'size':size,'data0':data0,'ns':ns,'stride':stride,'remainder':rem%stride})
        ntr=rem//stride
        if family_header_fallback and ntr!=1747: raise RuntimeError(f'fallback trace-count mismatch {ntr}')
        X=np.empty((ntr,ns),np.float32); gx=np.empty(ntr,np.float64); gy=np.empty(ntr,np.float64); sx=np.empty(ntr,np.float64); sy=np.empty(ntr,np.float64)
        f.seek(data0)
        for i in range(ntr):
            th=f.read(240)
            ns_t=u16(th,114) or ns
            if ns_t!=ns: raise RuntimeError(f'variable trace length {ns_t} at {i}')
            sc=i16(th,70); sx[i]=scale_coord(i32(th,72),sc); sy[i]=scale_coord(i32(th,76),sc); gx[i]=scale_coord(i32(th,80),sc); gy[i]=scale_coord(i32(th,84),sc)
            raw=f.read(4*ns); X[i]=np.frombuffer(raw,dtype='<f4',count=ns)
    return X,gx,gy,sx,sy,{'file_bytes':size,'data_offset':data0,'dt_us':dt,'ns':ns,'format':fmt,'trace_count':int(ntr),'family_header_fallback':bool(family_header_fallback)}

def dtype_code(a):
    lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    return 1 if lo>=-128 and hi<=127 else (2 if lo>=-32768 and hi<=32767 else 3)

def encode_frozen(X,eps):
    # Frozen Soda sparse-state principle: legal 2*eps lattice, time delta,
    # sparse nonzero bitmap+values, Zstd-22. No parameter search.
    step=2.0*eps
    Q=np.rint(X/step).astype(np.int32)
    K=Q.copy(); K[:,1:]-=Q[:,:-1]
    mask=K!=0; mb=np.packbits(mask.ravel(),bitorder='little').tobytes(); vals=K[mask]; dc=dtype_code(vals)
    mz=ZC.compress(mb); vz=ZC.compress(np.ascontiguousarray(vals.astype(DT[dc],copy=False)).tobytes())
    h=struct.pack(HDR,MAG,float(eps),X.shape[0],X.shape[1],dc,len(mz),len(vz))
    return h+mz+vz,{'K_nonzero_fraction':float(mask.mean()),'K_nonzero_count':int(mask.sum()),'dtype_code':dc,'mask_bytes':len(mz),'value_bytes':len(vz),'header_bytes':HS,'Q_min':int(Q.min()),'Q_max':int(Q.max()),'K_min':int(K.min()),'K_max':int(K.max())}

def decode_frozen(blob):
    magic,eps,ntr,ns,dc,lm,lv=struct.unpack(HDR,blob[:HS])
    if magic!=MAG: raise RuntimeError('bad magic')
    p=HS;mz=blob[p:p+lm];p+=lm;vz=blob[p:p+lv];p+=lv
    if p!=len(blob): raise RuntimeError('length')
    n=ntr*ns; mask=np.unpackbits(np.frombuffer(ZD.decompress(mz),np.uint8),bitorder='little',count=n).astype(bool)
    nv=int(mask.sum()); vals=np.frombuffer(ZD.decompress(vz),dtype=DT[dc],count=nv).astype(np.int32)
    if vals.size!=nv: raise RuntimeError('values')
    K=np.zeros(n,np.int32);K[mask]=vals;K=K.reshape(ntr,ns)
    Q=np.cumsum(K,axis=1,dtype=np.int32)
    return Q.astype(np.float32)*np.float32(2.0*eps),float(eps)

def sz3_bench(X,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    b,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(b,np.float32,X.shape)
    return {'bytes':int(b.size),'ratio':float(X.nbytes/int(b.size)),'maxerr':float(np.max(np.abs(X-R)))}

def geometry_summary(gx,gy,sx,sy):
    pairs=list(zip(gx.tolist(),gy.tolist())); mult=Counter(Counter(pairs).values()); pts=np.unique(np.c_[gx,gy],axis=0)
    out={'receiver_unique':int(len(pts)),'receiver_multiplicity':{str(k):int(v) for k,v in sorted(mult.items())},'source_unique':int(len(set(zip(sx.tolist(),sy.tolist()))))}
    good=~((pts[:,0]==0)&(pts[:,1]==0)) if len(pts) else np.array([],bool);P=pts[good]
    if 1<len(P)<=5000:
        best=np.full(len(P),np.inf)
        for a in range(0,len(P),256):
            q=P[a:a+256];d2=np.sum((q[:,None,:]-P[None,:,:])**2,axis=2);rows=np.arange(a,min(a+256,len(P)));d2[np.arange(len(rows)),rows]=np.inf;best[a:a+len(rows)]=np.min(d2,axis=1)
        nn=np.sqrt(best);out['nearest_spacing']={'median':float(np.median(nn)),'q10':float(np.quantile(nn,.1)),'q90':float(np.quantile(nn,.9))}
    return out

def main(path):
    X,gx,gy,sx,sy,meta=load_little_segy(path)
    if not np.isfinite(X).all(): raise RuntimeError('nonfinite samples')
    std=float(X.astype(np.float64).std());eps=.1*std;raw=int(X.nbytes)
    blob,diag=encode_frozen(X,eps);R,ee=decode_frozen(blob);me=float(np.max(np.abs(X-R)))
    sz3=sz3_bench(X,eps)
    vals,cnt=np.unique(np.diff(np.rint(X/(2*eps)).astype(np.int32),axis=1),return_counts=True);oi=np.argsort(cnt)[::-1][:12]
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_sample_bytes':raw,'std':std,'eps':eps,'segy':meta,'geometry':geometry_summary(gx,gy,sx,sy),'frozen_representation':{'lattice_step':'2*eps','delta_axis':'time','representation':'sparse mask+values','zstd_level':22,'trace_order':'original file order'},'state':diag,'container_bytes':len(blob),'ratio':float(raw/len(blob)),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':sz3,'gain_vs_sz3':float((raw/len(blob))/sz3['ratio']),'delta_top_values':[{'v':int(vals[i]),'count':int(cnt[i])} for i in oi]}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('forge_raw_frozen_state.json','w'),indent=2)

main(sys.argv[1])
