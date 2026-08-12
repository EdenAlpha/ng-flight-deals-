import json,math,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=64
STARTS=(512,1280,2560,4480,6656)
BS=(256,512)
KS=(1,2,4,8,16)
ALPHAS=(0.25,0.5,1.0)
SAFETY=1-1e-5
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()


def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))


def previous_reconstruction(d,c0,c1,eps):
    x=np.asarray(d[:,c0:c1],np.float64);step=2*eps*SAFETY
    return np.rint(x/step).astype(np.int32).astype(np.float64)*step


def windows(x,B):
    nwin=(x.shape[0]+B-1)//B;out=np.zeros((nwin,B,x.shape[1]),np.float64)
    for w in range(nwin):
        a=w*B;b=min(x.shape[0],a+B);out[w,:b-a]=x[a:b]
    return out


def train_frequency_modes(prev,B,Kmax):
    # Stack non-overlapping STFT snapshots from two already-decoded minutes.
    FF=[]
    for x in prev:
        w=windows(x,B);FF.append(np.fft.rfft(w,axis=1))
    F=np.concatenate(FF,axis=0) # windows,freq,channel
    nw,nf,c=F.shape
    U=np.empty((nf,c,Kmax),np.complex128);sig=np.empty((nf,Kmax),np.float64)
    for f in range(nf):
        A=F[:,f,:]
        cov=(A.conj().T@A)/max(1,A.shape[0]);cov=(cov+cov.conj().T)*0.5
        e,V=np.linalg.eigh(cov);ix=np.argsort(e)[::-1][:Kmax];V=V[:,ix];e=np.maximum(e[ix],0.)
        # Deterministic complex phase convention.
        for k in range(V.shape[1]):
            j=int(np.argmax(np.abs(V[:,k])));ph=np.angle(V[j,k]);V[:,k]*=np.exp(-1j*ph)
            if V[j,k].real<0:V[:,k]*=-1
        U[f]=V;sig[f]=np.sqrt(e)
    # Prior coefficient scales are decoder-known and remove all transmitted quantizer scales.
    return U,sig


def signed_dtype(a):
    mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max:return dt
    return np.dtype('<i8')


def encode_int(a):
    a=np.asarray(a,np.int32);cands=[]
    reps={'raw':a}
    if a.ndim>=2:
        x=a.copy();x[1:]-=a[:-1];reps['d0']=x
    for name,x in reps.items():
        dt=signed_dtype(x);blob=ZC.compress(np.ascontiguousarray(x).astype(dt).tobytes())
        rr=np.frombuffer(ZD.decompress(blob),dtype=dt,count=x.size).astype(np.int32).reshape(x.shape)
        dec=rr if name=='raw' else np.cumsum(rr,axis=0,dtype=np.int32)
        if not np.array_equal(dec,a):raise RuntimeError(('roundtrip',name))
        cands.append((len(blob)+48,name,dt.str))
    return min(cands)


def encode_correction(k):
    k=np.asarray(k,np.int32);cands=[]
    reps={'raw':k}
    dt=k.copy();dt[1:]-=k[:-1];reps['dt']=dt
    dc=k.copy();dc[:,1:]-=k[:,:-1];reps['dc']=dc
    lor=k.copy();lor[1:,1:]=k[1:,1:]-k[:-1,1:]-k[1:,:-1]+k[:-1,:-1];reps['lorenzo']=lor
    for name,a in reps.items():
        typ=signed_dtype(a);blob=ZC.compress(np.ascontiguousarray(a).astype(typ).tobytes());cands.append((len(blob)+48,name,typ.str))
    nz=k!=0;sup=ZC.compress(np.packbits(nz.astype(np.uint8).ravel(),bitorder='little').tobytes());v=k[nz];typ=signed_dtype(v);vb=ZC.compress(v.astype(typ).tobytes()) if v.size else b''
    cands.append((len(sup)+len(vb)+80,'sparse',typ.str))
    return min(cands),float(np.mean(nz))


def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        row=(int(b.size),'T' if tr else 'TC')
        if best is None or row[0]<best[0]:best=row
    return best


