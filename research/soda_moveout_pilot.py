import json, os, struct, sys
import numpy as np
import segyio, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()
VELS=[0.,1200.,1600.,2000.,2500.,3200.,4000.,5000.,6500.]
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
PH='<IHHIBBBB5Q'; PHS=struct.calcsize(PH)

def coord_scale(s):
    s=np.asarray(s,dtype=np.float64)
    return np.where(s<0,1.0/np.maximum(1.0,-s),np.where(s>0,s,1.0))

def pack_int(a):
    a=np.asarray(a); lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
    return code,ZC.compress(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())

def unpack_int(blob,code,n):
    a=np.frombuffer(ZD.decompress(blob),dtype=IDT[code],count=n)
    if a.size!=n: raise RuntimeError('int stream mismatch')
    return a.astype(np.int32,copy=False)

def diff1(a,axis):
    o=a.copy(); s1=[slice(None)]*a.ndim; s0=[slice(None)]*a.ndim
    s1[axis]=slice(1,None);s0[axis]=slice(None,-1);o[tuple(s1)]=a[tuple(s1)]-a[tuple(s0)];return o

def corr_options(Q):
    Kt=diff1(Q,1); Kx=diff1(Q,0); Kl=diff1(Kt,0)
    cand=[]
    for mode,K in [(0,Q),(1,Kt),(2,Kx),(3,Kl)]:
        dc,a=pack_int(K); cand.append((len(a),mode,0,dc,a,b'',float(np.mean(K!=0))))
        m=K!=0; mz=ZC.compress(np.packbits(m.ravel(),bitorder='little').tobytes()); dc2,v=pack_int(K[m]); cand.append((len(mz)+len(v),mode,1,dc2,mz,v,float(m.mean())))
    return min(cand,key=lambda x:x[0])

