import json,math,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np,zstandard as zstd
from research.imperial_valley_das_large_screen import build_blob,decode_blob,sz3_best
from research.imperial_valley_frozen_brady_transfer import encode_tile

SPACE=128;TIME=1024;SAFETY=1.0-1e-4;Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()


def numeric_2d(f):
    rows=[]
    def v(name,obj):
        if isinstance(obj,h5py.Dataset) and obj.ndim==2 and np.issubdtype(obj.dtype,np.number):
            rows.append((int(np.prod(obj.shape))*obj.dtype.itemsize,name,tuple(obj.shape),str(obj.dtype)))
    f.visititems(v);rows.sort(reverse=True)
    if not rows:raise RuntimeError('no numeric 2D dataset')
    return rows[0],rows[:20]


def choose_axes(shape):
    # Public Cape files are sequential one-minute records at 1000 Hz. Prefer the axis nearest 60k samples.
    d=[abs(int(x)-60000) for x in shape];ta=int(np.argmin(d));ca=1-ta
    if shape[ta]<10000 or shape[ca]<100:raise RuntimeError(('unexpected Cape shape',shape,ta))
    return ta,ca


def read_block(d,ta,t0,t1,c0,c1):
    if ta==0:a=np.asarray(d[t0:t1,c0:c1])
    else:a=np.asarray(d[c0:c1,t0:t1]).T
    return np.ascontiguousarray(a)  # time x channel


def global_stats(d,ta,T,C):
    s=ss=0.;n=0
    for t0 in range(0,T,2048):
        A=read_block(d,ta,t0,min(T,t0+2048),6,C).astype(np.float64,copy=False)
        s+=float(A.sum(dtype=np.float64));ss+=float((A*A).sum(dtype=np.float64));n+=A.size
    m=s/n;std=math.sqrt(max(0.,ss/n-m*m));return m,std,n


def enc_array(a):
    a=np.asarray(a,np.int32);shape=a.shape;flat=a.ravel();cands=[]
    def signed_blob(v):
        lo=int(v.min()) if v.size else 0;hi=int(v.max()) if v.size else 0
        for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
            if lo>=np.iinfo(dt).min and hi<=np.iinfo(dt).max:
                b=Z.compress(v.astype(dt,copy=False).tobytes());r=np.frombuffer(D.decompress(b),dt,count=v.size).astype(np.int32);return len(b),dt.str,b,r
        raise RuntimeError(('range',lo,hi))
    nb,ds,b,r=signed_blob(flat);cands.append((nb+32,'raw_'+ds,b,b'',r.copy()))
    if a.ndim==2:
        dt=a.copy();dt[:,1:]-=a[:,:-1];nb,ds,b,r=signed_blob(dt.ravel());q=np.cumsum(r.reshape(shape),axis=1,dtype=np.int32);cands.append((nb+32,'dt_'+ds,b,b'',q.ravel()))
        dc=a.copy();dc[1:]-=a[:-1];nb,ds,b,r=signed_blob(dc.ravel());q=np.cumsum(r.reshape(shape),axis=0,dtype=np.int32);cands.append((nb+32,'dc_'+ds,b,b'',q.ravel()))
        L=a.copy();L[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];L[0,1:]=a[0,1:]-a[0,:-1];L[1:,0]=a[1:,0]-a[:-1,0]
        nb,ds,b,r=signed_blob(L.ravel());q=np.cumsum(np.cumsum(r.reshape(shape),axis=0,dtype=np.int32),axis=1,dtype=np.int32);cands.append((nb+32,'lorenzo_'+ds,b,b'',q.ravel()))
    else:
        dv=a.copy();dv[1:]-=a[:-1];nb,ds,b,r=signed_blob(dv);q=np.cumsum(r,dtype=np.int32);cands.append((nb+32,'d1_'+ds,b,b'',q))
    nz=flat!=0;sb=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());vals=flat[nz]
    if vals.size:
        vb_n,ds,vb,vr=signed_blob(vals)
    else:
        ds='i1';vb=Z.compress(b'');vb_n=len(vb);vr=np.empty(0,np.int32)
    mask=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=flat.size).astype(bool);q=np.zeros(flat.size,np.int32);q[mask]=vr
    cands.append((len(sb)+vb_n+64,'sparse_'+ds,sb,vb,q))
    best=min(cands,key=lambda x:x[0])
    if not np.array_equal(best[4],flat):raise RuntimeError(('array decode',best[1]))
    return best[0],best[1],best[4].reshape(shape)


