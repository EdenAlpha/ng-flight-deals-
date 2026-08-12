import json, os, struct, sys
from collections import defaultdict
import numpy as np
import segyio, zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()
DT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
MAG=b'GLATv001'
MAIN_HDR='<8sBBBBIIIIH'; MH=struct.calcsize(MAIN_HDR)
OUT_HDR='<8sBBBBIIH'; OH=struct.calcsize(OUT_HDR)
TOP_HDR='<8sdQQ'; TH=struct.calcsize(TOP_HDR)

def dtype_code(A):
    lo=int(A.min()) if A.size else 0; hi=int(A.max()) if A.size else 0
    return 1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3

def delta(A,axis):
    B=A.copy(); sl=[slice(None)]*A.ndim; prv=[slice(None)]*A.ndim
    sl[axis]=slice(1,None); prv[axis]=slice(None,-1)
    B[tuple(sl)]=A[tuple(sl)]-A[tuple(prv)]
    return B

def undelta(A,axis): return np.cumsum(A,axis=axis,dtype=np.int32)

def transform(G,mask):
    A=G
    if mask&1:A=delta(A,3) # time
    if mask&2:A=delta(A,2) # station
    if mask&4:A=delta(A,1) # line
    return A

def inverse_transform(A,mask):
    G=A
    if mask&4:G=undelta(G,1)
    if mask&2:G=undelta(G,2)
    if mask&1:G=undelta(G,3)
    return G

def group_views(A,group):
    if group==0:return [A]
    if group==1:return [A[c] for c in range(A.shape[0])]
    if group==2:return [A[c,l] for c in range(A.shape[0]) for l in range(A.shape[1])]
    raise ValueError(group)

def encode_main(G,mask,group):
    A=transform(G,mask); dc=dtype_code(A); frames=[ZC.compress(np.ascontiguousarray(v.astype(DT[dc],copy=False)).tobytes()) for v in group_views(A,group)]
    h=struct.pack(MAIN_HDR,MAG,1,mask,group,dc,*G.shape,len(frames)); lens=b''.join(struct.pack('<Q',len(b)) for b in frames)
    return h+lens+b''.join(frames)

def decode_main(blob):
    magic,ver,mask,group,dc,C,L,S,T,nf=struct.unpack(MAIN_HDR,blob[:MH]);
    if magic!=MAG or ver!=1:raise RuntimeError('bad main header')
    p=MH;lens=[]
    for _ in range(nf):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    frames=[]
    for n in lens:frames.append(blob[p:p+n]);p+=n
    if p!=len(blob):raise RuntimeError('main length')
    A=np.empty((C,L,S,T),np.int32)
    if group==0:
        raw=ZD.decompress(frames[0]); q=np.frombuffer(raw,dtype=DT[dc],count=C*L*S*T).astype(np.int32);A[:]=q.reshape(C,L,S,T)
    elif group==1:
        if nf!=C:raise RuntimeError('nf comp')
        for c,b in enumerate(frames):A[c]=np.frombuffer(ZD.decompress(b),dtype=DT[dc],count=L*S*T).astype(np.int32).reshape(L,S,T)
    elif group==2:
        if nf!=C*L:raise RuntimeError('nf line')
        k=0
        for c in range(C):
            for l in range(L):A[c,l]=np.frombuffer(ZD.decompress(frames[k]),dtype=DT[dc],count=S*T).astype(np.int32).reshape(S,T);k+=1
    else:raise RuntimeError('group')
    return inverse_transform(A,mask)

def encode_out(Q,tdiff,group):
    A=delta(Q,1) if tdiff else Q;dc=dtype_code(A)
    views=[A] if group==0 else [A[i] for i in range(A.shape[0])]
    frames=[ZC.compress(np.ascontiguousarray(v.astype(DT[dc],copy=False)).tobytes()) for v in views]
    h=struct.pack(OUT_HDR,MAG,1,int(tdiff),group,dc,*Q.shape,len(frames));lens=b''.join(struct.pack('<Q',len(b)) for b in frames)
    return h+lens+b''.join(frames)

def decode_out(blob):
    magic,ver,tdiff,group,dc,N,T,nf=struct.unpack(OUT_HDR,blob[:OH]);
    if magic!=MAG or ver!=1:raise RuntimeError('bad out header')
    p=OH;lens=[]
    for _ in range(nf):lens.append(struct.unpack('<Q',blob[p:p+8])[0]);p+=8
    fs=[]
    for n in lens:fs.append(blob[p:p+n]);p+=n
    A=np.empty((N,T),np.int32)
    if group==0:A[:]=np.frombuffer(ZD.decompress(fs[0]),dtype=DT[dc],count=N*T).astype(np.int32).reshape(N,T)
    else:
        for i,b in enumerate(fs):A[i]=np.frombuffer(ZD.decompress(b),dtype=DT[dc],count=T).astype(np.int32)
    return undelta(A,1) if tdiff else A

def make_top(eps,mb,ob): return struct.pack(TOP_HDR,MAG,float(eps),len(mb),len(ob))+mb+ob

