#!/usr/bin/env python3
import datetime,zlib
MAGIC=b'PNL1'

def vi(n):
    if n<0: raise ValueError('negative varint')
    o=bytearray()
    while True:
        b=n&127;n>>=7
        if n:o.append(b|128)
        else:o.append(b);return bytes(o)
def uv(b,p):
    n=0;s=0
    while True:
        if p>=len(b):raise ValueError('truncated varint')
        x=b[p];p+=1;n|=(x&127)<<s
        if not x&128:return n,p
        s+=7
def sv(n):return vi((n<<1)^(n>>63))
def us(b,p):
    x,p=uv(b,p);return (x>>1)^-(x&1),p

def _s(o,x):o+=vi(len(x))+x
def _rs(b,p):
    n,p=uv(b,p);return b[p:p+n],p+n

def _date(x):
    try:
        s=x.decode('ascii');d=datetime.date.fromisoformat(s)
        return d.toordinal() if d.isoformat()==s else None
    except:return None

def _dense(seqs):
    o=bytearray()
    for a in seqs:
        prev=0
        for x in a:o+=sv(x-prev);prev=x
    return bytes(o)
def _sparse(seqs):
    o=bytearray()
    for a in seqs:
        prev=0;last=-1;ev=[]
        for i,x in enumerate(a):
            d=x-prev;prev=x
            if d:ev.append((i-last-1,d));last=i
        o+=vi(len(ev))
        for gap,d in ev:o+=vi(gap)+sv(d)
    return bytes(o)
def _undense(b,p,lens):
    out=[]
    for n in lens:
        a=[];prev=0
        for _ in range(n):d,p=us(b,p);prev+=d;a.append(prev)
        out.append(a)
    return out,p
def _unsparse(b,p,lens):
    out=[]
    for n in lens:
        m,p=uv(b,p);deltas=[0]*n;pos=-1
        for _ in range(m):gap,p=uv(b,p);d,p=us(b,p);pos+=gap+1
        
            # assigned below after bounds check
        out.append((deltas,m))
    raise AssertionError('unreachable')

def pack(data):
    # Purposefully narrow/fail-closed first law: exact NYT-style six-column panel data.
    lines=data.splitlines(keepends=True)
    if len(lines)<16:return None
    ends=[];rows=[]
    for x in lines:
        if x.endswith(b'\r\n'):e=b'\r\n';q=x[:-2]
        elif x.endswith(b'\n'):e=b'\n';q=x[:-1]
        elif x.endswith(b'\r'):e=b'\r';q=x[:-1]
        else:e=b'';q=x
        ends.append(e);f=q.split(b',')
        if len(f)!=6:return None
        rows.append(f)
    if rows[0]!=[b'date',b'county',b'state',b'fips',b'cases',b'deaths']:return None
    if any(e!=ends[0] for e in ends[:-1]):return None
    if ends[-1] not in (ends[0],b''):return None
    nl=ends[0];last_nl=1 if ends[-1]==nl else 0
    body=rows[1:];dates=[];groups=[];cur=None
    for r in body:
        d=_date(r[0])
        if d is None:return None
        if cur!=d:dates.append(d);groups.append([]);cur=d
        groups[-1].append(r)
    if any(dates[i]<=dates[i-1] for i in range(1,len(dates))):return None
    # Entity identity is a stable fact. Store each identity once, in canonical row-order key order.
    et=set((r[2],r[1],r[3]) for r in body)
    ents=sorted(et);eid={e:i for i,e in enumerate(ents)}
    # This law applies only when each day's rows are already in that canonical order.
    dayids=[]
    for g in groups:
        ids=[eid[(r[2],r[1],r[3])] for r in g]
        if ids!=sorted(ids) or len(ids)!=len(set(ids)):return None
        dayids.append(ids)
    states=sorted(set(e[0] for e in ents));counties=sorted(set(e[1] for e in ents));sm={x:i for i,x in enumerate(states)};cm={x:i for i,x in enumerate(counties)}
    # Presence is a slowly-changing set: encode only toggles from the previous day.
    pres=bytearray();active=set()
    occurrences=[0]*len(ents)
    for ids in dayids:
        now=set(ids);tog=sorted(active^now);pres+=vi(len(tog));prev=-1
        for x in tog:pres+=vi(x-prev-1);prev=x
        active=now
        for x in ids:occurrences[x]+=1
    # Entity-major measurement histories.
    vals=[[[] for _ in ents] for _ in range(2)]
    for g in groups:
        for r in g:
            i=eid[(r[2],r[1],r[3])]
            try:a=int(r[4]);b=int(r[5])
            except:return None
            if str(a).encode()!=r[4] or str(b).encode()!=r[5]:return None
            vals[0][i].append(a);vals[1][i].append(b)
    if any(len(vals[0][i])!=occurrences[i] or len(vals[1][i])!=occurrences[i] for i in range(len(ents))):return None
    bands=[]
    for m in range(2):
        dense=_dense(vals[m]);sparse=_sparse(vals[m])
        # representation choice is local MDL proxy; final outer compressor still decides actual cost.
        if len(zlib.compress(sparse,6))<len(zlib.compress(dense,6)):bands.append((1,sparse))
        else:bands.append((0,dense))
    o=bytearray(MAGIC);_s(o,nl);o.append(last_nl);o+=vi(len(dates))+vi(dates[0])
    prev=dates[0]
    for d in dates[1:]:o+=vi(d-prev);prev=d
    o+=vi(len(states))
    for x in states:_s(o,x)
    o+=vi(len(counties))
    for x in counties:_s(o,x)
    o+=vi(len(ents))
    for st,co,fp in ents:o+=vi(sm[st])+vi(cm[co]);_s(o,fp)
    o+=vi(len(pres))+pres
    for mode,b in bands:o.append(mode);o+=vi(len(b))+b
    return bytes(o)

