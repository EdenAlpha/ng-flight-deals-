import json, os, struct
import numpy as np
import zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

MAGIC=b'KXYFTOP1'
HDR='<8sHIII d II BB QQQQQ'
HS=struct.calcsize(HDR)
CCTX=zstd.ZstdCompressor(level=19)
DCTX=zstd.ZstdDecompressor()

X=np.fromfile('data/forge_subcube_f32.bin',np.float32).reshape(64,64,512)
meta=json.load(open('data/forge_subcube_meta.json'))
eps=float(meta['eps_10pct_std'])
raw=int(X.nbytes)
step=2.0*eps

DTYPES={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
def pack_int(a):
    lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    if lo>=-128 and hi<=127: code=1
    elif lo>=-32768 and hi<=32767: code=2
    else: code=3
    b=np.ascontiguousarray(a.astype(DTYPES[code],copy=False)).tobytes()
    return code,CCTX.compress(b)

def unpack_int(blob,code,count):
    b=DCTX.decompress(blob)
    a=np.frombuffer(b,dtype=DTYPES[code],count=count).astype(np.int32,copy=False)
    if a.size!=count: raise RuntimeError('integer stream length mismatch')
    return a

def forward(W):
    return np.fft.fft(np.fft.fft(np.fft.rfft(W,axis=2),axis=1),axis=0)

def inverse(C,B):
    return np.fft.irfft(np.fft.ifft(np.fft.ifft(C,axis=0),axis=1),n=B,axis=2).real.astype(np.float32)

def encode_candidate(B,frac,specs):
    shp=specs[0].shape; m=int(np.prod(shp)); N=max(1,min(m,int(round(frac*m))))
    nblk=len(specs); inds=[]; vals=[]; scales=[]; P=np.empty_like(X)
    for b,C in enumerate(specs):
        flat=C.reshape(-1); ii=np.argpartition(np.abs(flat),-N)[-N:]; ii=np.sort(ii).astype(np.uint32)
        v=flat[ii]; comp=np.stack([v.real,v.imag],axis=1)
        s=max(float(np.max(np.abs(comp)))/127.0,1e-30); s16=np.float16(s); sd=float(np.float32(s16))
        q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8)
        vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*np.float32(sd)
        cq=np.zeros(m,np.complex64); cq[ii.astype(np.int64)]=vq; cq=cq.reshape(shp)
        P[:,:,b*B:(b+1)*B]=inverse(cq,B)
        inds.append(ii); vals.append(q); scales.append(s16)
    idx_z=CCTX.compress(np.concatenate(inds).astype('<u4',copy=False).tobytes())
    val_z=CCTX.compress(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes())
    scl_z=CCTX.compress(np.asarray(scales,dtype='<f2').tobytes())

    Ccorr=np.rint((X-P)/step).astype(np.int32)
    corr_options=[]
    code,zb=pack_int(Ccorr); corr_options.append((len(zb),0,code,zb,b''))
    K=Ccorr.copy(); K[:,:,1:]-=Ccorr[:,:,:-1]
    code,zb=pack_int(K); corr_options.append((len(zb),1,code,zb,b''))
    mask=K!=0; packed=np.packbits(mask.reshape(-1),bitorder='little'); mask_z=CCTX.compress(packed.tobytes())
    code,valcorr_z=pack_int(K[mask]); corr_options.append((len(mask_z)+len(valcorr_z),2,code,mask_z,valcorr_z))
    _,cmode,dcode,ca,cb=min(corr_options,key=lambda t:t[0])
    header=struct.pack(HDR,MAGIC,1,*X.shape,float(eps),B,N,cmode,dcode,len(idx_z),len(val_z),len(scl_z),len(ca),len(cb))
    blob=header+idx_z+val_z+scl_z+ca+cb
    return blob,N,float(mask.mean())

def decode(blob):
    if len(blob)<HS: raise RuntimeError('short container')
    fields=struct.unpack(HDR,blob[:HS]); magic,ver,nx,ny,nt,ee,B,N,cmode,dcode,*lens=fields
    if magic!=MAGIC or ver!=1: raise RuntimeError('bad container')
    p=HS; streams=[]
    for L in lens:
        streams.append(blob[p:p+L]);p+=L
    if p!=len(blob): raise RuntimeError('container length mismatch')
    idx_z,val_z,scl_z,ca,cb=streams; nblk=nt//B; shp=(nx,ny,B//2+1); m=int(np.prod(shp)); count=nblk*N
    idx=np.frombuffer(DCTX.decompress(idx_z),dtype='<u4',count=count)
    q=np.frombuffer(DCTX.decompress(val_z),dtype=np.int8,count=count*2).reshape(count,2)
    scales=np.frombuffer(DCTX.decompress(scl_z),dtype='<f2',count=nblk)
    if idx.size!=count or q.shape[0]!=count or scales.size!=nblk: raise RuntimeError('model stream mismatch')
    P=np.empty((nx,ny,nt),np.float32)
    for b in range(nblk):
        sl=slice(b*N,(b+1)*N); ii=idx[sl].astype(np.int64); qq=q[sl]; sd=np.float32(scales[b])
        v=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*sd
        cq=np.zeros(m,np.complex64); cq[ii]=v
        P[:,:,b*B:(b+1)*B]=inverse(cq.reshape(shp),B)
    total=nx*ny*nt
    if cmode==0:
        C=unpack_int(ca,dcode,total).reshape(nx,ny,nt)
    elif cmode==1:
        K=unpack_int(ca,dcode,total).reshape(nx,ny,nt); C=np.cumsum(K,axis=2,dtype=np.int32)
    elif cmode==2:
        mb=DCTX.decompress(ca); mask=np.unpackbits(np.frombuffer(mb,np.uint8),bitorder='little',count=total).astype(bool)
        nv=int(mask.sum()); vv=unpack_int(cb,dcode,nv); K=np.zeros(total,np.int32);K[mask]=vv;C=np.cumsum(K.reshape(nx,ny,nt),axis=2,dtype=np.int32)
    else: raise RuntimeError('bad correction mode')
    return P+C.astype(np.float32)*np.float32(2.0*ee)

rows=[]
fracs=[0.0005,0.001,0.002,0.004,0.008,0.016,0.032]
for B in [128,256,512]:
    specs=[forward(X[:,:,t:t+B]) for t in range(0,X.shape[2],B)]
    for frac in fracs:
        blob,N,event=encode_candidate(B,frac,specs); R=decode(blob); me=float(np.max(np.abs(X-R)))
        row={'B':B,'frac':frac,'N_per_block':N,'bytes':len(blob),'ratio':raw/len(blob),'event_fraction':event,'maxerr':me,'valid':bool(me<=eps*(1+2e-6))}
        rows.append(row); print(json.dumps(row),flush=True)

cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps)
bb,_=sz.compress(np.ascontiguousarray(X),cfg); RR,_=sz.decompress(bb,np.float32,X.shape)
sz3={'bytes':int(bb.size),'ratio':raw/int(bb.size),'maxerr':float(np.max(np.abs(X-RR)))}
rows.sort(key=lambda r:r['ratio'],reverse=True)
out={'shape':list(X.shape),'eps':eps,'raw_bytes':raw,'header_bytes':HS,'top':rows[:21],'sz3':sz3,'known_hpez_q4_ratio':35.74244128574837,'known_hpez_gamma12_ratio':35.95461851348629}
json.dump(out,open('forge_topn_kxyf_results.json','w'),indent=2)
print('BEST',json.dumps(rows[:10],indent=2),flush=True); print('SZ3',json.dumps(sz3),flush=True)
