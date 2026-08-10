#!/usr/bin/env python3
import re,collections,struct,sys,hashlib
MAGIC=b'PST1';WORD=re.compile(rb"[A-Za-z]+(?:'[A-Za-z]+)?")
def vi(n):
 o=bytearray()
 while n>=128:o.append((n&127)|128);n>>=7
 o.append(n);return bytes(o)
def uv(b,p):
 n=s=0
 while 1:
  x=b[p];p+=1;n|=(x&127)<<s
  if x<128:return n,p
  s+=7
def loadlex(path):
 out=[];seen=set()
 for line in open(path,'rb'):
  try:w,c=line.rstrip(b'\n').rsplit(b' ',1);w=w.lower()
  except:continue
  if w and w not in seen:seen.add(w);out.append(w)
  if len(out)>=50000:break
 return out
def tokenc(n):return bytes([n]) if n<255 else b'\xff'+struct.pack('<H',n)
def tokdec(b,p):
 x=b[p];p+=1
 if x<255:return x,p
 return struct.unpack_from('<H',b,p)[0],p+2
def pack(data,lex):
 rank={w:i for i,w in enumerate(lex)};ms=list(WORD.finditer(data));words=[];seps=[];cases=[];last=0
 for m in ms:
  seps.append(data[last:m.start()]);w=m.group();lo=w.lower();words.append(lo);cases.append(0 if w==lo else 1 if w==lo[:1].upper()+lo[1:] else 2 if w==lo.upper() else 3);last=m.end()
 seps.append(data[last:]);uc=collections.Counter(w for w in words if w not in rank);ud=[x for x,_ in sorted(uc.items(),key=lambda kv:(-kv[1],kv[0]))];um={w:i for i,w in enumerate(ud)}
 wb=bytearray()
 for w in words:wb+=tokenc(rank[w] if w in rank else 50000+um[w])
 sc=collections.Counter(seps);sd=[x for x,_ in sorted(sc.items(),key=lambda kv:(-kv[1],kv[0]))];sm={x:i for i,x in enumerate(sd)};sb=bytearray()
 for s in seps:sb+=tokenc(sm[s])
 cp=bytearray((len(cases)+3)//4)
 for i,c in enumerate(cases):
  if c==3:raise ValueError('mixed case not supported by PST1')
  cp[i//4]|=c<<(2*(i%4))
 udb=vi(len(ud))+b''.join(vi(len(x))+x for x in ud);sdb=vi(len(sd))+b''.join(vi(len(x))+x for x in sd);bands=[bytes(wb),bytes(cp),bytes(sb),udb,sdb]
 o=bytearray(MAGIC)+vi(len(words))+hashlib.sha256(data).digest()
 for q in bands:o+=vi(len(q))+q
 return bytes(o)
def unpack(blob,lex):
 if blob[:4]!=MAGIC:raise ValueError('magic')
 p=4;n,p=uv(blob,p);digest=blob[p:p+32];p+=32;bands=[]
 for _ in range(5):l,p=uv(blob,p);bands.append(blob[p:p+l]);p+=l
 if p!=len(blob):raise ValueError('trailing')
 wb,cp,sb,udb,sdb=bands;p0=0;nu,p0=uv(udb,p0);ud=[]
 for _ in range(nu):l,p0=uv(udb,p0);ud.append(udb[p0:p0+l]);p0+=l
 p0=0;ns,p0=uv(sdb,p0);sd=[]
 for _ in range(ns):l,p0=uv(sdb,p0);sd.append(sdb[p0:p0+l]);p0+=l
 wi=si=0;out=bytearray();sid,si=tokdec(sb,si);out+=sd[sid]
 for i in range(n):
  tid,wi=tokdec(wb,wi);w=lex[tid] if tid<50000 else ud[tid-50000];cm=(cp[i//4]>>(2*(i%4)))&3;v=w if cm==0 else w[:1].upper()+w[1:] if cm==1 else w.upper() if cm==2 else None
  if v is None:raise ValueError('case')
  out+=v;sid,si=tokdec(sb,si);out+=sd[sid]
 if wi!=len(wb) or si!=len(sb) or hashlib.sha256(out).digest()!=digest:raise ValueError('integrity')
 return bytes(out)
if __name__=='__main__':
 cmd,src,dst,lexp=sys.argv[1:];lex=loadlex(lexp);open(dst,'wb').write(pack(open(src,'rb').read(),lex) if cmd=='c' else unpack(open(src,'rb').read(),lex))
