import json, os, struct, sys
import numpy as np
import segyio, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()
MAGIC=b'SODAGRD1'; HDR='<8sHHHHIIdIIBB6Q'; HS=struct.calcsize(HDR)
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

def pack_int(a):
    lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
    return code,ZC.compress(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())

def unpack_int(blob,code,n):
    a=np.frombuffer(ZD.decompress(blob),dtype=IDT[code],count=n)
    if a.size!=n: raise RuntimeError('integer stream length mismatch')
    return a.astype(np.int32,copy=False)

def d1(a,axis):
    o=a.copy(); s1=[slice(None)]*a.ndim; s0=[slice(None)]*a.ndim
    s1[axis]=slice(1,None); s0[axis]=slice(0,-1); o[tuple(s1)]=a[tuple(s1)]-a[tuple(s0)]
    return o

def corr_transform(Q,mode):
    axes={0:(),1:(3,),2:(2,),3:(1,),4:(3,2,1),5:(0,3),6:(0,3,2,1)}[mode]
    K=Q
    for ax in axes: K=d1(K,ax)
    return K,axes

def corr_inverse(K,axes):
    Q=K
    for ax in reversed(axes): Q=np.cumsum(Q,axis=ax,dtype=np.int32)
    return Q

def load_grid(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy()
        gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64)
        gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
        dt=int(segyio.tools.dt(f))
    groups={}
    for i,k in enumerate(zip(gx.tolist(),gy.tolist())): groups.setdefault(k,[]).append(i)
    counts=np.asarray([len(v) for v in groups.values()],np.int32)
    mode=int(np.bincount(counts).argmax()) if counts.size else 0
    ux=np.unique(gx); uy=np.unique(gy); cartesian=(len(ux)*len(uy)==len(groups))
    if mode<2 or mode>8 or not cartesian:
        raise RuntimeError(f'not a compact Cartesian multicomponent receiver grid: mode={mode} ux={len(ux)} uy={len(uy)} groups={len(groups)}')
    xi={int(v):i for i,v in enumerate(sorted(ux.tolist()))}; yi={int(v):i for i,v in enumerate(sorted(uy.tolist()))}
    C=mode; ny=len(uy); nx=len(ux); nt=X.shape[1]
    V=np.zeros((C,ny,nx,nt),np.float32); present=np.zeros((C,ny,nx),bool); trace_map=[]
    for (xx,yy),ids in groups.items():
        j=yi[int(yy)]; i=xi[int(xx)]
        for c,tid in enumerate(ids[:C]):
            V[c,j,i]=X[tid]; present[c,j,i]=True; trace_map.append((tid,c,j,i))
    trace_map.sort()
    return X,V,present,trace_map,dt,{'unique_x':nx,'unique_y':ny,'unique_receivers':len(groups),'component_mode':C,'mode_fraction':float(np.mean(counts==mode)),'missing_component_traces':int(C*ny*nx-X.shape[0]),'cartesian':bool(cartesian)}

def fwd(W): return np.fft.rfftn(W,axes=(0,1,2))
def inv(F,shape): return np.fft.irfftn(F,s=shape,axes=(0,1,2)).real.astype(np.float32)

def encode(V,eps,B,frac,specs):
    C,ny,nx,nt=V.shape; nblk=(nt+B-1)//B; shp=specs[0][0].shape; M=int(np.prod(shp)); N=max(1,min(M,int(round(frac*M))))
    P=np.zeros_like(V); inds=[]; vals=[]; scales=[]
    for c in range(C):
        for b in range(nblk):
            F=specs[c][b]; flat=F.reshape(-1); ii=np.argpartition(np.abs(flat),-N)[-N:]; ii=np.sort(ii).astype(np.uint32)
            vv=flat[ii]; comp=np.stack([vv.real,vv.imag],axis=1); sc=max(float(np.max(np.abs(comp)))/127.0,1e-30); sc16=np.float16(sc); sd=np.float32(sc16)
            q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8); vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd
            fq=np.zeros(M,np.complex64); fq[ii.astype(np.int64)]=vq; R=inv(fq.reshape(shp),(ny,nx,B)); t0=b*B; m=min(B,nt-t0); P[c,:,:,t0:t0+m]=R[:,:,:m]
            inds.append(ii); vals.append(q); scales.append(sc16)
    iz=ZC.compress(np.concatenate(inds).astype('<u4',copy=False).tobytes()); vz=ZC.compress(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes()); szb=ZC.compress(np.asarray(scales,dtype='<f2').tobytes())
    Q=np.rint((V-P)/(2.0*eps)).astype(np.int32)
    opts=[]
    for mode in range(7):
        K,axes=corr_transform(Q,mode); dc,dense=pack_int(K); opts.append((len(dense),mode,0,dc,dense,b'',float(np.mean(K!=0))))
        mask=K!=0; mz=ZC.compress(np.packbits(mask.reshape(-1),bitorder='little').tobytes()); dc2,vz2=pack_int(K[mask]); opts.append((len(mz)+len(vz2),mode,1,dc2,mz,vz2,float(mask.mean())))
    _,cmode,sparse,dcode,ca,cb,event=min(opts,key=lambda x:x[0])
    lens=(len(iz),len(vz),len(szb),len(ca),len(cb),0)
    head=struct.pack(HDR,MAGIC,1,C,ny,nx,nt,B,float(eps),N,nblk,cmode,(sparse<<4)|dcode,*lens)
    blob=head+iz+vz+szb+ca+cb
    return blob,{'N':N,'model_bytes':len(iz)+len(vz)+len(szb)+HS,'corr_bytes':len(ca)+len(cb),'corr_mode':cmode,'corr_sparse':bool(sparse),'event_fraction':event}

