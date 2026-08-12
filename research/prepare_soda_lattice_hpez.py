import json,sys
import numpy as np
src=open('research/soda_lattice_kxyf.py').read().split("\nout={'shots':[]}")[0]
exec(compile(src,'soda_lattice_kxyf.py','exec'),globals())
X,V,Vf,present,tmap,extra,dt,geom=load(sys.argv[1])
C,ny,nx,nt=Vf.shape
# Stack component and receiver-line axes into one regular 3-D tensor so HPEZ
# can exploit component, cross-line, station and temporal continuity within its
# supported 3-D CLI. The exact present-mask is decoder-known from retained SEG-Y headers.
A=Vf.reshape(C*ny,nx,nt)
A.astype('<f4').tofile('soda_lattice_hpez.bin')
present.astype(np.uint8).tofile('soda_lattice_present.bin')
V.astype('<f4').tofile('soda_lattice_true.bin')
if extra.size:extra.astype('<f4').tofile('soda_lattice_extra.bin')
meta={'raw_bytes':int(X.nbytes),'std':float(X.astype(np.float64).std()),'eps':float(.1*X.astype(np.float64).std()),'shape_tensor':[C*ny,nx,nt],'shape_grid':[C,ny,nx,nt],'extra_shape':list(extra.shape),'geometry':geom}
json.dump(meta,open('soda_lattice_hpez_meta.json','w'),indent=2);print(json.dumps(meta,indent=2))
