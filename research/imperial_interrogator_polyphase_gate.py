import json,sys
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode

REGIONS=(512,2304,4608,6784); NC=64; STRIDES=(1,2,4,8,16); LAGS=tuple(range(1,33))

def jv(v):
    if isinstance(v,bytes): return v.decode('utf-8','replace')
    if isinstance(v,np.ndarray): return v.tolist()
    if isinstance(v,np.generic): return v.item()
    try: json.dumps(v); return v
    except Exception: return str(v)

def metadata(f):
    out={'file_attrs':{k:jv(v) for k,v in f.attrs.items()},'objects':{}}
    def visit(name,obj):
        row={'type':type(obj).__name__,'attrs':{k:jv(v) for k,v in obj.attrs.items()}}
        if isinstance(obj,h5py.Dataset): row.update({'shape':list(obj.shape),'dtype':str(obj.dtype),'chunks':list(obj.chunks) if obj.chunks else None,'compression':obj.compression,'compression_opts':jv(obj.compression_opts),'shuffle':bool(obj.shuffle),'fletcher32':bool(obj.fletcher32)})
        out['objects'][name]=row
    f.visititems(visit); return out

def stats(d):
    s=ss=0.; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64); s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n; return m,float(np.sqrt(max(0.,ss/n-m*m)))

def sz_one(A,eps):
    best=None
    for tr in (False,True):
        B=np.ascontiguousarray((A.T if tr else A).astype(np.float32))
        cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=float(eps)
        b,_=sz.compress(B,cfg); R,_=sz.decompress(b,np.float32,B.shape)
        me=float(np.max(np.abs(B-R)))
        if me>eps*(1+5e-6): raise RuntimeError(('sz bound',me,eps))
        row=(int(b.size),'T' if tr else 'CT',R)
        if best is None or row[0]<best[0]: best=row
    return best

def corr(a,b):
    a=np.asarray(a,np.float64).ravel(); b=np.asarray(b,np.float64).ravel();
    am=a.mean(); bm=b.mean(); da=a-am; db=b-bm; den=np.sqrt(float(np.dot(da,da))*float(np.dot(db,db)))
    return float(np.dot(da,db)/den) if den else 0.0

def phase_codec(X,eps,stride):
    if stride==1:
        b,ori,R=sz_one(X,eps); return {'bytes':b+32,'payload_bytes':b,'orientations':[ori],'maxerr':float(np.max(np.abs(X-(R.T if ori=='T' else R))))}
    RR=np.empty_like(X,np.float32); total=32+8*stride; oris=[]; payload=0
    for p in range(stride):
        A=X[p::stride,:]; b,ori,R=sz_one(A,eps); payload+=b; total+=b; oris.append(ori)
        dec=R.T if ori=='T' else R; RR[p::stride,:]=dec
    me=float(np.max(np.abs(X-RR.astype(np.float64))))
    if me>eps*(1+5e-6): raise RuntimeError(('poly bound',stride,me,eps))
    return {'bytes':total,'payload_bytes':payload,'orientations':oris,'maxerr':me}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; meta=metadata(f); _,std=stats(d); eps=.1*std; rows=[]; lagrows=[]
        for c0 in REGIONS:
            X=np.asarray(d[:,c0:c0+NC],np.float64)
            cs=[]
            for lag in LAGS:
                cs.append({'lag':lag,'corr':corr(X[:-lag],X[lag:])})
            lagrows.append({'c0':c0,'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),'lag_corr':cs})
            direct=None
            for s in STRIDES:
                r=phase_codec(X,eps,s); r.update({'c0':c0,'stride':s,'samples':int(X.size),'bps':8*r['bytes']/X.size})
                rows.append(r)
                if s==1: direct=r['bytes']
                r['gain_vs_unsplit_sz3']=direct/r['bytes'] if direct else 1.0
                print(json.dumps({'c0':c0,'stride':s,'bytes':r['bytes'],'bps':r['bps'],'gain':r['gain_vs_unsplit_sz3'],'maxerr':r['maxerr']}),flush=True)
        combos=[]
        for s in STRIDES:
            rr=[r for r in rows if r['stride']==s]; b=sum(r['bytes'] for r in rr); base=sum(r['bytes'] for r in rows if r['stride']==1); n=sum(r['samples'] for r in rr)
            combos.append({'stride':s,'bytes':b,'unsplit_sz3_bytes':base,'bps':8*b/n,'gain_vs_unsplit_sz3':base/b,'min_region_gain':min(r['gain_vs_unsplit_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['bytes'])
        out={'metadata':meta,'shape':list(d.shape),'dtype':str(d.dtype),'global_std':std,'eps':eps,'regions':list(REGIONS),'channels_per_region':NC,'strides':list(STRIDES),'combos':combos,'rows':rows,'lag_rows':lagrows,'scope':'Instrument-specific temporal polyphase gate. Official acquisition uses a 2 kHz laser pulse rate and archived 500 Hz strain-rate output; this experiment does not assume a vendor implementation, but tests whether a periodic/polyphase state survives in the stored samples. Full 30,000-sample x 64-channel regions are split into decoder-known t mod stride streams, each independently SZ3-compressed at the exact same global 10%-std absolute error. All phase streams are byte-decoded, reinterleaved, and hard-error verified. Metadata/attributes from the actual HDF5 are dumped verbatim where serializable. No target fitting.'}
        print(json.dumps({'combos':combos,'lag_rows':lagrows},indent=2),flush=True); json.dump(out,open('imperial_interrogator_polyphase_gate.json','w'),indent=2)
if __name__=='__main__': main(sys.argv[1])
