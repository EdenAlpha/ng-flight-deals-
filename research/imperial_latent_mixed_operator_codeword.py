import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5
RANKS=(2,4,8,16)
ROUNDS=(0,2,8)
SPECS=(('easy',14488,1696),('medium',14488,3392),('hard',14488,6784))
Z=zstd.ZstdCompressor(level=19)

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def integ2(X):
    return np.cumsum(np.cumsum(X,axis=1,dtype=np.float64),axis=0,dtype=np.float64)

def diff2(U):
    V=U.copy()
    V[:,1:]=U[:,1:]-U[:,:-1]
    X=V.copy()
    X[1:]=V[1:]-V[:-1]
    return X

def rank_basis(U,k):
    G=U@U.T
    w,Q=np.linalg.eigh(G);Q=Q[:,-k:]
    H=Q.T@U
    return Q,H,Q@H

def box_project_potential(U,X,b):
    Y=diff2(U)
    Y=np.clip(Y,X-b,X+b)
    return integ2(Y)

def project_candidate(X,b,k,rounds,method):
    U=integ2(X)
    Zs=U.copy();best=None
    for it in range(rounds+1):
        Q,H,R=rank_basis(Zs,k)
        Y=diff2(R)
        excess=np.maximum(np.abs(Y-X)-b,0.0)
        row=(float(excess.max()),float(np.mean(excess>0)),float(np.sqrt(np.mean((Y-X)**2))),it,Q,H,R)
        if best is None or row[:3]<best[:3]:best=row
        if it==rounds:break
        if method=='ap':
            Zs=box_project_potential(R,X,b)
        else:
            B=box_project_potential(Zs,X,b)
            _,_,A=rank_basis(2*B-Zs,k)
            Zs=Zs+A-B
    return best

