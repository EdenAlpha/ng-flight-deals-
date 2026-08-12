import json,math,os,sys
import numpy as np,segyio,zstandard as zstd
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.imperial_valley_das_large_screen import build_blob,decode_blob,sz3_best
from research.imperial_valley_frozen_brady_transfer import encode_tile

SPACE=128;TIME=1024;SAFETY=1.0-1e-4;Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def enc_int(a):
    a=np.asarray(a,np.int32);flat=a.ravel();c=[]
    def sd(v):
        mn=int(v.min()) if v.size else 0;mx=int(v.max()) if v.size else 0
        for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
            if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
                b=Z.compress(v.astype(dt,copy=False).tobytes());r=np.frombuffer(D.decompress(b),dt,count=v.size).astype(np.int32);return len(b),dt.str,r
        raise RuntimeError(('int range',mn,mx))
    nb,ds,r=sd(flat);c.append((nb+32,'raw_'+ds,r.copy()))
    if a.ndim==2:
        dt=a.copy();dt[:,1:]-=a[:,:-1];nb,ds,r=sd(dt.ravel());q=np.cumsum(r.reshape(a.shape),axis=1,dtype=np.int32);c.append((nb+32,'dt_'+ds,q.ravel()))
        dc=a.copy();dc[1:]-=a[:-1];nb,ds,r=sd(dc.ravel());q=np.cumsum(r.reshape(a.shape),axis=0,dtype=np.int32);c.append((nb+32,'dc_'+ds,q.ravel()))
        L=a.copy();L[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];L[0,1:]=a[0,1:]-a[0,:-1];L[1:,0]=a[1:,0]-a[:-1,0];nb,ds,r=sd(L.ravel());q=np.cumsum(np.cumsum(r.reshape(a.shape),axis=0,dtype=np.int32),axis=1,dtype=np.int32);c.append((nb+32,'lorenzo_'+ds,q.ravel()))
    nz=flat!=0;sb=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());vals=flat[nz]
    if vals.size:
        vb,ds,vr=sd(vals)
    else:vb=0;ds='i1';vr=np.empty(0,np.int32)
    mask=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=flat.size).astype(bool);q=np.zeros(flat.size,np.int32);q[mask]=vr;c.append((len(sb)+vb+64,'sparse_'+ds,q))
    best=min(c,key=lambda x:x[0])
    if not np.array_equal(best[2],flat):raise RuntimeError(('enc_int decode',best[1]))
    return best[0],best[1],best[2].reshape(a.shape)

def checker_tile(W,pub,internal):
    nc,nt=W.shape;sign=np.where(np.arange(nt)%2==0,1.,-1.)[None,:];Y=W.astype(np.float64)*sign;h=2*internal;phi=h/4.0
    cc=np.arange(nc)[:,None];tt=np.arange(nt)[None,:];mask=((cc+tt)&1)==0
    q=np.zeros((nc,nt),np.int32);q[mask]=np.rint((Y[mask]-phi)/h).astype(np.int32)
    A0=q[0::2,0::2];A1=q[1::2,1::2];b0,r0,A0d=enc_int(A0);b1,r1,A1d=enc_int(A1)
    P=np.zeros((nc,nt),np.float64);P[0::2,0::2]=phi+h*A0d;P[1::2,1::2]=phi+h*A1d
    ss=np.zeros_like(P);sc=np.zeros(P.shape,np.int16);ts=np.zeros_like(P);tc=np.zeros(P.shape,np.int16)
    ss[1:]+=P[:-1];sc[1:]+=mask[:-1];ss[:-1]+=P[1:];sc[:-1]+=mask[1:];ts[:,1:]+=P[:,:-1];tc[:,1:]+=mask[:,:-1];ts[:,:-1]+=P[:,1:];tc[:,:-1]+=mask[:,1:]
    sp=np.divide(ss,sc,out=np.zeros_like(P),where=sc>0);tp=np.divide(ts,tc,out=np.zeros_like(P),where=tc>0);both=(sc>0)&(tc>0);miss=~mask
    P[miss&both]=.5*(sp[miss&both]+tp[miss&both]);P[miss&(sc>0)&~both]=sp[miss&(sc>0)&~both];P[miss&(tc>0)&~both]=tp[miss&(tc>0)&~both]
    K=np.rint((Y[miss]-P[miss])/h).astype(np.int32);bk,rk,Kd=enc_int(K);P[miss]+=h*Kd;R=P*sign;me=float(np.max(np.abs(W.astype(np.float64)-R)))
    if not np.all(np.isfinite(R)) or not math.isfinite(me) or me>pub*(1+5e-6):raise RuntimeError(('checker hard',me,pub))
    return b0+b1+bk+160,me,{'control_bytes':b0+b1,'correction_bytes':bk,'correction_nonzero':float(np.mean(K!=0)),'control_reps':[r0,r1],'correction_rep':rk}

def lattice_tile(A,pub,internal):
    step=2*internal;Q=np.rint(A.astype(np.float64)/step).astype(np.int32);K=np.empty_like(Q);K[:,0]=Q[:,0];K[:,1:]=Q[:,1:]-Q[:,:-1]
    rows=[]
    for rep in (0,1,2):
        b=build_blob(K,rep);RK=decode_blob(b)
        if not np.array_equal(RK,K):raise RuntimeError('lattice integer')
        rows.append((len(b),rep,b))
    nb,rep,b=min(rows,key=lambda x:x[0]);RK=decode_blob(b);RQ=np.cumsum(RK,axis=1,dtype=np.int32);R=RQ.astype(np.float64)*step;me=float(np.max(np.abs(A.astype(np.float64)-R)))
    if not math.isfinite(me) or me>pub*(1+5e-6):raise RuntimeError(('lattice hard',me,pub))
    return nb,me,float(np.mean(K!=0)),['raw','sparse','ternary'][rep]

