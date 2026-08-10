#!/usr/bin/env python3
from axiom3_common import vi,uv
import tar_transform,png_law_transform
try:
 import font_glyf_law
except Exception:
 font_glyf_law=None
MAGIC=b'TFG5'
def pack(data):
 files=tar_transform.parse(data)
 if not files:return None
 sk=bytearray(data);reps=[];prev=0
 for ds,sz,name in files:
  raw=data[ds:ds+sz];sk[ds:ds+sz]=b'\0'*sz
  q=png_law_transform.pack(raw) if name.lower().endswith(b'.png') else None
  if q:
   reps.append((1,q))
  elif font_glyf_law is not None and name.lower().endswith((b'.ttf',b'.otf')):
   fq=font_glyf_law.pack(raw)
   reps.append((2,fq) if fq else (0,raw))
  else:
   reps.append((0,raw))
 o=bytearray(MAGIC)+vi(len(files))+vi(len(sk))+sk
 prev=0
 for (ds,sz,name),(mode,r) in zip(files,reps):
  o+=vi(ds-prev)+vi(sz)+bytes([mode])+vi(len(r))+r;prev=ds+sz
 return bytes(o)
def unpack(rep):
 if rep[:4] not in (b'TFG4',MAGIC):raise ValueError('tar graph')
 p=4;n,p=uv(rep,p);sl,p=uv(rep,p);sk=bytearray(rep[p:p+sl]);p+=sl;prev=0
 for _ in range(n):
  gap,p=uv(rep,p);sz,p=uv(rep,p);mode=rep[p];p+=1;rl,p=uv(rep,p);r=rep[p:p+rl];p+=rl;ds=prev+gap
  raw=png_law_transform.unpack(r) if mode==1 else font_glyf_law.unpack(r) if mode==2 and font_glyf_law is not None else r
  if len(raw)!=sz:raise ValueError('size')
  sk[ds:ds+sz]=raw;prev=ds+sz
 if p!=len(rep):raise ValueError('trailing')
 return bytes(sk)
