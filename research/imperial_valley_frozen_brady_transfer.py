import json,os,struct,sys
import h5py
import numpy as np
import zstandard as zstd

# Frozen from independently measured Brady PR #56 winner.
SPACE=128
TIME=1024
NKEEP=256
SAFETY=1.0-1e-4
ZLEVEL=19
MAG=b'IVBRD001'
HDR='<8sBBBBHHHIIII'
HS=struct.calcsize(HDR)
DT={0:np.dtype('i1'),1:np.dtype('<i2'),2:np.dtype('<i4')}


def dc(a):
    if a.size==0:return 0
    lo=int(a.min());hi=int(a.max())
    if -128<=lo and hi<=127:return 0
    if -32768<=lo and hi<=32767:return 1
    return 2


def comp(raw):return zstd.ZstdCompressor(level=ZLEVEL).compress(raw)
def decomp(blob):return zstd.ZstdDecompressor().decompress(blob)


def encode_int(A):
    c=dc(A);return c,comp(np.ascontiguousarray(A).astype(DT[c],copy=False).tobytes())


def decode_int(blob,c,shape):
    n=int(np.prod(shape));return np.frombuffer(decomp(blob),dtype=DT[c],count=n).astype(np.int32).reshape(shape)


def correction_candidates(C):
    # C is exact integer correction field, channel x time.
    rows=[]
    K=C.copy()
    if K.shape[1]>1:K[:,1:]-=C[:,:-1]
    c,b=encode_int(K);rows.append((len(b),0,c,b,b''))
    m=K!=0;vals=K[m];c2=dc(vals);mb=comp(np.packbits(m.ravel(),bitorder='little').tobytes());vb=comp(vals.astype(DT[c2],copy=False).tobytes()) if vals.size else b'';rows.append((len(mb)+len(vb),1,c2,mb,vb))
    S=C.copy()
    if S.shape[0]>1:S[1:]-=C[:-1]
    c,b=encode_int(S);rows.append((len(b),2,c,b,b''))
    L=C.copy()
    if L.shape[0]>1 and L.shape[1]>1:L[1:,1:]=C[1:,1:]-C[:-1,1:]-C[1:,:-1]+C[:-1,:-1]
    c,b=encode_int(L);rows.append((len(b),3,c,b,b''))
    return min(rows,key=lambda q:q[0]),[(r[0],r[1]) for r in rows]


def decode_correction(mode,c,b1,b2,shape):
    if mode==0:
        K=decode_int(b1,c,shape);return np.cumsum(K,axis=1,dtype=np.int32)
    if mode==1:
        n=int(np.prod(shape));m=np.unpackbits(np.frombuffer(decomp(b1),np.uint8),bitorder='little',count=n).astype(bool);K=np.zeros(n,np.int32)
        if m.any():K[m]=np.frombuffer(decomp(b2),dtype=DT[c],count=int(m.sum())).astype(np.int32)
        return np.cumsum(K.reshape(shape),axis=1,dtype=np.int32)
    if mode==2:
        S=decode_int(b1,c,shape);return np.cumsum(S,axis=0,dtype=np.int32)
    if mode==3:
        L=decode_int(b1,c,shape);C=L.copy()
        for i in range(1,C.shape[0]):
            for j in range(1,C.shape[1]):C[i,j]=L[i,j]+C[i-1,j]+C[i,j-1]-C[i-1,j-1]
        return C
    raise RuntimeError(('bad correction mode',mode))


def prediction_from_model(nc,nt,idx,qv,scale):
    nf=nt//2+1;Cq=np.zeros((nc,nf),np.complex128);flat=Cq.ravel();v=(qv[:,0].astype(np.float32)+1j*qv[:,1].astype(np.float32))*np.float32(scale);flat[idx]=v;Cq=flat.reshape(nc,nf)
    return np.fft.irfft(np.fft.ifft(Cq,axis=0),n=nt,axis=1).real.astype(np.float32)


def encode_tile(W,internal_eps):
    nc,nt=W.shape;F=np.fft.fft(np.fft.rfft(W,axis=1),axis=0);flat=F.ravel();n=min(NKEEP,flat.size)
    ii=np.argpartition(np.abs(flat),-n)[-n:] if n<flat.size else np.arange(flat.size);ii=np.sort(ii).astype(np.uint32);v=flat[ii];xy=np.stack([v.real,v.imag],axis=-1);rawscale=max(float(np.max(np.abs(xy)))/127.0,1e-30);s16=np.float16(rawscale);scale=float(np.float32(s16));q=np.clip(np.rint(xy/scale),-127,127).astype(np.int8)
    P=prediction_from_model(nc,nt,ii,q,scale);step=2*internal_eps;Q=np.rint((W.astype(np.float64)-P.astype(np.float64))/step).astype(np.int32);best,allcorr=correction_candidates(Q);_,mode,c,b1,b2=best
    ib=comp(ii.tobytes());vb=comp(q.tobytes());header=struct.pack(HDR,MAG,1,mode,c,0,nc,nt,n,len(ib),len(vb),len(b1),len(b2));blob=header+s16.tobytes()+ib+vb+b1+b2
    R=decode_tile(blob,internal_eps)
    me=float(np.max(np.abs(W-R)))
    return blob,me,{'mode':mode,'model_bytes':len(ib)+len(vb)+2,'correction_bytes':len(b1)+len(b2),'header_bytes':HS,'scale':scale,'correction_candidates':allcorr,'correction_nonzero_fraction':float(np.mean(Q!=0))}