def main(path):
    file_bytes=os.path.getsize(path)
    with segyio.open(path,'r',ignore_geometry=True) as f:
        f.mmap();ntr=f.tracecount;ns=len(f.samples);fmt=int(f.bin[segyio.BinField.Format]);dt=int(f.bin[segyio.BinField.Interval]);A=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
    if not np.all(np.isfinite(A)):raise RuntimeError('nonfinite')
    std=float(A.std(dtype=np.float64));mean=float(A.mean(dtype=np.float64));pub=.1*std;internal=pub*SAFETY
    totals={'sz3':0,'lattice':0,'checker':0,'spectral':0};mx={k:0. for k in ('sz3','lattice','checker','spectral')};diag={'samples':0,'lattice_nz':0.,'checker_corr_nz':0.,'spectral_corr_nz':0.,'checker_control':0,'checker_corr':0,'spectral_model':0,'spectral_corr':0};rows=[];tiles=0
    for c0 in range(0,ntr,SPACE):
        c1=min(ntr,c0+SPACE)
        for t0 in range(0,ns,TIME):
            t1=min(ns,t0+TIME);W=np.ascontiguousarray(A[c0:c1,t0:t1]);AT=np.ascontiguousarray(W.T)
            sb,so,sme=sz3_best(AT,pub);lb,lme,lnz,lrep=lattice_tile(W,pub,internal);cb,cme,cd=checker_tile(W,pub,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob)
            if not math.isfinite(pme) or pme>pub*(1+5e-6):raise RuntimeError(('spectral hard',pme,pub,c0,t0))
            for k,v in [('sz3',sb),('lattice',lb),('checker',cb),('spectral',pb)]:totals[k]+=v
            for k,v in [('sz3',sme),('lattice',lme),('checker',cme),('spectral',pme)]:mx[k]=max(mx[k],v)
            n=W.size;tiles+=1;diag['samples']+=n;diag['lattice_nz']+=lnz*n;diag['checker_corr_nz']+=cd['correction_nonzero']*int((~(((np.arange(W.shape[0])[:,None]+np.arange(W.shape[1])[None,:])&1)==0)).sum());diag['spectral_corr_nz']+=pd['correction_nonzero_fraction']*n;diag['checker_control']+=cd['control_bytes'];diag['checker_corr']+=cd['correction_bytes'];diag['spectral_model']+=pd['model_bytes'];diag['spectral_corr']+=pd['correction_bytes']
            if tiles<=6 or tiles%50==0:
                r={'tile':tiles,'c0':c0,'t0':t0,'shape':list(W.shape),'sz3':sb,'lattice':lb,'checker':cb,'spectral':pb,'gains':{'lattice':sb/lb,'checker':sb/cb,'spectral':sb/pb},'bps':{'sz3':8*sb/n,'lattice':8*lb/n,'checker':8*cb/n,'spectral':8*pb/n},'lattice_nz':lnz,'checker_corr_nz':cd['correction_nonzero'],'spectral_corr_nz':pd['correction_nonzero_fraction']};rows.append(r);print(json.dumps(r),flush=True)
    n=A.size;raw=A.nbytes;methods={}
    for k in ('lattice','checker','spectral'):methods[k]={'bytes':totals[k],'ratio_raw':raw/totals[k],'bps':8*totals[k]/n,'gain_vs_matched_sz3':totals['sz3']/totals[k],'maxerr':mx[k]}
    out={'file_bytes':file_bytes,'tracecount':ntr,'ns':ns,'shape':[ntr,ns],'format':fmt,'sample_interval_us':dt,'numeric_bytes':raw,'mean':mean,'std':std,'public_eps_10pct_std':pub,'internal_eps':internal,'tiles':tiles,'matched_sz3':{'bytes':totals['sz3'],'ratio_raw':raw/totals['sz3'],'bps':8*totals['sz3']/n,'maxerr':mx['sz3'],'metadata_charged':0},'methods':methods,'diagnostics':{'lattice_transition_nonzero':diag['lattice_nz']/n,'checker_control_bytes':diag['checker_control'],'checker_correction_bytes':diag['checker_corr'],'spectral_correction_nonzero':diag['spectral_corr_nz']/n,'spectral_model_bytes':diag['spectral_model'],'spectral_correction_bytes':diag['spectral_corr']},'sampled_rows':rows,'valid':all(math.isfinite(mx[k]) and mx[k]<=pub*(1+5e-6) for k in mx),'scope':'Entire 1,984x12,600 DAS sample array. One global epsilon=10% std of this actual array. Same 128x1024 tiling for all candidates and SZ3; SZ3 gets best orientation and zero metadata. Candidate integer/model streams are byte-decoded and final hard errors verified. SEG-Y headers are outside this sample-array generalization gate.'}
    print(json.dumps({k:out[k] for k in ('shape','numeric_bytes','std','public_eps_10pct_std','tiles','matched_sz3','methods','diagnostics','valid')},indent=2),flush=True);json.dump(out,open('garner_valley_das_full_benchmark.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
