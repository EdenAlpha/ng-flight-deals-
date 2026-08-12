import json,math,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128
CBS=(0,4,10,20,26,35,46,53)
KS=(8,16,32,64,128)
ALPHAS=(0.5,1.0,2.0,4.0)
POWERS=(0.0,0.5,1.0)
SAFETY=1-1e-5
ZC=zstd.ZstdCompressor(level=19)
ZD=zstd.ZstdDecompressor()


def stats(d):
    s=ss=0.0;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.0,ss/n-m*m)))


def decoded_nearest_block(d,c0,c1,eps):
    # Decoder-honest previous-minute representation: the previous source is first
    # mapped to its own public hard-error lattice, so the target basis never needs
    # access to unreconstructable previous raw values.
    x=np.asarray(d[:,c0:c1],np.float64)
    step=2*eps*(1-1e-5)
    q=np.rint(x/step).astype(np.int32)
    return q.astype(np.float64)*step


def train_basis(ds,eps_prev,c0,c1):
    n=0
    sm=np.zeros(c1-c0,np.float64)
    ss=np.zeros((c1-c0,c1-c0),np.float64)
    # Two previous decoded minutes. Process each independently to limit peak memory.
    for d,e in zip(ds,eps_prev):
        x=decoded_nearest_block(d,c0,c1,e)
        sm+=x.sum(axis=0);ss+=x.T@x;n+=x.shape[0]
    mu=sm/n
    cov=ss/n-np.outer(mu,mu)
    cov=(cov+cov.T)*0.5
    w,U=np.linalg.eigh(cov)
    order=np.argsort(w)[::-1]
    w=np.maximum(w[order],0.0);U=U[:,order]
    # Deterministic sign convention removes the arbitrary eigenvector sign.
    for j in range(U.shape[1]):
        i=int(np.argmax(np.abs(U[:,j])))
        if U[i,j]<0:U[:,j]*=-1
    sig=np.sqrt(w)
    return mu,U,sig


def smallest_signed_dtype(a):
    mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max:return dt
    return np.dtype('<i8')


def encode_matrix_exact(q):
    q=np.asarray(q,np.int32)
    cands=[]
    # Coefficient-major layout keeps each eigenmode contiguous in the byte stream.
    for name,a in [('raw',q.T),('dt',np.concatenate([q[:1],np.diff(q,axis=0)],axis=0).T)]:
        dt=smallest_signed_dtype(a)
        raw=np.ascontiguousarray(a).astype(dt).tobytes()
        blob=ZC.compress(raw)
        rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape)
        if name=='raw':dec=rr.T
        else:dec=np.cumsum(rr.T,axis=0,dtype=np.int32)
        if not np.array_equal(dec,q):raise RuntimeError(('model roundtrip',name))
        cands.append((len(blob)+48,name,dt.str))
    return min(cands)


def encode_int_field(k):
    k=np.asarray(k,np.int32)
    cands=[]
    reps={'raw':k}
    dt=k.copy();dt[1:]-=k[:-1];reps['dt']=dt
    dc=k.copy();dc[:,1:]-=k[:,:-1];reps['dc']=dc
    lor=k.copy();lor[1:,1:]=k[1:,1:]-k[:-1,1:]-k[1:,:-1]+k[:-1,:-1];reps['lorenzo']=lor
    for name,a in reps.items():
        dtype=smallest_signed_dtype(a)
        blob=ZC.compress(np.ascontiguousarray(a).astype(dtype).tobytes())
        rr=np.frombuffer(ZD.decompress(blob),dtype=dtype,count=a.size).astype(np.int32).reshape(a.shape)
        if name=='raw':dec=rr
        elif name=='dt':dec=np.cumsum(rr,axis=0,dtype=np.int32)
        elif name=='dc':dec=np.cumsum(rr,axis=1,dtype=np.int32)
        else:
            dec=rr.copy()
            for i in range(1,dec.shape[0]):
                for j in range(1,dec.shape[1]):
                    dec[i,j]=rr[i,j]+dec[i-1,j]+dec[i,j-1]-dec[i-1,j-1]
        if not np.array_equal(dec,k):raise RuntimeError(('corr roundtrip',name))
        cands.append((len(blob)+48,name,dtype.str))
    nz=k!=0
    support=ZC.compress(np.packbits(nz.astype(np.uint8).ravel(),bitorder='little').tobytes())
    vals=k[nz];dtype=smallest_signed_dtype(vals)
    vb=ZC.compress(vals.astype(dtype).tobytes()) if vals.size else b''
    # Explicit support+values decoder audit.
    mask=np.unpackbits(np.frombuffer(ZD.decompress(support),np.uint8),bitorder='little')[:k.size].astype(bool).reshape(k.shape)
    vv=np.frombuffer(ZD.decompress(vb),dtype=dtype).astype(np.int32) if vals.size else np.empty(0,np.int32)
    dec=np.zeros_like(k);dec[mask]=vv
    if not np.array_equal(dec,k):raise RuntimeError('sparse correction roundtrip')
    cands.append((len(support)+len(vb)+80,'sparse',dtype.str))
    return min(cands),float(np.mean(nz))


