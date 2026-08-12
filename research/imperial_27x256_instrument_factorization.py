import json,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

NB=27; NP=256; NC=NB*NP; SAFETY=1-1e-5
BLOCKS=(0,9,18,26)
TWO_T0=12288; TWO_NT=2048
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()


def stats(d):
    s=ss=0.0;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.0,ss/n-m*m)))


def zpack(a):
    a=np.asarray(a)
    mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max:break
    b=ZC.compress(np.ascontiguousarray(a).astype(dt).tobytes())
    r=np.frombuffer(ZD.decompress(b),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape)
    if not np.array_equal(r,a.astype(np.int32)):raise RuntimeError('model roundtrip')
    return len(b)+24,dt.str


def szrun(A,eps):
    A=np.asarray(A,np.float32)
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray(A.T if tr else A)
        cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape)
        me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
        if tr:R=R.T
        row=(int(b.size),R.astype(np.float64),'T' if tr else 'CT',me)
        if best is None or row[0]<best[0]:best=row
    return best


def block_mode(X,eps):
    # One exact integer common-mode sample for every 256 source samples.
    base=np.rint(np.mean(X.astype(np.float64),axis=1)).astype(np.int32)
    residual=X.astype(np.int32)-base[:,None]
    mb,mrep=zpack(base)
    rb,Rr,orient,rme=szrun(residual,eps)
    recon=base[:,None].astype(np.float64)+Rr
    me=float(np.max(np.abs(X.astype(np.float64)-recon)))
    if me>eps*(1+5e-6):raise RuntimeError(('block hard error',me,eps))
    db,_,dorient,dme=szrun(X,eps)
    return {'direct_sz3_bytes':db,'direct_orientation':dorient,'model_bytes':mb,'model_rep':mrep,
            'residual_sz3_bytes':rb,'residual_orientation':orient,'total_bytes':mb+rb+32,
            'gain_vs_direct_sz3':db/(mb+rb+32),'maxerr':me,
            'source_std':float(X.std()),'residual_std':float(residual.std()),
            'residual_std_fraction':float(residual.std()/max(1e-30,X.std())),
            'base_std':float(base.std())}


def two_way(X,eps,order):
    # X: time x 27 x 256. Exact integer additive predictor, then lossy residual.
    Xi=X.astype(np.int32)
    if order=='block_then_position':
        row=np.rint(np.mean(Xi.astype(np.float64),axis=2)).astype(np.int32)
        rem=Xi-row[:,:,None]
        col=np.rint(np.mean(rem.astype(np.float64),axis=1)).astype(np.int32)
    else:
        col=np.rint(np.mean(Xi.astype(np.float64),axis=1)).astype(np.int32)
        rem=Xi-col[:,None,:]
        row=np.rint(np.mean(rem.astype(np.float64),axis=2)).astype(np.int32)
    pred=row[:,:,None]+col[:,None,:]
    residual=Xi-pred
    rb,rrep=zpack(row);cb,crep=zpack(col)
    flat=residual.reshape(len(X),NC)
    sb,Rr,orient,sme=szrun(flat,eps)
    recon=pred.reshape(len(X),NC).astype(np.float64)+Rr
    src=Xi.reshape(len(X),NC).astype(np.float64)
    me=float(np.max(np.abs(src-recon)))
    if me>eps*(1+5e-6):raise RuntimeError(('two-way hard error',me,eps))
    db,_,dorient,dme=szrun(src,eps)
    total=rb+cb+sb+64
    return {'order':order,'direct_sz3_bytes':db,'direct_orientation':dorient,
            'row_model_bytes':rb,'row_rep':rrep,'col_model_bytes':cb,'col_rep':crep,
            'residual_sz3_bytes':sb,'residual_orientation':orient,'total_bytes':total,
            'gain_vs_direct_sz3':db/total,'maxerr':me,
            'source_std':float(src.std()),'residual_std':float(residual.std()),
            'residual_std_fraction':float(residual.std()/max(1e-30,src.std())),
            'row_std':float(row.std()),'col_std':float(col.std())}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=stats(d);eps=.1*std
        blocks=[]
        for b in BLOCKS:
            c0=b*NP;X=np.asarray(d[:,c0:c0+NP],np.int16)
            r=block_mode(X,eps);r.update({'block':b,'c0':c0,'c1':c0+NP});blocks.append(r)
            print(json.dumps({'block':b,'result':r}),flush=True)
        Xw=np.asarray(d[TWO_T0:TWO_T0+TWO_NT,:],np.int16).reshape(TWO_NT,NB,NP)
        tw=[]
        for order in ('block_then_position','position_then_block'):
            r=two_way(Xw,eps,order);tw.append(r);print(json.dumps({'two_way':r}),flush=True)
        bsz=sum(r['direct_sz3_bytes'] for r in blocks);btot=sum(r['total_bytes'] for r in blocks)
        out={'shape':[30000,6912],'factorization':[NB,NP],'std':std,'eps':eps,'blocks':blocks,
             'block_aggregate':{'direct_sz3_bytes':bsz,'factorized_bytes':btot,'gain_vs_direct_sz3':bsz/btot},
             'two_way_window':{'t0':TWO_T0,'nt':TWO_NT,'rows':tw},
             'scope':'Instrument-coordinate factorization screen motivated only by the exact arithmetic identity 6912=27*256; no hardware grouping is assumed. Four full-minute 256-channel blocks test an exact transmitted per-time common mode plus matched-SZ3 residual. A separate 2048-sample full-cable window reshapes each time slice to 27x256 and tests exact integer two-way additive row/position modes plus matched-SZ3 residual. All model streams are actually Zstd serialized/decoded, residuals are SZ3 decoded, and final source-domain samples satisfy the unchanged 10%-global-std hard max-error. Direct SZ3 is rerun on identical arrays. No AI.'}
        print(json.dumps({'block_aggregate':out['block_aggregate'],'two_way':tw},indent=2),flush=True)
        json.dump(out,open('imperial_27x256_instrument_factorization.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
