import json,os,sys,struct
import numpy as np
import segyio,zstandard as zstd
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

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
            if j>=len(b):raise RuntimeError('truncated')
            v=b[j];j+=1;x|=(v&127)<<sh
            if v<128:break
            sh+=7
        a[i]=x;i+=1
    if j!=len(b):raise RuntimeError('trailing')
    return a

def load(path):
    with segyio.open(path,'r',ignore_geometry=True) as f:
        X=np.asarray(f.trace.raw[:],dtype=np.float32).copy();gx=np.asarray(f.attributes(segyio.TraceField.GroupX)[:],dtype=np.int64);gy=np.asarray(f.attributes(segyio.TraceField.GroupY)[:],dtype=np.int64)
    groups={};bad=[]
    for i,(x,y) in enumerate(zip(gx,gy)):
        if x==0 and y==0:bad.append(i);continue
        groups.setdefault((int(x),int(y)),[]).append(i)
    keys=sorted(groups);counts=np.asarray([len(groups[k]) for k in keys]);C=int(np.bincount(counts).argmax());panels=[]
    for c in range(C):panels.append(np.stack([X[groups[k][c]] for k in keys]))
    return X,panels,{'receivers':len(keys),'components':C,'bad_traces':len(bad)}
def events(A,eps):
    Q=np.rint(A/(2*eps)).astype(np.int32);K=Q.copy();K[:,1:]-=Q[:,:-1];return [np.flatnonzero(K[r]).astype(np.int32) for r in range(len(K))],[K[r,np.flatnonzero(K[r])].astype(np.int8) for r in range(len(K))]
def gaps(T):return (np.diff(np.r_[-1,T]).astype(np.int64)-1).astype(np.uint16) if len(T) else np.empty(0,np.uint16)

def build_sequences(E,V,scheme,component_ids):
    n=len(E);cnt=np.asarray([len(x) for x in E],np.int32);ids=list(range(n))
    if scheme.startswith('count'):ids=sorted(ids,key=lambda i:(int(cnt[i]),component_ids[i],i))
    seqg=[];seqv=[];order_events=[]
    if 'rank' in scheme:
        maxc=int(cnt.max()) if n else 0
        for r in range(maxc):
            for i in ids:
                if cnt[i]>r:
                    g=gaps(E[i]);seqg.append(int(g[r]));seqv.append(int(V[i][r]));order_events.append((i,r))
    else:
        for i in ids:
            g=gaps(E[i]);seqg.extend(map(int,g));seqv.extend(map(int,V[i]));order_events.extend((i,r) for r in range(len(E[i])))
    return cnt,np.asarray(seqg,np.uint16),np.asarray(seqv,np.int8),ids,order_events

def decode_positions(cnt,gseq,ids,scheme):
    n=len(cnt);G=[np.empty(int(c),np.uint16) for c in cnt];p=0
    if 'rank' in scheme:
        for r in range(int(cnt.max())):
            for i in ids:
                if cnt[i]>r:G[i][r]=gseq[p];p+=1
    else:
        for i in ids:
            c=int(cnt[i]);G[i][:]=gseq[p:p+c];p+=c
    if p!=len(gseq):raise RuntimeError('gap token mismatch')
    return [(np.cumsum(g.astype(np.int64)+1)-1).astype(np.int32) for g in G]

def codec(E,V,scheme,component_ids,fmt):
    cnt,g,v,ids,oe=build_sequences(E,V,scheme,component_ids);cb=Z.compress(leb(cnt.astype(np.uint64)))
    if fmt=='leb':gb=Z.compress(leb(g.astype(np.uint64)))
    else:gb=Z.compress(g.astype('<u2',copy=False).tobytes())
    vb=Z.compress(v.tobytes());head=struct.pack('<QQQ',len(cb),len(gb),len(vb));blob=head+cb+gb+vb
    # Exact decode. Scheme and fmt are fixed codec-mode metadata (charged by outer selector in final container).
    hs=struct.calcsize('<QQQ');lc,lg,lv=struct.unpack('<QQQ',blob[:hs]);p=hs;dcnt=unleb(D.decompress(blob[p:p+lc]),len(cnt)).astype(np.int32);p+=lc;rawg=D.decompress(blob[p:p+lg]);p+=lg;rawv=D.decompress(blob[p:p+lv]);p+=lv
    if p!=len(blob):raise RuntimeError('length mismatch')
    ne=int(dcnt.sum());dg=unleb(rawg,ne).astype(np.uint16) if fmt=='leb' else np.frombuffer(rawg,dtype='<u2',count=ne);dv=np.frombuffer(rawv,dtype=np.int8,count=ne)
    EE=decode_positions(dcnt,dg,ids,scheme)
    for a,b in zip(EE,E):
        if not np.array_equal(a,b):raise RuntimeError('event position roundtrip')
    if not np.array_equal(dv,v):raise RuntimeError('value stream roundtrip')
    return {'scheme':scheme,'fmt':fmt,'bytes':len(blob),'count_bytes':len(cb),'gap_bytes':len(gb),'value_bytes':len(vb),'events':ne}

def run(path):
    X,panels,geom=load(path);eps=.1*float(X.astype(np.float64).std());EA=[];VA=[];cc=[]
    for c,A in enumerate(panels):
        e,v=events(A,eps);EA.extend(e);VA.extend(v);cc.extend([c]*len(e))
    rows=[]
    for scheme in ['trace','count_trace','rank','count_rank']:
        for fmt in ['leb','u16']:rows.append(codec(EA,VA,scheme,cc,fmt))
    # Also isolate components into independent entropy streams; no side map needed.
    for scheme in ['trace','count_trace','rank','count_rank']:
      for fmt in ['leb','u16']:
        parts=[]
        for c in range(len(panels)):
            ids=[i for i,x in enumerate(cc) if x==c];E=[EA[i] for i in ids];V=[VA[i] for i in ids];parts.append(codec(E,V,scheme,[0]*len(E),fmt))
        rows.append({'scheme':'component_'+scheme,'fmt':fmt,'bytes':sum(x['bytes'] for x in parts),'count_bytes':sum(x['count_bytes'] for x in parts),'gap_bytes':sum(x['gap_bytes'] for x in parts),'value_bytes':sum(x['value_bytes'] for x in parts),'events':sum(x['events'] for x in parts)})
    rows.sort(key=lambda x:x['bytes']);out={'file':os.path.basename(path),'shape':list(X.shape),'eps':eps,'geometry':geom,'rows':rows};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_gap_order_probe.json','w'),indent=2)
run(sys.argv[1])
