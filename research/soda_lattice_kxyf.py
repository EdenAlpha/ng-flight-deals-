import json, os, struct, sys
import numpy as np
import segyio, zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()
MAGIC=b'SODALAT1'; HDR='<8sHHHHIIdIIBB6Q'; HS=struct.calcsize(HDR)
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

def pack_int(a):
    a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0
    code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
    return code,ZC.compress(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())

def unpack_int(blob,code,n):
    a=np.frombuffer(ZD.decompress(blob),dtype=IDT[code],count=n)
    if a.size!=n:raise RuntimeError('integer stream mismatch')
    return a.astype(np.int32,copy=False)

def d1(a,axis):
    o=a.copy();s1=[slice(None)]*a.ndim;s0=[slice(None)]*a.ndim;s1[axis]=slice(1,None);s0[axis]=slice(None,-1);o[tuple(s1)]=a[tuple(s1)]-a[tuple(s0)];return o

def corr_transform(Q,mode):
    axes={0:(),1:(3,),2:(2,),3:(1,),4:(3,2),5:(3,1),6:(3,2,1),7:(0,3,2,1)}[mode];K=Q
    for ax in axes:K=d1(K,ax)
    return K,axes

def corr_inverse(K,axes):
    Q=K
    for ax in reversed(axes):Q=np.cumsum(Q,axis=ax,dtype=np.int32)
    return Q

def infer_lattice(P):
    # exact nearest neighbours, N<700 so dense pairwise distance is cheap and deterministic
    D=P[:,None,:]-P[None,:,:];d2=np.sum(D*D,axis=2);np.fill_diagonal(d2,np.inf);j=np.argmin(d2,axis=1);vec=P[j]-P;nn=np.sqrt(d2[np.arange(len(P)),j]);nnmed=float(np.median(nn))
    ang=np.mod(np.arctan2(vec[:,1],vec[:,0]),np.pi);z=np.mean(np.exp(2j*ang));theta=(.5*np.angle(z))%np.pi;u=np.array([np.cos(theta),np.sin(theta)]);v=np.array([-u[1],u[0]])
    along=P@u;cross=P@v
    # provisional cross-line clusters only to estimate the regular line spacing
    order=np.argsort(cross);eps=.35*nnmed;cent=[];cur=[int(order[0])]
    for a,b in zip(order[:-1],order[1:]):
        if cross[b]-cross[a]>eps:cent.append(float(np.median(cross[cur])));cur=[]
        cur.append(int(b))
    cent.append(float(np.median(cross[cur])));cent=np.sort(np.asarray(cent));g=np.diff(cent);cross_step=float(np.median(g)) if g.size else nnmed
    # snap to ideal survey lattice; iterative phase refinement suppresses bent-line fragments
    c0=float(cross.min())
    for _ in range(6):
        li=np.rint((cross-c0)/cross_step).astype(int);c0+=float(np.median(cross-(c0+li*cross_step)))
    a0=float(along.min());along_step=nnmed
    for _ in range(6):
        si=np.rint((along-a0)/along_step).astype(int);a0+=float(np.median(along-(a0+si*along_step)))
    li-=li.min();si-=si.min();pairs=list(zip(li.tolist(),si.tolist()))
    return li,si,{'line_angle_deg':float(np.rad2deg(theta)),'direction_concentration':float(abs(z)),'along_step':along_step,'cross_step':cross_step,'n_lines':int(li.max()+1),'n_stations':int(si.max()+1),'grid_cells':int((li.max()+1)*(si.max()+1)),'occupied_cells':len(set(pairs)),'occupancy':float(len(set(pairs))/((li.max()+1)*(si.max()+1))),'duplicates':int(len(P)-len(set(pairs))),'nn_median':nnmed}

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64);dt=int(segyio.tools.dt(f))
    groups={};extra=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:extra.append(i);continue
        groups.setdefault((int(x),int(y)),[]).append(i)
    keys=list(groups);P=np.asarray(keys,dtype=np.float64);counts=np.asarray([len(groups[k]) for k in keys]);C=int(np.bincount(counts).argmax());li,si,geom=infer_lattice(P)
    if geom['duplicates']:
        raise RuntimeError(f"lattice collision count {geom['duplicates']}")
    ny,nx=geom['n_lines'],geom['n_stations'];nt=X.shape[1];V=np.zeros((C,ny,nx,nt),np.float32);present=np.zeros((C,ny,nx),bool);trace_map=[]
    for g,k in enumerate(keys):
        for c,tid in enumerate(groups[k][:C]):V[c,li[g],si[g]]=X[tid];present[c,li[g],si[g]]=True;trace_map.append((tid,c,int(li[g]),int(si[g])))
    trace_map.sort();geom.update({'component_mode':C,'mode_fraction':float(np.mean(counts==C)),'extra_traces':len(extra),'shape_grid':[C,ny,nx,nt]})
    # Model-only nearest-neighbour fill of missing lattice sites to avoid zero-hole spectral edges.
    Vf=V.copy()
    for c in range(C):
        pc=np.argwhere(present[c]);mc=np.argwhere(~present[c])
        if len(mc):
            dd=((mc[:,None,:]-pc[None,:,:])**2).sum(axis=2);nn=np.argmin(dd,axis=1)
            for q,pidx in zip(mc,nn):Vf[c,q[0],q[1]]=V[c,pc[pidx,0],pc[pidx,1]]
    return X,V,Vf,present,trace_map,X[np.asarray(extra)] if extra else np.empty((0,nt),np.float32),dt,geom

