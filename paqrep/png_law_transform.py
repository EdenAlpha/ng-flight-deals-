#!/usr/bin/env python3
import zlib
from axiom3_common import vi,uv
MAGIC=b'PNG4'
def chunks(d):
 if d[:8]!=b'\x89PNG\r\n\x1a\n':return None
 p=8;out=[]
 while p+12<=len(d):
  ln=int.from_bytes(d[p:p+4],'big');typ=d[p+4:p+8];ds=p+8;de=ds+ln
  if de+4>len(d):return None
  out.append((p,typ,ds,ln));p=de+4
  if typ==b'IEND':break
 return out if p==len(d) else None
def paeth(a,b,c):
 q=a+b-c;pa=abs(q-a);pb=abs(q-b);pc=abs(q-c)
 return a if pa<=pb and pa<=pc else b if pb<=pc else c
def unfilter(raw,w,h,bpp):
 stride=w*bpp
 if len(raw)!=h*(stride+1):return None
 out=bytearray();fs=bytearray();prev=bytearray(stride);p=0
 for _ in range(h):
  f=raw[p];p+=1
  if f>4:return None
  fs.append(f);scan=raw[p:p+stride];p+=stride;rec=bytearray(stride)
  for x,v in enumerate(scan):
   a=rec[x-bpp] if x>=bpp else 0;b=prev[x];c=prev[x-bpp] if x>=bpp else 0
   pred=0 if f==0 else a if f==1 else b if f==2 else (a+b)//2 if f==3 else paeth(a,b,c)
   rec[x]=(v+pred)&255
  out+=rec;prev=rec
 return bytes(fs)+bytes(out)
def refilter(body,w,h,bpp):
 if len(body)!=h+w*h*bpp:return None
 fs=body[:h];pix=body[h:];stride=w*bpp;out=bytearray();prev=bytes(stride);p=0
 for y in range(h):
  f=fs[y];rec=pix[p:p+stride];p+=stride;scan=bytearray(stride)
  for x,v in enumerate(rec):
   a=rec[x-bpp] if x>=bpp else 0;b=prev[x];c=prev[x-bpp] if x>=bpp else 0
   pred=0 if f==0 else a if f==1 else b if f==2 else (a+b)//2 if f==3 else paeth(a,b,c)
   scan[x]=(v-pred)&255
  out.append(f);out+=scan;prev=rec
 return bytes(out)
def pack(d):
 cs=chunks(d)
 if not cs:return None
 ih=[x for x in cs if x[1]==b'IHDR'];ids=[x for x in cs if x[1]==b'IDAT']
 if len(ih)!=1 or not ids:return None
 _,_,ds,ln=ih[0];H=d[ds:ds+ln]
 if len(H)!=13:return None
 w=int.from_bytes(H[:4],'big');h=int.from_bytes(H[4:8],'big');bd=H[8];ct=H[9];inter=H[12]
 comp=b''.join(d[x[2]:x[2]+x[3]] for x in ids)
 try:raw=zlib.decompress(comp)
 except:return None
 law=None
 for lev in range(1,10):
  for mem in range(5,10):
   co=zlib.compressobj(lev,zlib.DEFLATED,15,mem,zlib.Z_DEFAULT_STRATEGY);q=co.compress(raw)+co.flush()
   if q==comp:law=(lev,mem);break
  if law:break
 if not law:return None
 mode=0;body=raw
 if bd==8 and inter==0 and ct in {0,2,3,4,6}:
  bpp={0:1,2:3,3:1,4:2,6:4}[ct];q=unfilter(raw,w,h,bpp)
  if q is not None:mode=1;body=q
 sk=bytearray(d)
 for _,_,ds,ln in ids:sk[ds:ds+ln]=b'\0'*ln
 return MAGIC+bytes([law[0],law[1],mode])+vi(len(sk))+bytes(sk)+vi(len(body))+body
def unpack(rep):
 if rep[:4]!=MAGIC:raise ValueError('png law')
 p=4;lev,mem,mode=rep[p],rep[p+1],rep[p+2];p+=3;sl,p=uv(rep,p);sk=bytearray(rep[p:p+sl]);p+=sl;bl,p=uv(rep,p);body=rep[p:p+bl];p+=bl
 if p!=len(rep):raise ValueError('trailing')
 cs=chunks(sk);ih=[x for x in cs if x[1]==b'IHDR'][0];ids=[x for x in cs if x[1]==b'IDAT'];_,_,ds,ln=ih;H=sk[ds:ds+ln];w=int.from_bytes(H[:4],'big');h=int.from_bytes(H[4:8],'big');ct=H[9]
 raw=body
 if mode:raw=refilter(body,w,h,{0:1,2:3,3:1,4:2,6:4}[ct])
 co=zlib.compressobj(lev,zlib.DEFLATED,15,mem,zlib.Z_DEFAULT_STRATEGY);comp=co.compress(raw)+co.flush()
 if len(comp)!=sum(x[3] for x in ids):raise ValueError('idat length')
 q=0
 for _,_,ds,ln in ids:sk[ds:ds+ln]=comp[q:q+ln];q+=ln
 return bytes(sk)
