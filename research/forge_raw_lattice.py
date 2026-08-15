import json,os,struct,sys,itertools
import numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

MAG=b'FRLAT001'; HDR='<8sBBBBIIQQ'; HS=struct.calcsize(HDR)
DT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

def i16(b,o):return int.from_bytes(b[o:o+2],'little',signed=True)
def u16(b,o):return int.from_bytes(b[o:o+2],'little',signed=False)
def i32(b,o):return int.from_bytes(b[o:o+4],'little',signed=True)
def scaled(v,s):return float(v)*(float(s) if s>0 else (1.0/float(-s) if s<0 else 1.0))
def dtype_code(a):
    lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0
    return 1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3

def load_segy(path):
    size=os.path.getsize(path);mm=np.memmap(path,np.uint8,'r')
    bh=bytes(mm[3200:3600]);dt=u16(bh,16);ns=u16(bh,20);fmt=u16(bh,24);fixed=u16(bh,302);ext=i16(bh,304);family_header_fallback=False
    if fmt!=5:
        fam_ns=16001;fam_dt=1000;fam_fmt=5;fam_st=240+4*fam_ns
        if not np.any(np.asarray(mm[:3600])) and size==3600+1747*fam_st:
            ns=fam_ns;dt=fam_dt;fmt=fam_fmt;fixed=0;ext=0;family_header_fallback=True
        else:raise RuntimeError(f'expected little-endian IEEE float format 5, got {fmt}')
    data0=3600+(ext if ext>0 else 0)*3200;st=240+4*ns
    if ns<=0 or dt<=0 or (size-data0)%st:raise RuntimeError(f'layout mismatch size={size} data0={data0} ns={ns} dt={dt} remainder={(size-data0)%st}')
    ntr=(size-data0)//st
    X=np.ndarray((ntr,ns),dtype='<f4',buffer=mm,offset=data0+240,strides=(st,4))
    gx=np.empty(ntr,np.float64);gy=np.empty(ntr,np.float64);sx=np.empty(ntr,np.float64);sy=np.empty(ntr,np.float64);offs=np.empty(ntr,np.int64)
    for i in range(ntr):
        o=data0+i*st;th=bytes(mm[o:o+240]);sc=i16(th,70);sx[i]=scaled(i32(th,72),sc);sy[i]=scaled(i32(th,76),sc);gx[i]=scaled(i32(th,80),sc);gy[i]=scaled(i32(th,84),sc);offs[i]=i32(th,36)
        tns=u16(th,114);tdt=u16(th,116)
        if tns not in (0,ns) or tdt not in (0,dt):raise RuntimeError(f'variable trace at {i}: ns={tns} dt={tdt}')
    return np.asarray(X,np.float32).copy(),gx,gy,sx,sy,offs,{'file_bytes':size,'ntr':int(ntr),'ns':int(ns),'dt_us':int(dt),'format':int(fmt),'fixed':int(fixed),'extended_headers':int(ext),'trace_bytes':int(st),'family_header_fallback':bool(family_header_fallback)}

def orders(gx,gy,sx,sy,offs):
    n=len(gx);idx=np.arange(n);out=[]
    def add(name,o):
        o=np.asarray(o,np.int64)
        if not any(np.array_equal(o,q[1]) for q in out):out.append((name,o))
    add('file',idx);add('x_y',np.lexsort((idx,gy,gx)));add('y_x',np.lexsort((idx,gx,gy)))
    pts=np.stack([gx,gy],1);cen=pts-pts.mean(0);cov=cen.T@cen/max(n,1);w,V=np.linalg.eigh(cov);u=V[:,np.argmax(w)];v=np.array([-u[1],u[0]]);a=cen@u;b=cen@v
    add('pca_line',np.lexsort((idx,a,b)));add('pca_along',np.lexsort((idx,b,a)))
    rs=np.sqrt((gx-sx)**2+(gy-sy)**2);add('radial',np.lexsort((idx,rs)));add('offset_header',np.lexsort((idx,offs)))
    return out,{'pca_eigenvalues':w.tolist(),'pca_axis':u.tolist(),'unique_receiver_coords':int(len(set(zip(gx.tolist(),gy.tolist())))),'unique_source_coords':int(len(set(zip(sx.tolist(),sy.tolist())))),'offset_min':int(offs.min()),'offset_max':int(offs.max())}

def pack2(c):
    n=c.size;pad=(-n)%4
    if pad:c=np.pad(c,(0,pad))
    q=c.reshape(-1,4).astype(np.uint8);return (q[:,0]|q[:,1]<<2|q[:,2]<<4|q[:,3]<<6).tobytes()
def unpack2(b,n):
    q=np.frombuffer(b,np.uint8);c=np.empty(q.size*4,np.uint8);c[0::4]=q&3;c[1::4]=(q>>2)&3;c[2::4]=(q>>4)&3;c[3::4]=(q>>6)&3;return c[:n]