def decode_top(blob):
    magic,eps,lm,lo=struct.unpack(TOP_HDR,blob[:TH]);
    if magic!=MAG:raise RuntimeError('top magic')
    p=TH;mb=blob[p:p+lm];p+=lm;ob=blob[p:p+lo];p+=lo
    if p!=len(blob):raise RuntimeError('top length')
    return float(eps),decode_main(mb),decode_out(ob)

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],np.int64);dt=int(segyio.tools.dt(f))
    return X,gx,gy,dt

def geometry_map(X,gx,gy):
    coord=defaultdict(list)
    for i,k in enumerate(zip(gx.tolist(),gy.tolist())):coord[k].append(i)
    keys=list(coord.keys());pts=np.asarray(keys,float);N=len(pts)
    d=pts[:,None,:]-pts[None,:,:];ds=np.sum(d*d,2);ds[ds==0]=np.inf;jj=np.argmin(ds,1);v=pts[jj]-pts;v=np.where(((v[:,0]<0)|((v[:,0]==0)&(v[:,1]<0)))[:,None],-v,v);lens=np.linalg.norm(v,axis=1);sp=float(np.median(lens));vv=v[(lens>.5*sp)&(lens<1.5*sp)];u=np.median(vv,0);u=u/np.linalg.norm(u);perp=np.array([-u[1],u[0]]);a=pts@u;b=pts@perp
    order=np.argsort(b);cuts=np.where(np.diff(b[order])>.2*sp)[0]+1;groups=np.split(order,cuts);main=[g for g in groups if len(g)>=10];main=sorted(main,key=lambda g:float(np.mean(b[g])));main_idx=np.concatenate(main);amin=float(a[main_idx].min())
    # infer common station spacing + phase exactly as diagnostic
    best=None
    for scale in np.linspace(.995,1.005,101):
        s=sp*scale;mods=np.mod(a[main_idx]-amin,s)
        for phase in np.quantile(mods,[0,.1,.25,.5,.75,.9]):
            qi=np.rint((a[main_idx]-amin-phase)/s).astype(int);pred=amin+phase+qi*s;res=np.abs(a[main_idx]-pred);span=int(qi.max()-qi.min()+1);occ=len(main_idx)/(len(main)*span);score=float(np.median(res)+np.quantile(res,.95)+s*(1-occ)*.05)
            if best is None or score<best[0]:best=(score,s,float(phase),int(qi.min()),int(qi.max()))
    _,s,phase,jmin,jmax=best;S=jmax-jmin+1;T=X.shape[1];C=3;L=len(main);G=np.zeros((C,L,S,T),np.int32);trace_map=[];used=set();site_count=0
    for li,g in enumerate(main):
        for q in g.tolist():
            ids=coord[keys[q]]
            if len(ids)!=3:continue
            st=int(round((a[q]-amin-phase)/s))-jmin
            if not (0<=st<S):raise RuntimeError('station range')
            for c,tid in enumerate(ids):trace_map.append((tid,c,li,st));used.add(tid)
            site_count+=1
    outids=np.asarray([i for i in range(X.shape[0]) if i not in used],np.int64)
    return G,trace_map,outids,{'unique_sites':N,'line_count':L,'station_count':S,'main_sites':site_count,'grid_occupancy':site_count/(L*S),'outlier_traces':int(outids.size),'along_spacing':s,'along_axis':u.tolist()}

def sz3_bytes(X,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps);b,_=sz.compress(np.ascontiguousarray(X),cfg);R,_=sz.decompress(b,np.float32,X.shape);return int(b.size),float(np.max(np.abs(X-R)))

def main(path):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes
    G,tm,outids,geom=geometry_map(X,gx,gy)
    # populate legal reconstruction lattice. Geometry/mask is side information retained with SEG-Y for every compressor.
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32)
    main_rows=[]
    names={0:'none',1:'t',2:'s',3:'ts',4:'l',5:'tl',6:'sl',7:'tsl'};groups={0:'all',1:'component',2:'component_line'}
    for mask in range(8):
        for group in range(3):
            b=encode_main(G,mask,group);R=decode_main(b)
            if not np.array_equal(R,G):raise RuntimeError('main integer decode mismatch')
            main_rows.append({'mask':mask,'transform':names[mask],'group':groups[group],'bytes':len(b)})
    out_rows=[]
    for td in [0,1]:
        for group in [0,1]:
            b=encode_out(O,td,group);R=decode_out(b)
            if not np.array_equal(R,O):raise RuntimeError('out integer decode mismatch')
            out_rows.append({'tdiff':bool(td),'group':'all' if group==0 else 'per_trace','bytes':len(b)})
    main_rows.sort(key=lambda r:r['bytes']);out_rows.sort(key=lambda r:r['bytes']);bm=encode_main(G,main_rows[0]['mask'],list(groups.values()).index(main_rows[0]['group']));bo=encode_out(O,int(out_rows[0]['tdiff']),0 if out_rows[0]['group']=='all' else 1);blob=make_top(eps,bm,bo);ee,RG,RO=decode_top(blob)
    recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
    recon[outids]=RO.astype(np.float32)*np.float32(2*ee)
    me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'dt_us':dt,'raw_bytes':raw,'std':std,'eps':eps,'geometry':geom,'best_main':main_rows[:12],'best_outlier':out_rows,'container_bytes':len(blob),'ratio':raw/len(blob),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':szb,'ratio':raw/szb,'maxerr':sze}}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_grid_lattice.json','w'),indent=2)
main(sys.argv[1])
