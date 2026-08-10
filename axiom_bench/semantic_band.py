#!/usr/bin/env python3
import struct,subprocess,lzma
MAGIC=b'SBP1'
STREAMS=['meta','tags','ulen','utf','refs','n4','n8','kinds','rem','other','flags']

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

def zc(d): return subprocess.run(['zstd','-22','--ultra','-q','-c'],input=d,stdout=subprocess.PIPE,check=True).stdout
def zd(d): return subprocess.run(['zstd','-d','-q','-c'],input=d,stdout=subprocess.PIPE,check=True).stdout

def bestc(d):
 if not d:return 0,b''
 cand=[(1,zc(d)),(2,lzma.compress(d,preset=9|lzma.PRESET_EXTREME))]
 return min(cand,key=lambda x:len(x[1]))
def dec(cid,d):
 if cid==0:return b''
 if cid==1:return zd(d)
 if cid==2:return lzma.decompress(d)
 raise ValueError('codec')

def parse_class(b):
 if len(b)<10 or b[:4]!=b'\xca\xfe\xba\xbe':return None
 p=4;minor=int.from_bytes(b[p:p+2],'big');major=int.from_bytes(b[p+2:p+4],'big');p+=4;cp=int.from_bytes(b[p:p+2],'big');p+=2
 tags=bytearray();utf=bytearray();ulen=bytearray();refs=bytearray();n4=bytearray();n8=bytearray();kinds=bytearray();idx=1
 try:
  while idx<cp:
   tag=b[p];p+=1;tags.append(tag)
   if tag==1:
    n=int.from_bytes(b[p:p+2],'big');p+=2;ulen+=vi(n);utf+=b[p:p+n];p+=n
   elif tag in (3,4):n4+=b[p:p+4];p+=4
   elif tag in (5,6):n8+=b[p:p+8];p+=8;idx+=1
   elif tag in (7,8,16,19,20):
    x=int.from_bytes(b[p:p+2],'big');p+=2;refs+=vi(x)
   elif tag in (9,10,11,12,17,18):
    x=int.from_bytes(b[p:p+2],'big');y=int.from_bytes(b[p+2:p+4],'big');p+=4;refs+=vi(x)+vi(y)
   elif tag==15:
    kinds.append(b[p]);x=int.from_bytes(b[p+1:p+3],'big');p+=3;refs+=vi(x)
   else:return None
   idx+=1
 except Exception:return None
 meta=vi(minor)+vi(major)+vi(cp)+vi(len(tags))+vi(len(b)-p)
 return {'meta':meta,'tags':bytes(tags),'ulen':bytes(ulen),'utf':bytes(utf),'refs':bytes(refs),'n4':bytes(n4),'n8':bytes(n8),'kinds':bytes(kinds),'rem':b[p:]}

def pack(members):
 bands={k:bytearray() for k in STREAMS};flags=bytearray((len(members)+7)//8);classes=0
 for i,b in enumerate(members):
  pc=parse_class(b)
  if pc:
   flags[i>>3]|=1<<(i&7);classes+=1
   for k,v in pc.items():bands[k]+=v
  else:bands['other']+=b
 bands['flags']=flags
 header=bytearray(MAGIC)+vi(len(members))+vi(classes)+vi(len(STREAMS));payload=bytearray()
 for k in STREAMS:
  raw=bytes(bands[k]);cid,c=bestc(raw);header.append(cid);header+=vi(len(raw))+vi(len(c));payload+=c
 return bytes(header+payload)

def unpack(blob,lengths):
 if blob[:4]!=MAGIC:raise ValueError('bad SBP')
 p=4;n,p=uv(blob,p);classes,p=uv(blob,p);ns,p=uv(blob,p)
 if n!=len(lengths) or ns!=len(STREAMS):raise ValueError('count')
 hdr=[]
 for _ in STREAMS:
  cid=blob[p];p+=1;ul,p=uv(blob,p);cl,p=uv(blob,p);hdr.append((cid,ul,cl))
 bands={}
 for k,(cid,ul,cl) in zip(STREAMS,hdr):
  raw=dec(cid,blob[p:p+cl]);p+=cl
  if len(raw)!=ul:raise ValueError(('stream len',k,len(raw),ul))
  bands[k]=raw
 curs={k:0 for k in STREAMS};out=[]
 def getu(k,n):
  q=curs[k];v=bands[k][q:q+n];curs[k]=q+n
  if len(v)!=n:raise ValueError(('short',k))
  return v
 def getv(k):
  q=curs[k];v,q2=uv(bands[k],q);curs[k]=q2;return v
 flags=bands['flags']
 for i,need in enumerate(lengths):
  isclass=(flags[i>>3]>>(i&7))&1
  if not isclass:
   b=getu('other',need);out.append(b);continue
  minor=getv('meta');major=getv('meta');cp=getv('meta');nt=getv('meta');rlen=getv('meta')
  tags=getu('tags',nt);b=bytearray(b'\xca\xfe\xba\xbe')+minor.to_bytes(2,'big')+major.to_bytes(2,'big')+cp.to_bytes(2,'big');idx=1
  for tag in tags:
   b.append(tag)
   if tag==1:
    ln=getv('ulen');b+=ln.to_bytes(2,'big')+getu('utf',ln)
   elif tag in (3,4):b+=getu('n4',4)
   elif tag in (5,6):b+=getu('n8',8);idx+=1
   elif tag in (7,8,16,19,20):b+=getv('refs').to_bytes(2,'big')
   elif tag in (9,10,11,12,17,18):b+=getv('refs').to_bytes(2,'big')+getv('refs').to_bytes(2,'big')
   elif tag==15:b+=getu('kinds',1)+getv('refs').to_bytes(2,'big')
   else:raise ValueError('tag')
   idx+=1
  b+=getu('rem',rlen)
  if len(b)!=need:raise ValueError(('class len',len(b),need))
  out.append(bytes(b))
 return out