def fwd(W):return np.fft.rfftn(W,axes=(0,1,2))
def inv(F,shape):return np.fft.irfftn(F,s=shape,axes=(0,1,2)).real.astype(np.float32)

def encode(V,Vf,present,eps,B,frac,specs):
    C,ny,nx,nt=V.shape;nblk=(nt+B-1)//B;shp=specs[0][0].shape;M=int(np.prod(shp));N=max(1,min(M,int(round(frac*M))));P=np.zeros_like(V);inds=[];vals=[];scales=[]
    for c in range(C):
      for b in range(nblk):
        F=specs[c][b];flat=F.reshape(-1);ii=np.argpartition(np.abs(flat),-N)[-N:];ii=np.sort(ii).astype(np.uint32);vv=flat[ii];comp=np.stack([vv.real,vv.imag],axis=1);sc=max(float(np.max(np.abs(comp)))/127.,1e-30);sc16=np.float16(sc);sd=np.float32(sc16);q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8);vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd;fq=np.zeros(M,np.complex64);fq[ii.astype(np.int64)]=vq;R=inv(fq.reshape(shp),(ny,nx,B));t0=b*B;m=min(B,nt-t0);P[c,:,:,t0:t0+m]=R[:,:,:m];inds.append(ii);vals.append(q);scales.append(sc16)
    iz=ZC.compress(np.concatenate(inds).astype('<u4',copy=False).tobytes());vz=ZC.compress(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes());szb=ZC.compress(np.asarray(scales,dtype='<f2').tobytes())
    Q=np.zeros(V.shape,np.int32);D=(V-P)/(2.*eps);Q[present]=np.rint(D[present]).astype(np.int32)
    opts=[]
    for mode in range(8):
        K,axes=corr_transform(Q,mode);dc,dense=pack_int(K);opts.append((len(dense),mode,0,dc,dense,b'',float(np.mean(K!=0))))
        mask=K!=0;mz=ZC.compress(np.packbits(mask.ravel(),bitorder='little').tobytes());dc2,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),mode,1,dc2,mz,vv,float(mask.mean())))
    _,cm,sp,dc,ca,cb,event=min(opts,key=lambda x:x[0]);lens=(len(iz),len(vz),len(szb),len(ca),len(cb),0);head=struct.pack(HDR,MAGIC,1,C,ny,nx,nt,B,float(eps),N,nblk,cm,(sp<<4)|dc,*lens)
    return head+iz+vz+szb+ca+cb,{'N':N,'model_bytes':HS+len(iz)+len(vz)+len(szb),'corr_bytes':len(ca)+len(cb),'corr_mode':cm,'corr_sparse':bool(sp),'event_fraction':event}

