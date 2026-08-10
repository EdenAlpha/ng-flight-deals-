#!/usr/bin/env python3
import zlib
from io import BytesIO
from PIL import Image
from axiom3_common import vi,uv
import png_law_transform as P
MAGIC=b'PW5'
def pack(d):
 cs=P.chunks(d)
 if not cs:return None
 ih=[x for x in cs if x[1]==b'IHDR'];ids=[x for x in cs if x[1]==b'IDAT']
 if len(ih)!=1 or not ids:return None
 _,_,ds,ln=ih[0];H=d[ds:ds+ln]
 if len(H)!=13:return None
 w=int.from_bytes(H[:4],'big');h=int.from_bytes(H[4:8],'big');bd,ct,inter=H[8],H[9],H[12]
 if (bd,ct,inter)!=(8,6,0):return None
 comp=b''.join(d[x[2]:x[2]+x[3]] for x in ids)
 try:raw=zlib.decompress(comp)
 except Exception:return None
 law=None
 for lev in range(1,10):
  for mem in range(5,10):
   co=zlib.compressobj(lev,zlib.DEFLATED,15,mem,zlib.Z_DEFAULT_STRATEGY);q=co.compress(raw)+co.flush()
   if q==comp:law=(lev,mem);break
  if law:break
 if not law:return None
 body=P.unfilter(raw,w,h,4)
 if body is None:return None
 fs=body[:h];pix=body[h:]
 try:
  bio=BytesIO();Image.frombytes('RGBA',(w,h),pix).save(bio,'WEBP',lossless=True,quality=100,method=6,exact=True)
  web=bio.getvalue()
  if Image.open(BytesIO(web)).convert('RGBA').tobytes()!=pix:return None
 except Exception:return None
 sk=bytearray(d)
 for _,_,ds,ln in ids:sk[ds:ds+ln]=b'\0'*ln
 rep=MAGIC+bytes(law)+vi(len(sk))+bytes(sk)+vi(len(fs))+fs+vi(len(web))+web
 try:return rep if unpack(rep)==d else None
 except Exception:return None
def unpack(rep):
 if rep[:3]!=MAGIC:raise ValueError('png webp law')
 p=3;lev,mem=rep[p],rep[p+1];p+=2;sl,p=uv(rep,p);sk=bytearray(rep[p:p+sl]);p+=sl;fl,p=uv(rep,p);fs=rep[p:p+fl];p+=fl;wl,p=uv(rep,p);web=rep[p:p+wl];p+=wl
 if p!=len(rep):raise ValueError('trailing png webp law')
 cs=P.chunks(sk);ih=[x for x in cs if x[1]==b'IHDR'][0];ids=[x for x in cs if x[1]==b'IDAT'];_,_,ds,ln=ih;H=sk[ds:ds+ln];w=int.from_bytes(H[:4],'big');h=int.from_bytes(H[4:8],'big')
 pix=Image.open(BytesIO(web)).convert('RGBA').tobytes()
 if len(pix)!=w*h*4:raise ValueError('pixel size')
 raw=P.refilter(fs+pix,w,h,4)
 co=zlib.compressobj(lev,zlib.DEFLATED,15,mem,zlib.Z_DEFAULT_STRATEGY);comp=co.compress(raw)+co.flush()
 if len(comp)!=sum(x[3] for x in ids):raise ValueError('idat length')
 q=0
 for _,_,ds,ln in ids:sk[ds:ds+ln]=comp[q:q+ln];q+=ln
 return bytes(sk)
