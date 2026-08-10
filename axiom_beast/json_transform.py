#!/usr/bin/env python3
import re,collections,zlib
from axiom3_common import vi,uv,enc_svar,dec_svar
MAGIC=b'JSN3'
KMARK=0; SMARK=1; NMARK=2; LMARK=3
INT=re.compile(rb'-?(?:0|[1-9]\d*)$')
NUMSTART=set(b'-0123456789')

def _scan_string(d,i):
    if d[i]!=34:return None
    j=i+1
    while j<len(d):
        c=d[j]
        if c==34:return j+1
        if c==92:
            j+=2
            if j>len(d):return None
        else:
            if c<32:return None
            j+=1
    return None

def _scan_number(d,i):
    j=i
    if d[j:j+1]==b'-':j+=1
    if j>=len(d):return None
    if d[j]==48:j+=1
    elif 49<=d[j]<=57:
        j+=1
        while j<len(d) and 48<=d[j]<=57:j+=1
    else:return None
    if j<len(d) and d[j]==46:
        j+=1;k=j
        while j<len(d) and 48<=d[j]<=57:j+=1
        if j==k:return None
    if j<len(d) and d[j] in (69,101):
        j+=1
        if j<len(d) and d[j] in (43,45):j+=1
        k=j
        while j<len(d) and 48<=d[j]<=57:j+=1
        if j==k:return None
    return j

def tokenize(d):
    out=[];i=0
    while i<len(d):
        c=d[i]
        if c in b' \t\r\n':
            j=i+1
            while j<len(d) and d[j] in b' \t\r\n':j+=1
            out.append(('w',d[i:j]));i=j
        elif c==34:
            j=_scan_string(d,i)
            if j is None:return None
            out.append(('s',d[i:j]));i=j
        elif c in NUMSTART:
            j=_scan_number(d,i)
            if j is None:return None
            out.append(('n',d[i:j]));i=j
        elif c in b'{}[],:':out.append(('p',bytes([c])));i+=1
        elif d.startswith(b'true',i):out.append(('l',b'true'));i+=4
        elif d.startswith(b'false',i):out.append(('l',b'false'));i+=5
        elif d.startswith(b'null',i):out.append(('l',b'null'));i+=4
        else:return None
    return out

def _dict_pack(vals):
    c=collections.Counter(vals);ds=[x for x,_ in sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))];mp={x:i for i,x in enumerate(ds)}
    return b'D'+vi(len(ds))+b''.join(vi(len(x))+x for x in ds)+b''.join(vi(mp[x]) for x in vals)
def _dict_unpack(rep,n):
    p=1;k,p=uv(rep,p);ds=[]
    for _ in range(k):l,p=uv(rep,p);ds.append(rep[p:p+l]);p+=l
    out=[]
    for _ in range(n):i,p=uv(rep,p);out.append(ds[i])
    if p!=len(rep):raise ValueError('dict band trailing')
    return out

def _raw_pack(vals):return b'R'+b''.join(vi(len(x))+x for x in vals)
def _raw_unpack(rep,n):
    p=1;out=[]
    for _ in range(n):l,p=uv(rep,p);out.append(rep[p:p+l]);p+=l
    if p!=len(rep):raise ValueError('raw band trailing')
    return out

def _int_pack(vals):
    if not vals:return None
    xs=[]
    for v in vals:
        if not INT.fullmatch(v):return None
        q=int(v)
        if str(q).encode()!=v:return None
        xs.append(q)
    ab=bytearray();db=bytearray();prev=0
    for q in xs:ab+=enc_svar(q);db+=enc_svar(q-prev);prev=q
    mode=0 if len(zlib.compress(ab,6))<=len(zlib.compress(db,6)) else 1
    return b'I'+bytes([mode])+(bytes(ab) if mode==0 else bytes(db))
def _int_unpack(rep,n):
    p=2;mode=rep[1];out=[];prev=0
    for _ in range(n):q,p=dec_svar(rep,p);q=prev+q if mode else q;prev=q if mode else prev;out.append(str(q).encode())
    if p!=len(rep):raise ValueError('int band trailing')
    return out

def _lit_pack(vals):
    mp={b'null':0,b'false':1,b'true':2}
    if any(v not in mp for v in vals):return None
    return b'L'+bytes(mp[v] for v in vals)
def _lit_unpack(rep,n):
    ds=[b'null',b'false',b'true'];x=[ds[v] for v in rep[1:]]
    if len(x)!=n:return None
    return x

