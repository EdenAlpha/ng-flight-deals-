import json,sys,struct
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;TB=1024;SQ=256


def ceil_div(a,b):
    return -((-int(a))//int(b))


def iround_div(n,d):
    n=int(n);d=int(d)
    if n>=0:return (n+d//2)//d
    return -((-n+d//2)//d)


def line_segments(X,r):
    counts=[];lengths=[];anchors=[];slopes=[];R=np.empty_like(X,dtype=np.int32)
    for c in range(X.shape[0]):
        x=X[c].astype(np.int64);t0=0;prevk=0;nseg=0
        while t0<x.size:
            a=int(x[t0]);lo=-2**31;hi=2**31-1;t=t0+1
            # Feasible quantized slopes k/SQ such that the continuous line stays
            # inside every [x-r,x+r]. Integer rounding at decode adds <=0.5.
            while t<x.size:
                j=t-t0
                lk=ceil_div(SQ*(int(x[t])-r-a),j)
                hk=(SQ*(int(x[t])+r-a))//j
                nlo=max(lo,lk);nhi=min(hi,hk)
                if nlo>nhi:break
                lo,hi=nlo,nhi;t+=1
            k=min(max(prevk,lo),hi) if t>t0+1 else 0
            L=t-t0
            for j in range(L):R[c,t0+j]=iround_div(a*SQ+k*j,SQ)
            lengths.append(L);anchors.append(a);slopes.append(k)
            prevk=k;nseg+=1;t0=t
        counts.append(nseg)
    return (np.asarray(counts,np.uint16),np.asarray(lengths,np.uint16),
            np.asarray(anchors,np.int32),np.asarray(slopes,np.int32),R)


def encode_decode(counts,lengths,anchors,slopes,shape):
    # Delta-code anchors and slopes within each channel before entropy coding.
    ad=[];kd=[];p=0
    for n in counts.astype(np.int64):
        A=anchors[p:p+n].astype(np.int64);K=slopes[p:p+n].astype(np.int64)
        da=np.empty(int(n),np.int32);dk=np.empty(int(n),np.int32)
        if n:
            da[0]=int(A[0]);dk[0]=int(K[0])
            if n>1:
                da[1:]=np.diff(A).astype(np.int32);dk[1:]=np.diff(K).astype(np.int32)
        ad.append(da);kd.append(dk);p+=n
    ad=np.concatenate(ad) if ad else np.empty(0,np.int32)
    kd=np.concatenate(kd) if kd else np.empty(0,np.int32)
    z=zstd.ZstdCompressor(level=19)
    parts=[z.compress(a.tobytes()) for a in (counts,lengths,ad,kd)]
    blob=struct.pack('<IIII',*(len(p) for p in parts))+b''.join(parts)
    n1,n2,n3,n4=struct.unpack('<IIII',blob[:16]);q=16;zd=zstd.ZstdDecompressor()
    cd=np.frombuffer(zd.decompress(blob[q:q+n1]),np.uint16).copy();q+=n1
    ld=np.frombuffer(zd.decompress(blob[q:q+n2]),np.uint16).copy();q+=n2
    aad=np.frombuffer(zd.decompress(blob[q:q+n3]),np.int32).copy();q+=n3
    kkd=np.frombuffer(zd.decompress(blob[q:q+n4]),np.int32).copy()
    if not np.array_equal(cd,counts) or not np.array_equal(ld,lengths):raise RuntimeError('metadata')
    R=np.empty(shape,np.int32);ip=0;iv=0
    for c,n in enumerate(cd.astype(np.int64)):
        pos=0;pa=0;pk=0
        for s in range(int(n)):
            L=int(ld[ip]);ip+=1
            a=int(aad[iv]) if s==0 else pa+int(aad[iv])
            k=int(kkd[iv]) if s==0 else pk+int(kkd[iv]);iv+=1
            if pos+L>shape[1]:raise RuntimeError('overflow')
            for j in range(L):R[c,pos+j]=iround_div(a*SQ+k*j,SQ)
            pos+=L;pa=a;pk=k
        if pos!=shape[1]:raise RuntimeError(('length',c,pos))
    if ip!=len(ld) or iv!=len(aad) or iv!=len(kkd):raise RuntimeError('trailing')
    return blob,R


def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;r=int(np.floor(eps-.5));rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64)
            counts,lengths,anchors,slopes,R=line_segments(X,r)
            blob,Rd=encode_decode(counts,lengths,anchors,slopes,X.shape)
            if not np.array_equal(R,Rd):raise RuntimeError((region,'decode'))
            me=float(np.max(np.abs(XF-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'hard',me,eps))
            _,co=h.fits(XF);_,K0=h.run_ar(XF,co);base,*_=h.arithmetic(K0)
            sz=0
            for t0 in range(0,NT,TB):
                b,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(b)
            L=lengths.astype(np.float64)
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'radius':r,'slope_quantum':1/SQ,
                 'segments':int(len(lengths)),'mean_run':float(L.mean()),'median_run':float(np.median(L)),
                 'p90_run':float(np.quantile(L,.9)),'p99_run':float(np.quantile(L,.99)),'max_run':int(lengths.max()),
                 'bytes':len(blob),'bps':8*len(blob)/X.size,'step267_bytes':int(base),'step267_bps':8*int(base)/X.size,
                 'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'gain_vs_step267':float(base/len(blob)),
                 'gain_vs_sz3':float(sz/len(blob)),'ratio_to_2x_sz3_target':float(len(blob)/(sz/2)),'maxerr':me}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'radius':r,'slope_quantum':1/SQ,'rows':rows,
                   'scope':'Executable hard-box piecewise-linear segmentation. Each segment anchor is transmitted as an integer source value. A shared slope k/256 is feasible only while the continuous line lies inside every source interval [x-r,x+r], with r=floor(epsilon-0.5)=133; deterministic integer rounding at decode adds at most 0.5, guaranteeing <=133.5<epsilon. The segment extends greedily until the quantized-slope feasible interval is empty. Counts, lengths, anchor deltas, and slope deltas are Zstd-19 compressed, byte-decoded, full source reconstructed and hard-error checked. Huber AR32 step267 arithmetic and matched SZ3 are rerun identically. No oracle side information, no AI.'},open('imperial_hardbox_swinging_door_lines.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
