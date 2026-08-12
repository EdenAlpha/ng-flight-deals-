import json, os, sys
import numpy as np
import segyio
from pysz import sz,szConfig,szErrorBoundMode

def u16(b,o):return int.from_bytes(b[o:o+2],'little',signed=False)
def i16(b,o):return int.from_bytes(b[o:o+2],'little',signed=True)
def manual(path):
    size=os.path.getsize(path)
    with open(path,'rb') as f:
        h=f.read(3600);bh=h[3200:3600];dt=u16(bh,16);ns=u16(bh,20);fmt=u16(bh,24);ext=i16(bh,304);data0=3600+max(0,ext)*3200
        if fmt!=5:raise RuntimeError(('format',fmt))
        stride=240+4*ns;rem=size-data0
        if rem%stride:raise RuntimeError(('stride',rem,stride,rem%stride))
        ntr=rem//stride;X=np.empty((ntr,ns),np.float32);f.seek(data0)
        for i in range(ntr):
            th=f.read(240);nst=u16(th,114) or ns
            if nst!=ns:raise RuntimeError(('ns',i,nst,ns))
            X[i]=np.frombuffer(f.read(4*ns),dtype='<f4',count=ns)
    return X,{'file_bytes':size,'dt_us':dt,'ns':ns,'format':fmt,'data_offset':data0,'trace_count':int(ntr)}

def sz3(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(b,np.float32,A.shape);return {'bytes':int(b.size),'ratio':float(A.nbytes/int(b.size)),'maxerr':float(np.max(np.abs(A-R)))}

def prepare(path):
    X,meta=manual(path)
    with segyio.open(path,'r',ignore_geometry=True,endian='little') as s:
        Y=np.asarray(s.trace.raw[:],np.float32).copy();sd=int(segyio.tools.dt(s))
    parser={'segyio_shape':list(Y.shape),'manual_shape':list(X.shape),'segyio_dt_us':sd,'exact_sample_match':bool(np.array_equal(X,Y)),'max_sample_difference':float(np.max(np.abs(X-Y))) if X.shape==Y.shape else None}
    if X.shape!=Y.shape or not np.array_equal(X,Y):raise RuntimeError({'parser_mismatch':parser})
    std=float(X.astype(np.float64).std());eps=.1*std;os.makedirs('fair',exist_ok=True);np.ascontiguousarray(X.astype('<f4',copy=False)).tofile('fair/file.bin');np.ascontiguousarray(X.T.astype('<f4',copy=False)).tofile('fair/transposed.bin')
    prep={'meta':meta,'parser':parser,'shape':list(X.shape),'raw_bytes':int(X.nbytes),'std':std,'eps':eps,'sz3_file':sz3(X,eps),'sz3_transposed':sz3(X.T.copy(),eps)};json.dump(prep,open('fair/prep.json','w'),indent=2);print(json.dumps(prep,indent=2),flush=True)

def analyze(path):
    X,meta=manual(path);p=json.load(open('fair/prep.json'));eps=float(p['eps']);raw=int(p['raw_bytes']);rows=[]
    for name,ref in [('file',X),('transposed',X.T)]:
        cb=f'fair/{name}.hpez';ob=f'fair/{name}.out';R=np.fromfile(ob,dtype='<f4').reshape(ref.shape);me=float(np.max(np.abs(ref-R)));rows.append({'layout':name,'bytes':os.path.getsize(cb),'ratio':float(raw/os.path.getsize(cb)),'maxerr':me,'valid':bool(me<=eps*(1+3e-6))})
    rows.sort(key=lambda r:r['bytes']);out={'raw_bytes':raw,'eps':eps,'parser':p['parser'],'hpez':rows,'hpez_best':rows[0],'sz3_file':p['sz3_file'],'sz3_transposed':p['sz3_transposed']};json.dump(out,open('forge_raw_hpez_audit.json','w'),indent=2);print(json.dumps(out,indent=2),flush=True)

if sys.argv[1]=='prepare':prepare(sys.argv[2])
elif sys.argv[1]=='analyze':analyze(sys.argv[2])
else:raise SystemExit('prepare|analyze file')
