import itertools,json,os,subprocess,sys,tempfile
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode
src=open('research/soda_lattice_kxyf.py').read().split("\nout={'shots':[]}")[0]
exec(compile(src,'soda_lattice_kxyf.py','exec'),globals())

BIN=os.path.abspath(sys.argv[1]); paths=sys.argv[2:]; OUT=[]
def sz3_extra(E,eps):
    if not E.size:return 0,0.0
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(E),cfg);R,_=sz.decompress(b,np.float32,E.shape);return int(b.size),float(np.max(np.abs(E-R)))

for si,path in enumerate(paths):
    X,V,Vf,present,tmap,extra,dt,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);C,ny,nx,nt=Vf.shape;A=Vf.reshape(C*ny,nx,nt);eb,ee=sz3_extra(extra,eps)
    natural=(C*ny,nx,nt);dims=[]
    if si==1:
        dims += sorted(set(itertools.permutations(natural)))
        alt=(C,ny*nx,nt);dims += [d for d in sorted(set(itertools.permutations(alt))) if d not in dims]
    else:
        dims=[natural,(nt,nx,C*ny),(nx,nt,C*ny)]
    rows=[]
    with tempfile.TemporaryDirectory() as td:
        inp=os.path.join(td,'block.bin');A.astype('<f4').tofile(inp)
        for k,d in enumerate(dims):
            tag='x'.join(map(str,d));cb=os.path.join(td,f'{k}.hpez');ob=os.path.join(td,f'{k}.out')
            subprocess.run([BIN,'-f','-i',inp,'-z',cb,'-3',*map(str,d),'-M','ABS',str(eps),'-q','4'],check=True,stdout=subprocess.DEVNULL)
            subprocess.run([BIN,'-f','-z',cb,'-o',ob,'-3',*map(str,d)],check=True,stdout=subprocess.DEVNULL)
            Y=np.fromfile(ob,'<f4').reshape(V.shape);me=0.0
            for c in range(C):me=max(me,float(np.max(np.abs(V[c][present[c]]-Y[c][present[c]]))))
            total=os.path.getsize(cb)+eb;rows.append({'dims':list(d),'core_bytes':os.path.getsize(cb),'extra_bytes':eb,'bytes':total,'ratio':raw/total,'maxerr':max(me,ee),'valid':bool(max(me,ee)<=eps*(1+5e-6))});print('HPEZ',os.path.basename(path),rows[-1],flush=True)
    rows.sort(key=lambda r:r['ratio'],reverse=True);OUT.append({'file':os.path.basename(path),'raw_bytes':raw,'eps':eps,'geometry':geom,'rows':rows})
json.dump({'shots':OUT},open('soda_hpez_three_fairness.json','w'),indent=2)
print('BEST',json.dumps([{'file':s['file'],'best':s['rows'][0]} for s in OUT],indent=2))
