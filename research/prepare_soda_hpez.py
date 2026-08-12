import json,sys
import numpy as np
import segyio

p=sys.argv[1]
with segyio.open(p,'r',ignore_geometry=True) as f:
    X=np.asarray(f.trace.raw[:],dtype=np.float32).copy()
    gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.float64)
    gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.float64)
    sx=np.asarray(f.attributes(segyio.TraceField.SourceX)[:],dtype=np.float64)
    sy=np.asarray(f.attributes(segyio.TraceField.SourceY)[:],dtype=np.float64)
    try: sc=np.asarray(f.attributes(segyio.TraceField.SourceGroupScalar)[:],dtype=np.float64)
    except Exception: sc=np.ones(len(X),np.float64)
scale=np.where(sc<0,1.0/np.maximum(1.0,-sc),np.where(sc>0,sc,1.0));gx*=scale;gy*=scale;sx*=scale;sy*=scale
std=float(X.astype(np.float64).std());eps=.1*std
X.astype('<f4').tofile('soda_file.bin')
groups={};extra=[]
for i,(x,y) in enumerate(zip(gx,gy)):
    if x==0 and y==0: extra.append(i); continue
    groups.setdefault((round(float(x),6),round(float(y),6)),[]).append(i)
keys=list(groups);counts=np.array([len(v) for v in groups.values()]);C=int(np.bincount(counts).argmax())
src=np.array([np.median(sx[np.isfinite(sx)&(sx!=0)]),np.median(sy[np.isfinite(sy)&(sy!=0)])]);rec=np.asarray(keys,float);off=np.linalg.norm(rec-src,axis=1)
layouts={
 'receiver':np.arange(len(keys)),
 'offset':np.argsort(off),
 'lexgeo':np.lexsort((rec[:,0],rec[:,1]))
}
for name,o in layouts.items():
    V=np.stack([np.stack([X[groups[keys[j]][c]] for j in o]) for c in range(C)])
    V.astype('<f4').tofile(f'soda_{name}3d.bin')
if extra:
    X[np.asarray(extra)].astype('<f4').tofile('soda_extra.bin')
meta={'shape_file':list(X.shape),'raw_bytes':int(X.nbytes),'std':std,'eps':eps,'receiver_groups':len(keys),'components':C,'extra_traces':len(extra),'shape_grouped':[C,len(keys),X.shape[1]]}
json.dump(meta,open('soda_hpez_meta.json','w'),indent=2)
print(json.dumps(meta,indent=2))
