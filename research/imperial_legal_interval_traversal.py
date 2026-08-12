import json, math, os, struct, sys, lzma
import h5py
import numpy as np
import zstandard as zstd
from pysz import sz, szConfig, szErrorBoundMode

TIME=1024
SPACE=128
SAFETY=1.0-1e-5
ZC=zstd.ZstdCompressor(level=19)
ZD=zstd.ZstdDecompressor()

# Directions are (dt, dc). dt>0 permits either spatial sign; dt=0 uses dc>0.
VECTORS=[
 (1,0),(2,0),(3,0),(4,0),(6,0),(8,0),(12,0),(16,0),
 (0,1),(0,2),(0,4),(0,8),(0,16),
 (1,1),(1,-1),(1,2),(1,-2),(1,4),(1,-4),(1,8),(1,-8),
 (2,1),(2,-1),(2,2),(2,-2),(2,4),(2,-4),(2,8),(2,-8),
 (3,1),(3,-1),(3,2),(3,-2),(3,4),(3,-4),
 (4,1),(4,-1),(4,2),(4,-2),(4,4),(4,-4),
 (6,1),(6,-1),(8,1),(8,-1)
]
MODS=['none','time_alt','chan_alt','checker','time_0011','time_0110']


def zc(b): return ZC.compress(b)
def zd(b): return ZD.decompress(b)

def uleb(n):
    out=bytearray(); n=int(n)
    while True:
        b=n&127; n >>= 7
        if n: out.append(b|128)
        else: out.append(b); return bytes(out)

def zzig(x):
    x=int(x); return (x<<1) ^ (x>>63)

def read_uleb(buf,p):
    v=0;sh=0
    while True:
        b=buf[p];p+=1;v|=(b&127)<<sh
        if b<128:return v,p
        sh+=7

def modulation(shape,t0,c0,name):
    nc,nt=shape
    tt=np.arange(t0,t0+nt,dtype=np.int64)[None,:]
    cc=np.arange(c0,c0+nc,dtype=np.int64)[:,None]
    if name=='none': s=np.ones((nc,nt),np.int8)
    elif name=='time_alt': s=np.where((tt&1)==0,1,-1).astype(np.int8);s=np.broadcast_to(s,(nc,nt))
    elif name=='chan_alt': s=np.where((cc&1)==0,1,-1).astype(np.int8);s=np.broadcast_to(s,(nc,nt))
    elif name=='checker': s=np.where(((tt+cc)&1)==0,1,-1).astype(np.int8)
    elif name=='time_0011': s=np.where((tt%4)<2,1,-1).astype(np.int8);s=np.broadcast_to(s,(nc,nt))
    elif name=='time_0110': s=np.where(((tt+1)%4)<2,1,-1).astype(np.int8);s=np.broadcast_to(s,(nc,nt))
    else: raise ValueError(name)
    return s

def shifted_views(A,dt,dc):
    nc,nt=A.shape
    if dt<0: raise ValueError('dt')
    if dt>=nt or abs(dc)>=nc:return None,None
    tA=slice(0,nt-dt) if dt else slice(None)
    tB=slice(dt,nt) if dt else slice(None)
    if dc>=0:
        cA=slice(0,nc-dc) if dc else slice(None); cB=slice(dc,nc) if dc else slice(None)
    else:
        d=-dc;cA=slice(d,nc);cB=slice(0,nc-d)
    return A[cA,tA],A[cB,tB]

def overlap_rate(A,eps,dt,dc):
    a,b=shifted_views(A,dt,dc)
    if a is None:return 0.0
    return float(np.mean(np.abs(a.astype(np.float64)-b.astype(np.float64)) <= 2.0*eps))

def chain_paths(nc,nt,dt,dc):
    starts=[]
    for c in range(nc):
        for t in range(nt):
            pc=c-dc;pt=t-dt
            if not (0<=pc<nc and 0<=pt<nt):starts.append((c,t))
    paths=[];seen=0
    for c0,t0 in starts:
        c,t=c0,t0;path=[]
        while 0<=c<nc and 0<=t<nt:
            path.append((c,t));seen+=1;c+=dc;t+=dt
        paths.append(path)
    if seen!=nc*nt:raise RuntimeError(('chain coverage',seen,nc*nt,dt,dc))
    return paths

