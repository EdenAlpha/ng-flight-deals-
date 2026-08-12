import json, os, struct, sys
import numpy as np
import segyio, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

C=zstd.ZstdCompressor(level=19); D=zstd.ZstdDecompressor()
PANEL_HDR='<IIIIIBBQQQQQ'; PHS=struct.calcsize(PANEL_HDR)
MAGIC=b'SODATPN1'; TOP_HDR='<8sdII'; THS=struct.calcsize(TOP_HDR)
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

def z(b): return C.compress(b)
def pack_int(a):
    a=np.asarray(a); lo=int(a.min()) if a.size else 0; hi=int(a.max()) if a.size else 0
    code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
    return code,z(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())
def unpack_int(blob,code,n):
    a=np.frombuffer(D.decompress(blob),dtype=IDT[code],count=n)
    if a.size!=n: raise RuntimeError('int stream mismatch')
    return a.astype(np.int32,copy=False)

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy()
        try: gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64)
        except Exception: gx=np.zeros(X.shape[0],np.int64)
        try: gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
        except Exception: gy=np.zeros(X.shape[0],np.int64)
        dt=int(segyio.tools.dt(f))
    return X,gx,gy,dt

def layouts(X,gx,gy):
    out={'file':[X]}; n=X.shape[0]
    valid=(gx.size==n and gy.size==n and np.count_nonzero(gx)+np.count_nonzero(gy)>n//2)
    if not valid: return out,{'coords_valid':False}
    ii=np.arange(n); order=np.lexsort((ii,gx,gy)); out['geo']=[X[order]]
    groups={}
    for k,i in zip(zip(gx.tolist(),gy.tolist()),range(n)): groups.setdefault(k,[]).append(i)
    counts=np.asarray([len(v) for v in groups.values()],np.int32); mode=int(np.bincount(counts).argmax()) if counts.size else 1
    if 2<=mode<=8 and np.mean(counts==mode)>=0.5:
        keys=sorted(groups); panels=[]
        for r in range(int(counts.max())):
            ids=[groups[k][r] for k in keys if len(groups[k])>r]
            if ids: panels.append(X[np.asarray(ids,np.int64)])
        if sum(p.shape[0] for p in panels)==n: out['component_geo']=panels
    return out,{'coords_valid':True,'unique_receivers':len(groups),'multiplicity_mode':mode,'mode_fraction':float(np.mean(counts==mode)),'max_multiplicity':int(counts.max())}

def fwd(W): return np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
def inv(F,B): return np.fft.irfft(np.fft.ifft(F,axis=0),n=B,axis=1).real.astype(np.float32)

def encode_panel(X,eps,B,frac):
    nr,nt=X.shape; nblk=(nt+B-1)//B; step=2.0*eps
    idxs=[]; vals=[]; scales=[]; P=np.zeros_like(X); N=None
    for b in range(nblk):
        t0=b*B; m=min(B,nt-t0); W=np.zeros((nr,B),np.float32); W[:,:m]=X[:,t0:t0+m]
        F=fwd(W); flat=F.reshape(-1); NN=max(1,min(flat.size,int(round(frac*flat.size))))
        if N is None: N=NN
        if NN!=N: raise RuntimeError('N changed')
        ix=np.argpartition(np.abs(flat),-N)[-N:]; ix=np.sort(ix).astype(np.uint32); v=flat[ix]
        comp=np.stack([v.real,v.imag],axis=1); sc=max(float(np.max(np.abs(comp)))/127.0,1e-30); sc16=np.float16(sc); sd=np.float32(sc16)
        q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8)
        vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd
        fq=np.zeros(flat.size,np.complex64); fq[ix.astype(np.int64)]=vq
        R=inv(fq.reshape(F.shape),B); P[:,t0:t0+m]=R[:,:m]
        idxs.append(ix); vals.append(q); scales.append(sc16)
    iz=z(np.concatenate(idxs).astype('<u4',copy=False).tobytes()); vz=z(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes()); szb=z(np.asarray(scales,dtype='<f2').tobytes())
    Q=np.rint((X-P)/step).astype(np.int32)
    opts=[]
    dc,a=pack_int(Q);opts.append((len(a),0,dc,a,b''))
    K=Q.copy();K[:,1:]-=Q[:,:-1];dc,a=pack_int(K);opts.append((len(a),1,dc,a,b''))
    mask=K!=0;mz=z(np.packbits(mask.ravel(),bitorder='little').tobytes());dc,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),2,dc,mz,vv))
    _,cm,dc,ca,cb=min(opts,key=lambda q:q[0])
    h=struct.pack(PANEL_HDR,nr,nt,B,N,nblk,cm,dc,len(iz),len(vz),len(szb),len(ca),len(cb))
    return h+iz+vz+szb+ca+cb,float(mask.mean())