def candidate(X,U,sig,B,K,alpha,eps):
    W=windows(X,B);F=np.fft.rfft(W,axis=1);nf=F.shape[1];nwin=F.shape[0]
    Qr=np.zeros((nwin,nf,K),np.int32);Qi=np.zeros_like(Qr);Fh=np.zeros_like(F)
    for f in range(nf):
        V=U[f,:,:K];coef=F[:,f,:]@V.conj()
        # Prior eigen-amplitude scale; alpha controls target coefficient granularity.
        sc=np.maximum(alpha*sig[f,:K],eps*math.sqrt(B)/64.0)
        qr=np.rint(coef.real/sc).astype(np.int32);qi=np.rint(coef.imag/sc).astype(np.int32)
        Qr[:,f]=qr;Qi[:,f]=qi
        ch=(qr.astype(np.float64)+1j*qi.astype(np.float64))*sc
        Fh[:,f,:]=ch@V.T
    # rfft endpoint imaginary parts must be real for a decoder-identical irfft.
    Fh[:,0,:]=Fh[:,0,:].real
    if B%2==0:Fh[:,-1,:]=Fh[:,-1,:].real
    P=np.fft.irfft(Fh,n=B,axis=1).reshape(-1,C)[:X.shape[0]]
    mb1=encode_int(Qr);mb2=encode_int(Qi);model=mb1[0]+mb2[0]+64
    step=2*eps*SAFETY;corr=np.rint((X-P)/step).astype(np.int32);cb,nz=encode_correction(corr);R=P+step*corr
    me=float(np.max(np.abs(X-R)))
    if not np.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard',B,K,alpha,me,eps))
    total=model+cb[0]+96
    return {'B':B,'K':K,'alpha':alpha,'bytes':total,'model_bytes':model,'correction_bytes':cb[0],'correction_rep':cb[1],'correction_nonzero':nz,'maxerr':me,
            'median_prior_mode_energy_fraction':float(np.median(np.sum(sig[:,:K]**2,axis=1)/np.maximum(np.sum(sig**2,axis=1),1e-30)))}


def main(paths):
    fs=[h5py.File(p,'r') for p in paths]
    try:
        ds=[f['Acoustic'] for f in fs];stds=[stats(d)[1] for d in ds];epss=[.1*s for s in stds];eps=epss[-1]
        rows=[];tiles=[]
        for c0 in STARTS:
            c1=c0+C;prev=[previous_reconstruction(ds[i],c0,c1,epss[i]) for i in (0,1)];X=np.asarray(ds[2][:,c0:c1],np.float64);sb=szrun(X,eps);raw=X.size*2
            tiles.append({'c0':c0,'c1':c1,'local_std':float(X.std()),'sz3_bytes':sb[0],'sz3_orientation':sb[1],'raw':raw})
            for B in BS:
                U,sig=train_frequency_modes(prev,B,max(KS))
                for K in KS:
                    for alpha in ALPHAS:
                        r=candidate(X,U,sig,B,K,alpha,eps);r.update({'c0':c0,'c1':c1,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
        combos=[]
        for B in BS:
            for K in KS:
                for alpha in ALPHAS:
                    rr=[r for r in rows if r['B']==B and r['K']==K and r['alpha']==alpha];b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=sum(t['raw']//2 for t in tiles)
                    combos.append({'B':B,'K':K,'alpha':alpha,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/n,'model_bytes':sum(r['model_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),'min_region_gain':min(r['gain_vs_sz3'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero'] for r in rr])),'median_prior_mode_energy_fraction':float(np.median([r['median_prior_mode_energy_fraction'] for r in rr]))})
        combos.sort(key=lambda r:r['bytes'])
        out={'files':3,'shape':[30000,6912],'width':C,'starts':list(STARTS),'stds':stds,'eps':epss,'B_values':list(BS),'K_values':list(KS),'alphas':list(ALPHAS),'tiles':tiles,'combos':combos,'best':combos[:12],'rows':rows,
             'fullfile_sz3_bps_reference':3.331839158950617,'strict_2x_target_bps':1.6659195794753086,
             'scope':'Cross-minute frequency-conditioned spatial modal codec. Two previous nearest-hard-error decoded minutes define a complex spatial eigenbasis independently at every STFT frequency and all coefficient scales, so no basis/scale bytes are transmitted. Target modal integer coefficients and exact 2epsilon measurement-domain correction are actually serialized and counted; matched SZ3 is rerun on each identical full-minute 64-channel region. Final samples satisfy the unchanged target-minute 10%-std max error. Exploratory screen, no whole-file claim.'}
        print(json.dumps({'best':combos[:12],'tiles':tiles},indent=2),flush=True);json.dump(out,open('imperial_crossminute_frequency_spatial_modes.json','w'),indent=2)
    finally:
        for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