def predict_controls(P,mask):
    ss=np.zeros_like(P);sc=np.zeros(P.shape,np.int16);ts=np.zeros_like(P);tc=np.zeros(P.shape,np.int16)
    ss[1:]+=P[:-1];sc[1:]+=mask[:-1]
    ss[:-1]+=P[1:];sc[:-1]+=mask[1:]
    ts[:,1:]+=P[:,:-1];tc[:,1:]+=mask[:,:-1]
    ts[:,:-1]+=P[:,1:];tc[:,:-1]+=mask[:,1:]
    sp=np.divide(ss,sc,out=np.zeros_like(P),where=sc>0);tp=np.divide(ts,tc,out=np.zeros_like(P),where=tc>0)
    both=(sc>0)&(tc>0);out=P.copy();miss=~mask
    out[miss&both]=.5*(sp[miss&both]+tp[miss&both]);out[miss&(sc>0)&~both]=sp[miss&(sc>0)&~both];out[miss&(tc>0)&~both]=tp[miss&(tc>0)&~both]
    return out


def checker_tile(W,public_eps,internal_eps):
    # W channel x time. Freeze the PR236 winning geometry: deterministic Nyquist demod, checkerboard half controls, temporal/spatial equal view.
    nc,nt=W.shape;sign=np.where(np.arange(nt)%2==0,1.,-1.)[None,:];Y=W.astype(np.float64)*sign;h=2*internal_eps;phi=h/4.0
    cc=np.arange(nc)[:,None];tt=np.arange(nt)[None,:];mask=((cc+tt)&1)==0
    q=np.zeros((nc,nt),np.int32);q[mask]=np.rint((Y[mask]-phi)/h).astype(np.int32)
    C0=q[0::2,0::2];C1=q[1::2,1::2];b0,r0,C0d=enc_array(C0);b1,r1,C1d=enc_array(C1)
    P=np.zeros((nc,nt),np.float64);P[0::2,0::2]=phi+h*C0d;P[1::2,1::2]=phi+h*C1d;P=predict_controls(P,mask)
    K=np.rint((Y[~mask]-P[~mask])/h).astype(np.int32);bk,rk,Kd=enc_array(K)
    P[~mask]+=h*Kd;R=P*sign;me=float(np.max(np.abs(W.astype(np.float64)-R)))
    if not np.all(np.isfinite(R)) or not math.isfinite(me) or me>public_eps*(1+5e-6):raise RuntimeError(('checker hard',me,public_eps))
    return b0+b1+bk+160,me,{'control_bytes':b0+b1,'correction_bytes':bk,'correction_nonzero':float(np.mean(K!=0)),'control_reps':[r0,r1],'correction_rep':rk}


def lattice_tile(A,public_eps,internal_eps):
    step=2*internal_eps;Q=np.rint(A.astype(np.float64)/step).astype(np.int32);K=np.empty_like(Q);K[0]=Q[0];K[1:]=Q[1:]-Q[:-1]
    rows=[]
    for rep in (0,1,2):
        b=build_blob(K,rep);RK=decode_blob(b)
        if not np.array_equal(RK,K):raise RuntimeError('lattice integer')
        rows.append((len(b),rep,b))
    nb,rep,b=min(rows,key=lambda x:x[0]);RQ=np.cumsum(decode_blob(b),axis=0,dtype=np.int32);R=RQ.astype(np.float64)*step;me=float(np.max(np.abs(A.astype(np.float64)-R)))
    if not math.isfinite(me) or me>public_eps*(1+5e-6):raise RuntimeError(('lattice hard',me,public_eps))
    return nb,me,float(np.mean(K!=0)),['raw','sparse','ternary'][rep]