def segment_path(A,path,eps):
    vals=[int(A[c,t]) for c,t in path]
    seg=[];start=0;mn=mx=vals[0]
    for i in range(1,len(vals)):
        v=vals[i];nmn=min(mn,v);nmx=max(mx,v)
        if (nmx-nmn) <= 2.0*eps:
            mn,mx=nmn,nmx
        else:
            seg.append((i-start,mx));start=i;mn=mx=v
    seg.append((len(vals)-start,mx))
    return seg

def pack_candidate(A,eps,dt,dc):
    paths=chain_paths(*A.shape,dt,dc)
    lens=[];anchors=[]
    for p in paths:
        ss=segment_path(A,p,eps)
        lens.extend([q[0] for q in ss]);anchors.extend([q[1] for q in ss])
    lb=b''.join(uleb(x) for x in lens);lcomp=zc(lb)
    ar=np.asarray(anchors,np.int32)
    raw=zc(ar.astype('<i4').tobytes())
    # Reset delta at chain boundaries would need side info; global delta is still exact and cheap.
    if ar.size:
        d=np.empty_like(ar);d[0]=ar[0];d[1:]=ar[1:]-ar[:-1]
        db=b''.join(uleb(zzig(int(x))) for x in d);dcomp=zc(db)
    else:dcomp=b''
    if len(dcomp)<len(raw):amode=1;acomp=dcomp
    else:amode=0;acomp=raw
    # Count explicit fixed header/mode/direction. epsilon and tile shape are top-level in a future container.
    total=24+len(lcomp)+len(acomp)
    return {'bytes':total,'segments':len(lens),'chains':len(paths),'length_bytes':len(lcomp),'anchor_bytes':len(acomp),'anchor_mode':amode,'lens':lens,'anchors':anchors,'paths':paths,'lblob':lcomp,'ablob':acomp}

def decode_candidate(meta,shape,eps,dt,dc):
    nc,nt=shape;paths=meta['paths'];lraw=zd(meta['lblob'])
    # Number of segments is known from decoded chain lengths: parse lengths until every chain fills.
    p=0;lens=[]
    for path in paths:
        rem=len(path)
        while rem:
            v,p=read_uleb(lraw,p);lens.append(v);rem-=v
            if rem<0:raise RuntimeError('length overflow')
    if p!=len(lraw):raise RuntimeError('length trailing')
    if meta['anchor_mode']==0:
        anchors=np.frombuffer(zd(meta['ablob']),dtype='<i4',count=len(lens)).astype(np.int64)
    else:
        db=zd(meta['ablob']);q=0;ds=[]
        for _ in lens:
            u,q=read_uleb(db,q);ds.append((u>>1)^-(u&1))
        if q!=len(db):raise RuntimeError('anchor trailing')
        anchors=np.cumsum(np.asarray(ds,np.int64))
    out=np.empty((nc,nt),np.float64);k=0
    for path in paths:
        pos=0
        while pos<len(path):
            L=lens[k];a=float(anchors[k]);y=a-eps
            for c,t in path[pos:pos+L]:out[c,t]=y
            pos+=L;k+=1
    if k!=len(lens):raise RuntimeError('segment mismatch')
    return out