def decode(blob):
    f=struct.unpack(HDR,blob[:HS]);magic,ver,C,ny,nx,nt,B,eps,N,nblk,cm,flags,*lens=f
    if magic!=MAGIC or ver!=1:raise RuntimeError('bad container')
    dc=flags&15;sp=(flags>>4)&1;p=HS;ss=[]
    for L in lens:ss.append(blob[p:p+L]);p+=L
    iz,vz,szb,ca,cb,_=ss;count=C*nblk*N;shp=(ny,nx,B//2+1);M=int(np.prod(shp));ii=np.frombuffer(ZD.decompress(iz),dtype='<u4',count=count);q=np.frombuffer(ZD.decompress(vz),dtype=np.int8,count=2*count).reshape(count,2);sc=np.frombuffer(ZD.decompress(szb),dtype='<f2',count=C*nblk);P=np.zeros((C,ny,nx,nt),np.float32);k=0
    for c in range(C):
      for b in range(nblk):
        sl=slice(k*N,(k+1)*N);jj=ii[sl].astype(np.int64);qq=q[sl];vv=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*np.float32(sc[k]);F=np.zeros(M,np.complex64);F[jj]=vv;R=inv(F.reshape(shp),(ny,nx,B));t0=b*B;m=min(B,nt-t0);P[c,:,:,t0:t0+m]=R[:,:,:m];k+=1
    total=C*ny*nx*nt
    if sp:
        mask=np.unpackbits(np.frombuffer(ZD.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;K=K.reshape(C,ny,nx,nt)
    else:K=unpack_int(ca,dc,total).reshape(C,ny,nx,nt)
    axes={0:(),1:(3,),2:(2,),3:(1,),4:(3,2),5:(3,1),6:(3,2,1),7:(0,3,2,1)}[cm];Q=corr_inverse(K,axes);return P+Q.astype(np.float32)*np.float32(2.*eps)

def sz3_array(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);bb,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(bb,np.float32,A.shape);return int(bb.size),float(np.max(np.abs(A-R)))

def bench(path):
    X,V,Vf,present,tmap,extra,dt,geom=load(path);std=float(X.astype(np.float64).std());eps=.1*std;raw=X.nbytes;rows=[];b0,e0=sz3_array(X,eps);bases=[{'layout':'file2d','bytes':b0,'ratio':raw/b0,'maxerr':e0}]
    # Give SZ3 exactly the same line/station receiver ordering, without charging nonexistent grid holes.
    seq=[]
    for c in range(V.shape[0]):
        ids=np.argwhere(present[c]);ids=ids[np.lexsort((ids[:,1],ids[:,0]))];seq.append(np.stack([V[c,y,x] for y,x in ids]))
    bs=0;es=0.
    for A in seq:b,e=sz3_array(A,eps);bs+=b;es=max(es,e)
    if extra.size:b,e=sz3_array(extra,eps);bs+=b;es=max(es,e)
    bases.append({'layout':'lattice_sequence','bytes':bs,'ratio':raw/bs,'maxerr':es})
    extra_bytes=0;extra_err=0.
    if extra.size:extra_bytes,extra_err=sz3_array(extra,eps)
    for B in [512,1024]:
        nblk=(V.shape[3]+B-1)//B;specs=[]
        for c in range(V.shape[0]):
            cs=[]
            for b in range(nblk):
                t0=b*B;m=min(B,V.shape[3]-t0);W=np.zeros((V.shape[1],V.shape[2],B),np.float32);W[:,:,:m]=Vf[c,:,:,t0:t0+m];cs.append(fwd(W))
            specs.append(cs)
        for frac in [0.0005,0.001,0.002,0.004]:
            blob,meta=encode(V,Vf,present,eps,B,frac,specs);R=decode(blob);me=0.
            for c in range(V.shape[0]):me=max(me,float(np.max(np.abs(V[c][present[c]]-R[c][present[c]]))))
            total=len(blob)+extra_bytes+16;row={'B':B,'frac':frac,'bytes':total,'ratio':raw/total,'maxerr':max(me,extra_err),'valid':bool(max(me,extra_err)<=eps*(1+5e-6)),'extra_bytes':extra_bytes,**meta};rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);bases.sort(key=lambda r:r['ratio'],reverse=True);return {'file':os.path.basename(path),'shape_file':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'top':rows,'sz3':bases}

out={'shots':[]}
for p in sys.argv[1:]:
    print('BENCH',p,flush=True);r=bench(p);out['shots'].append(r);print('BEST',json.dumps({'file':r['file'],'codec':r['top'][0],'sz3':r['sz3'][0],'geometry':r['geometry']},indent=2),flush=True)
json.dump(out,open('soda_lattice_kxyf_results.json','w'),indent=2)