def decode_tile(blob,internal_eps):
    if len(blob)<HS+2:raise RuntimeError('short tile')
    magic,ver,mode,c,_r,nc,nt,n,li,lv,l1,l2=struct.unpack(HDR,blob[:HS])
    if magic!=MAG or ver!=1:raise RuntimeError('tile header')
    p=HS;scale=float(np.frombuffer(blob[p:p+2],np.float16,count=1)[0]);p+=2;ib=blob[p:p+li];p+=li;vb=blob[p:p+lv];p+=lv;b1=blob[p:p+l1];p+=l1;b2=blob[p:p+l2];p+=l2
    if p!=len(blob):raise RuntimeError('tile length')
    ii=np.frombuffer(decomp(ib),np.uint32,count=n).astype(np.int64);q=np.frombuffer(decomp(vb),np.int8,count=n*2).reshape(n,2);P=prediction_from_model(nc,nt,ii,q,scale);Q=decode_correction(mode,c,b1,b2,(nc,nt));return P+Q.astype(np.float32)*np.float32(2*internal_eps)


def dataset_info(f):
    rows=[]
    def v(name,obj):
        if isinstance(obj,h5py.Dataset) and obj.ndim==2 and np.issubdtype(obj.dtype,np.number):rows.append((int(np.prod(obj.shape))*obj.dtype.itemsize,name,obj.shape,str(obj.dtype)))
    f.visititems(v);rows.sort(reverse=True)
    if not rows:raise RuntimeError('no 2D numeric dataset')
    return rows[0]


def stats(d):
    s=ss=0.0;n=0
    for t in range(0,d.shape[0],2048):
        x=np.asarray(d[t:min(d.shape[0],t+2048)]).astype(np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mu=s/n;return mu,float(np.sqrt(max(0.0,ss/n-mu*mu)))


def main(path):
    fbytes=os.path.getsize(path)
    with h5py.File(path,'r') as f:
        native,name,shape,dtype=dataset_info(f);d=f[name]
        if tuple(shape)!=(30000,6912) or dtype!='int16':raise RuntimeError(('unexpected IV array',name,shape,dtype))
        mu,std=stats(d);public_eps=.1*std;internal_eps=public_eps*SAFETY
        total=64;tiles=0;model=0;corr=0;maxerr=0.0;mode_counts={str(i):0 for i in range(4)};nz_weight=0.0;samples=0;rows=[]
        for t0 in range(0,shape[0],TIME):
            t1=min(shape[0],t0+TIME)
            for s0 in range(0,shape[1],SPACE):
                s1=min(shape[1],s0+SPACE);W=np.asarray(d[t0:t1,s0:s1]).T.astype(np.float32,copy=False);blob,me,diag=encode_tile(W,internal_eps);R=decode_tile(blob,internal_eps)
                if not np.array_equal(R,decode_tile(blob,internal_eps)):raise RuntimeError('nondeterministic decode')
                me2=float(np.max(np.abs(W-R)))
                if me2>public_eps*(1+3e-6):raise RuntimeError(('hard error',t0,s0,me2,public_eps))
                total+=len(blob);tiles+=1;model+=diag['model_bytes'];corr+=diag['correction_bytes'];maxerr=max(maxerr,me2);mode_counts[str(diag['mode'])]+=1;nz_weight+=diag['correction_nonzero_fraction']*W.size;samples+=W.size
                if tiles<=5 or tiles%100==0:print(json.dumps({'tile':tiles,'t0':t0,'s0':s0,'shape':list(W.shape),'bytes':len(blob),'ratio':W.nbytes/len(blob),'mode':diag['mode'],'corr_nz':diag['correction_nonzero_fraction'],'maxerr':me2}),flush=True)
        # Exact baseline from PR #204 file slot 2; same HDF5 key, numeric array, global epsilon, and full-array block screen.
        baseline_native=414720000;baseline_eps=133.69778037805762;baseline_sz3=86361271
        if native!=baseline_native or abs(public_eps-baseline_eps)>1e-6:raise RuntimeError(('baseline identity drift',native,public_eps,baseline_native,baseline_eps))
        out={'file_bytes':fbytes,'dataset':name,'shape':list(shape),'dtype':dtype,'native_numeric_bytes':native,'global_mean':mu,'global_std':std,'public_eps':public_eps,'internal_eps':internal_eps,'frozen_brady_definition':{'space_tile':SPACE,'time_tile':TIME,'topN':NKEEP,'coefficient_quantization':'int8 complex','scale_storage':'float16','zstd_level':ZLEVEL,'source':'PR56 Brady winner; scale decode made exact here'},'tiles':tiles,'container_bytes':total,'ratio_native':native/total,'model_bytes':model,'correction_bytes':corr,'correction_nonzero_fraction':nz_weight/samples,'correction_mode_counts':mode_counts,'maxerr':maxerr,'valid':bool(maxerr<=public_eps*(1+3e-6)),'pr204_matched_block_sz3_bytes':baseline_sz3,'pr204_sz3_ratio':native/baseline_sz3,'gain_vs_pr204_sz3':baseline_sz3/total,'pr204_generic_lattice_bytes':100374449,'gain_vs_pr204_generic_lattice':100374449/total,'scope':'entire Acoustic numeric array; HDF5 metadata not included'}
        print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_valley_frozen_brady_transfer.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
