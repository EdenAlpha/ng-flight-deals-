import json,sys,struct
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;TB=1024


def maximal_runs(X,r):
    """Minimal-count greedy constant segments whose source intervals share an integer point."""
    all_lengths=[];all_values=[];counts=[];R=np.empty_like(X,dtype=np.int32)
    for c in range(X.shape[0]):
        x=X[c].astype(np.int64);t0=0;prev=0;nseg=0
        while t0<x.size:
            lo=int(x[t0]-r);hi=int(x[t0]+r);t=t0+1
            while t<x.size:
                nlo=max(lo,int(x[t]-r));nhi=min(hi,int(x[t]+r))
                if nlo>nhi:break
                lo,hi=nlo,nhi;t+=1
            # Within the common legal intersection, choose the point nearest the
            # previous segment value. This minimizes value deltas without changing
            # the provably minimal segment count.
            v=min(max(prev,lo),hi)
            L=t-t0
            all_lengths.append(L);all_values.append(v);R[c,t0:t]=v
            prev=v;nseg+=1;t0=t
        counts.append(nseg)
    return (np.asarray(all_lengths,np.uint16),np.asarray(all_values,np.int32),
            np.asarray(counts,np.uint16),R)


def pack_decode(lengths,values,counts,shape):
    # Values are delta-coded independently per channel; lengths/counts are exact.
    vd=[];p=0
    for n in counts.astype(np.int64):
        a=values[p:p+n].astype(np.int64)
        if n:
            d=np.empty(n,np.int32);d[0]=int(a[0]);
            if n>1:d[1:]=np.diff(a).astype(np.int32)
            vd.append(d)
        p+=n
    vd=np.concatenate(vd) if vd else np.empty(0,np.int32)
    z=zstd.ZstdCompressor(level=19)
    c_counts=z.compress(counts.tobytes())
    c_len=z.compress(lengths.tobytes())
    c_val=z.compress(vd.tobytes())
    blob=struct.pack('<III',len(c_counts),len(c_len),len(c_val))+c_counts+c_len+c_val
    # Byte-real decode.
    n1,n2,n3=struct.unpack('<III',blob[:12]);q=12;zd=zstd.ZstdDecompressor()
    cd=np.frombuffer(zd.decompress(blob[q:q+n1]),dtype=np.uint16).copy();q+=n1
    ld=np.frombuffer(zd.decompress(blob[q:q+n2]),dtype=np.uint16).copy();q+=n2
    dd=np.frombuffer(zd.decompress(blob[q:q+n3]),dtype=np.int32).copy()
    if not np.array_equal(cd,counts) or not np.array_equal(ld,lengths):raise RuntimeError('metadata decode')
    R=np.empty(shape,np.int32);ip=0;iv=0
    for c,n in enumerate(cd.astype(np.int64)):
        total=0;prev=0
        for _ in range(int(n)):
            L=int(ld[ip]);d=int(dd[iv]);ip+=1;iv+=1
            v=d if total==0 else prev+d
            if total+L>shape[1]:raise RuntimeError('run overflow')
            R[c,total:total+L]=v;total+=L;prev=v
        if total!=shape[1]:raise RuntimeError(('run length',c,total))
    if ip!=len(ld) or iv!=len(dd):raise RuntimeError('trailing run data')
    return blob,R


def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;r=int(np.floor(eps));rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64)
            lengths,values,counts,R=maximal_runs(X,r);blob,Rd=pack_decode(lengths,values,counts,X.shape)
            if not np.array_equal(R,Rd):raise RuntimeError((region,'decode mismatch'))
            me=float(np.max(np.abs(XF-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'hard error',me,eps))
            _,co=h.fits(XF);R0,K0=h.run_ar(XF,co);base,*_=h.arithmetic(K0)
            sz=0
            for t0 in range(0,NT,TB):
                b,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(b)
            L=lengths.astype(np.float64)
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'radius':r,
                 'segments':int(len(lengths)),'segments_per_sample':float(len(lengths)/X.size),
                 'mean_run':float(L.mean()),'median_run':float(np.median(L)),
                 'p90_run':float(np.quantile(L,.90)),'p99_run':float(np.quantile(L,.99)),
                 'max_run':int(lengths.max()),'bytes':len(blob),'bps':8*len(blob)/X.size,
                 'step267_bytes':int(base),'step267_bps':8*int(base)/X.size,
                 'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,
                 'gain_vs_step267':float(base/len(blob)),'gain_vs_sz3':float(sz/len(blob)),
                 'ratio_to_2x_sz3_target':float(len(blob)/(sz/2)),'maxerr':me}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'radius':r,'rows':rows,
             'scope':'Executable maximal constant-interval segmentation under the unchanged Imperial L-infinity tolerance. For each channel, a segment extends while all integer source intervals [x-r,x+r] have a nonempty common intersection; greedy maximal extension minimizes the number of constant segments. The reconstruction point is chosen inside the intersection nearest the previous segment value to reduce transmitted deltas. Segment counts, uint16 lengths and int32 per-channel value deltas are independently Zstd-19 compressed, framed, byte-decoded, the complete source is regenerated and max error verified. Huber AR32 step267 arithmetic and matched SZ3 are rerun on identical 128x8192 regions. No oracle side information, no AI.'}
        json.dump(out,open('imperial_maximal_hardbox_interval_runs.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