def main(path):
    fbytes=os.path.getsize(path)
    with h5py.File(path,'r') as f:
        best,cands=numeric_2d(f);native,name,shape,dtype=best;d=f[name];ta,ca=choose_axes(shape);T=shape[ta];C=shape[ca]
        if C<=6:raise RuntimeError(('no DAS after geophones',shape))
        mean,std,n=global_stats(d,ta,T,C);eps=.1*std;internal=eps*SAFETY
        if not (eps>0 and math.isfinite(eps)):raise RuntimeError(('epsilon',eps,std))
        totals={'sz3':0,'lattice':0,'checker':0,'spectral':0};maxerr={'sz3':0.,'lattice':0.,'checker':0.,'spectral':0.};tiles=0;diag={'lattice_nz_num':0.,'checker_nz_num':0.,'samples':0,'spectral_corr_nz_num':0.,'control_bytes':0,'checker_correction_bytes':0,'spectral_model_bytes':0,'spectral_correction_bytes':0};rows=[]
        for t0 in range(0,T,TIME):
            t1=min(T,t0+TIME)
            for c0 in range(6,C,SPACE):
                c1=min(C,c0+SPACE);A=read_block(d,ta,t0,t1,c0,c1).astype(np.float32,copy=False);W=A.T
                sb,so,sme=sz3_best(A,eps);lb,lme,lnz,lrep=lattice_tile(A,eps,internal);cb,cme,cd=checker_tile(W,eps,internal);blob,pme,pd=encode_tile(W,internal);pb=len(blob)
                if pme>eps*(1+5e-6) or not math.isfinite(pme):raise RuntimeError(('spectral hard',t0,c0,pme,eps))
                totals['sz3']+=sb;totals['lattice']+=lb;totals['checker']+=cb;totals['spectral']+=pb;maxerr['sz3']=max(maxerr['sz3'],sme);maxerr['lattice']=max(maxerr['lattice'],lme);maxerr['checker']=max(maxerr['checker'],cme);maxerr['spectral']=max(maxerr['spectral'],pme);tiles+=1
                ns=A.size;diag['samples']+=ns;diag['lattice_nz_num']+=lnz*ns;diag['checker_nz_num']+=cd['correction_nonzero']*int((~(((np.arange(W.shape[0])[:,None]+np.arange(W.shape[1])[None,:])&1)==0)).sum());diag['spectral_corr_nz_num']+=pd['correction_nonzero_fraction']*ns;diag['control_bytes']+=cd['control_bytes'];diag['checker_correction_bytes']+=cd['correction_bytes'];diag['spectral_model_bytes']+=pd['model_bytes'];diag['spectral_correction_bytes']+=pd['correction_bytes']
                if tiles<=4 or tiles%100==0:rows.append({'tile':tiles,'t0':t0,'c0':c0,'shape':list(A.shape),'sz3':sb,'lattice':lb,'checker':cb,'spectral':pb,'gains':{'lattice':sb/lb,'checker':sb/cb,'spectral':sb/pb},'lattice_nz':lnz,'checker_corr_nz':cd['correction_nonzero'],'spectral_corr_nz':pd['correction_nonzero_fraction']})
                if tiles<=4 or tiles%100==0:print(json.dumps(rows[-1]),flush=True)
        raw=n*2;methods={}
        for k in ('lattice','checker','spectral'):
            methods[k]={'bytes':totals[k],'ratio_raw':raw/totals[k],'bps':8*totals[k]/n,'gain_vs_matched_sz3':totals['sz3']/totals[k],'maxerr':maxerr[k]}
        out={'file':os.path.basename(path),'h5_file_bytes':fbytes,'dataset':name,'dataset_shape':list(shape),'dataset_dtype':dtype,'numeric_candidates':[{'bytes':x[0],'name':x[1],'shape':list(x[2]),'dtype':x[3]} for x in cands],'time_axis':ta,'channel_axis':ca,'time_samples':T,'all_traces':C,'excluded_geophone_traces':6,'das_channels':C-6,'das_samples':n,'das_native_bytes':raw,'das_mean':mean,'das_std':std,'public_eps_10pct_std':eps,'internal_eps':internal,'tiles':tiles,'matched_sz3':{'bytes':totals['sz3'],'ratio_raw':raw/totals['sz3'],'bps':8*totals['sz3']/n,'maxerr':maxerr['sz3'],'metadata_charged':0},'methods':methods,'diagnostics':{'lattice_transition_nonzero':diag['lattice_nz_num']/diag['samples'],'spectral_correction_nonzero':diag['spectral_corr_nz_num']/diag['samples'],'checker_control_bytes':diag['control_bytes'],'checker_correction_bytes':diag['checker_correction_bytes'],'spectral_model_bytes':diag['spectral_model_bytes'],'spectral_correction_bytes':diag['spectral_correction_bytes']},'sampled_tile_rows':rows,'valid':all(math.isfinite(maxerr[k]) and maxerr[k]<=eps*(1+5e-6) for k in maxerr),'scope':'DAS traces only: first six published geophone traces excluded. One global epsilon = 10% std of the actual DAS array. All candidates and SZ3 use identical 128x1024 tiling; SZ3 gets best orientation and zero metadata. Candidate streams are byte-decoded and hard-error verified; HDF5 metadata is outside this sample-array gate.'}
        print(json.dumps({k:out[k] for k in ('dataset','dataset_shape','das_channels','das_native_bytes','das_std','public_eps_10pct_std','tiles','matched_sz3','methods','diagnostics','valid')},indent=2),flush=True);json.dump(out,open('cape_egs_das_benchmark.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