def _choose(vals,kind):
    cand=[_raw_pack(vals),_dict_pack(vals)]
    if kind=='n':
        q=_int_pack(vals)
        if q:cand.append(q)
    if kind=='l':
        q=_lit_pack(vals)
        if q:cand.append(q)
    return min(cand,key=lambda x:len(zlib.compress(x,6)))

def pack(data):
    toks=tokenize(data)
    if not toks or len(toks)<32:return None
    iskey=set()
    for i,(t,v) in enumerate(toks):
        if t!='s':continue
        j=i+1
        while j<len(toks) and toks[j][0]=='w':j+=1
        if j<len(toks) and toks[j]==('p',b':'):iskey.add(i)
    keys=[toks[i][1] for i in sorted(iskey)]
    if not keys:return None
    kc=collections.Counter(keys);kd=[x for x,_ in sorted(kc.items(),key=lambda kv:(-kv[1],kv[0]))];kmap={x:i for i,x in enumerate(kd)}
    keyids=[];skeleton=bytearray();bands=collections.defaultdict(list);pending=None;last_key=None
    for i,(t,v) in enumerate(toks):
        if i in iskey:
            kid=kmap[v];keyids.append(kid);last_key=kid;skeleton.append(KMARK);continue
        if t=='p' and v==b':':
            skeleton+=v;pending=last_key;continue
        if t=='w':skeleton+=v;continue
        if t=='p':
            skeleton+=v
            if v in (b'{',b'['):pending=None
            continue
        if t in ('s','n','l'):
            mark={'s':SMARK,'n':NMARK,'l':LMARK}[t];skeleton.append(mark)
            key=pending if pending is not None else -1
            bands[(key,t)].append(v);pending=None
            continue
        raise ValueError('token')
    keyidstream=b''.join(vi(i) for i in keyids)
    o=bytearray(MAGIC)+vi(len(kd))+b''.join(vi(len(x))+x for x in kd)
    o+=vi(len(keyidstream))+keyidstream+vi(len(skeleton))+skeleton
    items=sorted(bands.items(),key=lambda kv:(kv[0][0],kv[0][1]))
    o+=vi(len(items))
    tcode={'s':0,'n':1,'l':2}
    for (kid,t),vals in items:
        rep=_choose(vals,t);o+=enc_svar(kid)+bytes([tcode[t]])+vi(len(vals))+vi(len(rep))+rep
    return bytes(o)

def unpack(rep):
    if rep[:4]!=MAGIC:raise ValueError('json magic')
    p=4;nk,p=uv(rep,p);kd=[]
    for _ in range(nk):l,p=uv(rep,p);kd.append(rep[p:p+l]);p+=l
    kl,p=uv(rep,p);kis=rep[p:p+kl];p+=kl;sl,p=uv(rep,p);sk=rep[p:p+sl];p+=sl
    nb,p=uv(rep,p);bands={};tdec={0:'s',1:'n',2:'l'}
    for _ in range(nb):
        kid,p=dec_svar(rep,p);tc=rep[p];p+=1;n,p=uv(rep,p);rl,p=uv(rep,p);r=rep[p:p+rl];p+=rl
        if r[:1]==b'R':vals=_raw_unpack(r,n)
        elif r[:1]==b'D':vals=_dict_unpack(r,n)
        elif r[:1]==b'I':vals=_int_unpack(r,n)
        elif r[:1]==b'L':vals=_lit_unpack(r,n)
        else:raise ValueError('json band')
        bands[(kid,tdec[tc])]=[vals,0]
    if p!=len(rep):raise ValueError('json trailing')
    kp=0;last_key=None;pending=None;out=bytearray();i=0
    while i<len(sk):
        c=sk[i]
        if c==KMARK:
            kid,kp=uv(kis,kp);out+=kd[kid];last_key=kid;i+=1;continue
        if c==58:
            out.append(c);pending=last_key;i+=1;continue
        if c in (123,91):
            out.append(c);pending=None;i+=1;continue
        if c in (SMARK,NMARK,LMARK):
            t={SMARK:'s',NMARK:'n',LMARK:'l'}[c];key=pending if pending is not None else -1
            vals,pos=bands[(key,t)];out+=vals[pos];bands[(key,t)][1]=pos+1;pending=None;i+=1;continue
        out.append(c);i+=1
    if kp!=len(kis):raise ValueError('key ids trailing')
    for vals,pos in bands.values():
        if pos!=len(vals):raise ValueError('unused json band')
    return bytes(out)
