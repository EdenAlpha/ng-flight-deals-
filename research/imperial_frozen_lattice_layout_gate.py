import json,sys
import h5py,numpy as np
import zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=4096
TB=1024
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
ZC=zstd.ZstdCompressor(level=22)
ZD=zstd.ZstdDecompressor()


def dtype_for(A):
    lo=int(A.min()) if A.size else 0
    hi=int(A.max()) if A.size else 0
    if lo>=-128 and hi<=127:return np.dtype('<i1'),1
    if lo>=-32768 and hi<=32767:return np.dtype('<i2'),2
    return np.dtype('<i4'),4


def transform(Q,name):
    Q=np.asarray(Q,np.int32)
    if name=='direct':
        return Q.copy()
    K=Q.copy()
    if name=='time_delta':
        K[:,1:]=Q[:,1:]-Q[:,:-1]
        return K
    if name=='space_delta':
        K[1:,:]=Q[1:,:]-Q[:-1,:]
        return K
    if name=='lorenzo2d':
        K[1:,1:]=Q[1:,1:]-Q[1:,:-1]-Q[:-1,1:]+Q[:-1,:-1]
        # First row and first column stay absolute, making the transform exact.
        return K
    raise ValueError(name)


def inverse(K,name):
    K=np.asarray(K,np.int32)
    if name=='direct':return K.copy()
    Q=np.empty_like(K)
    if name=='time_delta':
        return np.cumsum(K,axis=1,dtype=np.int32)
    if name=='space_delta':
        return np.cumsum(K,axis=0,dtype=np.int32)
    if name=='lorenzo2d':
        Q[0,:]=K[0,:]
        Q[:,0]=K[:,0]
        for c in range(1,K.shape[0]):
            for t in range(1,K.shape[1]):
                Q[c,t]=K[c,t]+Q[c,t-1]+Q[c-1,t]-Q[c-1,t-1]
        return Q
    raise ValueError(name)


def dense_codec(K):
    dt,w=dtype_for(K)
    raw=np.ascontiguousarray(K.astype(dt,copy=False)).tobytes()
    blob=ZC.compress(raw)
    dec=np.frombuffer(ZD.decompress(blob),dtype=dt,count=K.size).astype(np.int32).reshape(K.shape)
    if not np.array_equal(dec,K):raise RuntimeError('dense decode')
    return 24+len(blob),{'layout':'dense','dtype_bytes':w,'payload_bytes':len(blob)}


def sparse_codec(K):
    mask=K!=0
    vals=K[mask]
    dt,w=dtype_for(vals if vals.size else np.zeros(1,np.int32))
    mb=np.packbits(mask.ravel(),bitorder='little').tobytes()
    vb=np.ascontiguousarray(vals.astype(dt,copy=False)).tobytes()
    mz=ZC.compress(mb);vz=ZC.compress(vb)
    md=np.unpackbits(np.frombuffer(ZD.decompress(mz),np.uint8),bitorder='little',count=K.size).astype(bool)
    vd=np.frombuffer(ZD.decompress(vz),dtype=dt,count=int(md.sum())).astype(np.int32)
    dec=np.zeros(K.size,np.int32);dec[md]=vd;dec=dec.reshape(K.shape)
    if not np.array_equal(dec,K):raise RuntimeError('sparse decode')
    return 40+len(mz)+len(vz),{
        'layout':'sparse','dtype_bytes':w,'mask_bytes':len(mz),'value_bytes':len(vz),
        'nonzero_fraction':float(mask.mean()),'nonzero_count':int(mask.sum())}


def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;step=2.0*eps;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            Q=np.rint(X/step).astype(np.int32)
            nearest=Q.astype(np.float64)*step
            qerr=float(np.max(np.abs(X-nearest)))
            if qerr>eps*(1+3e-6):raise RuntimeError((region,'nearest hard',qerr,eps))

            cands=[]
            for tr in ('direct','time_delta','space_delta','lorenzo2d'):
                K=transform(Q,tr)
                for codec in (dense_codec,sparse_codec):
                    n,diag=codec(K)
                    # one selector byte plus common lattice/framing fields
                    n+=1
                    # Re-run the exact codec to obtain a decoded field, then invert.
                    # The codec functions already byte-decode and verify K; inverse is
                    # separately checked against the legal source lattice here.
                    Qd=inverse(K,tr)
                    if not np.array_equal(Qd,Q):raise RuntimeError((region,tr,'inverse'))
                    R=Qd.astype(np.float64)*step
                    me=float(np.max(np.abs(X-R)))
                    if me>eps*(1+3e-6):raise RuntimeError((region,tr,'hard',me,eps))
                    q={'transform':tr,'bytes':int(n),'bps':8*n/X.size,'maxerr':me,
                       'field_zero_fraction':float(np.mean(K==0)),'field_std':float(K.std())}
                    q.update(diag);cands.append(q)

            best=min(cands,key=lambda q:q['bytes'])

            # Incumbent and matched SZ3 controls on identical region/samples.
            _,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu);bb,bbit,bnb,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,hu)
            bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'incumbent hard',bme,eps))
            sz=0
            for t0 in range(0,NT,TB):
                n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)

            for q in cands:
                q['gain_vs_incumbent']=bb/q['bytes'];q['gain_vs_sz3']=sz/q['bytes']
            best=min(cands,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'lattice_step':step,
                 'source_lattice_zero_fraction':float(np.mean(Q==0)),
                 'source_lattice_temporal_change_fraction':float(np.mean(transform(Q,'time_delta')!=0)),
                 'incumbent':{'bytes':int(bb),'bps':8*bb/X.size,'zero_fraction':float(np.mean(Kb==0)),'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},'best_frozen':best,'candidates':cands}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)

        out={'global_std':gstd,'eps':eps,'step':step,'nt':NT,'channels':C,'rows':rows,
             'scope':'Apples-to-apples transfer of the successful raw-FORGE frozen-state principle to Imperial Valley. The source is reconstructed on the same legal 2*epsilon nearest lattice, then four exact lossless layouts are screened: direct Q, temporal delta, spatial delta and 2-D Lorenzo; each is coded both densely and as a sparse mask+nonzero stream with Zstd-22. All payloads are byte-decompressed, integer fields and inverse transforms are verified, and final source max error is checked. Incumbent Huber AR32 step267 cold-start arithmetic and matched SZ3 are rerun on identical 128x4096 hard/easy/medium/far regions. This asks whether any Imperial regime is secretly FORGE-like without changing the error contract. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_frozen_lattice_layout_gate.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