def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32))
        cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape)
        me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
        row=(int(b.size),'T' if tr else 'CT',me)
        if best is None or row[0]<best[0]:best=row
    return best


def one_candidate(X,mu,U,sig,eps,K,alpha,power):
    Uk=U[:,:K]
    Y=(X-mu)@Uk
    s=sig[:K].copy()
    med=float(np.median(s[s>0])) if np.any(s>0) else 1.0
    rel=np.clip(s/max(med,1e-12),0.0625,16.0)
    delta=alpha*eps*np.power(rel,power)
    delta=np.maximum(delta,eps/64.0)
    q=np.rint(Y/delta).astype(np.int32)
    mb=encode_matrix_exact(q)
    Yh=q.astype(np.float64)*delta
    R=Yh@Uk.T+mu
    step=2*eps*SAFETY
    corr=np.rint((X-R)/step).astype(np.int32)
    cb,nzf=encode_int_field(corr)
    F=R+step*corr
    me=float(np.max(np.abs(X-F)))
    if not np.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard error',K,alpha,power,me,eps))
    total=mb[0]+cb[0]+96
    return {'K':K,'alpha':alpha,'power':power,'bytes':total,'model_bytes':mb[0],'model_rep':mb[1],'model_dtype':mb[2],
            'correction_bytes':cb[0],'correction_rep':cb[1],'correction_dtype':cb[2],
            'correction_nonzero_fraction':nzf,'maxerr':me,
            'prior_modes_energy_fraction':float(np.sum(sig[:K]**2)/max(np.sum(sig**2),1e-30)),
            'delta_min':float(delta.min()),'delta_median':float(np.median(delta)),'delta_max':float(delta.max())}


def main(paths):
    fs=[h5py.File(p,'r') for p in paths]
    try:
        ds=[f['Acoustic'] for f in fs]
        if any(tuple(d.shape)!=(30000,6912) for d in ds):raise RuntimeError('shape drift')
        stds=[stats(d)[1] for d in ds];epss=[.1*s for s in stds]
        target=ds[-1];eps=epss[-1]
        rows=[];tiles=[]
        for cb in CBS:
            c0=cb*C;c1=c0+C
            mu,U,sig=train_basis(ds[:2],epss[:2],c0,c1)
            X=np.asarray(target[:,c0:c1],np.float64)
            sb=szrun(X,eps);raw=X.size*2
            tiles.append({'cb':cb,'c0':c0,'c1':c1,'raw':raw,'sz3_bytes':sb[0],'sz3_orientation':sb[1],'sz3_maxerr':sb[2],
                          'local_std':float(X.std()),'eps_over_local_std':eps/max(float(X.std()),1e-30),
                          'prior_top8_energy':float(np.sum(sig[:8]**2)/max(np.sum(sig**2),1e-30)),
                          'prior_top16_energy':float(np.sum(sig[:16]**2)/max(np.sum(sig**2),1e-30)),
                          'prior_top32_energy':float(np.sum(sig[:32]**2)/max(np.sum(sig**2),1e-30))})
            for K in KS:
                for alpha in ALPHAS:
                    for power in POWERS:
                        r=one_candidate(X,mu,U,sig,eps,K,alpha,power)
                        r.update({'cb':cb,'c0':c0,'c1':c1,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes'],
                                  'bps':8*r['bytes']/X.size,'ratio_raw':raw/r['bytes']})
                        rows.append(r)
        combos=[]
        for K in KS:
            for alpha in ALPHAS:
                for power in POWERS:
                    rr=[r for r in rows if r['K']==K and r['alpha']==alpha and r['power']==power]
                    b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=sum(t['raw']//2 for t in tiles)
                    combos.append({'K':K,'alpha':alpha,'power':power,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/n,
                                   'min_block_gain':min(r['gain_vs_sz3'] for r in rr),'median_block_gain':float(np.median([r['gain_vs_sz3'] for r in rr])),
                                   'model_bytes':sum(r['model_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),
                                   'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr]))})
        combos.sort(key=lambda r:r['bytes'])
        out={'files':3,'shape':[30000,6912],'stds':stds,'eps':epss,'blocks':list(CBS),'K_values':list(KS),'alphas':list(ALPHAS),'powers':list(POWERS),
             'tiles':tiles,'fixed_definition_combos':combos,'best_fixed':combos[:12],'rows':rows,
             'fullfile_sz3_bps_reference':3.331839158950617,'strict_2x_fullfile_target_bps':1.6659195794753086,
             'scope':'Decoder-known cross-minute spatial eigenbasis codec screen. Spatial mean/basis/eigenvalue scales are derived only from nearest-hard-error reconstructions of the two already-decoded previous minutes. Target coefficients and exact 2epsilon correction frames are actually Zstd serialized, byte-decoded, and final target samples are hard-error verified. No basis/model bytes are transmitted because the sequential decoder recomputes them from previous reconstructions. Eight fixed 128-channel regions span hard/easy/medium cable regimes. Exploratory screen; no whole-file claim.'}
        print(json.dumps({'best':combos[:12],'tiles':tiles},indent=2),flush=True)
        json.dump(out,open('imperial_crossminute_spatial_eigenbasis.json','w'),indent=2)
    finally:
        for f in fs:f.close()

if __name__=='__main__':main(sys.argv[1:])
