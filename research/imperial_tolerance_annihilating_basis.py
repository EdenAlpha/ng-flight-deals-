import json, math, sys
import h5py
import numpy as np
import zstandard as zstd
from scipy.optimize import linprog
from scipy.linalg import hadamard, dct

SAFETY=1-1e-5
Z=zstd.ZstdCompressor(level=19)
REGIONS=(0,2304,4606,6848)
TIMES=(1000,6000,11000,16000,21000,27000)
H=8; W=8; N=H*W
TARGET_BPS=1.6659195794753086
SZ3_BPS=3.331839158950617


def stats(d):
    s=ss=0.0;n=0
    for t0 in range(0,d.shape[0],2048):
        x=np.asarray(d[t0:min(t0+2048,d.shape[0])],np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n
    return m,math.sqrt(max(0.0,ss/n-m*m))


def bases():
    h=hadamard(N).astype(np.float64)/math.sqrt(N)
    d8=dct(np.eye(8),type=2,norm='ortho',axis=0)
    d2=np.kron(d8,d8)
    # Decoder-known union dictionary. Each column is a unit atom.
    u=np.concatenate([h,d2],axis=1)
    return [('hadamard64',h),('dct2d_8x8',d2),('union_hadamard_dct2d',u)]


def l1_box(x,D,bound):
    # min ||a||_1 subject to x-bound <= D a <= x+bound.
    n,m=D.shape
    c=np.r_[np.zeros(m),np.ones(m)]
    I=np.eye(m)
    A=np.vstack([
        np.c_[ I,-I],
        np.c_[-I,-I],
        np.c_[ D,np.zeros((n,m))],
        np.c_[-D,np.zeros((n,m))],
    ])
    rhs=np.r_[np.zeros(m),np.zeros(m),x+bound,-x+bound]
    res=linprog(c,A_ub=A,b_ub=rhs,bounds=[(None,None)]*m+[(0,None)]*m,method='highs',options={'presolve':True})
    if not res.success: raise RuntimeError(('LP failed',res.message))
    a=res.x[:m]
    # HiGHS leaves numerical dust. Dropping it is safe because the exact
    # post-serialization correction below is authoritative.
    scale=max(1.0,float(np.max(np.abs(a))))
    a[np.abs(a)<scale*1e-10]=0.0
    return a


def encode_correction(k):
    k=np.asarray(k,np.int32).ravel(); cands=[]
    mn=int(k.min()) if k.size else 0; mx=int(k.max()) if k.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            cands.append((len(Z.compress(k.astype(dt).tobytes())),'dense_'+dt.str));break
    zz=((k.astype(np.int64)<<1)^(k.astype(np.int64)>>63)).astype(np.uint64)
    mz=int(zz.max()) if zz.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:
            cands.append((len(Z.compress(zz.astype(dt).tobytes())),'zigzag_'+dt.str));break
    nz=k!=0
    sup=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes())
    v=k[nz]; vmn=int(v.min()) if v.size else 0; vmx=int(v.max()) if v.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if vmn>=np.iinfo(dt).min and vmx<=np.iinfo(dt).max:
            cands.append((len(sup)+len(Z.compress(v.astype(dt).tobytes())),'sparse_'+dt.str));break
    return min(cands)


