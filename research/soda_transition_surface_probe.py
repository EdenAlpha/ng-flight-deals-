import json,os,struct,sys
import numpy as np
import zstandard as zstd

# Reuse only the deterministic SEG-Y/lattice loader from the audited lattice codec.
src=open('research/soda_lattice_kxyf.py').read().split('\ndef fwd(W)')[0]
exec(compile(src,'soda_lattice_kxyf.py','exec'),globals())
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def leb(u):
    out=bytearray()
    for x in np.asarray(u,dtype=np.uint64).ravel():
        x=int(x)
        while x>=128:out.append((x&127)|128);x>>=7
        out.append(x)
    return bytes(out)
def unleb(b,n):
    out=np.empty(n,np.uint64);i=j=0
    while i<n:
        x=sh=0
        while True:
            if j>=len(b):raise RuntimeError('varint truncation')
            v=b[j];j+=1;x|=(v&127)<<sh
            if v<128:break
            sh+=7
        out[i]=x;i+=1
    if j!=len(b):raise RuntimeError('varint trailing')
    return out
def zz(x):
    x=np.asarray(x,dtype=np.int64);return ((x<<1)^(x>>63)).astype(np.uint64)
def unzz(u):
    u=np.asarray(u,dtype=np.uint64);return ((u>>1).astype(np.int64)^-((u&1).astype(np.int64)))

def event_lists(K,present):
    C,ny,nx,nt=K.shape;out={}
    for c in range(C):
      for y in range(ny):
       for x in range(nx):
        if present[c,y,x]:out[(c,y,x)]=np.flatnonzero(K[c,y,x]).astype(np.int32)
    return out

def parent_for(key,decoded,counts,scheme):
    c,y,x=key;cand=[]
    for q in [(c,y,x-1),(c,y-1,x),(c,y-1,x-1),(c,y-1,x+1)]:
        if q in decoded and counts.get(q,0)>0:cand.append(q)
    if not cand:return None
    if scheme=='leftup':return cand[0]
    # Decoder knows current target count from the transmitted count table, so choosing
    # the already-decoded parent with closest event count costs no side information.
    return min(cand,key=lambda q:(abs(counts[q]-counts[key]),q))

