import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as a

REGIONS=(('easy',2304),('medium',4608))
C=128;NT=8192;TB=1024;STEP=267
RANKS=(0,1,2,4,8,16,24,32)
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
DT=(np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4'))


def dtype_id(x):
    lo=int(x.min()) if x.size else 0; hi=int(x.max()) if x.size else 0
    return 0 if -128<=lo and hi<=127 else (1 if -32768<=lo and hi<=32767 else 2)


def pack_int(x):
    x=np.ascontiguousarray(x)
    k=dtype_id(x)
    return bytes([k])+Z.compress(x.astype(DT[k],copy=False).tobytes())


def unpack_int(b,shape):
    k=b[0]; raw=D.decompress(b[1:]); n=int(np.prod(shape))
    return np.frombuffer(raw,DT[k],count=n).astype(np.int32).reshape(shape)


def repair_encode(Q):
    shape=Q.shape; cand=[]
    b=pack_int(Q); cand.append((len(b)+1,0,bytes([0])+b))
    T=Q.copy(); T[:,1:]-=Q[:,:-1]
    b=pack_int(T); cand.append((len(b)+1,1,bytes([1])+b))
    S=Q.copy(); S[1:]-=Q[:-1]
    b=pack_int(S); cand.append((len(b)+1,2,bytes([2])+b))
    L=Q.copy(); L[1:,1:]=Q[1:,1:]-Q[:-1,1:]-Q[1:,:-1]+Q[:-1,:-1]; L[0,1:]=Q[0,1:]-Q[0,:-1]; L[1:,0]=Q[1:,0]-Q[:-1,0]
    b=pack_int(L); cand.append((len(b)+1,3,bytes([3])+b))
    m=(Q!=0).ravel(order='C'); vals=Q.ravel(order='C')[m]
    mb=Z.compress(np.packbits(m,bitorder='little').tobytes()); vb=pack_int(vals) if vals.size else pack_int(np.empty(0,np.int32))
    payload=len(mb).to_bytes(4,'little')+mb+vb; cand.append((len(payload)+1,4,bytes([4])+payload))
    return min(cand,key=lambda x:x[0]),float(np.mean(Q!=0))


def repair_decode(blob,shape):
    mode=blob[0]; b=blob[1:]
    if mode==0:return unpack_int(b,shape)
    if mode==1:return np.cumsum(unpack_int(b,shape),axis=1,dtype=np.int32)
    if mode==2:return np.cumsum(unpack_int(b,shape),axis=0,dtype=np.int32)
    if mode==3:return np.cumsum(np.cumsum(unpack_int(b,shape),axis=0,dtype=np.int64),axis=1,dtype=np.int64).astype(np.int32)
    if mode==4:
        n=int.from_bytes(b[:4],'little'); mb=b[4:4+n]; vb=b[4+n:]
        m=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little')[:int(np.prod(shape))].astype(bool)
        v=unpack_int(vb,(int(m.sum()),)).ravel(); q=np.zeros(m.size,np.int32); q[m]=v
        return q.reshape(shape)
    raise ValueError(mode)


def model_encode(mean,A,B,rank):
    mb=pack_int(mean.astype(np.int32))
    if rank:
        ab=Z.compress(np.ascontiguousarray(A.astype(np.float16)).tobytes())
        bb=Z.compress(np.ascontiguousarray(B.astype(np.float16)).tobytes())
    else:
        ab=b'';bb=b''
    return bytes([rank])+len(mb).to_bytes(4,'little')+len(ab).to_bytes(4,'little')+mb+ab+bb


def model_decode(blob,shape):
    rank=blob[0]; lm=int.from_bytes(blob[1:5],'little'); la=int.from_bytes(blob[5:9],'little')
    off=9; mb=blob[off:off+lm]; off+=lm; ab=blob[off:off+la]; off+=la; bb=blob[off:]
    mean=unpack_int(mb,(shape[0],)).astype(np.float32)
    if rank:
        A=np.frombuffer(D.decompress(ab),np.float16).astype(np.float32).reshape(shape[0],rank)
        B=np.frombuffer(D.decompress(bb),np.float16).astype(np.float32).reshape(rank,shape[1])
        P=np.rint(mean[:,None]+A@B).astype(np.int32)
    else:
        P=np.broadcast_to(mean[:,None],shape).astype(np.int32).copy()
    return rank,P


def tile(W,eps):
    mean=np.rint(np.mean(W.astype(np.float64),axis=1)).astype(np.int32)
    Xc=W.astype(np.float32)-mean[:,None].astype(np.float32)
    U,S,Vt=np.linalg.svd(Xc,full_matrices=False)
    candidates=[]
    for rank in RANKS:
        if rank:
            A=(U[:,:rank]*S[:rank][None,:]).astype(np.float32); B=Vt[:rank,:].astype(np.float32)
        else:
            A=np.empty((W.shape[0],0),np.float32); B=np.empty((0,W.shape[1]),np.float32)
        model=model_encode(mean,A,B,rank); rd,P=model_decode(model,W.shape)
        if rd!=rank:raise RuntimeError('rank decode')
        Q=np.rint((W.astype(np.float64)-P.astype(np.float64))/STEP).astype(np.int32)
        (_,mode,repair),dens=repair_encode(Q); Qd=repair_decode(repair,W.shape)
        if not np.array_equal(Q,Qd):raise RuntimeError(('repair decode',rank,mode))
        R=P+STEP*Qd; me=float(np.max(np.abs(W.astype(np.float64)-R.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('hard',rank,me,eps))
        total=len(model)+len(repair)+8
        candidates.append({'rank':rank,'bytes':total,'model_bytes':len(model),'repair_bytes':len(repair),'repair_mode':int(mode),'repair_density':dens,'base_rmse':float(np.sqrt(np.mean((W.astype(np.float64)-P.astype(np.float64))**2))),'base_maxerr':float(np.max(np.abs(W.astype(np.float64)-P.astype(np.float64)))),'maxerr':me})
    return min(candidates,key=lambda x:x['bytes']),candidates


def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=a.m.stats(d);eps=.1*gs;rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rh,Kh=a.run_ar(X,hu);ab,_,_,Kd=a.arithmetic(Kh);Rd=a.decode_source(Kd,hu)
            if not np.array_equal(Rd,Rh):raise RuntimeError('AR decode')
            if float(np.max(np.abs(X-Rd.astype(np.float64))))>eps*(1+1e-12):raise RuntimeError('AR hard')
            total=0;tiles=[];sz=0
            for t0 in range(0,NT,TB):
                W=X[:,t0:t0+TB].astype(np.int32);best,screen=tile(W,eps);best['t0']=t0;best['screen']=screen;tiles.append(best);total+=best['bytes'];sb,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(sb)
            row={'region':name,'c0':c0,'samples':int(X.size),'lowrank_repair_bytes':int(total),'lowrank_repair_bps':8*total/X.size,'arithmetic_bytes':int(ab),'arithmetic_bps':8*ab/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'gain_vs_arithmetic':ab/total,'gain_vs_sz3':sz/total,'rank_counts':{str(r):sum(t['rank']==r for t in tiles) for r in RANKS},'mean_repair_density':float(np.mean([t['repair_density'] for t in tiles])),'model_fraction':float(sum(t['model_bytes'] for t in tiles)/total),'repair_fraction':float(sum(t['repair_bytes'] for t in tiles)/total),'tiles':tiles};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='tiles'},indent=2),flush=True)
        out={'global_std':gs,'eps':eps,'repair_step':STEP,'ranks':list(RANKS),'rows':rows,'scope':'Low-rank degrees-of-freedom pilot on easy/medium Imperial. Each 128x1024 source tile transmits a rounded per-channel mean plus a truncated SVD base using zstd-compressed float16 factors. The base is fully byte-decoded, then exact Q=round((X-P)/267) repair is encoded with the cheapest fully decoded raw/time/space/Lorenzo/sparse Zstd representation. Final P+267Q is independently hard-error checked. All factor, mean, repair and framing bytes are charged. Rank is selected by actual final bytes per tile. Matched Huber AR32 arithmetic and SZ3 controls are rerun. No AI.'};json.dump(out,open('imperial_lowrank_base_hardrepair.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