def materialize(a,mode):
    nz=a!=0
    vals=a[nz]
    if mode=='fp32':
        return nz,vals.astype('<f4'),None,vals.astype(np.float32).astype(np.float64)
    mx=float(np.max(np.abs(vals))) if vals.size else 0.0
    lim=127 if mode=='q8' else 32767
    scale=(mx/lim) if mx>0 else 1.0
    q=np.rint(vals/scale)
    if mode=='q8': q=q.astype(np.int8)
    else: q=q.astype('<i2')
    dec=q.astype(np.float64)*np.float32(scale)
    return nz,q,np.float32(scale),dec


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY;step=2*bound
        blocks=[]
        for c0 in REGIONS:
            for t0 in TIMES:
                X=np.asarray(d[t0:t0+W,c0:c0+H],np.float64).T
                if X.shape!=(H,W):raise RuntimeError(('shape',c0,t0,X.shape))
                blocks.append((c0,t0,X.ravel()))
        rows=[]
        for bname,D in bases():
            solved=[]
            for c0,t0,x in blocks:
                a=l1_box(x,D,bound)
                raw=D@a
                solved.append((c0,t0,x,a))
            for mode in ('fp32','q16','q8'):
                masks=[];values=[];scales=[];corrs=[];nonzero=[];legal_before=[];maxerrs=[]
                for c0,t0,x,a in solved:
                    mask,q,scale,decvals=materialize(a,mode)
                    aq=np.zeros(D.shape[1],np.float64);aq[mask]=decvals
                    r=D@aq
                    legal_before.append(float(np.mean(np.abs(x-r)<=eps)))
                    k=np.rint((x-r)/step).astype(np.int32)
                    rr=r+step*k
                    me=float(np.max(np.abs(x-rr)))
                    if not np.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard error',bname,mode,c0,t0,me,eps))
                    masks.append(np.packbits(mask.astype(np.uint8),bitorder='little'))
                    values.append(q)
                    if scale is not None:scales.append(scale)
                    corrs.append(k);nonzero.append(int(mask.sum()));maxerrs.append(me)
                mask_blob=Z.compress(np.concatenate(masks).tobytes())
                if mode=='fp32': val_raw=np.concatenate(values).astype('<f4').tobytes()
                elif mode=='q16': val_raw=np.concatenate(values).astype('<i2').tobytes()
                else: val_raw=np.concatenate(values).astype(np.int8).tobytes()
                val_blob=Z.compress(val_raw)
                scale_blob=Z.compress(np.asarray(scales,dtype='<f4').tobytes()) if scales else b''
                corr_bytes,corr_rep=encode_correction(np.concatenate(corrs))
                total=len(mask_blob)+len(val_blob)+len(scale_blob)+corr_bytes+96
                samples=len(blocks)*N
                rows.append({'basis':bname,'atoms':int(D.shape[1]),'mode':mode,'blocks':len(blocks),'samples':samples,
                    'bytes':total,'bps':8*total/samples,'gain_vs_verified_fullfile_sz3_rate':SZ3_BPS/(8*total/samples),
                    'ratio_to_strict_2x_target':(8*total/samples)/TARGET_BPS,'mask_bytes':len(mask_blob),'value_bytes':len(val_blob),
                    'scale_bytes':len(scale_blob),'correction_bytes':corr_bytes,'correction_rep':corr_rep,
                    'mean_nonzero_coefficients':float(np.mean(nonzero)),'median_nonzero_coefficients':float(np.median(nonzero)),
                    'mean_sparse_fraction':float(np.mean(np.asarray(nonzero)/D.shape[1])),'mean_fraction_legal_before_correction':float(np.mean(legal_before)),
                    'maxerr':max(maxerrs)})
        rows.sort(key=lambda r:r['bytes'])
        out={'shape':list(d.shape),'std':std,'eps':eps,'internal_bound':bound,'block_shape':[H,W],'regions':list(REGIONS),'times':list(TIMES),
            'verified_fullfile_sz3_bps':SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,'rows':rows,
            'scope':'Hard-error distortion-shaping screen. Each source block is treated only as an L-infinity box. LP chooses the minimum-L1 coefficient vector in a decoder-known dense basis/dictionary whose reconstruction lies in that box. Coefficients are then actually serialized (fp32/q16/q8 sparse support+values), decoder-reconstructed, and any quantization damage is repaired by a fully counted 2epsilon correction. This tests coefficient annihilation by distortion geometry, not ordinary transform quantization.'}
        print(json.dumps({'best':rows[:9]},indent=2),flush=True)
        json.dump(out,open('imperial_tolerance_annihilating_basis.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