def corr_inverse(K,mode):
    if mode==0:return K
    if mode==1:return np.cumsum(K,axis=1,dtype=np.int32)
    if mode==2:return np.cumsum(K,axis=0,dtype=np.int32)
    if mode==3:return np.cumsum(np.cumsum(K,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
    raise RuntimeError('bad correction mode')

def warp_forward(X,offset,dt,v):
    if v<=0:return X.copy()
    nr,nt=X.shape; tau=np.arange(nt,dtype=np.float64)*dt; Y=np.zeros_like(X)
    for i,x in enumerate(offset):
        t=np.sqrt(tau*tau+(float(x)/v)**2); q=t/dt; j=np.floor(q).astype(np.int64); a=(q-j).astype(np.float32); good=j<nt-1
        jj=j[good]; Y[i,good]=X[i,jj]*(1-a[good])+X[i,jj+1]*a[good]
    return Y

def warp_inverse(Y,offset,dt,v):
    if v<=0:return Y.copy()
    nr,nt=Y.shape; t=np.arange(nt,dtype=np.float64)*dt; X=np.zeros_like(Y)
    for i,x in enumerate(offset):
        rad=t*t-(float(x)/v)**2; good=rad>=0; tau=np.sqrt(np.maximum(rad,0)); q=tau/dt; j=np.floor(q).astype(np.int64); a=(q-j).astype(np.float32); good &= (j<nt-1)
        jj=j[good]; X[i,good]=Y[i,jj]*(1-a[good])+Y[i,jj+1]*a[good]
    return X

def fwd(W):return np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
def inv(F,B):return np.fft.irfft(np.fft.ifft(F,axis=0),n=B,axis=1).real.astype(np.float32)

def encode_panel(X,offset,dt,eps,B,frac,vidx,specs):
    nr,nt=X.shape;nblk=(nt+B-1)//B; M=specs[0].size;N=max(1,min(M,int(round(frac*M)))); inds=[]; vals=[]; scales=[]; Yp=np.zeros_like(X)
    for b,F in enumerate(specs):
        flat=F.reshape(-1); ii=np.argpartition(np.abs(flat),-N)[-N:];ii=np.sort(ii).astype(np.uint32);vv=flat[ii]
        comp=np.stack([vv.real,vv.imag],axis=1);sc=max(float(np.max(np.abs(comp)))/127.,1e-30);sc16=np.float16(sc);sd=np.float32(sc16);q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8)
        vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd;fq=np.zeros(M,np.complex64);fq[ii.astype(np.int64)]=vq;R=inv(fq.reshape(F.shape),B);t0=b*B;m=min(B,nt-t0);Yp[:,t0:t0+m]=R[:,:m]
        inds.append(ii);vals.append(q);scales.append(sc16)
    iz=ZC.compress(np.concatenate(inds).astype('<u4',copy=False).tobytes());vz=ZC.compress(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes());szb=ZC.compress(np.asarray(scales,dtype='<f2').tobytes())
    P=warp_inverse(Yp,offset,dt,VELS[vidx]);Q=np.rint((X-P)/(2*eps)).astype(np.int32);_,cm,sp,dc,ca,cb,event=corr_options(Q)
    header=struct.pack(PH,nr,nt,B,N,nblk,vidx,(sp<<4)|dc,cm,len(iz),len(vz),len(szb),len(ca),len(cb))
    return header+iz+vz+szb+ca+cb,{'model_bytes':PHS+len(iz)+len(vz)+len(szb),'corr_bytes':len(ca)+len(cb),'corr_mode':cm,'corr_sparse':bool(sp),'event_fraction':event,'N':N}

def decode_panel(blob,offset,dt,eps):
    f=struct.unpack(PH,blob[:PHS]);nr,nt,B,N,nblk,vidx,flags,cm,*lens=f;dc=flags&15;sp=(flags>>4)&1;p=PHS;ss=[]
    for L in lens:ss.append(blob[p:p+L]);p+=L
    iz,vz,szb,ca,cb=ss;count=nblk*N;shape=(nr,B//2+1);M=int(np.prod(shape));ii=np.frombuffer(ZD.decompress(iz),dtype='<u4',count=count);q=np.frombuffer(ZD.decompress(vz),dtype=np.int8,count=2*count).reshape(count,2);sc=np.frombuffer(ZD.decompress(szb),dtype='<f2',count=nblk);Yp=np.zeros((nr,nt),np.float32)
    for b in range(nblk):
        sl=slice(b*N,(b+1)*N);jj=ii[sl].astype(np.int64);qq=q[sl];vv=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*np.float32(sc[b]);F=np.zeros(M,np.complex64);F[jj]=vv;R=inv(F.reshape(shape),B);t0=b*B;m=min(B,nt-t0);Yp[:,t0:t0+m]=R[:,:m]
    P=warp_inverse(Yp,offset,dt,VELS[vidx]);total=nr*nt
    if sp:
        m=np.unpackbits(np.frombuffer(ZD.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(m.sum()));K=np.zeros(total,np.int32);K[m]=vv;K=K.reshape(nr,nt)
    else:K=unpack_int(ca,dc,total).reshape(nr,nt)
    Q=corr_inverse(K,cm);return P+Q.astype(np.float32)*np.float32(2*eps)

def sz3_bytes(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);bb,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(bb,np.float32,A.shape);return int(bb.size),float(np.max(np.abs(A-R)))

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.float64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.float64);sx=np.asarray(f.attributes(segyio.TraceField.SourceX)[:],np.float64);sy=np.asarray(f.attributes(segyio.TraceField.SourceY)[:],np.float64);dt=float(segyio.tools.dt(f))*1e-6
        try:sc=np.asarray(f.attributes(segyio.TraceField.SourceGroupScalar)[:],np.float64)
        except Exception:sc=np.ones(len(X),np.float64)
    scale=coord_scale(sc);gx*=scale;gy*=scale;sx*=scale;sy*=scale
    groups={};extra=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:extra.append(i);continue
        groups.setdefault((round(float(x),6),round(float(y),6)),[]).append(i)
    counts=np.array([len(v) for v in groups.values()]);C=int(np.bincount(counts).argmax()); keys=list(groups); src=np.array([np.median(sx[np.isfinite(sx)&(sx!=0)]),np.median(sy[np.isfinite(sy)&(sy!=0)])]); rec=np.asarray(keys,float); off=np.linalg.norm(rec-src,axis=1)
    orders={'receiver':np.arange(len(keys)), 'offset':np.argsort(off)}; layouts={}
    for name,o in orders.items():
        panels=[];offs=[]
        for c in range(C):
            ids=[groups[keys[j]][c] for j in o];panels.append(X[np.asarray(ids)]);offs.append(off[o])
        layouts[name]=(panels,offs)
    return X,layouts,X[np.asarray(extra)] if extra else np.empty((0,X.shape[1]),np.float32),dt,{'source_xy':src.tolist(),'offset_min':float(off.min()),'offset_max':float(off.max()),'offset_median':float(np.median(off)),'receiver_groups':len(keys),'components':C,'extra_traces':len(extra)}

def bench(path):
    X,layouts,extra,dt,geom=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes
    sb,se=sz3_bytes(X,eps);extra_bytes=0;extra_err=0.
    if extra.size:extra_bytes,extra_err=sz3_bytes(extra,eps)
    rows=[];B=512
    for lname,(panels,offs) in layouts.items():
      for vidx,v in enumerate(VELS):
        allspec=[]
        for panel,off in zip(panels,offs):
            Y=warp_forward(panel,off,dt,v);spec=[]
            for t0 in range(0,Y.shape[1],B):
                m=min(B,Y.shape[1]-t0);W=np.zeros((Y.shape[0],B),np.float32);W[:,:m]=Y[:,t0:t0+m];spec.append(fwd(W))
            allspec.append(spec)
        for frac in [0.0005,0.001,0.002,0.004]:
            blobs=[];met=[];me=0.
            for panel,off,spec in zip(panels,offs,allspec):
                b,m=encode_panel(panel,off,dt,eps,B,frac,vidx,spec);R=decode_panel(b,off,dt,eps);me=max(me,float(np.max(np.abs(panel-R))));blobs.append(b);met.append(m)
            total=32+sum(map(len,blobs))+extra_bytes; row={'layout':lname,'velocity_mps':v,'frac':frac,'bytes':total,'ratio':raw/total,'maxerr':max(me,extra_err),'valid':bool(max(me,extra_err)<=eps*(1+5e-6)),'model_bytes':sum(m['model_bytes'] for m in met),'corr_bytes':sum(m['corr_bytes'] for m in met),'extra_bytes':extra_bytes,'event_fraction':float(np.mean([m['event_fraction'] for m in met]))};rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'dt_s':dt,'geometry':geom,'top':rows[:30],'sz3':{'bytes':sb,'ratio':raw/sb,'maxerr':se}};json.dump(out,open('soda_moveout_pilot.json','w'),indent=2);print('BEST',json.dumps(rows[:12],indent=2));print('SZ3',out['sz3'])

bench(sys.argv[1])
