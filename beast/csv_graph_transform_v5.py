#!/usr/bin/env python3
import re,datetime,collections,zlib
from axiom3_common import vi,uv,enc_svar,dec_svar
MAGIC=b'CSV5'
DATE=re.compile(rb'\d{4}-\d{2}-\d{2}$')
INT=re.compile(rb'-?(?:0|[1-9]\d*)$')

def split_line(line,delim=44):
    fs=[];start=0;i=0;inq=False
    while i<len(line):
        c=line[i]
        if c==34:
            if inq and i+1<len(line) and line[i+1]==34:i+=2;continue
            inq=not inq;i+=1;continue
        if c==delim and not inq:fs.append(line[start:i]);start=i+1
        i+=1
    if inq:return None
    fs.append(line[start:]);return fs

def _pack_raw(vals):return b'R'+b''.join(vi(len(x))+x for x in vals)
def _unpack_raw(rep,n):
    p=1;out=[]
    for _ in range(n):l,p=uv(rep,p);out.append(rep[p:p+l]);p+=l
    if p!=len(rep):raise ValueError('raw trailing')
    return out

def _pack_dict(vals):
    c=collections.Counter(vals);ds=[x for x,_ in sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))];mp={x:i for i,x in enumerate(ds)}
    return b'D'+vi(len(ds))+b''.join(vi(len(x))+x for x in ds)+b''.join(vi(mp[x]) for x in vals)
def _unpack_dict(rep,n):
    p=1;k,p=uv(rep,p);ds=[]
    for _ in range(k):l,p=uv(rep,p);ds.append(rep[p:p+l]);p+=l
    out=[]
    for _ in range(n):i,p=uv(rep,p);out.append(ds[i])
    if p!=len(rep):raise ValueError('dict trailing')
    return out

