#!/usr/bin/env python3
import datetime,zlib,heapq
MAGIC=b'PNL2'

def vi(n):
    if n<0: raise ValueError('negative varint')
    o=bytearray()
    while True:
        q=n&127;n>>=7
        if n:o.append(q|128)
        else:o.append(q);return bytes(o)
def uv(b,p):
    n=s=0
    while True:
        if p>=len(b):raise ValueError('truncated varint')
        q=b[p];p+=1;n|=(q&127)<<s
        if not q&128:return n,p
        s+=7
        if s>70:raise ValueError('varint too long')
def sv(n):return vi((n<<1)^(n>>63))
def us(b,p):
    q,p=uv(b,p);return (q>>1)^-(q&1),p
def puts(o,x):o+=vi(len(x))+x
def gets(b,p):
    n,p=uv(b,p);return b[p:p+n],p+n

def dord(x):
    try:
        s=x.decode('ascii');d=datetime.date.fromisoformat(s)
        return d.toordinal() if d.isoformat()==s else None
    except:return None

def canonical_entities(day_entities):
    nodes=set(x for day in day_entities for x in day);adj={x:set() for x in nodes};ind={x:0 for x in nodes}
    for day in day_entities:
        for a,c in zip(day,day[1:]):
            if c not in adj[a]:adj[a].add(c);ind[c]+=1
    heap=[x for x in nodes if ind[x]==0];heapq.heapify(heap);out=[]
    while heap:
        x=heapq.heappop(heap);out.append(x)
        for y in adj[x]:
            ind[y]-=1
            if ind[y]==0:heapq.heappush(heap,y)
    return out if len(out)==len(nodes) else None

def dense(seqs):
    o=bytearray()
    for a in seqs:
        prev=0
        for x in a:o+=sv(x-prev);prev=x
    return bytes(o)
def sparse(seqs):
    o=bytearray()
    for a in seqs:
        prev=0;last=-1;ev=[]
        for i,x in enumerate(a):
            d=x-prev;prev=x
            if d:ev.append((i-last-1,d));last=i
        o+=vi(len(ev))
        for gap,d in ev:o+=vi(gap)+sv(d)
    return bytes(o)
def undense(b,lens):
    p=0;out=[]
    for n in lens:
        a=[];v=0
        for _ in range(n):d,p=us(b,p);v+=d;a.append(v)
        out.append(a)
    if p!=len(b):raise ValueError('dense trailing')
    return out
def unsparse(b,lens):
    p=0;out=[]
    for n in lens:
        m,p=uv(b,p);ds=[0]*n;pos=-1
        for _ in range(m):
            gap,p=uv(b,p);d,p=us(b,p);pos+=gap+1
            if pos<0 or pos>=n:raise ValueError('sparse position')
            ds[pos]=d
        a=[];v=0
        for d in ds:v+=d;a.append(v)
        out.append(a)
    if p!=len(b):raise ValueError('sparse trailing')
    return out