def unpack(b):
    if b[:4]!=MAGIC:raise ValueError('panel magic')
    p=4;nl,p=_rs(b,p);last_nl=b[p];p+=1;nd,p=uv(b,p);first,p=uv(b,p);dates=[first];prev=first
    for _ in range(nd-1):d,p=uv(b,p);prev+=d;dates.append(prev)
    ns,p=uv(b,p);states=[]
    for _ in range(ns):x,p=_rs(b,p);states.append(x)
    nc,p=uv(b,p);counties=[]
    for _ in range(nc):x,p=_rs(b,p);counties.append(x)
    ne,p=uv(b,p);ents=[]
    for _ in range(ne):si,p=uv(b,p);ci,p=uv(b,p);fp,p=_rs(b,p);ents.append((states[si],counties[ci],fp))
    pl,p=uv(b,p);pres=b[p:p+pl];p+=pl;pp=0;active=set();dayids=[];occ=[0]*ne
    for _ in range(nd):
        nt,pp=uv(pres,pp);tog=[];prev=-1
        for _ in range(nt):gap,pp=uv(pres,pp);x=prev+gap+1
        
            # append after validation below
            if x<0 or x>=ne:raise ValueError('presence id')
            tog.append(x);prev=x
        for x in tog:
            if x in active:active.remove(x)
            else:active.add(x)
        ids=sorted(active);dayids.append(ids)
        for x in ids:occ[x]+=1
    if pp!=len(pres):raise ValueError('presence trailing')
    measures=[]
    for _m in range(2):
        mode=b[p];p+=1;bl,p=uv(b,p);band=b[p:p+bl];p+=bl;bp=0;seqs=[]
        if mode==0:
            seqs,bp=_undense(band,0,occ)
        elif mode==1:
            for n in occ:
                m,bp=uv(band,bp);ds=[0]*n;pos=-1
                for _ in range(m):gap,bp=uv(band,bp);d,bp=us(band,bp);pos+=gap+1
                
                    # set after bounds check
                    if pos<0 or pos>=n:raise ValueError('sparse pos')
                    ds[pos]=d
                a=[];v=0
                for d in ds:v+=d;a.append(v)
                seqs.append(a)
        else:raise ValueError('measure mode')
        if bp!=len(band):raise ValueError('measure trailing')
        measures.append(seqs)
    if p!=len(b):raise ValueError('panel trailing')
    idx=[0]*ne;out=bytearray(b'date,county,state,fips,cases,deaths'+nl)
    for di,ids in enumerate(dayids):
        dt=datetime.date.fromordinal(dates[di]).isoformat().encode()
        for e in ids:
            st,co,fp=ents[e];j=idx[e];idx[e]+=1
            out+=b','.join((dt,co,st,fp,str(measures[0][e][j]).encode(),str(measures[1][e][j]).encode()))
            if di!=len(dayids)-1 or e!=ids[-1] or last_nl:out+=nl
    return bytes(out)