def _pack_int(vals):
    parsed=[];bits=bytearray((len(vals)+7)//8)
    for i,v in enumerate(vals):
        if v==b'':parsed.append(None);continue
        if not INT.fullmatch(v):return None
        q=int(v)
        if str(q).encode()!=v:return None
        bits[i>>3]|=1<<(i&7);parsed.append(q)
    a=bytearray();d=bytearray();prev=0
    for q in parsed:
        if q is None:continue
        a+=enc_svar(q);d+=enc_svar(q-prev);prev=q
    mode=0 if len(zlib.compress(a,6))<=len(zlib.compress(d,6)) else 1
    return b'I'+bytes([mode])+vi(len(bits))+bits+(a if mode==0 else d)
def _unpack_int(rep,n):
    p=1;mode=rep[p];p+=1;bl,p=uv(rep,p);bits=rep[p:p+bl];p+=bl;out=[];prev=0
    for i in range(n):
        if not ((bits[i>>3]>>(i&7))&1):out.append(b'');continue
        q,p=dec_svar(rep,p)
        if mode:q=prev+q;prev=q
        out.append(str(q).encode())
    if p!=len(rep):raise ValueError('int trailing')
    return out

def _day(v):
    try:
        if not DATE.fullmatch(v):return None
        y,m,d=map(int,v.split(b'-'));dt=datetime.date(y,m,d)
        if dt.isoformat().encode()!=v:return None
        return dt.toordinal()
    except:return None
def _pack_date(vals):
    days=[_day(v) for v in vals]
    if any(x is None for x in days):return None
    o=bytearray(b'T');prev=0
    for x in days:o+=enc_svar(x-prev);prev=x
    return bytes(o)
def _unpack_date(rep,n):
    p=1;prev=0;out=[]
    for _ in range(n):d,p=dec_svar(rep,p);x=prev+d;prev=x;out.append(datetime.date.fromordinal(x).isoformat().encode())
    if p!=len(rep):raise ValueError('date trailing')
    return out

def _pack_group_int(vals,cols,keyids):
    bits=bytearray((len(vals)+7)//8);state={};stream=bytearray()
    for i,v in enumerate(vals):
        if v==b'':continue
        if not INT.fullmatch(v):return None
        q=int(v)
        if str(q).encode()!=v:return None
        bits[i>>3]|=1<<(i&7);key=tuple(cols[k][i] for k in keyids);prev=state.get(key,0);stream+=enc_svar(q-prev);state[key]=q
    return b'G'+vi(len(keyids))+b''.join(vi(k) for k in keyids)+vi(len(bits))+bits+stream
def _unpack_group_int(rep,n,cols):
    p=1;nk,p=uv(rep,p);kids=[]
    for _ in range(nk):k,p=uv(rep,p);kids.append(k)
    bl,p=uv(rep,p);bits=rep[p:p+bl];p+=bl;state={};out=[]
    for i in range(n):
        if not ((bits[i>>3]>>(i&7))&1):out.append(b'');continue
        d,p=dec_svar(rep,p);key=tuple(cols[k][i] for k in kids);q=state.get(key,0)+d;state[key]=q;out.append(str(q).encode())
    if p!=len(rep):raise ValueError('group trailing')
    return out

def _pack_group_int_clustered(vals,cols,keyids):
    # Serialize a keyed residual process in its own causal coordinate system.
    # No row permutation is stored: decoded key columns regenerate it exactly.
    groups={};order=[]
    for i,v in enumerate(vals):
        key=tuple(cols[k][i] for k in keyids)
        if key not in groups:groups[key]=[];order.append(key)
        groups[key].append(v)
    bits=bytearray((len(vals)+7)//8);stream=bytearray();qpos=0
    for key in order:
        prev=0
        for v in groups[key]:
            if v==b'':qpos+=1;continue
            if not INT.fullmatch(v):return None
            q=int(v)
            if str(q).encode()!=v:return None
            bits[qpos>>3]|=1<<(qpos&7);qpos+=1;stream+=enc_svar(q-prev);prev=q
    return b'H'+vi(len(keyids))+b''.join(vi(k) for k in keyids)+vi(len(bits))+bits+stream
def _unpack_group_int_clustered(rep,n,cols):
    p=1;nk,p=uv(rep,p);kids=[]
    for _ in range(nk):k,p=uv(rep,p);kids.append(k)
    bl,p=uv(rep,p);bits=rep[p:p+bl];p+=bl;groups={};order=[]
    for i in range(n):
        key=tuple(cols[k][i] for k in kids)
        if key not in groups:groups[key]=[];order.append(key)
        groups[key].append(i)
    out=[None]*n;qpos=0
    for key in order:
        prev=0
        for i in groups[key]:
            if not ((bits[qpos>>3]>>(qpos&7))&1):out[i]=b'';qpos+=1;continue
            qpos+=1;d,p=dec_svar(rep,p);q=prev+d;prev=q;out[i]=str(q).encode()
    if p!=len(rep) or any(x is None for x in out):raise ValueError('cluster trailing')
    return out

def _pack_fd(vals,cols,keyids):
    mp={};order=[]
    for i,v in enumerate(vals):
        key=tuple(cols[k][i] for k in keyids)
        if key in mp:
            if mp[key]!=v:return None
        else:mp[key]=v;order.append(key)
    if len(order)>len(vals)*0.80:return None
    o=bytearray(b'F')+vi(len(keyids))+b''.join(vi(k) for k in keyids)+vi(len(order))
    for k in order:v=mp[k];o+=vi(len(v))+v
    return bytes(o)
def _unpack_fd(rep,n,cols):
    p=1;nk,p=uv(rep,p);kids=[]
    for _ in range(nk):k,p=uv(rep,p);kids.append(k)
    m,p=uv(rep,p);keys=[];seen=set()
    for i in range(n):
        key=tuple(cols[k][i] for k in kids)
        if key not in seen:seen.add(key);keys.append(key)
    if len(keys)!=m:raise ValueError('fd unique count')
    mp={}
    for key in keys:l,p=uv(rep,p);mp[key]=rep[p:p+l];p+=l
    if p!=len(rep):raise ValueError('fd trailing')
    return [mp[tuple(cols[k][i] for k in kids)] for i in range(n)]

def _keysets(j):
    out=[(k,) for k in range(j)]
    for a in range(j):
        for b in range(a+1,j):out.append((a,b))
    return out
def _choose(vals):
    cand=[_pack_raw(vals),_pack_dict(vals)];a=_pack_int(vals);b=_pack_date(vals)
    if a:cand.append(a)
    if b:cand.append(b)
    return min(cand,key=lambda x:len(zlib.compress(x,6)))

def pack(data):
    rawlines=data.splitlines(keepends=True)
    if len(rawlines)<8:return None
    rows=[];ends=[]
    for x in rawlines:
        if x.endswith(b'\r\n'):line=x[:-2];e=2
        elif x.endswith(b'\n'):line=x[:-1];e=1
        elif x.endswith(b'\r'):line=x[:-1];e=3
        else:line=x;e=0
        f=split_line(line)
        if f is None:return None
        rows.append(f);ends.append(e)
    nc=len(rows[0])
    if nc<2 or any(len(r)!=nc for r in rows):return None
    header=rows[0];body=rows[1:];nr=len(body);cols=[[r[j] for r in body] for j in range(nc)];reps=[]
    for j,c in enumerate(cols):
        cand=[_choose(c)]
        for ks in _keysets(j):
            for fn in (_pack_fd,_pack_group_int,_pack_group_int_clustered):
                q=fn(c,cols,ks)
                if q:cand.append(q)
        reps.append(min(cand,key=lambda x:len(zlib.compress(x,6))))
    o=bytearray(MAGIC)+vi(nc)+vi(nr)+b''.join(vi(len(x))+x for x in header)+vi(len(ends))+bytes(ends)
    for r in reps:o+=vi(len(r))+r
    return bytes(o)

def unpack(rep):
    if rep[:4]!=MAGIC:raise ValueError('csv magic')
    p=4;nc,p=uv(rep,p);nr,p=uv(rep,p);header=[]
    for _ in range(nc):l,p=uv(rep,p);header.append(rep[p:p+l]);p+=l
    ne,p=uv(rep,p);ends=list(rep[p:p+ne]);p+=ne;cols=[]
    for _ in range(nc):
        l,p=uv(rep,p);r=rep[p:p+l];p+=l;t=r[:1]
        if t==b'R':vals=_unpack_raw(r,nr)
        elif t==b'D':vals=_unpack_dict(r,nr)
        elif t==b'I':vals=_unpack_int(r,nr)
        elif t==b'T':vals=_unpack_date(r,nr)
        elif t==b'G':vals=_unpack_group_int(r,nr,cols)
        elif t==b'H':vals=_unpack_group_int_clustered(r,nr,cols)
        elif t==b'F':vals=_unpack_fd(r,nr,cols)
        else:raise ValueError('col mode')
        cols.append(vals)
    if p!=len(rep) or len(ends)!=nr+1:raise ValueError('csv trailing/count')
    em={0:b'',1:b'\n',2:b'\r\n',3:b'\r'};out=bytearray(b','.join(header)+em[ends[0]])
    for i in range(nr):out+=b','.join(cols[j][i] for j in range(nc))+em[ends[i+1]]
    return bytes(out)
