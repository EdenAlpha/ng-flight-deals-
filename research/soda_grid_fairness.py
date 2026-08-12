import itertools,json,os,sys
import numpy as np,segyio
from pysz import sz,szConfig,szErrorBoundMode

src=open('research/soda_grid_lattice.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_grid_lattice.py','exec'),globals())

def sz3_one(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    b,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(b,np.float32,A.shape)
    return int(b.size),float(np.max(np.abs(A-R)))

def prepare(path):
    X,gx,gy,dt=load(path);eps=.1*float(X.astype(np.float64).std());raw=X.nbytes
    Gi,tm,outids,geom=geometry_map(X,gx,gy);F=np.zeros(Gi.shape,np.float32)
    for tid,c,l,s in tm:F[c,l,s]=X[tid]
    O=X[outids].copy();os.makedirs('fair',exist_ok=True);cmd=[];items=[]
    def add(name,A,kind,comp=None,perm=None):
        p=f'fair/{name}.bin';z=f'fair/{name}.hpez';o=f'fair/{name}.out';np.ascontiguousarray(A.astype('<f4',copy=False)).tofile(p);sh=A.shape
        dims=' '.join(str(int(x)) for x in sh[::-1]);cmd.append(f'$BIN -f -i {p} -z {z} -{len(sh)} {dims} -M ABS "$EPS" -q 4');cmd.append(f'$BIN -f -z {z} -o {o} -{len(sh)} {dims}')
        items.append({'name':name,'kind':kind,'comp':comp,'perm':list(perm) if perm is not None else None,'shape':list(sh),'source_shape':list(A.shape),'input':p,'compressed':z,'output':o})
    # File-order baseline and exact transpose.
    add('file_p01',X,'file',perm=(0,1));add('file_p10',X.T.copy(),'file',perm=(1,0))
    # Geometry-aware component grids with all physical axis permutations.
    perms=list(itertools.permutations(range(3)))
    sz_components=[]
    for c in range(F.shape[0]):
        sr=[]
        for p in perms:
            A=F[c].transpose(p).copy();name=f'grid_c{c}_p{"".join(map(str,p))}';add(name,A,'grid',comp=c,perm=p);bb,me=sz3_one(A,eps);sr.append({'perm':list(p),'bytes':bb,'maxerr':me})
        sr.sort(key=lambda r:r['bytes']);sz_components.append(sr)
    sz_out=[]
    for p in [(0,1),(1,0)]:
        A=O.transpose(p).copy();name=f'out_p{p[0]}{p[1]}';add(name,A,'out',perm=p);bb,me=sz3_one(A,eps);sz_out.append({'perm':list(p),'bytes':bb,'maxerr':me})
    sz_out.sort(key=lambda r:r['bytes'])
    sz_file=[]
    for p,A in [((0,1),X),((1,0),X.T.copy())]:
        bb,me=sz3_one(A,eps);sz_file.append({'perm':list(p),'bytes':bb,'maxerr':me})
    sz_file.sort(key=lambda r:r['bytes'])
    prep={'file':os.path.basename(path),'raw_bytes':raw,'eps':eps,'dt_us':dt,'geometry':geom,'grid_shape':list(F.shape),'out_shape':list(O.shape),'items':items,'sz3_file':sz_file,'sz3_components':sz_components,'sz3_out':sz_out}
    prep['sz3_geometry']={'bytes':sum(r[0]['bytes'] for r in sz_components)+sz_out[0]['bytes']}
    prep['sz3_geometry']['ratio']=raw/prep['sz3_geometry']['bytes']
    json.dump(prep,open('fair/prep.json','w'),indent=2)
    open('fair/run_hpez.sh','w').write('set -euo pipefail\n'+"\n".join(cmd)+'\n')
    print(json.dumps({'eps':eps,'raw':raw,'geometry':geom,'sz3_file_best':sz_file[0],'sz3_geometry':prep['sz3_geometry']},indent=2),flush=True)

def analyze(path):
    prep=json.load(open('fair/prep.json'));eps=float(prep['eps']);raw=int(prep['raw_bytes']);X,gx,gy,dt=load(path);Gi,tm,outids,geom=geometry_map(X,gx,gy);F=np.zeros(Gi.shape,np.float32)
    for tid,c,l,s in tm:F[c,l,s]=X[tid]
    O=X[outids].copy();rows=[]
    for it in prep['items']:
        cb=it['compressed'];ob=it['output'];A=np.fromfile(ob,'<f4').reshape(tuple(it['shape']));kind=it['kind'];p=tuple(it['perm'])
        if kind=='file': ref=X if p==(0,1) else X.T
        elif kind=='grid': ref=F[int(it['comp'])].transpose(p)
        else: ref=O.transpose(p)
        me=float(np.max(np.abs(ref-A)));rows.append({**it,'bytes':os.path.getsize(cb),'ratio':raw/os.path.getsize(cb),'maxerr':me,'valid':bool(me<=eps*(1+3e-6))})
    valid=[r for r in rows if r['valid']];file_rows=sorted([r for r in valid if r['kind']=='file'],key=lambda r:r['bytes']);grid=[]
    for c in range(F.shape[0]):grid.append(sorted([r for r in valid if r['kind']=='grid' and r['comp']==c],key=lambda r:r['bytes']))
    out_rows=sorted([r for r in valid if r['kind']=='out'],key=lambda r:r['bytes']);hpez_geom_bytes=sum(g[0]['bytes'] for g in grid)+out_rows[0]['bytes']
    # Aggressive hybrid comparator: per geometry segment choose the smaller official HPEZ or SZ3 result.
    hybrid_main=sum(min(grid[c][0]['bytes'],prep['sz3_components'][c][0]['bytes']) for c in range(len(grid)));hybrid_out=min(out_rows[0]['bytes'],prep['sz3_out'][0]['bytes']);hybrid=hybrid_main+hybrid_out
    candidates=[('HPEZ_file',file_rows[0]['bytes']),('HPEZ_geometry',hpez_geom_bytes),('SZ3_file',prep['sz3_file'][0]['bytes']),('SZ3_geometry',prep['sz3_geometry']['bytes']),('geometry_hybrid',hybrid)];candidates.sort(key=lambda x:x[1])
    res={'raw_bytes':raw,'eps':eps,'geometry':geom,'hpez_file_best':file_rows[:2],'hpez_grid_best':[g[:2] for g in grid],'hpez_out_best':out_rows[:2],'hpez_geometry':{'bytes':hpez_geom_bytes,'ratio':raw/hpez_geom_bytes},'sz3_file_best':prep['sz3_file'][0],'sz3_geometry':prep['sz3_geometry'],'geometry_hybrid':{'bytes':hybrid,'ratio':raw/hybrid},'strongest':{'kind':candidates[0][0],'bytes':candidates[0][1],'ratio':raw/candidates[0][1]}}
    json.dump(res,open('soda_grid_fairness.json','w'),indent=2);print(json.dumps(res,indent=2),flush=True)

if __name__=='__main__':
    if sys.argv[1]=='prepare':prepare(sys.argv[2])
    elif sys.argv[1]=='analyze':analyze(sys.argv[2])
    else:raise SystemExit('prepare|analyze path')
