import json, math, sys
import h5py, numpy as np, zstandard as zstd
from scipy.optimize import linear_sum_assignment
from pysz import sz, szConfig, szErrorBoundMode

NT=1024; NC=64; SAFETY=1-1e-5
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6784))
DMAXS=(1,2,4,8)
DEMODS=(False,True)
ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()

def stats(d):
    s=ss=0.; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64); s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n; return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32))
        cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg); R,_=sz.decompress(b,np.float32,A.shape)
        me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6): raise RuntimeError(('sz error',me,eps))
        row=(int(b.size),'T' if tr else 'CT',me)
        if best is None or row[0]<best[0]: best=row
    return best

def dtype_bytes(a,dt): return np.ascontiguousarray(np.asarray(a,dtype=dt)).tobytes()

def build_paths(X,eps,dmax,demod):
    sign=((1-2*(np.arange(NT)&1)).astype(np.float64)) if demod else np.ones(NT,np.float64)
    Y=X*sign[:,None]; lo=Y-eps*SAFETY; hi=Y+eps*SAFETY
    paths=[]; active=[]
    for c in range(NC):
        paths.append({'t0':0,'c0':c,'cs':[c],'lo':float(lo[0,c]),'hi':float(hi[0,c]),'lastdx':0})
        active.append(len(paths)-1)
    for t in range(1,NT):
        # Assignment cost strongly prefers constant-velocity continuation, then small displacement,
        # then wide surviving interval. Dummy columns permit births when no legal continuation exists.
        C=np.full((NC,2*NC),1e6,np.float64)
        for j in range(NC):
            for ai,pid in enumerate(active):
                p=paths[pid]; pc=p['cs'][-1]; dx=j-pc
                if abs(dx)>dmax: continue
                nl=max(p['lo'],float(lo[t,j])); nh=min(p['hi'],float(hi[t,j]))
                if nl<=nh:
                    width=nh-nl
                    C[j,ai]=(0 if dx==p['lastdx'] else 4.0)+abs(dx-p['lastdx'])+0.15*abs(dx)-1e-4*width
            C[j,NC+j]=20.0 # explicit new-path option
        rr,cc=linear_sum_assignment(C)
        used_old=set(); next_active=[None]*NC
        for j,k in zip(rr,cc):
            if k<NC and C[j,k]<20.0:
                pid=active[k]
                if k in used_old: raise RuntimeError('duplicate assignment')
                used_old.add(k); p=paths[pid]; pc=p['cs'][-1]; dx=j-pc
                p['lo']=max(p['lo'],float(lo[t,j])); p['hi']=min(p['hi'],float(hi[t,j])); p['cs'].append(j); p['lastdx']=dx
                next_active[j]=pid
            else:
                paths.append({'t0':t,'c0':j,'cs':[j],'lo':float(lo[t,j]),'hi':float(hi[t,j]),'lastdx':0})
                next_active[j]=len(paths)-1
        if any(v is None for v in next_active): raise RuntimeError('uncovered time slice')
        active=next_active
    # Each path receives one fp32 amplitude from the intersection of every source interval it covers.
    for p in paths:
        p['v']=np.float32(0.5*(p['lo']+p['hi']))
        if not (p['lo']-1e-5 <= float(p['v']) <= p['hi']+1e-5):
            p['v']=np.float32(p['lo'])
    return paths,sign