def pred_rank(P,n,i):
    if len(P)==0:return 0
    if n<=1:return int(P[len(P)//2])
    j=int(round(i*(len(P)-1)/(n-1)));return int(P[j])

def timing_codec(events,present,scheme='gaps',delta_resid=False):
    keys=sorted(events);counts={k:len(events[k]) for k in keys};count_raw=leb([counts[k] for k in keys]);tokens=[];decoded={}
    for k in keys:
        T=events[k];n=len(T);Pkey=None if scheme=='gaps' else parent_for(k,decoded,counts,scheme)
        if Pkey is None:
            gaps=np.diff(np.r_[-1,T]).astype(np.int64)-1 if n else np.empty(0,np.int64);tokens.extend(gaps.astype(np.uint64).tolist())
        else:
            P=decoded[Pkey];r=np.asarray([int(T[i])-pred_rank(P,n,i) for i in range(n)],np.int64)
            if delta_resid and n:r=np.r_[r[0],np.diff(r)]
            tokens.extend(zz(r).tolist())
        decoded[k]=T.copy()
    cb=Z.compress(count_raw);tb=Z.compress(leb(tokens));header=struct.pack('<QQ',len(cb),len(tb));blob=header+cb+tb
    # Decode using only bytes + retained topology/present mask.
    hs=struct.calcsize('<QQ');lc,lt=struct.unpack('<QQ',blob[:hs]);cr=D.decompress(blob[hs:hs+lc]);tr=D.decompress(blob[hs+lc:hs+lc+lt]);cnt=unleb(cr,len(keys)).astype(int);counts2={k:int(v) for k,v in zip(keys,cnt)};ntok=int(cnt.sum());tok=unleb(tr,ntok);p=0;dec={}
    for k in keys:
        n=counts2[k];u=tok[p:p+n];p+=n;Pkey=None if scheme=='gaps' else parent_for(k,dec,counts2,scheme)
        if Pkey is None:
            T=(np.cumsum(u.astype(np.int64)+1)-1).astype(np.int32)
        else:
            r=unzz(u)
            if delta_resid and n:r=np.cumsum(r)
            P=dec[Pkey];T=np.asarray([pred_rank(P,n,i)+int(r[i]) for i in range(n)],np.int32)
        dec[k]=T
    if p!=len(tok):raise RuntimeError('timing token mismatch')
    for k in keys:
        if not np.array_equal(dec[k],events[k]):raise RuntimeError('timing roundtrip failure')
    return blob,{'scheme':scheme,'delta_resid':delta_resid,'count_bytes':len(cb),'timing_bytes':len(tb),'bytes':len(blob),'events':ntok}

def value_codec(K,events):
    keys=sorted(events);vals=[];trace_starts=[]
    for k in keys:
        trace_starts.append(len(vals));T=events[k];vals.extend(K[k][T].tolist())
    v=np.asarray(vals,np.int32);# baseline int8/int16 zstd
    lo=int(v.min()) if len(v) else 0;hi=int(v.max()) if len(v) else 0;dt=np.int8 if lo>=-128 and hi<=127 else np.int16
    base=Z.compress(v.astype(dt).tobytes())
    # Exact sign + magnitude exceptions. Every nonzero transition has magnitude>=1.
    neg=v<0;mag=np.abs(v);exc=mag!=1;sign=Z.compress(np.packbits(neg,bitorder='little').tobytes());em=Z.compress(np.packbits(exc,bitorder='little').tobytes());extras=(mag[exc]-2).astype(np.uint64);exb=Z.compress(leb(extras));plain=struct.pack('<QQQ',len(sign),len(em),len(exb))+sign+em+exb
    # Alternating-sign residual per trace: predicted sign is opposite previous event;
    # first event predicts positive. Store only disagreement bit.
    res=np.zeros(len(v),bool);off=0
    for k in keys:
        n=len(events[k]);prev=False
        for i in range(n):
            actual=bool(neg[off+i]);pred=False if i==0 else (not bool(neg[off+i-1]));res[off+i]=(actual!=pred)
        off+=n
    rb=Z.compress(np.packbits(res,bitorder='little').tobytes());alt=struct.pack('<QQQ',len(rb),len(em),len(exb))+rb+em+exb
    # Decode both novel candidates to verify values exactly.
    def decode_bits(blob,alternating):
        h=struct.calcsize('<QQQ');ls,lm,le=struct.unpack('<QQQ',blob[:h]);p=h;sb=blob[p:p+ls];p+=ls;mb=blob[p:p+lm];p+=lm;eb=blob[p:p+le];p+=le
        bits=np.unpackbits(np.frombuffer(D.decompress(sb),np.uint8),bitorder='little',count=len(v)).astype(bool);ee=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little',count=len(v)).astype(bool);ex=unleb(D.decompress(eb),int(ee.sum())).astype(np.int64)+2;mm=np.ones(len(v),np.int64);mm[ee]=ex
        if alternating:
            nn=np.zeros(len(v),bool);off=0
            for k in keys:
                n=len(events[k])
                for i in range(n):
                    pred=False if i==0 else (not nn[off+i-1]);nn[off+i]=pred^bits[off+i]
                off+=n
        else:nn=bits
        return np.where(nn,-mm,mm).astype(np.int32)
    if not np.array_equal(decode_bits(plain,False),v):raise RuntimeError('plain value roundtrip')
    if not np.array_equal(decode_bits(alt,True),v):raise RuntimeError('alt value roundtrip')
    opts=[('zstd_int',len(base)),('sign_mag',len(plain)),('alternating_sign_mag',len(alt))];opts.sort(key=lambda x:x[1]);return {'best':opts[0],'all':opts,'n_values':len(v),'nonunit_fraction':float(exc.mean()) if len(v) else 0.0,'negative_fraction':float(neg.mean()) if len(v) else 0.0,'alt_disagree_fraction':float(res.mean()) if len(v) else 0.0}

def run(path):
    X,V,Vf,present,tmap,extra,dt,geom=load(path);eps=.1*float(X.astype(np.float64).std());Q=np.zeros(V.shape,np.int32);Q[present]=np.rint(V[present]/(2*eps)).astype(np.int32);K=Q.copy();K[:,:,:,1:]-=Q[:,:,:,:-1];events=event_lists(K,present)
    timings=[]
    for scheme in ['gaps','leftup','closest_count']:
        for dr in ([False] if scheme=='gaps' else [False,True]):timings.append(timing_codec(events,present,scheme,dr)[1])
    timings.sort(key=lambda x:x['bytes']);vc=value_codec(K,events);out={'file':os.path.basename(path),'shape':list(X.shape),'eps':eps,'geometry':geom,'event_count':sum(len(v) for v in events.values()),'traces':len(events),'events_per_trace_mean':float(np.mean([len(v) for v in events.values()])),'timing':timings,'values':vc};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_transition_surface_probe.json','w'),indent=2)
run(sys.argv[1])