def encode_rep(A,order_code,orient,rep,level=19):
    P=A if orient==0 else A.T;flat=np.ascontiguousarray(P).ravel();zc=zstd.ZstdCompressor(level=level);chunks=[];dc=dtype_code(flat)
    if rep==0:chunks=[zc.compress(flat.astype(DT[dc],copy=False).tobytes())]
    elif rep==1:
        m=flat!=0;vals=flat[m];dc=dtype_code(vals);chunks=[zc.compress(np.packbits(m,bitorder='little').tobytes()),zc.compress(vals.astype(DT[dc],copy=False).tobytes())]
    elif rep==2:
        codes=np.zeros(flat.size,np.uint8);codes[flat==1]=1;codes[flat==-1]=2;exc=(flat!=0)&(flat!=1)&(flat!=-1);codes[exc]=3;vals=flat[exc];dc=dtype_code(vals);chunks=[zc.compress(pack2(codes)),zc.compress(vals.astype(DT[dc],copy=False).tobytes())]
    else:raise ValueError(rep)
    h=struct.pack(HDR,MAG,1,order_code,orient,rep,A.shape[0],A.shape[1],dc,len(chunks));lens=b''.join(struct.pack('<Q',len(x)) for x in chunks);return h+lens+b''.join(chunks)

def decode_rep(blob):
    magic,ver,oc,orient,rep,nr,nt,dc,nc=struct.unpack(HDR,blob[:HS])
    if magic!=MAG or ver!=1:raise RuntimeError('bad codec header')
    p=HS;lens=[]
    for _ in range(nc):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    fs=[]
    for L in lens:fs.append(blob[p:p+L]);p+=L
    if p!=len(blob):raise RuntimeError('stream length')
    shape=(nr,nt) if orient==0 else (nt,nr);n=nr*nt
    if rep==0:flat=np.frombuffer(zstd.ZstdDecompressor().decompress(fs[0]),dtype=DT[dc],count=n).astype(np.int32)
    elif rep==1:
        D=zstd.ZstdDecompressor();m=np.unpackbits(np.frombuffer(D.decompress(fs[0]),np.uint8),bitorder='little',count=n).astype(bool);vals=np.frombuffer(D.decompress(fs[1]),dtype=DT[dc],count=int(m.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[m]=vals
    else:
        D=zstd.ZstdDecompressor();codes=unpack2(D.decompress(fs[0]),n);exc=codes==3;vals=np.frombuffer(D.decompress(fs[1]),dtype=DT[dc],count=int(exc.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[codes==1]=1;flat[codes==2]=-1;flat[exc]=vals
    A=flat.reshape(shape);return int(oc),int(orient),(A if orient==0 else A.T)

def sz3_bytes(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(b,np.float32,A.shape);return int(b.size),float(np.max(np.abs(A-R)))

path=sys.argv[1];X,gx,gy,sx,sy,offs,layout=load_segy(path);raw=X.nbytes;std=float(X.astype(np.float64).std());public_eps=.1*std;internal_eps=public_eps*(1-1e-4);step=2*internal_eps
ordlist,gdiag=orders(gx,gy,sx,sy,offs);Q=np.rint(X.astype(np.float64)/step).astype(np.int32);K=np.empty_like(Q);K[:,0]=Q[:,0];K[:,1:]=Q[:,1:]-Q[:,:-1]
rows=[]
for oc,(name,o) in enumerate(ordlist):
    KO=K[o]
    for orient in (0,1):
      for rep in (1,2):
        b=encode_rep(KO,oc,orient,rep,19);roc,ro,R=decode_rep(b)
        if roc!=oc or ro!=orient or not np.array_equal(R,KO):raise RuntimeError('integer decode mismatch')
        rows.append({'bytes':len(b),'order':name,'order_code':oc,'orient':'trace_time' if orient==0 else 'time_trace','rep':'sparse' if rep==1 else 'ternary','level':19,'blob':b})
for oc in range(min(3,len(ordlist))):
    name,o=ordlist[oc];KO=K[o]
    for orient in (0,1):
        b=encode_rep(KO,oc,orient,0,19);_,_,R=decode_rep(b)
        if not np.array_equal(R,KO):raise RuntimeError('dense decode mismatch')
        rows.append({'bytes':len(b),'order':name,'order_code':oc,'orient':'trace_time' if orient==0 else 'time_trace','rep':'raw','level':19,'blob':b})
rows.sort(key=lambda r:r['bytes']);best=rows[0];oc=best['order_code'];o=ordlist[oc][1];_,orient,RKO=decode_rep(best['blob']);RK=np.empty_like(K);RK[o]=RKO;RQ=np.cumsum(RK,axis=1,dtype=np.int32);recon=RQ.astype(np.float32)*np.float32(2*internal_eps);me=float(np.max(np.abs(X-recon)))
szrows=[]
for name,o in ordlist:
    bb,mm=sz3_bytes(X[o],public_eps);szrows.append({'order':name,'bytes':bb,'ratio':raw/bb,'maxerr':mm})
szrows.sort(key=lambda r:r['bytes'])
vals,counts=np.unique(K,return_counts=True);ii=np.argsort(counts)[::-1]
out={'file':os.path.basename(path),'layout':layout,'shape':list(X.shape),'raw_sample_bytes':int(raw),'std':std,'public_eps':public_eps,'internal_eps':internal_eps,'geometry':gdiag,'K_nonzero_fraction':float(np.mean(K!=0)),'K_top_values':[{'v':int(vals[j]),'count':int(counts[j])} for j in ii[:12]],'codec_best':{k:v for k,v in best.items() if k!='blob'},'codec_ratio':float(raw/best['bytes']),'codec_maxerr':me,'codec_valid':bool(me<=public_eps),'top_candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows[:20]],'sz3_best':szrows[0],'sz3_candidates':szrows,'gain_vs_best_sz3':float((raw/best['bytes'])/szrows[0]['ratio'])}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('forge_raw_lattice.json','w'),indent=2)
