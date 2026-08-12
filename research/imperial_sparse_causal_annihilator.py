import json, math, sys
import h5py, numpy as np, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
NC=128; NT=30000; TRAIN_END=4096; STEP=256; MAXDT=64
OMP_TAPS=28
SAFETY=1-1e-8
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()

def stats(d):
    s=ss=0.; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.,ss/n-m*m)))

def dtype_signed(a):
    a=np.asarray(a); mn=int(a.min()) if a.size else 0; mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max:return dt
    return np.dtype('<i8')

def zzenc(a):
    x=np.asarray(a,np.int64)
    return ((x<<1)^(x>>63)).astype(np.uint64)

def zzdec(z):
    z=np.asarray(z,np.uint64)
    return ((z>>1).astype(np.int64) ^ (-(z&1).astype(np.int64)))

def encode_array(a):
    a=np.asarray(a,np.int64)
    cands=[]
    dt=dtype_signed(a); raw=np.ascontiguousarray(a.astype(dt)).tobytes()
    b=ZC.compress(raw); cands.append((len(b)+16,'raw',b,{'dtype':dt.str,'shape':a.shape}))
    if a.shape[1]>1:
        d=a.copy(); d[:,1:]=a[:,1:]-a[:,:-1]
        dt2=dtype_signed(d); bb=ZC.compress(np.ascontiguousarray(d.astype(dt2)).tobytes())
        cands.append((len(bb)+16,'dt',bb,{'dtype':dt2.str,'shape':a.shape}))
    if a.shape[0]>1:
        d=a.copy(); d[1:,:]=a[1:,:]-a[:-1,:]
        dt3=dtype_signed(d); bb=ZC.compress(np.ascontiguousarray(d.astype(dt3)).tobytes())
        cands.append((len(bb)+16,'dc',bb,{'dtype':dt3.str,'shape':a.shape}))
    if a.shape[0]>1 and a.shape[1]>1:
        d=a.copy()
        d[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1]
        d[0,1:]=a[0,1:]-a[0,:-1]; d[1:,0]=a[1:,0]-a[:-1,0]
        dt4=dtype_signed(d); bb=ZC.compress(np.ascontiguousarray(d.astype(dt4)).tobytes())
        cands.append((len(bb)+16,'lor',bb,{'dtype':dt4.str,'shape':a.shape}))
    zz=zzenc(a); mx=int(zz.max()) if zz.size else 0
    udt=np.dtype('u1') if mx<256 else (np.dtype('<u2') if mx<65536 else np.dtype('<u4'))
    bb=ZC.compress(np.ascontiguousarray(zz.astype(udt)).tobytes())
    cands.append((len(bb)+16,'zz',bb,{'dtype':udt.str,'shape':a.shape}))
    nbits=max(1,mx.bit_length())
    for tr in (False,True):
        z=zz.T if tr else zz
        planes=[]
        for bit in range(nbits-1,-1,-1):
            planes.append(np.packbits(((z>>bit)&1).astype(np.uint8).ravel(),bitorder='little').tobytes())
        payload=b''.join(planes); bb=ZC.compress(payload)
        cands.append((len(bb)+20,'bpT' if tr else 'bp',bb,{'nbits':nbits,'shape':a.shape}))
    best=min(cands,key=lambda x:x[0])
    total,rep,blob,meta=best; shape=tuple(a.shape)
    raw=ZD.decompress(blob)
    if rep in ('raw','dt','dc','lor'):
        q=np.frombuffer(raw,dtype=np.dtype(meta['dtype'])).astype(np.int64).reshape(shape)
        if rep=='dt': q=np.cumsum(q,axis=1,dtype=np.int64)
        elif rep=='dc': q=np.cumsum(q,axis=0,dtype=np.int64)
        elif rep=='lor': q=np.cumsum(np.cumsum(q,axis=0,dtype=np.int64),axis=1,dtype=np.int64)
    elif rep=='zz':
        z=np.frombuffer(raw,dtype=np.dtype(meta['dtype'])).astype(np.uint64).reshape(shape); q=zzdec(z)
    else:
        nbits=meta['nbits']; tshape=(shape[1],shape[0]) if rep=='bpT' else shape
        n=tshape[0]*tshape[1]; per=(n+7)//8; z=np.zeros(n,np.uint64)
        for j,bit in enumerate(range(nbits-1,-1,-1)):
            p=raw[j*per:(j+1)*per]
            bits=np.unpackbits(np.frombuffer(p,np.uint8),bitorder='little')[:n].astype(np.uint64)
            z |= bits<<bit
        z=z.reshape(tshape)
        if rep=='bpT': z=z.T
        q=zzdec(z)
    if not np.array_equal(q,a): raise RuntimeError(('frame roundtrip',rep))
    return total,rep