def encode_paths(paths,shape):
    paths=sorted(paths,key=lambda p:p['t0']*NC+p['c0'])
    starts=np.array([p['t0']*NC+p['c0'] for p in paths],np.int32)
    sdel=np.diff(np.concatenate((np.array([0],np.int64),starts.astype(np.int64)))).astype(np.int32)
    lens=np.array([len(p['cs']) for p in paths],np.uint16)
    vals=np.array([p['v'] for p in paths],np.float32)
    raw=[]; first=[]; accel=[]
    for p in paths:
        dx=np.diff(np.asarray(p['cs'],np.int16)).astype(np.int8)
        raw.extend(dx.tolist())
        if dx.size:
            first.append(int(dx[0]))
            if dx.size>1: accel.extend(np.diff(dx.astype(np.int16)).astype(np.int8).tolist())
    frames={}
    frames['starts']=ZC.compress(dtype_bytes(sdel,'<i4'))
    frames['lengths']=ZC.compress(dtype_bytes(lens,'<u2'))
    frames['values']=ZC.compress(dtype_bytes(vals,'<f4'))
    br=ZC.compress(dtype_bytes(raw,'i1')) if raw else b''
    bf=ZC.compress(dtype_bytes(first,'i1')) if first else b''
    ba=ZC.compress(dtype_bytes(accel,'i1')) if accel else b''
    if len(br)<=len(bf)+len(ba)+8:
        motion='raw'; frames['motion']=br
    else:
        motion='accel'; frames['first']=bf; frames['accel']=ba
    total=96+sum(len(v) for v in frames.values())
    # Byte-decode every stream and reconstruct exact path geometry.
    sd=np.frombuffer(ZD.decompress(frames['starts']),dtype='<i4',count=len(paths)); ss=np.cumsum(sd,dtype=np.int64)
    ll=np.frombuffer(ZD.decompress(frames['lengths']),dtype='<u2',count=len(paths)).astype(np.int64)
    vv=np.frombuffer(ZD.decompress(frames['values']),dtype='<f4',count=len(paths))
    if motion=='raw':
        nm=int(np.sum(ll-1)); dxall=np.frombuffer(ZD.decompress(frames['motion']),dtype='i1',count=nm).astype(np.int16) if nm else np.empty(0,np.int16)
    else:
        nf=int(np.sum(ll>1)); nd=int(np.sum(np.maximum(ll-2,0)))
        ff=np.frombuffer(ZD.decompress(frames['first']),dtype='i1',count=nf).astype(np.int16) if nf else np.empty(0,np.int16)
        aa=np.frombuffer(ZD.decompress(frames['accel']),dtype='i1',count=nd).astype(np.int16) if nd else np.empty(0,np.int16)
        chunks=[]; fi=ai=0
        for L in ll:
            if L<=1: continue
            d=[int(ff[fi])]; fi+=1
            for _ in range(int(L)-2): d.append(d[-1]+int(aa[ai])); ai+=1
            chunks.extend(d)
        dxall=np.asarray(chunks,np.int16)
    V=np.full(shape,np.nan,np.float32); di=0
    for st,L,v in zip(ss,ll,vv):
        t=int(st//NC); c=int(st%NC); V[t,c]=v
        for _ in range(int(L)-1):
            c += int(dxall[di]); di+=1; t+=1
            if not (0<=t<shape[0] and 0<=c<shape[1]): raise RuntimeError('decoded path out of bounds')
            if not np.isnan(V[t,c]): raise RuntimeError('decoded path collision')
            V[t,c]=v
    if np.isnan(V).any(): raise RuntimeError('decoded path holes')
    return total,V,motion,{k:len(v) for k,v in frames.items()}

def evaluate(X,eps,dmax,demod):
    paths,sign=build_paths(X,eps,dmax,demod); total,V,motion,fb=encode_paths(paths,X.shape)
    R=V.astype(np.float64)*sign[:,None]
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6): raise RuntimeError(('hard error',dmax,demod,me,eps))
    lengths=np.array([len(p['cs']) for p in paths],np.int32)
    dirs=np.concatenate([np.diff(np.asarray(p['cs'],np.int16)) for p in paths if len(p['cs'])>1]) if np.any(lengths>1) else np.empty(0,np.int16)
    if dirs.size:
        _,cnt=np.unique(dirs,return_counts=True); pp=cnt/cnt.sum(); de=float(-(pp*np.log2(pp)).sum())
    else: de=0.
    return {'dmax':dmax,'nyquist_demod':demod,'bytes':total,'bps':8*total/X.size,'paths':len(paths),'mean_path_len':float(lengths.mean()),'median_path_len':float(np.median(lengths)),'p90_path_len':float(np.percentile(lengths,90)),'max_path_len':int(lengths.max()),'direction_entropy_bps':de,'motion_rep':motion,'frame_bytes':fb,'maxerr':me}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,std=stats(d); eps=.1*std; rows=[]; tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64); sb=szrun(X,eps)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/X.size,'local_std':float(X.std())})
            for demod in DEMODS:
                for dm in DMAXS:
                    r=evaluate(X,eps,dm,demod); r.update({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes']}); rows.append(r)
                    print(json.dumps(r),flush=True)
        combos=[]
        for demod in DEMODS:
            for dm in DMAXS:
                rr=[r for r in rows if r['nyquist_demod']==demod and r['dmax']==dm]
                b=sum(r['bytes'] for r in rr); s=sum(r['sz3_bytes'] for r in rr); n=NT*NC*len(rr)
                combos.append({'dmax':dm,'nyquist_demod':demod,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,'median_mean_path_len':float(np.median([r['mean_path_len'] for r in rr])),'median_direction_entropy_bps':float(np.median([r['direction_entropy_bps'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['bytes'])
        out={'std':std,'eps':eps,'patch_shape':[NT,NC],'specs':[list(x) for x in SPECS],'dmaxs':list(DMAXS),'demods':list(DEMODS),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Real-byte hard-error interval transport-tube screen. Each spacetime source sample is only its +/-10%-global-std interval. A causal path may move up to dmax channels per time step and is extended only while the intersection of every interval on that path remains nonempty; the entire path is reconstructed from one transmitted fp32 amplitude. Path starts, lengths, amplitudes and either raw motion or acceleration motion are Zstd serialized and byte-decoded. Optional deterministic Nyquist demodulation preserves the L-infinity error exactly. Final patches are reconstructed from decoded path records and hard-error verified. Matched SZ3 is rerun on identical patches. Exploratory patch screen, no whole-array claim.'}
        print(json.dumps({'combos':combos},indent=2),flush=True); json.dump(out,open('imperial_isoamplitude_transport_tubes.json','w'),indent=2)
if __name__=='__main__': main(sys.argv[1])
