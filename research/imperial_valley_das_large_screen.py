import json,os,struct,sys
import h5py
import numpy as np
import zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

MAG=b'IVDBLK01'; HDR='<8sBBBBIIQQ'; HS=struct.calcsize(HDR)
DT={0:np.dtype('i1'),1:np.dtype('<i2'),2:np.dtype('<i4')}
BLOCK_T=2048
SAFETY=1.0-1e-4


def dtype_code(a):
    if a.size==0:return 0
    lo=int(a.min());hi=int(a.max())
    if -128<=lo and hi<=127:return 0
    if -32768<=lo and hi<=32767:return 1
    if -(1<<31)<=lo and hi<=(1<<31)-1:return 2
    raise RuntimeError(('integer range',lo,hi))


def pack2(c):
    c=np.asarray(c,np.uint8).ravel();n=c.size;pad=(-n)%4
    if pad:c=np.pad(c,(0,pad))
    q=c.reshape(-1,4)
    return (q[:,0]|(q[:,1]<<2)|(q[:,2]<<4)|(q[:,3]<<6)).tobytes()


def unpack2(b,n):
    q=np.frombuffer(b,np.uint8);c=np.empty(q.size*4,np.uint8)
    c[0::4]=q&3;c[1::4]=(q>>2)&3;c[2::4]=(q>>4)&3;c[3::4]=(q>>6)&3
    return c[:n]


def build_blob(K,rep):
    zc=zstd.ZstdCompressor(level=19);flat=np.ascontiguousarray(K).ravel();n0,n1=K.shape
    if rep==0:
        dc=dtype_code(flat);b1=zc.compress(flat.astype(DT[dc],copy=False).tobytes());b2=b''
    elif rep==1:
        m=flat!=0;dc=dtype_code(flat[m]);b1=zc.compress(np.packbits(m,bitorder='little').tobytes());b2=zc.compress(flat[m].astype(DT[dc],copy=False).tobytes())
    elif rep==2:
        codes=np.zeros(flat.size,np.uint8);codes[flat==1]=1;codes[flat==-1]=2;exc=(flat!=0)&(flat!=1)&(flat!=-1);codes[exc]=3;dc=dtype_code(flat[exc]);b1=zc.compress(pack2(codes));b2=zc.compress(flat[exc].astype(DT[dc],copy=False).tobytes())
    else:raise ValueError(rep)
    return struct.pack(HDR,MAG,1,rep,dc,0,n0,n1,len(b1),len(b2))+b1+b2