def sz_tile(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32))
        cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg); R,_=sz.decompress(b,np.float32,A.shape)
        me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6): raise RuntimeError(('sz err',me,eps))
        row=(int(b.size),'T' if tr else 'CT')
        if best is None or row[0]<best[0]: best=row
    return best

def matched_sz3(X,eps):
    total=0; reps=[]
    for t0 in range(0,X.shape[1],1024):
        t1=min(X.shape[1],t0+1024)
        b,rep=sz_tile(X[:,t0:t1],eps); total+=b; reps.append(rep)
    return total,reps

def candidate_offsets():
    ds=(1,2,3,4,6,8,12,16,24,32,48,64)
    cs=(-8,-4,-2,-1,0,1,2,4,8)
    off=[(dt,dc) for dt in ds for dc in cs]
    off += [(0,-1),(0,-2),(0,-4),(0,-8)]
    return off

def design_matrix(X,offsets):
    ts=np.arange(MAXDT,TRAIN_END,4,dtype=np.int32)
    cs=np.arange(8,NC-8,2,dtype=np.int32)
    tt=np.repeat(ts,cs.size); cc=np.tile(cs,ts.size)
    y=X[cc,tt].astype(np.float64)
    A=np.empty((y.size,len(offsets)),np.float64)
    for j,(dt,dc) in enumerate(offsets): A[:,j]=X[cc+dc,tt-dt]
    return A,y

def fit_omp(X,ntaps):
    offsets=candidate_offsets(); A,y=design_matrix(X,offsets)
    ym=float(y.mean()); y0=y-ym
    means=A.mean(axis=0); scales=A.std(axis=0)+1e-9
    An=(A-means)/scales
    selected=[]; resid=y0.copy(); avail=np.ones(An.shape[1],bool)
    for _ in range(ntaps):
        corr=np.abs(An.T@resid); corr[~avail]=-1
        j=int(np.argmax(corr)); selected.append(j); avail[j]=False
        B=An[:,selected]; coef=np.linalg.lstsq(B,y0,rcond=1e-4)[0]; resid=y0-B@coef
    B=A[:,selected]; D=np.column_stack([np.ones(B.shape[0]),B])
    ridge=1e-6*np.eye(D.shape[1]); ridge[0,0]=0
    beta=np.linalg.solve(D.T@D+ridge,D.T@y).astype(np.float32)
    return [offsets[j] for j in selected],beta

def fit_ar16(X):
    offs=[(dt,0) for dt in range(1,17)]
    ts=np.arange(16,TRAIN_END,2,dtype=np.int32); cs=np.arange(0,NC,2,dtype=np.int32)
    tt=np.repeat(ts,cs.size); cc=np.tile(cs,ts.size); y=X[cc,tt].astype(np.float64)
    A=np.empty((y.size,len(offs)),np.float64)
    for j,(dt,dc) in enumerate(offs): A[:,j]=X[cc,tt-dt]
    D=np.column_stack([np.ones(A.shape[0]),A]); ridge=1e-6*np.eye(D.shape[1]);ridge[0,0]=0
    beta=np.linalg.solve(D.T@D+ridge,D.T@y).astype(np.float32)
    return offs,beta

