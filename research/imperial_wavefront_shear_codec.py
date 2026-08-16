import json, math, sys
import h5py
import numpy as np
import zstandard as zstd

C=128; NT=30000; C0=512; STEP=267
CURRENT_BYTES=2468803; MATCHED_SZ3=2767977; HEADER_BYTES=32
SLOPES=tuple(range(-8,9))
TRANSFORMS=('dt','dtds','dthaar','raw')


def entropy(a):
    _,cnt=np.unique(np.asarray(a).reshape(-1),return_counts=True)
    p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def haar_fwd(a):
    x=np.asarray(a,dtype=np.int32).copy(); n=x.shape[0]
    while n>1:
        even=x[:n:2].copy(); odd=x[1:n:2].copy()
        d=odd-even; s=even+(d>>1)
        x[:n//2]=s; x[n//2:n]=d; n//=2
    return x


def haar_inv(a):
    x=np.asarray(a,dtype=np.int32).copy(); n=1; N=x.shape[0]
    while n<N:
        s=x[:n].copy(); d=x[n:2*n].copy()
        even=s-(d>>1); odd=d+even
        y=np.empty((2*n,x.shape[1]),np.int32); y[0::2]=even; y[1::2]=odd
        x[:2*n]=y; n*=2
    return x


def shear(q,s):
    y=np.empty_like(q)
    T=q.shape[1]
    for c in range(q.shape[0]): y[c]=np.roll(q[c],-(s*c)%T)
    return y


def unshear(y,s):
    q=np.empty_like(y)
    T=y.shape[1]
    for c in range(y.shape[0]): q[c]=np.roll(y[c],(s*c)%T)
    return q


def fwd(q,s,tr):
    y=shear(q,s)
    if tr=='raw': return y
    dt=y.copy(); dt[:,1:]=y[:,1:]-y[:,:-1]
    if tr=='dt': return dt
    if tr=='dtds':
        z=dt.copy(); z[1:]=dt[1:]-dt[:-1]; return z
    if tr=='dthaar': return haar_fwd(dt)
    raise ValueError(tr)


def inv(z,s,tr):
    if tr=='raw': y=z.copy()
    else:
        if tr=='dt': dt=z.copy()
        elif tr=='dtds':
            dt=z.copy(); dt=np.cumsum(dt,axis=0,dtype=np.int64).astype(np.int32)
        elif tr=='dthaar': dt=haar_inv(z)
        else: raise ValueError(tr)
        y=np.cumsum(dt,axis=1,dtype=np.int64).astype(np.int32)
    return unshear(y,s)


def zbytes(a):
    return zstd.ZstdCompressor(level=19).compress(np.ascontiguousarray(a,dtype=np.int32).tobytes())


def global_search(Q):
    screens=[]
    for tr in TRANSFORMS:
        for s in SLOPES:
            z=fwd(Q,s,tr); h=entropy(z)
            screens.append({'slope':s,'transform':tr,'h0_bps':h})
    screens.sort(key=lambda r:r['h0_bps'])
    forced=[r for r in screens if r['slope']==0 and r['transform']=='dt'][:1]
    finalists=[]; seen=set()
    for r in screens[:8]+forced:
        k=(r['slope'],r['transform'])
        if k in seen: continue
        seen.add(k); z=fwd(Q,*k); bb=zbytes(z)
        rr=dict(r); rr.update({'payload_bytes':len(bb),'total_bytes':HEADER_BYTES+1+len(bb)})
        finalists.append(rr); print(json.dumps({'global':rr}),flush=True)
    return min(finalists,key=lambda r:r['total_bytes']),screens[:20],finalists


def block_search(Q,B):
    zs=[]; selectors=[]; choices=[]; blocks=[]
    for t0 in range(0,NT,B):
        qb=Q[:,t0:min(NT,t0+B)]; best=None; bestz=None
        for tr in TRANSFORMS:
            for si,s in enumerate(SLOPES):
                z=fwd(qb,s,tr); score=entropy(z)
                if best is None or score<best[0]: best=(score,si,s,tr); bestz=z
        score,si,s,tr=best
        code=TRANSFORMS.index(tr)*len(SLOPES)+si
        selectors.append(code); choices.append({'t0':t0,'n':qb.shape[1],'slope':s,'transform':tr,'h0_bps':score})
        blocks.append(bestz)
    packed=np.concatenate(blocks,axis=1)
    bb=zbytes(packed)
    total=HEADER_BYTES+len(selectors)+len(bb)
    # literal decoder replay
    raw=zstd.ZstdDecompressor().decompress(bb,max_output_size=packed.nbytes)
    dec=np.frombuffer(raw,np.int32).reshape(C,NT)
    Qd=np.empty_like(Q); off=0
    for i,t0 in enumerate(range(0,NT,B)):
        n=min(B,NT-t0); code=selectors[i]; ti=code//len(SLOPES); si=code%len(SLOPES)
        tr=TRANSFORMS[ti]; s=SLOPES[si]
        Qd[:,t0:t0+n]=inv(dec[:,off:off+n],s,tr); off+=n
    if off!=NT or not np.array_equal(Qd,Q): raise RuntimeError(('replay',B,off))
    row={'block':B,'blocks':len(selectors),'selector_bytes':len(selectors),'payload_bytes':len(bb),'total_bytes':total,
         'bps':8.0*total/Q.size,'gain_vs_current':CURRENT_BYTES/total,'gain_vs_sz3':MATCHED_SZ3/total,
         'slope_hist':{str(s):sum(1 for x in choices if x['slope']==s) for s in SLOPES},
         'transform_hist':{tr:sum(1 for x in choices if x['transform']==tr) for tr in TRANSFORMS},'choices':choices}
    print(json.dumps({'block':{k:v for k,v in row.items() if k!='choices'}}),flush=True)
    return row


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; total=d.shape[0]*d.shape[1]; ss=ss2=0.0
        for i in range(0,d.shape[0],4096):
            a=np.asarray(d[i:i+4096,:],np.float64); ss+=float(a.sum()); ss2+=float(np.square(a).sum())
        mu=ss/total; eps=.1*math.sqrt(max(0.0,ss2/total-mu*mu)); X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if np.max(np.abs(X-Xi))>1e-6: raise RuntimeError('noninteger')
    Q=np.rint(Xi/STEP).astype(np.int32); R=Q.astype(np.int64)*STEP; me=float(np.max(np.abs(Xi-R)))
    if me>eps*(1+5e-6): raise RuntimeError(('hard',me,eps))
    gb,screens,finalists=global_search(Q)
    blocks=[block_search(Q,B) for B in (256,512,1024,2048,4096)]
    best=min([{'kind':'global',**gb}]+[{'kind':'block',**r} for r in blocks],key=lambda r:r['total_bytes'])
    out={'meta':{'shape':[C,NT],'samples':Q.size,'eps':eps,'step':STEP,'maxerr':me,'current_bytes':CURRENT_BYTES,'matched_sz3_bytes':MATCHED_SZ3},
         'global_best':gb,'global_screens':screens,'global_finalists':finalists,'block_results':blocks,'best':best,
         'note':'Every reported total is a physical zstd payload plus charged header/selectors on a reversible transform of a legal step-267 reconstruction. Decoder replay recovers exact Q and source max error is checked. This is a self-contained scalar-reconstruction codec test, not an entropy-only estimate.'}
    json.dump(out,open('imperial_wavefront_shear_codec.json','w'),indent=2)
    print(json.dumps({'summary':best},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