def sz3_bytes(W,eps):
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
    best=None
    for X in [np.ascontiguousarray(W.astype(np.float32)),np.ascontiguousarray(W.T.astype(np.float32))]:
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape)
        me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz3 hard error',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def stats(d):
    s=ss=0.;n=0
    for t in range(0,d.shape[0],2048):
        x=np.asarray(d[t:min(t+2048,d.shape[0])],dtype=np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mu=s/n;return mu,float(np.sqrt(max(0.,ss/n-mu*mu)))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if d.shape!=(30000,6912) or str(d.dtype)!='int16':raise RuntimeError((d.shape,d.dtype))
        mu,std=stats(d);public=.1*std;eps=public*SAFETY
        tpos=[0,14488,28976];cpos=[0,3392,6784]
        tiles=[];overlap={}
        for ti,t0 in enumerate(tpos):
            for ci,c0 in enumerate(cpos):
                W=np.asarray(d[t0:t0+TIME,c0:c0+SPACE]).T.astype(np.int32)
                if W.shape!=(SPACE,TIME):raise RuntimeError(W.shape)
                sb=sz3_bytes(W,public);tile={'id':f't{ti}c{ci}','t0':t0,'c0':c0,'raw':int(W.nbytes),'sz3':sb,'W':W};tiles.append(tile)
                for mod in MODS:
                    A=W*modulation(W.shape,t0,c0,mod).astype(np.int32)
                    for dt,dc in VECTORS:
                        key=(mod,dt,dc);overlap.setdefault(key,[]).append(overlap_rate(A,eps,dt,dc))
        ranked=sorted(overlap.items(),key=lambda kv:np.mean(kv[1]),reverse=True)
        # Always include chronological control plus strongest graph candidates.
        chosen=[]
        for k in [('none',1,0),('time_alt',1,0),('none',2,0),('none',0,1)]+[q[0] for q in ranked[:16]]:
            if k not in chosen:chosen.append(k)
        rows=[]
        for key in chosen:
            mod,dt,dc=key;tot=0;szsum=0;rawsum=0;seg=0;tile_rows=[]
            for tile in tiles:
                W=tile['W'];S=modulation(W.shape,tile['t0'],tile['c0'],mod).astype(np.int32);A=W*S
                meta=pack_candidate(A,eps,dt,dc);Rz=decode_candidate(meta,A.shape,eps,dt,dc);R=Rz*S
                me=float(np.max(np.abs(W.astype(np.float64)-R)))
                if me>public*(1+5e-6):raise RuntimeError(('hard error',key,tile['id'],me,public))
                tot+=meta['bytes'];szsum+=tile['sz3'];rawsum+=tile['raw'];seg+=meta['segments']
                tile_rows.append({'id':tile['id'],'bytes':meta['bytes'],'ratio':tile['raw']/meta['bytes'],'gain_sz3':tile['sz3']/meta['bytes'],'segments_per_sample':meta['segments']/W.size,'maxerr':me})
            rows.append({'mod':mod,'dt':dt,'dc':dc,'mean_pair_overlap':float(np.mean(overlap.get(key,[0]))),'bytes':tot,'raw_bytes':rawsum,'sz3_bytes':szsum,'ratio':rawsum/tot,'gain_vs_sz3':szsum/tot,'segments_per_sample':seg/(len(tiles)*SPACE*TIME),'tiles':tile_rows})
        rows.sort(key=lambda r:r['bytes'])
        # Per-tile oracle over the exact evaluated dictionary; this is a headroom screen, not a codec claim.
        oracle=0
        for i,tile in enumerate(tiles):oracle+=min(r['tiles'][i]['bytes'] for r in rows)
        rawsum=sum(t['raw'] for t in tiles);szsum=sum(t['sz3'] for t in tiles)
        out={'dataset':'Imperial Valley continuous DAS','file':os.path.basename(path),'shape':list(d.shape),'dtype':str(d.dtype),'mean':mu,'std':std,'public_eps':public,'internal_eps':eps,'screen_tiles':[{'id':t['id'],'t0':t['t0'],'c0':t['c0'],'raw':t['raw'],'sz3':t['sz3']} for t in tiles], 'top_overlap':[{'mod':k[0],'dt':k[1],'dc':k[2],'mean_overlap':float(np.mean(v)),'min_overlap':float(np.min(v)),'max_overlap':float(np.max(v))} for k,v in ranked[:30]],'evaluated':rows,'best_global':rows[0],'oracle_per_tile_bytes':oracle,'oracle_ratio':rawsum/oracle,'oracle_gain_vs_sz3':szsum/oracle,'scope':'9-tile feasibility screen; legal interval plateau chains, fully decoded; selected dictionary is exploratory, not a whole-file compression claim'}
        print(json.dumps({'std':std,'eps':public,'best_global':{k:rows[0][k] for k in ['mod','dt','dc','mean_pair_overlap','bytes','ratio','gain_vs_sz3','segments_per_sample']},'oracle_ratio':out['oracle_ratio'],'oracle_gain_vs_sz3':out['oracle_gain_vs_sz3'],'top_overlap':out['top_overlap'][:10]},indent=2),flush=True)
        json.dump(out,open('imperial_legal_interval_traversal.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