def encode_model(X,offs,beta,eps,name):
    maxdt=max(dt for dt,dc in offs)
    R=np.empty_like(X,dtype=np.int64); K=np.zeros_like(X,dtype=np.int64)
    R[:,:maxdt]=(STEP*np.rint(X[:,:maxdt]/STEP)).astype(np.int64)
    if float(np.max(np.abs(X[:,:maxdt]-R[:,:maxdt])))>128.000001: raise RuntimeError('seed err')
    coeff=np.asarray(beta[1:],np.float32); intercept=float(np.float32(beta[0]))
    for t in range(maxdt,NT):
        for c in range(NC):
            p=intercept
            for a,(dt,dc) in zip(coeff,offs):
                cc=c+dc
                if cc<0 or cc>=NC: continue
                p += float(a)*float(R[cc,t-dt] if dt>0 else R[cc,t])
            pi=int(np.rint(np.clip(p,-200000.0,200000.0)))
            k=int(np.rint((float(X[c,t])-pi)/STEP)); K[c,t]=k; R[c,t]=pi+STEP*k
    me=float(np.max(np.abs(X-R)))
    if me>128.000001 or me>eps: raise RuntimeError(('hard error',name,me,eps))
    seed_bytes,seed_rep=encode_array((R[:,:maxdt]//STEP).astype(np.int64))
    inv_bytes=0; reps={}
    for t0 in range(maxdt,NT,1024):
        t1=min(NT,t0+1024); b,rep=encode_array(K[:,t0:t1]); inv_bytes+=b; reps[rep]=reps.get(rep,0)+1
    model_bytes=32+4*len(beta)+2*len(offs); total=model_bytes+seed_bytes+inv_bytes
    return {'name':name,'bytes':int(total),'bps':8*total/X.size,'model_bytes':model_bytes,'seed_bytes':seed_bytes,
            'innovation_bytes':inv_bytes,'seed_rep':seed_rep,'innovation_reps':reps,'maxerr':me,'taps':len(offs),
            'offsets':[list(x) for x in offs],'coefficients':[float(x) for x in beta]}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,gstd=stats(d); eps=.1*gstd; rows=[]
        for label,c0 in REGIONS:
            X=np.asarray(d[:,c0:c0+NC],np.float64).T
            szb,_=matched_sz3(X,eps); ar_off,ar_b=fit_ar16(X); sp_off,sp_b=fit_omp(X,OMP_TAPS)
            ar=encode_model(X,ar_off,ar_b,eps,'ar16'); sp=encode_model(X,sp_off,sp_b,eps,'sparse_spacetime_annihilator')
            row={'region':label,'c0':c0,'samples':int(X.size),'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),
                 'sz3_bytes':int(szb),'sz3_bps':8*szb/X.size,'ar16':ar,'stencil':sp,
                 'stencil_gain_vs_ar16':ar['bytes']/sp['bytes'],'stencil_gain_vs_sz3':szb/sp['bytes'],'ar16_gain_vs_sz3':szb/ar['bytes']}
            rows.append(row); print(json.dumps({'region':label,'sz3_bps':row['sz3_bps'],'ar16_bps':ar['bps'],'stencil_bps':sp['bps'],
                'stencil_vs_ar16':row['stencil_gain_vs_ar16'],'stencil_vs_sz3':row['stencil_gain_vs_sz3'],'offsets':sp_off}),flush=True)
        n=sum(r['samples'] for r in rows); szb=sum(r['sz3_bytes'] for r in rows); ab=sum(r['ar16']['bytes'] for r in rows); sb=sum(r['stencil']['bytes'] for r in rows)
        out={'global_std':gstd,'eps':eps,'regions':[x[0] for x in REGIONS],'width':NC,'time_samples':NT,'train_samples':TRAIN_END,'omp_taps':OMP_TAPS,
             'candidate_max_time_lag':MAXDT,'aggregate':{'samples':n,'sz3_bytes':szb,'ar16_bytes':ab,'stencil_bytes':sb,'sz3_bps':8*szb/n,
             'ar16_bps':8*ab/n,'stencil_bps':8*sb/n,'ar16_gain_vs_sz3':szb/ab,'stencil_gain_vs_sz3':szb/sb,'stencil_gain_vs_ar16':ab/sb,
             'strict_2x_sz3_target_bps':(8*szb/n)/2},'rows':rows,
             'scope':'Persistent sparse causal space-time annihilator screen. One 128-channel model per region is selected/fitted only from the first 4096 source samples; tap coordinates and float32 coefficients are fully charged once. Candidate causal lags span past times through 64 samples and +/-8 channels plus same-time left taps. OMP chooses 28 taps, then the decoder recursively predicts the complete 30000-sample region and receives exact 256-step innovations. Seed, innovation frames and model bytes are all counted; encoded arrays are byte-decoded internally before acceptance; max reconstruction error is <=128, below the unchanged global 10%-std public epsilon. AR16 and matched SZ3 on identical 128x1024 tiling are rerun. No AI; four-region screen, not whole-array claim.'}
        print(json.dumps({'aggregate':out['aggregate']},indent=2),flush=True); json.dump(out,open('imperial_sparse_causal_annihilator.json','w'),indent=2)

if __name__=='__main__': main(sys.argv[1])
