import json,math,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

CB=128;TB=1024;STEP=256
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        if not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
        row=(int(b.size),'T' if tr else 'CT')
        if best is None or row[0]<best[0]:best=row
    return best

def sdtype(a):
    a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        z=np.iinfo(dt)
        if mn>=z.min and mx<=z.max:return dt
    raise RuntimeError((mn,mx))
def udtype(a):
    a=np.asarray(a);mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mx<=np.iinfo(dt).max:return dt
    raise RuntimeError(mx)

def zigzag(q):
    q=np.asarray(q,np.int64);return ((q<<1)^(q>>63)).astype(np.uint64)
def unzig(u):
    u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)
def gray(u):return np.asarray(u,np.uint64)^(np.asarray(u,np.uint64)>>1)
def ungray(g):
    x=np.asarray(g,np.uint64).copy();shift=1
    while shift<64:
        x^=x>>shift;shift*=2
    return x

def signed_blob(a):
    a=np.asarray(a,np.int32);dt=sdtype(a);blob=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(blob),dt,count=a.size).astype(np.int32).reshape(a.shape)
    return len(blob)+36,r,'signed_'+dt.str

def unsigned_blob(a):
    a=np.asarray(a,np.uint64);dt=udtype(a);blob=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(blob),dt,count=a.size).astype(np.uint64).reshape(a.shape)
    return len(blob)+36,r,'unsigned_'+dt.str

def inv_lorenzo(a):return np.cumsum(np.cumsum(a,axis=0,dtype=np.int32),axis=1,dtype=np.int32)

def signed_reps(q):
    q=np.asarray(q,np.int32);out=[]
    arr={'raw':q.copy()}
    a=q.copy();a[:,1:]=q[:,1:]-q[:,:-1];arr['dt']=a
    a=q.copy();a[1:]=q[1:]-q[:-1];arr['ds']=a
    a=q.copy();a[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1];a[0,1:]=q[0,1:]-q[0,:-1];a[1:,0]=q[1:,0]-q[:-1,0];arr['lorenzo']=a
    for name,a in arr.items():
        b,r,rep=signed_blob(a)
        if name=='raw':qq=r
        elif name=='dt':qq=np.cumsum(r,axis=1,dtype=np.int32)
        elif name=='ds':qq=np.cumsum(r,axis=0,dtype=np.int32)
        else:qq=inv_lorenzo(r)
        if not np.array_equal(qq,q):raise RuntimeError(('signed rep',name))
        out.append((b+8,name+'_'+rep,qq))
    return out

def xor_reps(q):
    u=zigzag(q).reshape(q.shape);out=[]
    for name,axis in [('zigzag_raw',None),('zigzag_xort',1),('zigzag_xors',0)]:
        a=u.copy()
        if axis==1:a[:,1:]=u[:,1:]^u[:,:-1]
        if axis==0:a[1:]=u[1:]^u[:-1]
        b,r,rep=unsigned_blob(a)
        if axis is None:uu=r
        elif axis==1:
            uu=r.copy()
            for j in range(1,uu.shape[1]):uu[:,j]^=uu[:,j-1]
        else:
            uu=r.copy()
            for i in range(1,uu.shape[0]):uu[i]^=uu[i-1]
        qq=unzig(uu).reshape(q.shape)
        if not np.array_equal(qq,q):raise RuntimeError(('xor rep',name))
        out.append((b+8,name+'_'+rep,qq))
    g=gray(u);b,r,rep=unsigned_blob(g);qq=unzig(ungray(r)).reshape(q.shape)
    if not np.array_equal(qq,q):raise RuntimeError('gray')
    out.append((b+8,'gray_'+rep,qq))
    return out

def bitplane_rep(q,use_gray=False):
    u=zigzag(q).reshape(q.shape);v=gray(u) if use_gray else u;mx=int(v.max()) if v.size else 0;nb=max(1,mx.bit_length());packed=[];lengths=[]
    for k in range(nb):
        bits=((v.ravel()>>k)&1).astype(np.uint8);raw=np.packbits(bits,bitorder='little').tobytes();bb=Z.compress(raw);packed.append(bb);lengths.append(len(bb))
    # Decoder-equivalent rebuild.
    vv=np.zeros(v.size,np.uint64);n=v.size
    for k,bb in enumerate(packed):
        bits=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:n].astype(np.uint64);vv|=bits<<k
    vv=vv.reshape(v.shape);uu=ungray(vv) if use_gray else vv;qq=unzig(uu).reshape(q.shape)
    if not np.array_equal(qq,q):raise RuntimeError('bitplane')
    total=sum(lengths)+4*nb+40
    return total,('gray_bitplanes' if use_gray else 'zigzag_bitplanes'),qq

