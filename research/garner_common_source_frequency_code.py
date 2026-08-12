import json,math,os,sys
import numpy as np,segyio,zstandard as zstd
from scipy.fft import rfft,irfft
sys.path.insert(0,os.path.dirname(__file__))
from garner_valley_das_full_benchmark import enc_int
from imperial_valley_das_large_screen import sz3_best

SPACE=128;TIME=1024;SAFETY=1-1e-4
KVALUES=(8,32,128,512)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()


def blob_roundtrip(a,dtype=None):
    x=np.ascontiguousarray(a if dtype is None else np.asarray(a,dtype=dtype))
    b=ZC.compress(x.tobytes())
    raw=ZD.decompress(b)
    r=np.frombuffer(raw,dtype=x.dtype,count=x.size).reshape(x.shape)
    if not np.array_equal(r,x):raise RuntimeError('blob roundtrip')
    return b,r


def matched_sz3(A,eps):
    total=0;mx=0.0
    for c0 in range(0,A.shape[0],SPACE):
        for t0 in range(0,A.shape[1],TIME):
            W=np.ascontiguousarray(A[c0:min(c0+SPACE,A.shape[0]),t0:min(t0+TIME,A.shape[1])])
            b,ori,me=sz3_best(np.ascontiguousarray(W.T),eps)
            total+=b;mx=max(mx,me)
    return total,mx


def encode_model(F,order,K,ns):
    idx=np.asarray(order[:K],np.uint16)
    C=np.asarray(F[:,idx],np.complex64)
    # One transmitted physical scale per selected temporal frequency, shared by all channels.
    peak=np.maximum(np.max(np.abs(C.real),axis=0),np.max(np.abs(C.imag),axis=0)).astype(np.float64)
    scale=np.maximum(peak/127.0,1e-30).astype(np.float32)
    qr=np.clip(np.rint(C.real/scale[None,:]),-127,127).astype(np.int8)
    qi=np.clip(np.rint(C.imag/scale[None,:]),-127,127).astype(np.int8)
    ib,idxd=blob_roundtrip(idx)
    sb,scaled=blob_roundtrip(scale)
    coeff=np.stack([qr,qi],axis=-1)
    cb,coeffd=blob_roundtrip(coeff)
    # Decoder reconstructs the exact transmitted spectrum, no target float coefficients hidden.
    H=np.zeros((F.shape[0],ns//2+1),np.complex64)
    qrd=coeffd[...,0].astype(np.float32);qid=coeffd[...,1].astype(np.float32)
    H[:,idxd.astype(np.int64)]=(qrd+1j*qid)*scaled[None,:]
    model_bytes=len(ib)+len(sb)+len(cb)+96
    return model_bytes,H,{'index_bytes':len(ib),'scale_bytes':len(sb),'coefficient_bytes':len(cb),'K':K,
                          'coefficient_raw_bytes':int(coeff.nbytes)}


def correction_bytes(A,P,eps):
    step=2*eps*SAFETY;total=0;mx=0.0;nz=0;n=0;reps={}
    for c0 in range(0,A.shape[0],SPACE):
        for t0 in range(0,A.shape[1],TIME):
            c1=min(c0+SPACE,A.shape[0]);t1=min(t0+TIME,A.shape[1])
            X=A[c0:c1,t0:t1].astype(np.float64);R=P[c0:c1,t0:t1].astype(np.float64)
            q=np.rint((X-R)/step).astype(np.int32)
            b,rep,qd=enc_int(q)
            F=R+step*qd
            me=float(np.max(np.abs(X-F)))
            if not np.all(np.isfinite(F)) or me>eps*(1+5e-6):raise RuntimeError(('hard correction',c0,t0,me,eps))
            total+=b;mx=max(mx,me);nz+=int(np.count_nonzero(q));n+=q.size;reps[rep]=reps.get(rep,0)+1
    return total,mx,nz/n,reps


def main(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    if not np.all(np.isfinite(A)):raise RuntimeError('nonfinite source')
    mean=float(A.mean(dtype=np.float64));std=float(A.std(dtype=np.float64));eps=.1*std
    szb,szme=matched_sz3(A,eps)
    F=rfft(A,axis=1,workers=-1)
    energy=np.sum(np.abs(F.astype(np.complex128))**2,axis=0,dtype=np.float64)
    order=np.argsort(energy)[::-1]
    et=float(energy.sum());rows=[]
    for K in KVALUES:
        mb,H,md=encode_model(F,order,K,ns)
        P=irfft(H,n=ns,axis=1,workers=-1).astype(np.float32)
        if not np.all(np.isfinite(P)):raise RuntimeError(('nonfinite model',K))
        cb,me,nzf,reps=correction_bytes(A,P,eps)
        total=mb+cb+64
        frac=float(energy[order[:K]].sum()/et) if et>0 else 1.0
        rows.append({'K':K,'bytes':total,'model_bytes':mb,'correction_bytes':cb,'matched_sz3_bytes':szb,
                     'gain_vs_sz3':szb/total,'bps':8*total/A.size,'ratio_raw':A.nbytes/total,
                     'global_temporal_fft_energy_fraction':frac,'correction_nonzero_fraction':nzf,
                     'maxerr':me,'model_breakdown':md,'correction_reps':reps})
        print(json.dumps(rows[-1]),flush=True)
    rows.sort(key=lambda r:r['bytes'])
    out={'file_bytes':os.path.getsize(path),'shape':list(A.shape),'numeric_bytes':int(A.nbytes),'mean':mean,'std':std,'eps':eps,
         'matched_sz3':{'bytes':szb,'bps':8*szb/A.size,'ratio_raw':A.nbytes/szb,'maxerr':szme},
         'K_values':list(KVALUES),'rows':rows,'best':rows[0],
         'top_frequency_indices':order[:min(32,len(order))].astype(int).tolist(),
         'scope':'Full Garner Valley DAS sample-array common-source frequency screen. One global set of target-selected temporal frequencies is transmitted explicitly; each channel gets int8 complex response coefficients at only those frequencies, with one transmitted float32 scale per frequency. The exact transmitted model is inverse-FFT decoded, then every remaining sample error is repaired by a fully serialized 2epsilon hard-error correction on the same 128x1024 partition. Matched SZ3 is rerun at identical 10%-actual-array-std epsilon with zero metadata. No header claim, no AI.'}
    print(json.dumps({'best':rows},indent=2),flush=True);json.dump(out,open('garner_common_source_frequency_code.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