def pack(data):
    lines=data.splitlines(keepends=True)
    if len(lines)<16:return None
    rows=[];ends=[]
    for x in lines:
        if x.endswith(b'\r\n'):q=x[:-2];e=b'\r\n'
        elif x.endswith(b'\n'):q=x[:-1];e=b'\n'
        elif x.endswith(b'\r'):q=x[:-1];e=b'\r'
        else:q=x;e=b''
        f=q.split(b',')
        if len(f)!=6:return None
        rows.append(f);ends.append(e)
    if rows[0]!=[b'date',b'county',b'state',b'fips',b'cases',b'deaths']:return None
    nl=ends[0]
    if not nl or any(e!=nl for e in ends[:-1]) or ends[-1] not in (nl,b''):return None
    last_nl=int(ends[-1]==nl);body=rows[1:]
    dates=[];groups=[];cur=None
    for r in body:
        d=dord(r[0])
        if d is None:return None
        if d!=cur:dates.append(d);groups.append([]);cur=d
        groups[-1].append(r)
    if not dates or any(b<=a for a,b in zip(dates,dates[1:])):return None
    dayents=[[(r[2],r[1],r[3]) for r in g] for g in groups]
    if any(len(x)!=len(set(x)) for x in dayents):return None
    ents=canonical_entities(dayents)
    if ents is None:return None
    eid={x:i for i,x in enumerate(ents)};dayids=[]
    for day in dayents:
        ids=[eid[x] for x in day]
        if ids!=sorted(ids):return None
        dayids.append(ids)
    states=sorted(set(x[0] for x in ents));counties=sorted(set(x[1] for x in ents));sm={x:i for i,x in enumerate(states)};cm={x:i for i,x in enumerate(counties)}
    pres=bytearray();active=set();occ=[0]*len(ents)
    for ids in dayids:
        now=set(ids);tog=sorted(active^now);pres+=vi(len(tog));last=-1
        for x in tog:pres+=vi(x-last-1);last=x
        active=now
        for x in ids:occ[x]+=1
    vals=[[[] for _ in ents] for _ in range(2)]
    for g in groups:
        for r in g:
            i=eid[(r[2],r[1],r[3])]
            try:a=int(r[4]);c=int(r[5])
            except:return None
            if str(a).encode()!=r[4] or str(c).encode()!=r[5]:return None
            vals[0][i].append(a);vals[1][i].append(c)
    bands=[]
    for m in range(2):
        a=dense(vals[m]);c=sparse(vals[m])
        bands.append((1,c) if len(zlib.compress(c,6))<len(zlib.compress(a,6)) else (0,a))
    o=bytearray(MAGIC);puts(o,nl);o.append(last_nl);o+=vi(len(dates))+vi(dates[0]);prev=dates[0]
    for d in dates[1:]:o+=vi(d-prev);prev=d
    o+=vi(len(states))
    for x in states:puts(o,x)
    o+=vi(len(counties))
    for x in counties:puts(o,x)
    o+=vi(len(ents))
    for st,co,fp in ents:o+=vi(sm[st])+vi(cm[co]);puts(o,fp)
    o+=vi(len(pres))+pres
    for mode,band in bands:o.append(mode);o+=vi(len(band))+band
    return bytes(o)

def unpack(b):
    if b[:4]!=MAGIC:raise ValueError('panel magic')
    p=4;nl,p=gets(b,p);last_nl=b[p];p+=1;nd,p=uv(b,p);first,p=uv(b,p);dates=[first];prev=first
    for _ in range(nd-1):q,p=uv(b,p);prev+=q;dates.append(prev)
    ns,p=uv(b,p);states=[]
    for _ in range(ns):x,p=gets(b,p);states.append(x)
    nc,p=uv(b,p);counties=[]
    for _ in range(nc):x,p=gets(b,p);counties.append(x)
    ne,p=uv(b,p);ents=[]
    for _ in range(ne):si,p=uv(b,p);ci,p=uv(b,p);fp,p=gets(b,p);ents.append((states[si],counties[ci],fp))
    pl,p=uv(b,p);pres=b[p:p+pl];p+=pl;pp=0;active=set();dayids=[];occ=[0]*ne
    for _ in range(nd):
        nt,pp=uv(pres,pp);tog=[];last=-1
        for _ in range(nt):
            gap,pp=uv(pres,pp);x=last+gap+1
            if x>=ne:raise ValueError('presence id')
            tog.append(x);last=x
        for x in tog:
            if x in active:active.remove(x)
            else:active.add(x)
        ids=sorted(active);dayids.append(ids)
        for x in ids:occ[x]+=1
    if pp!=len(pres):raise ValueError('presence trailing')
    measures=[]
    for _ in range(2):
        mode=b[p];p+=1;bl,p=uv(b,p);band=b[p:p+bl];p+=bl
        measures.append(undense(band,occ) if mode==0 else unsparse(band,occ) if mode==1 else (_ for _ in ()).throw(ValueError('measure mode')))
    if p!=len(b):raise ValueError('trailing panel')
    curs=[0]*ne;out=bytearray(b'date,county,state,fips,cases,deaths'+nl)
    total=sum(len(x) for x in dayids);written=0
    for di,ids in enumerate(dayids):
        dt=datetime.date.fromordinal(dates[di]).isoformat().encode()
        for e in ids:
            st,co,fp=ents[e];j=curs[e];curs[e]+=1;written+=1
            out+=b','.join((dt,co,st,fp,str(measures[0][e][j]).encode(),str(measures[1][e][j]).encode()))
            if written<total or last_nl:out+=nl
    return bytes(out)