def decode(blob):
    f=struct.unpack(HDR,blob[:HS]); magic,ver,C,ny,nx,nt,B,eps,N,nblk,cmode,flags,*lens=f
    if magic!=MAGIC or ver!=1: raise RuntimeError('bad container')
    dcode=flags&15; sparse=(flags>>4)&1; p=HS; ss=[]
    for L in lens:
        ss.append(blob[p:p+L]); p+=L
    if p!=len(blob): raise RuntimeError('container length mismatch')
    iz,vz,szb,ca,cb,_=ss; count=C*nblk*N; shp=(ny,nx,B//2+1); M=int(np.prod(shp))
    ii=np.frombuffer(ZD.decompress(iz),dtype='<u4',count=count); q=np.frombuffer(ZD.decompress(vz),dtype=np.int8,count=2*count).reshape(count,2); sc=np.frombuffer(ZD.decompress(szb),dtype='<f2',count=C*nblk)
    if ii.size!=count or q.shape[0]!=count or sc.size!=C*nblk: raise RuntimeError('model stream mismatch')
    P=np.zeros((C,ny,nx,nt),np.float32); k=0
    for c in range(C):
        for b in range(nblk):
            sl=slice(k*N,(k+1)*N); jj=ii[sl].astype(np.int64); qq=q[sl]; v=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*np.float32(sc[k]); fq=np.zeros(M,np.complex64); fq[jj]=v; R=inv(fq.reshape(shp),(ny,nx,B)); t0=b*B; m=min(B,nt-t0); P[c,:,:,t0:t0+m]=R[:,:,:m]; k+=1
    total=C*ny*nx*nt
    if sparse:
        mask=np.unpackbits(np.frombuffer(ZD.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool); vv=unpack_int(cb,dcode,int(mask.sum())); K=np.zeros(total,np.int32); K[mask]=vv; K=K.reshape(C,ny,nx,nt)
    else: K=unpack_int(ca,dcode,total).reshape(C,ny,nx,nt)
    axes={0:(),1:(3,),2:(2,),3:(1,),4:(3,2,1),5:(0,3),6:(0,3,2,1)}[cmode]; Q=corr_inverse(K,axes)
    return P+Q.astype(np.float32)*np.float32(2.0*eps)

def sz3_array(A,eps):
    cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps); bb,_=sz.compress(np.ascontiguousarray(A),cfg); R,_=sz.decompress(bb,np.float32,A.shape); return int(bb.size),R

def bench(path):
    X,V,present,tmap,dt,geom=load_grid(path); std=float(X.astype(np.float64).std()); eps=.1*std; raw=X.nbytes; rows=[]
    # Fair baselines: original file-order 2-D and geometry-aware component 3-D grids.
    b0,R0=sz3_array(X,eps); base=[{'layout':'file2d','bytes':b0,'ratio':raw/b0,'maxerr':float(np.max(np.abs(X-R0)))}]
    bg=0; mg=0.0
    for c in range(V.shape[0]):
        bb,RR=sz3_array(V[c],eps); bg+=bb; m=present[c]; mg=max(mg,float(np.max(np.abs(V[c][m]-RR[m]))))
    base.append({'layout':'grid3d_components','bytes':bg,'ratio':raw/bg,'maxerr':mg})
    for B in [512,1024]:
        nblk=(V.shape[3]+B-1)//B; specs=[]
        for c in range(V.shape[0]):
            cs=[]
            for b in range(nblk):
                t0=b*B; m=min(B,V.shape[3]-t0); W=np.zeros((V.shape[1],V.shape[2],B),np.float32); W[:,:,:m]=V[c,:,:,t0:t0+m]; cs.append(fwd(W))
            specs.append(cs)
        for frac in [0.0005,0.001,0.002,0.004]:
            blob,meta=encode(V,eps,B,frac,specs); RR=decode(blob); me=0.0
            for c in range(V.shape[0]):
                m=present[c]; me=max(me,float(np.max(np.abs(V[c][m]-RR[c][m]))))
            row={'B':B,'frac':frac,'bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),**meta}; rows.append(row); print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True); base.sort(key=lambda r:r['ratio'],reverse=True)
    return {'file':os.path.basename(path),'shape_file':list(X.shape),'shape_grid':list(V.shape),'dt_us':dt,'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows,'sz3':base}

out={'shots':[]}
for p in sys.argv[1:]:
    print('BENCH',p,flush=True); r=bench(p); out['shots'].append(r); print('BEST',json.dumps({'file':r['file'],'grid':r['top'][0],'sz3':r['sz3'][0],'geometry':r['geometry']},indent=2),flush=True)
json.dump(out,open('soda_grid_kxyf_results.json','w'),indent=2)
