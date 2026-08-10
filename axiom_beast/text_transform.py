#!/usr/bin/env python3
import re,collections
from axiom3_common import vi,uv
MAGIC=b'TXT3'
WORD=re.compile(rb"[A-Za-z]+(?:'[A-Za-z]+)?")
LEX=re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?")

def _ids(tokens):
    c=collections.Counter(tokens)
    dictionary=[x for x,_ in sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))]
    mp={x:i for i,x in enumerate(dictionary)}
    return dictionary,b''.join(vi(mp[x]) for x in tokens)

def _pack_dict(ds): return vi(len(ds))+b''.join(vi(len(x))+x for x in ds)
def _unpack_dict(b,p):
    n,p=uv(b,p);out=[]
    for _ in range(n):
        l,p=uv(b,p);out.append(b[p:p+l]);p+=l
    return out,p

def pack_words(data):
    words=[];seps=[];cases=bytearray();custom=bytearray();last=0
    for m in WORD.finditer(data):
        seps.append(data[last:m.start()]);w=m.group();lo=w.lower();words.append(lo)
        if w==lo:cases.append(0)
        elif w==lo[:1].upper()+lo[1:]:cases.append(1)
        elif w==lo.upper():cases.append(2)
        else:cases.append(3);custom+=w
        last=m.end()
    seps.append(data[last:])
    if len(words)<32:return None
    wd,wids=_ids(words);sd,sids=_ids(seps)
    o=bytearray(MAGIC)+b'W'+vi(len(words))+_pack_dict(wd)+_pack_dict(sd)
    for band in (wids,bytes(cases),sids,bytes(custom)):o+=vi(len(band))+band
    return bytes(o)

def unpack_words(blob):
    p=5;n,p=uv(blob,p);wd,p=_unpack_dict(blob,p);sd,p=_unpack_dict(blob,p);bands=[]
    for _ in range(4):l,p=uv(blob,p);bands.append(blob[p:p+l]);p+=l
    wids,cases,sids,custom=bands;wp=sp=cp=0;out=bytearray()
    def gid(stream,pos):return uv(stream,pos)
    sid,sp=gid(sids,sp);out+=sd[sid]
    for i in range(n):
        wid,wp=gid(wids,wp);w=wd[wid];cm=cases[i]
        if cm==0:v=w
        elif cm==1:v=w[:1].upper()+w[1:]
        elif cm==2:v=w.upper()
        elif cm==3:v=custom[cp:cp+len(w)];cp+=len(w)
        else:raise ValueError('case')
        out+=v;sid,sp=gid(sids,sp);out+=sd[sid]
    if wp!=len(wids) or sp!=len(sids) or cp!=len(custom):raise ValueError('band trailing')
    return bytes(out)

def pack_lex(data):
    toks=[];seps=[];last=0
    for m in LEX.finditer(data):
        seps.append(data[last:m.start()]);toks.append(m.group());last=m.end()
    seps.append(data[last:])
    if len(toks)<32:return None
    td,tids=_ids(toks);sd,sids=_ids(seps)
    o=bytearray(MAGIC)+b'L'+vi(len(toks))+_pack_dict(td)+_pack_dict(sd)
    for band in (tids,sids):o+=vi(len(band))+band
    return bytes(o)

def unpack_lex(blob):
    p=5;n,p=uv(blob,p);td,p=_unpack_dict(blob,p);sd,p=_unpack_dict(blob,p);bands=[]
    for _ in range(2):l,p=uv(blob,p);bands.append(blob[p:p+l]);p+=l
    tids,sids=bands;tp=sp=0;out=bytearray();sid,sp=uv(sids,sp);out+=sd[sid]
    for _ in range(n):
        tid,tp=uv(tids,tp);out+=td[tid];sid,sp=uv(sids,sp);out+=sd[sid]
    if tp!=len(tids) or sp!=len(sids):raise ValueError('trailing')
    return bytes(out)

def candidates(data):
    out=[]
    a=pack_words(data)
    if a:out.append(a)
    b=pack_lex(data)
    if b:out.append(b)
    return out

def unpack(blob):
    if blob[:4]!=MAGIC:raise ValueError('text magic')
    if blob[4:5]==b'W':return unpack_words(blob)
    if blob[4:5]==b'L':return unpack_lex(blob)
    raise ValueError('text mode')