def decode_blob(blob):
    magic,ver,rep,dc,_r,n0,n1,l1,l2=struct.unpack(HDR,blob[:HS])
    if magic!=MAG or ver!=1:raise RuntimeError('bad block header')
    p=HS;b1=blob[p:p+l1];p+=l1;b2=blob[p:p+l2];p+=l2
    if p!=len(blob):raise RuntimeError('block length')
    zd=zstd.ZstdDecompressor();n=n0*n1
    if rep==0:
        flat=np.frombuffer(zd.decompress(b1),dtype=DT[dc],count=n).astype(np.int32)
    elif rep==1:
        m=np.unpackbits(np.frombuffer(zd.decompress(b1),np.uint8),bitorder='little',count=n).astype(bool);vals=np.frombuffer(zd.decompress(b2),dtype=DT[dc],count=int(m.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[m]=vals
    elif rep==2:
        codes=unpack2(zd.decompress(b1),n);exc=codes==3;vals=np.frombuffer(zd.decompress(b2),dtype=DT[dc],count=int(exc.sum())).astype(np.int32);flat=np.zeros(n,np.int32);flat[codes==1]=1;flat[codes==2]=-1;flat[exc]=vals
    else:raise RuntimeError('rep')
    return flat.reshape(n0,n1)


def largest_numeric_2d(f):
    rows=[]
    def visit(name,obj):
        if isinstance(obj,h5py.Dataset) and obj.ndim==2 and np.issubdtype(obj.dtype,np.number):
            rows.append((int(np.prod(obj.shape))*obj.dtype.itemsize,name,obj.shape,str(obj.dtype)))
    f.visititems(visit)
    if not rows:raise RuntimeError('no numeric 2D dataset')
    rows.sort(reverse=True)
    return rows[0],rows[:12]


def read_time_block(d,time_axis,start,stop):
    sl=[slice(None),slice(None)];sl[time_axis]=slice(start,stop);a=np.asarray(d[tuple(sl)])
    if time_axis==1:a=a.T
    return np.ascontiguousarray(a)


def global_stats(d,time_axis):
    T=d.shape[time_axis];s=0.0;ss=0.0;n=0
    for a0 in range(0,T,BLOCK_T):
        a=read_time_block(d,time_axis,a0,min(T,a0+BLOCK_T));x=a.astype(np.float64,copy=False);s+=float(np.sum(x,dtype=np.float64));ss+=float(np.sum(x*x,dtype=np.float64));n+=x.size
    mean=s/n;var=max(0.0,ss/n-mean*mean);return mean,var**0.5,n


def sz3_best(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);rows=[]
    for orient,B in [('time_space',A),('space_time',A.T)]:
        X=np.ascontiguousarray(B,np.float32);b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+3e-6):raise RuntimeError(('SZ3 hard error',orient,me,eps))
        rows.append((int(b.size),orient,me))
    return min(rows,key=lambda q:q[0])


def main(path):
    fsize=os.path.getsize(path)
    with h5py.File(path,'r') as f:
        best,cands=largest_numeric_2d(f);native_bytes,name,shape,dtype=best;d=f[name]
        # Continuous DAS convention in this dataset has many more time samples than channels.
        time_axis=int(np.argmax(shape));space_axis=1-time_axis;mean,std,n=global_stats(d,time_axis)
        public_eps=.1*std;internal_eps=public_eps*SAFETY;step=2*internal_eps
        if not (public_eps>0):raise RuntimeError(('nonpositive epsilon',std))
        T=shape[time_axis];total_ours=0;total_sz3=0;total_nz=0;total_k=0;maxerr=0.0;szmax=0.0;rep_counts={'raw':0,'sparse':0,'ternary':0};sz_orient={'time_space':0,'space_time':0};blocks=[]
        for bi,a0 in enumerate(range(0,T,BLOCK_T)):
            A=read_time_block(d,time_axis,a0,min(T,a0+BLOCK_T)).astype(np.float32,copy=False)
            q64=np.rint(A.astype(np.float64)/step)
            if q64.min()<-(1<<31) or q64.max()>(1<<31)-1:raise RuntimeError(('Q overflow',float(q64.min()),float(q64.max())))
            Q=q64.astype(np.int32);K=np.empty_like(Q);K[0]=Q[0];K[1:]=Q[1:]-Q[:-1]
            candidates=[]
            for rep in (0,1,2):
                blob=build_blob(K,rep);RK=decode_blob(blob)
                if not np.array_equal(RK,K):raise RuntimeError(('block integer decode',bi,rep))
                candidates.append((len(blob),rep,blob))
            nb,rep,blob=min(candidates,key=lambda q:q[0]);RK=decode_blob(blob);RQ=np.cumsum(RK,axis=0,dtype=np.int32);Y=RQ.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(A-Y)))
            if me>public_eps*(1+3e-6):raise RuntimeError(('lattice hard error',bi,me,public_eps))
            sb,so,sme=sz3_best(A,public_eps)
            total_ours+=nb;total_sz3+=sb;total_nz+=int(np.count_nonzero(K));total_k+=K.size;maxerr=max(maxerr,me);szmax=max(szmax,sme);rep_counts[['raw','sparse','ternary'][rep]]+=1;sz_orient[so]+=1
            row={'block':bi,'time_start':a0,'time_stop':min(T,a0+BLOCK_T),'shape':list(A.shape),'lattice_bytes':nb,'rep':['raw','sparse','ternary'][rep],'K_nonzero_fraction':float(np.mean(K!=0)),'maxerr':me,'sz3_bytes':sb,'sz3_orientation':so,'sz3_maxerr':sme,'gain_vs_sz3':sb/nb};blocks.append(row)
            print(json.dumps(row),flush=True)
        top_header=64;ours=top_header+total_ours;sz3_bytes=total_sz3 # hostile: zero metadata charged to baseline
        out={'file':os.path.basename(path),'h5_file_bytes':fsize,'numeric_dataset':name,'numeric_shape':list(shape),'numeric_dtype':dtype,'native_numeric_bytes':int(native_bytes),'candidate_numeric_datasets':[{'native_bytes':r[0],'name':r[1],'shape':list(r[2]),'dtype':r[3]} for r in cands],'time_axis':time_axis,'space_axis':space_axis,'global_mean':mean,'global_std':std,'public_eps':public_eps,'internal_eps':internal_eps,'block_time_samples':BLOCK_T,'blocks':len(blocks),'lattice_container_bytes':ours,'lattice_ratio_native_bytes':native_bytes/ours,'lattice_maxerr':maxerr,'K_nonzero_fraction':total_nz/total_k,'representation_block_counts':rep_counts,'sz3_payload_bytes_hostile':sz3_bytes,'sz3_ratio_native_bytes':native_bytes/sz3_bytes,'sz3_maxerr':szmax,'sz3_orientation_block_counts':sz_orient,'gain_vs_block_sz3':sz3_bytes/ours,'valid':bool(maxerr<=public_eps*(1+3e-6)),'sz3_valid':bool(szmax<=public_eps*(1+3e-6)),'scope':'largest numeric HDF5 array only; HDF5 metadata/container not yet counted','blocks_detail':blocks}
        print(json.dumps({k:out[k] for k in ('h5_file_bytes','numeric_dataset','numeric_shape','numeric_dtype','native_numeric_bytes','public_eps','lattice_container_bytes','lattice_ratio_native_bytes','sz3_payload_bytes_hostile','sz3_ratio_native_bytes','gain_vs_block_sz3','K_nonzero_fraction','lattice_maxerr','valid')},indent=2),flush=True)
        json.dump(out,open('imperial_valley_das_large_screen.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
