import json,sys,math
import h5py,numpy as np
import zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=4096
TRAIN=1024
P=32
STEP=267
TB=1024
REGIONS=(('hard',512),('easy',2304))
PHASES=np.arange(-128,129,16,dtype=np.int16)  # public codebook, 17 legal lattice phases
ZC=zstd.ZstdCompressor(level=22)
ZD=zstd.ZstdDecompressor()


def score_symbols(k):
    """Prefix-only proxy for the incumbent context coder.

    Exact symbol conditional entropy given clipped previous K is used instead of
    MSE. Phase shifts mainly move samples across adjacent lattice boundaries, so
    this directly rewards concentrated/zero-heavy innovations.
    """
    k=np.asarray(k,np.int32).ravel()
    if k.size==0:return 0.0
    prev=np.empty_like(k);prev[0]=0;prev[1:]=k[:-1]
    pc=np.clip(prev,-4,4)
    bits=0.0
    for q in range(-4,5):
        v=k[pc==q]
        if v.size==0:continue
        _,cnt=np.unique(v,return_counts=True)
        p=cnt.astype(np.float64)/v.size
        bits += float(v.size)*float(-(p*np.log2(p)).sum())
    # tiny deterministic tiebreak favoring small magnitudes
    bits += 1e-6*float(np.abs(k.astype(np.int64)).sum())
    return bits


def trial_segment(Xc,Rbase,start,end,co,phase):
    R=Rbase.copy()
    K=np.empty(end-start,np.int32)
    aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for j,t in enumerate(range(start,end)):
        p=0 if t<P else int(np.rint(aa+float(np.dot(b,R[t-P:t][::-1].astype(np.float32)))))
        k=int(np.rint((float(Xc[t])-p-int(phase))/STEP))
        K[j]=k;R[t]=p+int(phase)+STEP*k
    return R[start:end].copy(),K


def run_fixed_prefix_phase(X,co):
    # Choose one phase per channel using only the first TRAIN samples, then
    # restart and apply that fixed phase to the complete channel.
    idx=np.zeros((C,1),np.uint8)
    for c in range(C):
        blank=np.zeros(NT,np.int32)
        best=None
        for j,ph in enumerate(PHASES):
            _,k=trial_segment(X[c],blank,0,TRAIN,co,int(ph))
            s=score_symbols(k)
            if best is None or s<best[0]:best=(s,j)
        idx[c,0]=best[1]
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        ph=int(PHASES[int(idx[c,0])])
        for t in range(NT):
            p=0 if t<P else int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            k=int(np.rint((float(X[c,t])-p-ph)/STEP));K[c,t]=k;R[c,t]=p+ph+STEP*k
    return R,K,idx


def run_greedy_block_phase(X,co):
    # Strong but fully deployable variant: one transmitted 0..16 phase index
    # per channel per 1024-sample block. Each block's phase is encoder-selected
    # by exact conditional symbol entropy while preserving the already committed
    # decoder history. The phase map is byte-compressed and charged.
    nb=(NT+TB-1)//TB
    idx=np.zeros((C,nb),np.uint8)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(C):
        for bi,start in enumerate(range(0,NT,TB)):
            end=min(start+TB,NT);best=None
            for j,ph in enumerate(PHASES):
                rseg,kseg=trial_segment(X[c],R[c],start,end,co,int(ph))
                s=score_symbols(kseg)
                if best is None or s<best[0]:best=(s,j,rseg,kseg)
            _,j,rseg,kseg=best;idx[c,bi]=j;R[c,start:end]=rseg;K[c,start:end]=kseg
    return R,K,idx


def phase_map_bytes(idx):
    raw=np.ascontiguousarray(idx,dtype=np.uint8).tobytes()
    z=ZC.compress(raw);dec=np.frombuffer(ZD.decompress(z),np.uint8,count=idx.size).reshape(idx.shape)
    if not np.array_equal(dec,idx):raise RuntimeError('phase map decode')
    return 16+len(z)


def decode_phased(K,co,idx,per_block):
    R=np.zeros(K.shape,np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            bi=t//TB if per_block else 0
            ph=int(PHASES[int(idx[c,bi])])
            p=0 if t<P else int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            R[c,t]=p+ph+STEP*int(K[c,t])
    return R


def evaluate(X,co,R,K,idx,mode,eps,baseline_bytes,sz_bytes):
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((mode,'encoder hard',me,eps))
    n,nbit,nb,Kd=a.arithmetic(K)
    pm=phase_map_bytes(idx)
    total=int(n+pm+1)
    Rd=decode_phased(Kd,co,idx,mode=='greedy_block')
    if not np.array_equal(Rd,R):raise RuntimeError((mode,'source replay'))
    dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if dme>eps*(1+1e-12):raise RuntimeError((mode,'decode hard',dme,eps))
    vals,cnt=np.unique(idx,return_counts=True)
    return {'mode':mode,'bytes':total,'bps':8*total/X.size,'arithmetic_bytes':int(n),
            'phase_map_bytes':int(pm+1),'phase_histogram':{str(int(v)):int(q) for v,q in zip(vals,cnt)},
            'phase_values_used':{str(int(v)):int(PHASES[int(v)]) for v in vals},
            'zero_fraction':float(np.mean(K==0)),'std_k':float(K.std()),'maxerr':dme,
            'arithmetic_bits':int(nbit),'symbol_bits':int(nb),
            'gain_vs_incumbent':baseline_bytes/total,'gain_vs_sz3':sz_bytes/total}


def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            _,co=a.fits(X)
            R0,K0=a.run_ar(X,co);b0,bit0,nb0,Kd0=a.arithmetic(K0);D0=a.decode_source(Kd0,co)
            me0=float(np.max(np.abs(X-D0.astype(np.float64))))
            if me0>eps*(1+1e-12):raise RuntimeError((region,'baseline hard'))
            sz=0
            for t0 in range(0,NT,TB):
                n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)

            Rf,Kf,If=run_fixed_prefix_phase(X,co)
            fixed=evaluate(X,co,Rf,Kf,If,'fixed_prefix',eps,b0,sz)
            Rg,Kg,Ig=run_greedy_block_phase(X,co)
            greedy=evaluate(X,co,Rg,Kg,Ig,'greedy_block',eps,b0,sz)
            best=min((fixed,greedy),key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,
                 'baseline':{'bytes':int(b0),'bps':8*b0/X.size,'zero_fraction':float(np.mean(K0==0)),'maxerr':me0},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},'best_phase':best,'candidates':[fixed,greedy]}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'step':STEP,'phases':[int(x) for x in PHASES],
             'nt':NT,'channels':C,'train':TRAIN,'rows':rows,
             'scope':'Decoder-real entropy-optimized phase placement of the unchanged step267 Huber AR32 reconstruction lattice. Any integer phase is legal because adjacent reconstruction levels remain 267 apart, giving worst scalar quantization error 133.5 < epsilon. fixed_prefix chooses one public-codebook phase per channel from only the first1024 source samples, then restarts/replays the complete trace. greedy_block is a stronger fully transmitted variant choosing one phase per channel per1024 block by exact conditional symbol entropy with committed decoder history. Phase maps are Zstd22 byte-decoded and charged; the fixed phase codebook is public. The incumbent arithmetic K stream, model/framing, phase map, exact K decode, full recursive source replay and unchanged hard-error check are all charged/verified. Matched SZ3 and the unshifted incumbent rerun on identical hard/easy128x4096 samples. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_ar32_quantizer_phase_gate.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