def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32))
        cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        bb,_=sz.compress(A,cfg);RR,_=sz.decompress(bb,np.float32,A.shape)
        me=float(np.max(np.abs(A-RR)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(bb.size)<best:best=int(bb.size)
    return best

def zblob(a):
    return Z.compress(np.ascontiguousarray(a).tobytes())

def factor_decode(Q,H,mode):
    k=Q.shape[1]
    if mode=='f16':
        # Scale each component before float16 storage. Raw H can exceed float16 range.
        Qs=np.maximum(np.max(np.abs(Q),axis=0),1e-30)
        Hs=np.maximum(np.max(np.abs(H),axis=1),1e-30)
        Qn=(Q/Qs).astype(np.float16);Hn=(H/Hs[:,None]).astype(np.float16)
        if not np.all(np.isfinite(Qn)) or not np.all(np.isfinite(Hn)):
            raise RuntimeError('nonfinite scaled float16 factors')
        qb=zblob(Qn);hb=zblob(Hn);D=zstd.ZstdDecompressor()
        Qd=np.frombuffer(D.decompress(qb),np.float16).astype(np.float64).reshape(Q.shape)*Qs
        Hd=np.frombuffer(D.decompress(hb),np.float16).astype(np.float64).reshape(H.shape)*Hs[:,None]
        R=Qd@Hd
        if not np.all(np.isfinite(R)):raise RuntimeError('nonfinite decoded f16 factor product')
        return R,len(qb)+len(hb)+8*k+64
    bits=8 if mode=='q8q8' else 16
    qmax=127
    Qs=np.maximum(np.max(np.abs(Q),axis=0)/qmax,1e-30)
    Qq=np.rint(Q/Qs).clip(-127,127).astype(np.int8)
    if bits==8:
        hmax=127;Hdt=np.int8
    else:
        hmax=32767;Hdt=np.int16
    Hs=np.maximum(np.max(np.abs(H),axis=1)/hmax,1e-30)
    Hq=np.rint(H/Hs[:,None]).clip(-hmax,hmax).astype(Hdt)
    qb=zblob(Qq);hb=zblob(Hq)
    Qd=Qq.astype(np.float64)*Qs
    Hd=Hq.astype(np.float64)*Hs[:,None]
    overhead=8*k+64
    return Qd@Hd,len(qb)+len(hb)+overhead

def encode_corr(K):
    K=np.asarray(K,np.int32);c=[]
    mn=int(K.min());mx=int(K.max())
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            c.append((len(zblob(K.astype(dt)))+24,'signed_'+dt.str));break
    zz=((K.astype(np.int64)<<1)^(K.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max())
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:
            c.append((len(zblob(zz.astype(dt)))+24,'zigzag_'+dt.str));break
    nz=K!=0;sup=zblob(np.packbits(nz.ravel().astype(np.uint8),bitorder='little'))
    vals=K[nz]
    if vals.size:
        mn=int(vals.min());mx=int(vals.max())
        for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
            if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
                c.append((len(sup)+len(zblob(vals.astype(dt)))+48,'sparse_'+dt.str));break
    else:c.append((len(sup)+48,'sparse_empty'))
    return min(c),float(np.mean(nz))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;b=eps*SAFETY;step=2*b
        rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T
            sb=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'raw_bytes':X.size*2})
            U0=integ2(X);s=np.linalg.svd(U0,compute_uv=False);tot=float((s*s).sum())
            for k in RANKS:
                for method in ('ap','dr'):
                    for rounds in ROUNDS:
                        v,frac,rm,it,Q,H,R=project_candidate(X,b,k,rounds,method)
                        for mode in ('f16','q8q8','q8q16'):
                            Rd,fb=factor_decode(Q,H,mode)
                            P=diff2(Rd)
                            if not np.all(np.isfinite(P)):raise RuntimeError(('nonfinite prediction',name,k,method,rounds,mode))
                            Qcorr=(X-P)/step
                            if not np.all(np.isfinite(Qcorr)):raise RuntimeError(('nonfinite correction coordinate',name,k,method,rounds,mode))
                            K=np.rint(Qcorr).astype(np.int32)
                            cb,nzf=encode_corr(K)
                            Xh=P+step*K
                            if not np.all(np.isfinite(Xh)):raise RuntimeError(('nonfinite reconstruction',name,k,method,rounds,mode))
                            me=float(np.max(np.abs(X-Xh)))
                            if not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard',name,k,method,rounds,mode,me,eps))
                            totalb=fb+cb[0]+64
                            rows.append({'tile':name,'rank':k,'method':method,'rounds':rounds,'factor_mode':mode,
                                         'prequant_max_excess':v,'prequant_violation_fraction':frac,'prequant_rmse_over_eps':rm/eps,
                                         'factor_bytes':fb,'correction_bytes':cb[0],'correction_rep':cb[1],
                                         'correction_nonzero_fraction':nzf,'total_bytes':totalb,'sz3_bytes':sb,
                                         'gain_vs_sz3':sb/totalb,'bps':8*totalb/X.size,'maxerr':me,
                                         'potential_topk_energy':float((s[:k]@s[:k])/tot)})
        combos=[]
        for k in RANKS:
            for method in ('ap','dr'):
                for rounds in ROUNDS:
                    for mode in ('f16','q8q8','q8q16'):
                        rr=[r for r in rows if r['rank']==k and r['method']==method and r['rounds']==rounds and r['factor_mode']==mode]
                        bsum=sum(r['total_bytes'] for r in rr);ss=sum(r['sz3_bytes'] for r in rr);ns=C*T*len(rr)
                        combos.append({'rank':k,'method':method,'rounds':rounds,'factor_mode':mode,'bytes':bsum,
                                       'sz3_bytes':ss,'gain_vs_sz3':ss/bsum,'bps':8*bsum/ns,
                                       'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),
                                       'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),
                                       'factor_bytes':sum(r['factor_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr)})
        combos.sort(key=lambda r:r['bytes'])
        out={'std':std,'eps':eps,'bound':b,'shape':[C,T],'two_x_sz3_target_bps':1.6659195794753086,
             'combos':combos,'rows':rows,'scope':'Latent mixed-potential operator code. The encoder searches for a low-rank double-integrated field; only its mixed derivative must satisfy the public hard-error box. Quantized transmitted factors are decoded first, then a fully counted exact 2epsilon measurement-domain correction is applied. Three precommitted easy/medium/hard tiles, one fixed definition in aggregate. Nonfinite decoded factors/predictions/reconstructions are fatal. No AI.'}
        print(json.dumps({'best':combos[:12]},indent=2),flush=True)
        json.dump(out,open('imperial_latent_mixed_operator_codeword.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
