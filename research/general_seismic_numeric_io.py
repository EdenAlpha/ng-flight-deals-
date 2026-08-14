import json, os
import numpy as np


def _panelize_rows(X, channels=128, time_limit=None):
    X=np.asarray(X)
    if X.ndim!=2: raise ValueError(('need 2D numeric array',X.shape))
    if time_limit is not None: X=X[:,:int(time_limit)]
    for c0 in range(0,X.shape[0],int(channels)):
        P=np.ascontiguousarray(X[c0:min(c0+int(channels),X.shape[0])])
        if P.shape[0] and P.shape[1]: yield P,c0


def segy_panels(path, channels=128, time_limit=None, max_panels=None):
    import segyio
    with segyio.open(path,'r',ignore_geometry=True) as f:
        ntr=int(f.tracecount)
        ns=int(len(f.samples))
        nout=0
        for c0 in range(0,ntr,int(channels)):
            ids=range(c0,min(c0+int(channels),ntr))
            P=np.asarray([np.asarray(f.trace[i],dtype=np.float32) for i in ids],dtype=np.float32)
            if time_limit is not None:P=P[:,:int(time_limit)]
            if P.size:
                yield np.ascontiguousarray(P),{'format':'SEG-Y','trace0':c0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':False,'source_dtype':'float32(segy-decoded)','file_trace_count':ntr,'file_samples_per_trace':ns}
                nout+=1
                if max_panels is not None and nout>=int(max_panels):break


def _numeric_h5_datasets(group,prefix=''):
    import h5py
    out=[]
    for k,v in group.items():
        p=f'{prefix}/{k}' if prefix else f'/{k}'
        if isinstance(v,h5py.Dataset) and np.issubdtype(v.dtype,np.number) and v.ndim>=2:
            out.append((p,v))
        elif isinstance(v,h5py.Group):out.extend(_numeric_h5_datasets(v,p))
    return out


def choose_h5_dataset(f, dataset=None):
    if dataset:
        d=f[dataset]
        if not np.issubdtype(d.dtype,np.number) or d.ndim<2:raise ValueError(('not numeric 2D+',dataset,d.dtype,d.shape))
        return dataset,d
    cands=_numeric_h5_datasets(f)
    if not cands:raise RuntimeError('no numeric >=2D HDF5 dataset')
    # Deterministic schema discovery only: prefer common seismic names, then largest dataset.
    names=('acoustic','data','strain','strain_rate','raw','samples','das')
    def score(q):
        p,d=q;low=p.lower();name_rank=min([i for i,n in enumerate(names) if n in low] or [len(names)])
        return (name_rank,-int(np.prod(d.shape)),p)
    return min(cands,key=score)


def hdf5_panels(path, channels=128, time_limit=None, max_panels=None, dataset=None, orientation='auto'):
    import h5py
    with h5py.File(path,'r') as f:
        dpath,d=choose_h5_dataset(f,dataset)
        if d.ndim!=2:raise ValueError(('current HDF5 reader requires 2D seismic dataset',dpath,d.shape))
        shape=tuple(map(int,d.shape));isint=bool(np.issubdtype(d.dtype,np.integer))
        if orientation=='time_channels' or (orientation=='auto' and shape[0]>=shape[1]):
            nt,nc=shape;nout=0
            for c0 in range(0,nc,int(channels)):
                t1=nt if time_limit is None else min(nt,int(time_limit));P=np.asarray(d[:t1,c0:min(c0+int(channels),nc)]).T
                if P.size:
                    yield np.ascontiguousarray(P),{'format':'HDF5','dataset':dpath,'orientation':'time_channels','channel0':c0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':isint,'source_dtype':str(d.dtype),'dataset_shape':list(shape)}
                    nout+=1
                    if max_panels is not None and nout>=int(max_panels):break
        else:
            nc,nt=shape;nout=0
            for c0 in range(0,nc,int(channels)):
                t1=nt if time_limit is None else min(nt,int(time_limit));P=np.asarray(d[c0:min(c0+int(channels),nc),:t1])
                if P.size:
                    yield np.ascontiguousarray(P),{'format':'HDF5','dataset':dpath,'orientation':'channels_time','channel0':c0,'trace_count':int(P.shape[0]),'samples_per_trace':int(P.shape[1]),'source_integer':isint,'source_dtype':str(d.dtype),'dataset_shape':list(shape)}
                    nout+=1
                    if max_panels is not None and nout>=int(max_panels):break


def matched_sz3(X,eps):
    from pysz import sz,szConfig,szErrorBoundMode
    X=np.ascontiguousarray(X)
    # SZ3/pysz operates on float32 here so both codecs see identical numeric values.
    A=np.ascontiguousarray(X.astype(np.float32,copy=False))
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    bb,_=sz.compress(A,cfg);R,_=sz.decompress(bb,np.float32,A.shape)
    me=float(np.max(np.abs(A.astype(np.float64)-R.astype(np.float64))))
    if me>float(eps)*(1+3e-6):raise RuntimeError(('SZ3 hard bound',me,float(eps)))
    return int(bb.size),me


def gate_panel(X,meta,portfolio_config):
    from general_seismic_codec_portfolio import load_config,encode_portfolio,decode_portfolio
    cfg=load_config(portfolio_config);A=np.asarray(X);eps=.1*float(A.astype(np.float64).std())
    if not np.isfinite(eps) or eps<=0:raise RuntimeError(('bad epsilon',eps))
    blob,pm=encode_portfolio(A,eps,cfg,bool(meta.get('source_integer',False)));R=decode_portfolio(blob);pme=float(np.max(np.abs(A.astype(np.float64)-np.asarray(R,np.float64))));szb,szme=matched_sz3(A,eps)
    return {'meta':meta,'shape':list(A.shape),'samples':int(A.size),'std':eps*10.,'eps':eps,'portfolio_bytes':len(blob),'portfolio_bps':8.*len(blob)/A.size,'selected_id':int(pm['selected_id']),'selected_engine':pm['selected_engine'],'portfolio_maxerr':pme,'sz3_bytes':int(szb),'sz3_bps':8.*szb/A.size,'sz3_maxerr':szme,'gain_sz3_over_portfolio':float(szb/len(blob)),'scope':'real-data mechanics gate only; epsilon is local to this gate slice and is NOT a headline benchmark result'}


def run_gate(segy_path,h5_path,portfolio_config,h5_dataset='Acoustic'):
    rows=[]
    P,m=next(segy_panels(segy_path,time_limit=4096,max_panels=1));rows.append(gate_panel(P,m,portfolio_config))
    P,m=next(hdf5_panels(h5_path,time_limit=4096,max_panels=1,dataset=h5_dataset,orientation='time_channels'));rows.append(gate_panel(P,m,portfolio_config))
    return {'rows':rows,'scope':'Real SEG-Y + HDF5 reader/portfolio/SZ3 correctness gate. Not part of frozen headline survey statistics.'}

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--gate',action='store_true');ap.add_argument('--segy');ap.add_argument('--h5');ap.add_argument('--h5-dataset',default='Acoustic');ap.add_argument('--config',default='benchmarks/general_seismic_codec_portfolio_v1.json');ap.add_argument('--out',default='general_seismic_real_data_gate.json');a=ap.parse_args()
 if a.gate:
  x=run_gate(a.segy,a.h5,a.config,a.h5_dataset);json.dump(x,open(a.out,'w'),indent=2);print(json.dumps(x,indent=2))