def decode_panel(blob,eps):
    vals=struct.unpack(PANEL_HDR,blob[:PHS]);nr,nt,B,N,nblk,cm,dc,*lens=vals;p=PHS;ss=[]
    for L in lens:ss.append(blob[p:p+L]);p+=L
    if p!=len(blob):raise RuntimeError('panel length mismatch')
    iz,vz,szb,ca,cb=ss; count=nblk*N
    ix=np.frombuffer(D.decompress(iz),dtype='<u4',count=count);q=np.frombuffer(D.decompress(vz),dtype=np.int8,count=2*count).reshape(count,2);sc=np.frombuffer(D.decompress(szb),dtype='<f2',count=nblk)
    if ix.size!=count or q.shape[0]!=count or sc.size!=nblk:raise RuntimeError('model mismatch')
    P=np.zeros((nr,nt),np.float32); shape=(nr,B//2+1); M=int(np.prod(shape))
    for b in range(nblk):
        sl=slice(b*N,(b+1)*N);ii=ix[sl].astype(np.int64);qq=q[sl];v=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*np.float32(sc[b]);F=np.zeros(M,np.complex64);F[ii]=v;R=inv(F.reshape(shape),B);t0=b*B;m=min(B,nt-t0);P[:,t0:t0+m]=R[:,:m]
    total=nr*nt
    if cm==0: Q=unpack_int(ca,dc,total).reshape(nr,nt)
    elif cm==1: Q=np.cumsum(unpack_int(ca,dc,total).reshape(nr,nt),axis=1,dtype=np.int32)
    elif cm==2:
        mask=np.unpackbits(np.frombuffer(D.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;Q=np.cumsum(K.reshape(nr,nt),axis=1,dtype=np.int32)
    else: raise RuntimeError('bad correction mode')
    return P+Q.astype(np.float32)*np.float32(2.0*eps)

def encode_layout(panels,eps,B,frac,layout_code):
    chunks=[];events=[]
    for p in panels:
        b,e=encode_panel(p,eps,B,frac);chunks.append(b);events.append(e)
    head=struct.pack(TOP_HDR,MAGIC,float(eps),len(chunks),layout_code);lens=b''.join(struct.pack('<Q',len(q)) for q in chunks)
    return head+lens+b''.join(chunks),float(np.average(events,weights=[q.size for q in panels]))
def decode_layout(blob):
    magic,eps,npan,lc=struct.unpack(TOP_HDR,blob[:THS]);
    if magic!=MAGIC:raise RuntimeError('bad magic')
    p=THS;lens=[]
    for _ in range(npan):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    out=[]
    for L in lens:out.append(decode_panel(blob[p:p+L],eps));p+=L
    if p!=len(blob):raise RuntimeError('top length mismatch')
    return out,eps,lc

def sz3_layout(panels,eps):
    total=0;mx=0.0
    for X in panels:
        cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);bb,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(bb,np.float32,X.shape);total+=int(bb.size);mx=max(mx,float(np.max(np.abs(X-R))))
    return total,mx

def bench(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;ls,geom=layouts(X,gx,gy);rows=[];baselines=[]
    for li,(lname,panels) in enumerate(ls.items()):
        sb,se=sz3_layout(panels,eps);baselines.append({'layout':lname,'bytes':sb,'ratio':raw/sb,'maxerr':se})
        for B in [256,512,1024,2048]:
            for frac in [0.001,0.002,0.004,0.008,0.016,0.032]:
                blob,event=encode_layout(panels,eps,B,frac,li);R,ee,_=decode_layout(blob);me=max(float(np.max(np.abs(a-b))) for a,b in zip(panels,R));rows.append({'layout':lname,'B':B,'frac':frac,'bytes':len(blob),'ratio':raw/len(blob),'event_fraction':event,'maxerr':me,'valid':bool(me<=eps*(1+3e-6))})
    rows.sort(key=lambda r:r['ratio'],reverse=True);baselines.sort(key=lambda r:r['ratio'],reverse=True)
    return {'file':os.path.basename(path),'shape':list(X.shape),'dt_us':dt,'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows[:20],'sz3':baselines}

files=sys.argv[1:]
if not files: raise SystemExit('give SEG-Y files')
out={'shots':[]}
for f in files:
    print('BENCH',f,flush=True);r=bench(f);out['shots'].append(r);print(json.dumps({'file':r['file'],'best':r['top'][0],'sz3':r['sz3'][0]},indent=2),flush=True)
json.dump(out,open('soda_raw_topn_results.json','w'),indent=2)
