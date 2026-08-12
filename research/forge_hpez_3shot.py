import json,os,sys
import numpy as np
from pysz import sz,szConfig,szErrorBoundMode

def i16(b,o):return int.from_bytes(b[o:o+2],'little',signed=True)
def u16(b,o):return int.from_bytes(b[o:o+2],'little',signed=False)
def i32(b,o):return int.from_bytes(b[o:o+4],'little',signed=True)
def scaled(v,s):return float(v)*(float(s) if s>0 else (1.0/float(-s) if s<0 else 1.0))

def load(path):
    size=os.path.getsize(path);mm=np.memmap(path,np.uint8,'r');bh=bytes(mm[3200:3600]);dt=u16(bh,16);ns=u16(bh,20);fmt=u16(bh,24);ext=i16(bh,304);fallback=False
    if fmt!=5:
        fam_ns=16001;fam_dt=1000;fam_st=240+4*fam_ns
        if not np.any(np.asarray(mm[:3600])) and size==3600+1747*fam_st:
            ns=fam_ns;dt=fam_dt;fmt=5;ext=0;fallback=True
        else:raise RuntimeError(('format',fmt,size))
    data0=3600+(ext if ext>0 else 0)*3200;st=240+4*ns
    if (size-data0)%st:raise RuntimeError(('layout',size,data0,st,(size-data0)%st))
    n=(size-data0)//st;X=np.ndarray((n,ns),dtype='<f4',buffer=mm,offset=data0+240,strides=(st,4)).copy()
    gx=np.empty(n);gy=np.empty(n);sx=np.empty(n);sy=np.empty(n);offs=np.empty(n,np.int64)
    for j in range(n):
        th=bytes(mm[data0+j*st:data0+j*st+240]);sc=i16(th,70);sx[j]=scaled(i32(th,72),sc);sy[j]=scaled(i32(th,76),sc);gx[j]=scaled(i32(th,80),sc);gy[j]=scaled(i32(th,84),sc);offs[j]=i32(th,36)
        tns=u16(th,114);tdt=u16(th,116)
        if tns not in (0,ns) or tdt not in (0,dt):raise RuntimeError(('trace',j,tns,tdt))
    return X,gx,gy,sx,sy,offs,{'ntr':int(n),'ns':int(ns),'dt':int(dt),'fallback':fallback}

def orderings(gx,gy,sx,sy,offs):
    n=len(gx);idx=np.arange(n);out=[]
    def add(name,o):
        o=np.asarray(o,np.int64)
        if not any(np.array_equal(o,x[1]) for x in out):out.append((name,o))
    add('file',idx);add('x_y',np.lexsort((idx,gy,gx)));add('y_x',np.lexsort((idx,gx,gy)))
    P=np.c_[gx,gy];C=P-P.mean(0);w,V=np.linalg.eigh(C.T@C/max(1,n));u=V[:,np.argmax(w)];v=np.array([-u[1],u[0]]);a=C@u;b=C@v
    add('pca_line',np.lexsort((idx,a,b)));add('pca_along',np.lexsort((idx,b,a)))
    r=np.sqrt((gx-sx)**2+(gy-sy)**2);add('radial',np.lexsort((idx,r)));add('offset_header',np.lexsort((idx,offs)))
    return out

def sz3(A,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);bb,_=sz.compress(np.ascontiguousarray(A),cfg);R,_=sz.decompress(bb,np.float32,A.shape);return int(bb.size),float(np.max(np.abs(A-R)))

def prepare(path):
    X,gx,gy,sx,sy,offs,layout=load(path);raw=int(X.nbytes);std=float(X.astype(np.float64).std());eps=.1*std;orders=orderings(gx,gy,sx,sy,offs);os.makedirs('fair',exist_ok=True);items=[];cmd=[];sz=[]
    for k,(name,o) in enumerate(orders):
        A=np.ascontiguousarray(X[o]);ip=f'fair/{k}_{name}.bin';zp=f'fair/{k}_{name}.hpez';op=f'fair/{k}_{name}.out';A.astype('<f4',copy=False).tofile(ip);items.append({'code':k,'name':name,'input':ip,'compressed':zp,'output':op});cmd.append(f'$BIN -f -i {ip} -z {zp} -2 {X.shape[1]} {X.shape[0]} -M ABS "$EPS" -q 4');cmd.append(f'$BIN -f -z {zp} -o {op} -2 {X.shape[1]} {X.shape[0]}');b,m=sz3(A,eps);sz.append({'name':name,'bytes':b,'ratio':raw/b,'maxerr':m})
    prep={'layout':layout,'shape':list(X.shape),'raw_bytes':raw,'std':std,'eps':eps,'items':items,'sz3':sorted(sz,key=lambda q:q['bytes'])};json.dump(prep,open('fair/prep.json','w'),indent=2);open('fair/run_hpez.sh','w').write('set -euo pipefail\n'+"\n".join(cmd)+'\n');print(json.dumps({'layout':layout,'raw':raw,'eps':eps,'sz3_best':prep['sz3'][0]},indent=2),flush=True)

def analyze(path):
    p=json.load(open('fair/prep.json'));X,gx,gy,sx,sy,offs,layout=load(path);orders=orderings(gx,gy,sx,sy,offs);eps=float(p['eps']);raw=int(p['raw_bytes']);rows=[]
    for it in p['items']:
        name=it['name'];o=dict(orders)[name];A=X[o];R=np.fromfile(it['output'],'<f4').reshape(A.shape);me=float(np.max(np.abs(A-R)));rows.append({'name':name,'bytes':os.path.getsize(it['compressed']),'ratio':raw/os.path.getsize(it['compressed']),'maxerr':me,'valid':bool(me<=eps*(1+3e-6))})
    rows.sort(key=lambda q:q['bytes']);out={'layout':layout,'shape':p['shape'],'raw_bytes':raw,'eps':eps,'hpez':rows,'hpez_best':next(q for q in rows if q['valid']),'sz3':p['sz3'],'sz3_best':p['sz3'][0]};json.dump(out,open('forge_hpez_3shot.json','w'),indent=2);print(json.dumps(out,indent=2),flush=True)

if sys.argv[1]=='prepare':prepare(sys.argv[2])
elif sys.argv[1]=='analyze':analyze(sys.argv[2])
else:raise SystemExit('prepare|analyze file')
