#!/usr/bin/env python3
import re,collections
WORD=re.compile(rb"[A-Za-z]+(?:'[A-Za-z]+)?");LEX=re.compile(rb"[A-Za-z_][A-Za-z0-9_]*|[0-9]+(?:\.[0-9]+)?")
def vi(n):
 o=bytearray()
 while n>=128:o.append((n&127)|128);n>>=7
 o.append(n);return bytes(o)
def uv(b,p):
 n=0;s=0
 while 1:
  x=b[p];p+=1;n|=(x&127)<<s
  if x<128:return n,p
  s+=7
def ids(tokens):
 c=collections.Counter(tokens);d=[x for x,_ in sorted(c.items(),key=lambda kv:(-kv[1],kv[0]))];m={x:i for i,x in enumerate(d)};return d,b''.join(vi(m[x]) for x in tokens)
def pd(d):return vi(len(d))+b''.join(vi(len(x))+x for x in d)
def ud(b,p):
 n,p=uv(b,p);o=[]
 for _ in range(n):l,p=uv(b,p);o.append(b[p:p+l]);p+=l
 return o,p
def pack_words(data):
 words=[];seps=[];cases=bytearray();custom=bytearray();last=0
 for m in WORD.finditer(data):
  seps.append(data[last:m.start()]);w=m.group();lo=w.lower();words.append(lo)
  if w==lo:cases.append(0)
  elif w==lo[:1].upper()+lo[1:]:cases.append(1)
  elif w==lo.upper():cases.append(2)
  else:cases.append(3);custom+=w
  last=m.end()
 seps.append(data[last:]);wd,wids=ids(words);sd,sids=ids(seps);o=bytearray(b'TPW1')+vi(len(words))+pd(wd)+pd(sd)
 for q in (wids,bytes(cases),sids,bytes(custom)):o+=vi(len(q))+q
 return bytes(o)
def unpack_words(b):
 p=4;n,p=uv(b,p);wd,p=ud(b,p);sd,p=ud(b,p);bs=[]
 for _ in range(4):l,p=uv(b,p);bs.append(b[p:p+l]);p+=l
 wids,cases,sids,custom=bs;wp=sp=cp=0;o=bytearray();sid,sp=uv(sids,sp);o+=sd[sid]
 for i in range(n):
  wid,wp=uv(wids,wp);w=wd[wid];cm=cases[i]
  if cm==0:v=w
  elif cm==1:v=w[:1].upper()+w[1:]
  elif cm==2:v=w.upper()
  else:v=custom[cp:cp+len(w)];cp+=len(w)
  o+=v;sid,sp=uv(sids,sp);o+=sd[sid]
 return bytes(o)
