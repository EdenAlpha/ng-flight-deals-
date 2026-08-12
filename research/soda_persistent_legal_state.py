import json,os,struct,sys
import numpy as np
import segyio,zstandard as zstd
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
FACTORS=[2.0,1.5,1.0,0.75,0.5,0.375,0.25,0.125]
IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}

def leb(u):
    o=bytearray()
    for x in np.asarray(u,dtype=np.uint64).ravel():
        x=int(x)
        while x>=128:o.append((x&127)|128);x>>=7
        o.append(x)
    return bytes(o)
def unleb(b,n):
    a=np.empty(n,np.uint64);i=j=0
    while i<n:
        x=sh=0
        while True:
            v=b[j];j+=1;x|=(v&127)<<sh
            if v<128:break
            sh+=7
        a[i]=x;i+=1
    if j!=len(b):raise RuntimeError('varint trailing')
    return a

def pack_int(a):
    a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dc=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3;b=Z.compress(np.ascontiguousarray(a.astype(IDT[dc],copy=False)).tobytes());return dc,b
def unpack_int(b,dc,n):
    a=np.frombuffer(D.decompress(b),dtype=IDT[dc],count=n)
    if a.size!=n:raise RuntimeError('int mismatch')
    return a.astype(np.int32,copy=False)

def choose_states(intervals):
    # Exact small-state DP minimizes sum absolute integer jumps, including from zero.
    opts=[np.arange(lo,hi+1,dtype=np.int32) for lo,hi in intervals];cost=np.abs(opts[0].astype(np.int64));backs=[]
    for i in range(1,len(opts)):
        p=opts[i-1].astype(np.int64);q=opts[i].astype(np.int64);M=cost[:,None]+np.abs(p[:,None]-q[None,:]);arg=np.argmin(M,axis=0);backs.append(arg.astype(np.int16));cost=M[arg,np.arange(len(q))]
    j=int(np.argmin(cost));out=[int(opts[-1][j])]
    for i in range(len(opts)-2,-1,-1):j=int(backs[i][j]);out.append(int(opts[i][j]))
    return out[::-1]

def legal_path(a,eps,delta):
    # Reserve a microscopic floating-point safety margin while preserving the public epsilon contract.
    e=eps*(1.0-2e-7);lo=np.ceil((a.astype(np.float64)-e)/delta).astype(np.int32);hi=np.floor((a.astype(np.float64)+e)/delta).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('no legal lattice state')
    seg=[];starts=[];s=0;L=int(lo[0]);H=int(hi[0])
    for t in range(1,len(a)):
        nL=max(L,int(lo[t]));nH=min(H,int(hi[t]))
        if nL<=nH:L,H=nL,nH
        else:starts.append(s);seg.append((L,H));s=t;L=int(lo[t]);H=int(hi[t])
    starts.append(s);seg.append((L,H));states=choose_states(seg);Q=np.empty(len(a),np.int32)
    for i,st in enumerate(starts):Q[st:(starts[i+1] if i+1<len(starts) else len(a))]=states[i]
    return Q,len(seg)

def encode_panel(A,eps,factor):
    delta=float(eps*factor*(1.0-3e-7));nr,nt=A.shape;Q=np.empty(A.shape,np.int32);segments=0
    for r in range(nr):Q[r],n=legal_path(A[r],eps,delta);segments+=n
    K=Q.copy();K[:,1:]-=Q[:,:-1];mask=K!=0;counts=mask.sum(axis=1).astype(np.uint64);posbytes=[];vals=[]
    for r in range(nr):
        pos=np.flatnonzero(mask[r]);g=(np.diff(np.r_[-1,pos]).astype(np.int64)-1).astype(np.uint64) if len(pos) else np.empty(0,np.uint64);posbytes.append(leb(g));vals.append(K[r,pos])
    cb=Z.compress(leb(counts));gb=Z.compress(b''.join(posbytes));vv=np.concatenate(vals) if vals else np.empty(0,np.int32);dc,vb=pack_int(vv);h=struct.pack('<dBQQQ',delta,dc,len(cb),len(gb),len(vb));blob=h+cb+gb+vb
    # Decode solely from emitted bytes and known panel shape.
    hs=struct.calcsize('<dBQQQ');dd,dc,lc,lg,lv=struct.unpack('<dBQQQ',blob[:hs]);p=hs;cr=D.decompress(blob[p:p+lc]);p+=lc;gr=D.decompress(blob[p:p+lg]);p+=lg;vbr=blob[p:p+lv];p+=lv
    if p!=len(blob):raise RuntimeError('container length')
    cc=unleb(cr,nr).astype(int);ne=int(cc.sum());gg=unleb(gr,ne).astype(np.int64);v=unpack_int(vbr,dc,ne);KK=np.zeros((nr,nt),np.int32);q=0
    for r,c in enumerate(cc):
        if c:
            po=np.cumsum(gg[q:q+c]+1)-1;KK[r,po]=v[q:q+c];q+=c
    QQ=np.cumsum(KK,axis=1,dtype=np.int32);R=QQ.astype(np.float32)*np.float32(dd)
    if not np.array_equal(QQ,Q):raise RuntimeError('state roundtrip')
    me=float(np.max(np.abs(A-R)))
    return blob,R,{'factor':factor,'delta':delta,'segments':segments,'events':ne,'event_fraction':ne/A.size,'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'dtype':dc,'bytes':len(blob),'maxerr':me}

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={};bad=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:bad.append(i);continue
        groups.setdefault((int(x),int(y)),[]).append(i)
    keys=sorted(groups);counts=np.asarray([len(groups[k]) for k in keys]);C=int(np.bincount(counts).argmax());panels=[np.stack([X[groups[k][c]] for k in keys]) for c in range(C)];extra=X[np.asarray(bad)] if bad else np.empty((0,X.shape[1]),np.float32);return X,panels,extra,{'receivers':len(keys),'components':C,'bad_traces':len(bad)}

def run(path):
    X,panels,extra,geom=load(path);eps=.1*float(X.astype(np.float64).std());raw=int(X.nbytes);rows=[]
    for f in FACTORS:
        total=32;metrics=[];me=0.
        for A in panels+[extra]:
            if not A.size:continue
            b,R,m=encode_panel(A,eps,f);total+=len(b);metrics.append(m);me=max(me,float(np.max(np.abs(A-R))))
        row={'factor':f,'bytes':total,'ratio':raw/total,'maxerr':me,'valid':bool(me<=eps*(1+2e-6)),'events':sum(m['events'] for m in metrics),'segments':sum(m['segments'] for m in metrics),'count_bytes':sum(m['count_bytes'] for m in metrics),'gap_bytes':sum(m['gap_bytes'] for m in metrics),'value_bytes':sum(m['value_bytes'] for m in metrics),'event_fraction':sum(m['events'] for m in metrics)/(X.size),'dtypes':[m['dtype'] for m in metrics]};rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda x:x['ratio'],reverse=True);out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'rows':rows};json.dump(out,open('soda_persistent_legal_state.json','w'),indent=2);print('BEST',json.dumps(rows,indent=2),flush=True)
run(sys.argv[1])
