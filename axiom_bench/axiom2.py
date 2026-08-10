#!/usr/bin/env python3
import argparse,hashlib,struct,subprocess,zlib,lzma,sys,os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import semantic_band
MAGIC=b'AXM2'

def vi(n):
 o=bytearray()
 while True:
  b=n&127;n>>=7
  if n:o.append(b|128)
  else:o.append(b);return bytes(o)
def uv(b,p):
 n=0;s=0
 while True:
  x=b[p];p+=1;n|=(x&127)<<s
  if not x&128:return n,p
  s+=7

def zc(d):return subprocess.run(['zstd','-22','--ultra','-q','-c'],input=d,stdout=subprocess.PIPE,check=True).stdout
def zd(d):return subprocess.run(['zstd','-d','-q','-c'],input=d,stdout=subprocess.PIPE,check=True).stdout
def bestc(d):
 if not d:return 0,b''
 c=[(1,zc(d)),(2,lzma.compress(d,preset=9|lzma.PRESET_EXTREME))]
 return min(c,key=lambda x:len(x[1]))
def dec(cid,d):
 if cid==0:return b''
 if cid==1:return zd(d)
 if cid==2:return lzma.decompress(d)
 raise ValueError('codec')
def putstream(raw):
 cid,c=bestc(raw);return bytes([cid])+vi(len(raw))+vi(len(c))+c
def getstream(blob,p):
 cid=blob[p];p+=1;ul,p=uv(blob,p);cl,p=uv(blob,p);raw=dec(cid,blob[p:p+cl]);p+=cl
 if len(raw)!=ul:raise ValueError('stream length')
 return raw,p

def parse_zip(d):
 p=d.rfind(b'PK\x05\x06')
 if p<0 or p+22>len(d):return []
 e=struct.unpack_from('<4s4H2LH',d,p);total=e[4];cd=e[6]
 if total==0xffff or cd==0xffffffff:return []
 pos=cd;out=[]
 for _ in range(total):
  if pos+46>len(d) or d[pos:pos+4]!=b'PK\x01\x02':return []
  v=struct.unpack_from('<4s6H3L5H2L',d,pos);m=v[4];cs=v[8];us=v[9];fn=v[10];ex=v[11];cm=v[12];lo=v[16]
  if lo+30<=len(d) and d[lo:lo+4]==b'PK\x03\x04':
   lv=struct.unpack_from('<4s5H3L2H',d,lo);ds=lo+30+lv[9]+lv[10]
   if ds+cs<=len(d):out.append((m,ds,cs,us))
  pos+=46+fn+ex+cm
 return out

def deflate_raw(u,lvl,ml,st):
 co=zlib.compressobj(lvl,zlib.DEFLATED,-15,ml,st);return co.compress(u)+co.flush()
def law(u,c):
 for ml in (8,9,7,6):
  for lvl in (6,5,4,7,8,9,3,2,1):
   t=(lvl,ml,zlib.Z_DEFAULT_STRATEGY)
   if deflate_raw(u,*t)==c:return t
 return None

def meta_encode(entries,laws):
 o=bytearray();o+=vi(len(laws))
 for lvl,ml,st in laws:o+=bytes((lvl,ml,st))
 o+=vi(len(entries));prev=0
 for ds,cs,us,lid in entries:
  o+=vi(ds-prev)+vi(cs)+vi(us)+vi(lid);prev=ds+cs
 return bytes(o)
def meta_decode(b):
 p=0;nl,p=uv(b,p);laws=[]
 for _ in range(nl):laws.append(tuple(b[p:p+3]));p+=3
 n,p=uv(b,p);es=[];prev=0
 for _ in range(n):
  gap,p=uv(b,p);cs,p=uv(b,p);us,p=uv(b,p);lid,p=uv(b,p);ds=prev+gap;es.append((ds,cs,us,lid));prev=ds+cs
 return es,laws

def make_zip_candidate(d):
 spans=parse_zip(d)
 if not spans:return None
 sk=bytearray(d);members=[];entries=[];law_ids={};laws=[]
 for m,ds,cs,us in spans:
  if m!=8 or cs==0:continue
  c=d[ds:ds+cs]
  try:u=zlib.decompress(c,-15)
  except:continue
  if len(u)!=us:continue
  L=law(u,c)
  if L is None:continue
  lid=law_ids.get(L)
  if lid is None:lid=len(laws);law_ids[L]=lid;laws.append(L)
  sk[ds:ds+cs]=b'\0'*cs;members.append(u);entries.append((ds,cs,us,lid))
 if not entries:return None
 meta=meta_encode(entries,laws);raw=b''.join(members);simple=putstream(raw)
 try:band=semantic_band.pack(members)
 except Exception:band=b''
 if band and len(band)+1 < len(simple)+1: sem=bytes([1])+vi(len(band))+band
 else: sem=bytes([0])+simple
 body=bytearray();body+=putstream(bytes(sk));body+=putstream(meta);body+=sem
 return bytes(body),len(entries)

def compress(src,dst):
 d=open(src,'rb').read();digest=hashlib.sha256(d).digest();raw_payload=putstream(d);best=bytes([0])+raw_payload;mode='raw';peeled=0
 z=make_zip_candidate(d)
 if z:
  body,n=z;cand=bytes([1])+body
  if len(cand)<len(best):best=cand;mode='zip-law';peeled=n
 out=MAGIC+vi(len(d))+digest+best;open(dst,'wb').write(out)
 return {'original':len(d),'compressed':len(out),'mode':mode,'peeled':peeled}

def decompress(src,dst):
 b=open(src,'rb').read()
 if b[:4]!=MAGIC:raise SystemExit('bad magic')
 p=4;orig,p=uv(b,p);digest=b[p:p+32];p+=32;mode=b[p];p+=1
 if mode==0:d,p=getstream(b,p)
 elif mode==1:
  sk,p=getstream(b,p);meta,p=getstream(b,p);entries,laws=meta_decode(meta);sm=b[p];p+=1;lens=[e[2] for e in entries]
  if sm==0:
   raw,p=getstream(b,p);members=[];q=0
   for n in lens:members.append(raw[q:q+n]);q+=n
   if q!=len(raw):raise ValueError('raw split')
  elif sm==1:
   bl,p=uv(b,p);members=semantic_band.unpack(b[p:p+bl],lens);p+=bl
  else:raise ValueError('semantic mode')
  d=bytearray(sk)
  for (ds,cs,us,lid),u in zip(entries,members):
   c=deflate_raw(u,*laws[lid])
   if len(c)!=cs:raise ValueError('law mismatch')
   d[ds:ds+cs]=c
  d=bytes(d)
 else:raise ValueError('mode')
 if len(d)!=orig or hashlib.sha256(d).digest()!=digest:raise SystemExit('integrity failure')
 open(dst,'wb').write(d);return {'output':len(d),'mode':mode}

def main():
 ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest='cmd',required=True);c=sp.add_parser('c');c.add_argument('src');c.add_argument('dst');x=sp.add_parser('d');x.add_argument('src');x.add_argument('dst');a=ap.parse_args();print(compress(a.src,a.dst) if a.cmd=='c' else decompress(a.src,a.dst))
if __name__=='__main__':main()