def byteshuffle_rep(q):
    u=zigzag(q).reshape(q.shape);dt=udtype(u);a=u.astype(dt);item=dt.itemsize;raw=a.view(np.uint8).reshape(a.size,item).T.copy().tobytes();bb=Z.compress(raw)
    rb=D.decompress(bb);m=np.frombuffer(rb,np.uint8).reshape(item,a.size).T.copy();uu=m.reshape(-1,item).view(dt).reshape(a.shape).astype(np.uint64);qq=unzig(uu).reshape(q.shape)
    if not np.array_equal(qq,q):raise RuntimeError('byteshuffle')
    return len(bb)+44,'zigzag_byteshuffle_'+dt.str,qq

def encode_dyadic(X,eps):
    if STEP/2>eps:raise RuntimeError(('dyadic step illegal',STEP,eps))
    # X is integer-valued int16 data carried as float64; nearest multiple of 256 has <=128 error.
    q=np.rint(X/STEP).astype(np.int32);R0=q.astype(np.float64)*STEP;me0=float(np.max(np.abs(X-R0)))
    if me0>eps*(1+1e-12):raise RuntimeError(('quant hard',me0,eps))
    c=signed_reps(q)+xor_reps(q)+[bitplane_rep(q,False),bitplane_rep(q,True),byteshuffle_rep(q)]
    best=min(c,key=lambda x:x[0]);R=best[2].astype(np.float64)*STEP;me=float(np.max(np.abs(X-R)))
    if me>eps*(1+1e-12):raise RuntimeError(('decode hard',me,eps,best[1]))
    return {'bytes':best[0]+8,'rep':best[1],'maxerr':me,'q_min':int(q.min()),'q_max':int(q.max()),'zero_fraction':float(np.mean(q==0))}

def main(path,slot):
    slot=int(slot)
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        if np.dtype(d.dtype).kind!='i' or np.dtype(d.dtype).itemsize!=2:raise RuntimeError(('dtype',d.dtype))
        tblocks=list(range(slot*10,min(30,(slot+1)*10)));rows=[]
        for tb in tblocks:
            t0=tb*TB;t1=min(d.shape[0],t0+TB)
            for cb,c0 in enumerate(range(0,d.shape[1],CB)):
                c1=min(d.shape[1],c0+CB);X=np.asarray(d[t0:t1,c0:c1],np.float64).T;ours=encode_dyadic(X,eps);sb,ori=szrun(X,eps);raw=X.size*2
                rows.append({'tb':tb,'cb':cb,'t0':t0,'c0':c0,'raw':raw,'ours':ours['bytes'],'sz3':sb,'gain':sb/ours['bytes'],'ours_bps':8*ours['bytes']/X.size,'sz3_bps':8*sb/X.size,'rep':ours['rep'],'maxerr':ours['maxerr'],'zero_fraction':ours['zero_fraction'],'sz3_orientation':ori})
        raw=sum(r['raw'] for r in rows);ob=sum(r['ours'] for r in rows);sb=sum(r['sz3'] for r in rows)
        from collections import Counter
        out={'slot':slot,'global_std':std,'eps':eps,'dyadic_step':STEP,'worst_quantization_error':STEP/2,'tiles':len(rows),'raw_bytes':raw,'ours_bytes':ob,'sz3_bytes':sb,'gain_vs_sz3':sb/ob,'ours_ratio':raw/ob,'sz3_ratio':raw/sb,'ours_bps':16*ob/raw,'sz3_bps':16*sb/raw,'min_tile_gain':min(r['gain'] for r in rows),'median_tile_gain':float(np.median([r['gain'] for r in rows])),'max_tile_gain':max(r['gain'] for r in rows),'representation_counts':dict(Counter(r['rep'] for r in rows)),'rows':rows,'scope':'One-third of the entire Imperial Acoustic array. Integer int16 samples are reconstructed on the fixed binary-native 256 grid; max quantization error is 128, strictly below public epsilon. A fixed decoder-real menu selects raw/time/spatial/Lorenzo signed frames, zigzag XOR/Gray, packed bitplanes or byte-shuffle per tile with mode overhead counted; every winning frame is byte-decoded before hard-error verification. Matched SZ3 uses identical 128x1024 tiles and best orientation.'}
        print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open(f'imperial_dyadic_legal_grid_full_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
