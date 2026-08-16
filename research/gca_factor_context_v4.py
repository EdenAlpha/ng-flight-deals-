#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
import numpy as np,zlib,struct,time
from pathlib import Path
from numba import njit
@njit
def emit(out,pos,b):
 if b:out[pos>>3]|=np.uint8(1<<(7-(pos&7)))
 return pos+1
@njit
def read(inp,pos,nb):
 if pos>=nb:return 0,pos+1
 return int((inp[pos>>3]>>(7-(pos&7)))&1),pos+1
@njit
def ac_mag_enc(R,C,maxbytes):
 NI,NX,NT=R.shape;K=C+2;base=C+3;nc=base**5;c=np.ones((nc,K),np.int32);tot=np.full(nc,K,np.int32)
 S=C+2;MS=np.empty((NI,NX,NT),np.int8);out=np.zeros(maxbytes,np.uint8);pos=0;low=np.uint64(0);high=np.uint64(0xffffffff);H=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xc0000000);pend=0
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    t1=int(MS[i,j,t-1]) if t>0 else S;t2=int(MS[i,j,t-2]) if t>1 else S;x=int(MS[i,j-1,t]) if j>0 else S;ii=int(MS[i-1,j,t]) if i>0 else S;d=int(MS[i-1,j-1,t]) if i>0 and j>0 else S
    ctx=((((t1*base+t2)*base+x)*base+ii)*base+d);a=abs(int(R[i,j,t]));s=a if a<=C else C+1
    cum=0
    for q in range(s):cum+=c[ctx,q]
    f=c[ctx,s];rng=high-low+np.uint64(1);high=low+(rng*np.uint64(cum+f))//np.uint64(tot[ctx])-np.uint64(1);low=low+(rng*np.uint64(cum))//np.uint64(tot[ctx])
    while True:
     if high<H:
      pos=emit(out,pos,0)
      for _ in range(pend):pos=emit(out,pos,1)
      pend=0
     elif low>=H:
      pos=emit(out,pos,1)
      for _ in range(pend):pos=emit(out,pos,0)
      pend=0;low-=H;high-=H
     elif low>=Q1 and high<Q3:pend+=1;low-=Q1;high-=Q1
     else:break
     low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1)
    MS[i,j,t]=s;c[ctx,s]+=1;tot[ctx]+=1
    if tot[ctx]>=2048:
     tt=0
     for q in range(K):c[ctx,q]=(c[ctx,q]+1)//2;tt+=c[ctx,q]
     tot[ctx]=tt
 pend+=1
 if low<Q1:
  pos=emit(out,pos,0)
  for _ in range(pend):pos=emit(out,pos,1)
 else:
  pos=emit(out,pos,1)
  for _ in range(pend):pos=emit(out,pos,0)
 return out,pos,MS
@njit
def ac_mag_dec(inp,nbits,NI,NX,NT,C):
 K=C+2;base=C+3;nc=base**5;c=np.ones((nc,K),np.int32);tot=np.full(nc,K,np.int32);S=C+2;MS=np.empty((NI,NX,NT),np.int8)
 pos=0;low=np.uint64(0);high=np.uint64(0xffffffff);code=np.uint64(0);H=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xc0000000)
 for _ in range(32):b,pos=read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    t1=int(MS[i,j,t-1]) if t>0 else S;t2=int(MS[i,j,t-2]) if t>1 else S;x=int(MS[i,j-1,t]) if j>0 else S;ii=int(MS[i-1,j,t]) if i>0 else S;d=int(MS[i-1,j-1,t]) if i>0 and j>0 else S
    ctx=((((t1*base+t2)*base+x)*base+ii)*base+d);rng=high-low+np.uint64(1);v=((code-low+np.uint64(1))*np.uint64(tot[ctx])-np.uint64(1))//rng;cum=0;s=0
    for q in range(K):
     nx=cum+c[ctx,q]
     if v<np.uint64(nx):s=q;break
     cum=nx
    f=c[ctx,s];high=low+(rng*np.uint64(cum+f))//np.uint64(tot[ctx])-np.uint64(1);low=low+(rng*np.uint64(cum))//np.uint64(tot[ctx])
    while True:
     if high<H:pass
     elif low>=H:low-=H;high-=H;code-=H
     elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
     else:break
     low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1);b,pos=read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
    MS[i,j,t]=s;c[ctx,s]+=1;tot[ctx]+=1
    if tot[ctx]>=2048:
     tt=0
     for q in range(K):c[ctx,q]=(c[ctx,q]+1)//2;tt+=c[ctx,q]
     tot[ctx]=tt
 return MS,pos
@njit
def ac_sign_enc(R,maxbytes):
 NI,NX,NT=R.shape;c=np.ones((4**5,2),np.int32);tot=np.full(4**5,2,np.int32);SS=np.empty((NI,NX,NT),np.int8);out=np.zeros(maxbytes,np.uint8);pos=0;low=np.uint64(0);high=np.uint64(0xffffffff);H=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xc0000000);pend=0
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    r=int(R[i,j,t]);state=1 if r==0 else (2 if r>0 else 0)
    if r!=0:
     t1=int(SS[i,j,t-1]) if t>0 else 3;t2=int(SS[i,j,t-2]) if t>1 else 3;x=int(SS[i,j-1,t]) if j>0 else 3;ii=int(SS[i-1,j,t]) if i>0 else 3;d=int(SS[i-1,j-1,t]) if i>0 and j>0 else 3;ctx=((((t1*4+t2)*4+x)*4+ii)*4+d);s=1 if r>0 else 0
     f0=c[ctx,0];f=c[ctx,s];cum=0 if s==0 else f0;rng=high-low+np.uint64(1);high=low+(rng*np.uint64(cum+f))//np.uint64(tot[ctx])-np.uint64(1);low=low+(rng*np.uint64(cum))//np.uint64(tot[ctx])
     while True:
      if high<H:
       pos=emit(out,pos,0)
       for _ in range(pend):pos=emit(out,pos,1)
       pend=0
      elif low>=H:
       pos=emit(out,pos,1)
       for _ in range(pend):pos=emit(out,pos,0)
       pend=0;low-=H;high-=H
      elif low>=Q1 and high<Q3:pend+=1;low-=Q1;high-=Q1
      else:break
      low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1)
     c[ctx,s]+=1;tot[ctx]+=1
     if tot[ctx]>=256:c[ctx,0]=(c[ctx,0]+1)//2;c[ctx,1]=(c[ctx,1]+1)//2;tot[ctx]=c[ctx,0]+c[ctx,1]
    SS[i,j,t]=state
 pend+=1
 if low<Q1:
  pos=emit(out,pos,0)
  for _ in range(pend):pos=emit(out,pos,1)
 else:
  pos=emit(out,pos,1)
  for _ in range(pend):pos=emit(out,pos,0)
 return out,pos
@njit
def ac_sign_dec(inp,nbits,MS):
 NI,NX,NT=MS.shape;c=np.ones((4**5,2),np.int32);tot=np.full(4**5,2,np.int32);SS=np.empty((NI,NX,NT),np.int8);SG=np.zeros((NI,NX,NT),np.int8);pos=0;low=np.uint64(0);high=np.uint64(0xffffffff);code=np.uint64(0);H=np.uint64(0x80000000);Q1=np.uint64(0x40000000);Q3=np.uint64(0xc0000000)
 for _ in range(32):b,pos=read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    if MS[i,j,t]!=0:
     t1=int(SS[i,j,t-1]) if t>0 else 3;t2=int(SS[i,j,t-2]) if t>1 else 3;x=int(SS[i,j-1,t]) if j>0 else 3;ii=int(SS[i-1,j,t]) if i>0 else 3;d=int(SS[i-1,j-1,t]) if i>0 and j>0 else 3;ctx=((((t1*4+t2)*4+x)*4+ii)*4+d);rng=high-low+np.uint64(1);v=((code-low+np.uint64(1))*np.uint64(tot[ctx])-np.uint64(1))//rng;s=0 if v<np.uint64(c[ctx,0]) else 1;cum=0 if s==0 else c[ctx,0];f=c[ctx,s];high=low+(rng*np.uint64(cum+f))//np.uint64(tot[ctx])-np.uint64(1);low=low+(rng*np.uint64(cum))//np.uint64(tot[ctx])
     while True:
      if high<H:pass
      elif low>=H:low-=H;high-=H;code-=H
      elif low>=Q1 and high<Q3:low-=Q1;high-=Q1;code-=Q1
      else:break
      low<<=np.uint64(1);high=(high<<np.uint64(1))+np.uint64(1);b,pos=read(inp,pos,nbits);code=(code<<np.uint64(1))|np.uint64(b)
     SG[i,j,t]=1 if s else -1;SS[i,j,t]=2 if s else 0;c[ctx,s]+=1;tot[ctx]+=1
     if tot[ctx]>=256:c[ctx,0]=(c[ctx,0]+1)//2;c[ctx,1]=(c[ctx,1]+1)//2;tot[ctx]=c[ctx,0]+c[ctx,1]
    else:SS[i,j,t]=1
 return SG,pos
@njit
def gamma_len(n):
 L=0
 while n>0:L+=1;n>>=1
 return 2*L-1
@njit
def tailbits(R,C):
 b=0
 NI,NX,NT=R.shape
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    a=abs(int(R[i,j,t]))
    if a>C:b+=gamma_len(a-C)
 return b
@njit
def tail_enc(R,C,total):
 out=np.zeros((total+7)//8,np.uint8);pos=0
 NI,NX,NT=R.shape
 for t in range(NT):
  for i in range(NI):
   for j in range(NX):
    a=abs(int(R[i,j,t]))
    if a>C:
     g=a-C;L=0;x=g
     while x>0:L+=1;x>>=1
     for _ in range(L-1):pos=emit(out,pos,0)
     for sh in range(L-1,-1,-1):pos=emit(out,pos,(g>>sh)&1)
 return out,pos
@njit
def tail_dec(inp,nbits,n):
 out=np.empty(n,np.int32);pos=0
 for k in range(n):
  z=0
  while True:
   b,pos=read(inp,pos,nbits)
   if b:break
   z+=1
  g=1
  for _ in range(z):b,pos=read(inp,pos,nbits);g=(g<<1)|b
  out[k]=g
 return out,pos

def load_regular_ieee_segy(path):
    p=Path(path); size=p.stat().st_size
    with p.open('rb') as f:
        hdr=f.read(3600)
        if len(hdr)!=3600: raise ValueError('short SEG-Y header')
        ns=int.from_bytes(hdr[3220:3222],'big'); fmt=int.from_bytes(hdr[3224:3226],'big')
        if ns<=0 or fmt!=5: raise ValueError(('require IEEE float32 SEG-Y',ns,fmt))
        stride=240+4*ns; rem=size-3600
        if rem<=0 or rem%stride: raise ValueError('non-regular fixed trace length')
        ntr=rem//stride; coords=[]; traces=[]
        for k in range(ntr):
            th=f.read(240); il=int.from_bytes(th[188:192],'big',signed=True); xl=int.from_bytes(th[192:196],'big',signed=True)
            b=f.read(4*ns)
            if len(b)!=4*ns: raise EOFError(k)
            coords.append((il,xl)); traces.append(np.frombuffer(b,dtype='>f4').astype(np.float32))
    ils=sorted(set(a for a,b in coords)); xls=sorted(set(b for a,b in coords))
    if len(ils)*len(xls)!=ntr: raise ValueError(('not complete regular inline/xline grid',len(ils),len(xls),ntr))
    im={v:i for i,v in enumerate(ils)}; xm={v:i for i,v in enumerate(xls)}
    X=np.empty((len(ils),len(xls),ns),np.float32); seen=set()
    for c,a in zip(coords,traces):
        if c in seen: raise ValueError(('duplicate coordinate',c))
        seen.add(c); X[im[c[0]],xm[c[1]]]=a
    return X, {'source_bytes':size,'format_code':fmt,'inlines':len(ils),'xlines':len(xls),'samples_per_trace':ns,'traces':ntr,
               'inline_min':ils[0],'inline_max':ils[-1],'xline_min':xls[0],'xline_max':xls[-1]}

def specs():
    return [('zero',0)]+[('x',d) for d in range(-4,5)]+[('i',d) for d in range(-4,5)]+[('x2',d) for d in range(-2,3)]+[('i2',d) for d in range(-2,3)]+[('ix',d) for d in range(-2,3)]

def legal_predict(X,eps):
    NI,NX,NT=X.shape; idx=np.arange(NT); sp=specs(); Q=np.empty((NI,NX,NT),np.int32); R=np.empty_like(Q); M=np.empty((NI,NX),np.uint8)
    def sh(a,d): return a[np.clip(idx+d,0,NT-1)]
    def pred(i,j,s):
        k,d=s
        if k=='zero': return np.zeros(NT,np.int32)
        if k=='x': return None if j<1 else sh(Q[i,j-1],d)
        if k=='i': return None if i<1 else sh(Q[i-1,j],d)
        if k=='x2': return None if j<2 else 2*sh(Q[i,j-1],d)-sh(Q[i,j-2],d)
        if k=='i2': return None if i<2 else 2*sh(Q[i-1,j],d)-sh(Q[i-2,j],d)
        if k=='ix': return None if i<1 or j<1 else sh(Q[i,j-1],d)+sh(Q[i-1,j],d)-sh(Q[i-1,j-1],d)
    for i in range(NI):
        for j in range(NX):
            x=X[i,j].astype(np.float64); lo=np.ceil((x-eps)/eps-1e-12).astype(np.int32); hi=np.floor((x+eps)/eps+1e-12).astype(np.int32)
            best=None; bs=None
            for m,s in enumerate(sp):
                p=pred(i,j,s)
                if p is None: continue
                q=np.minimum(np.maximum(p,lo),hi).astype(np.int32); r=q-p; ar=np.abs(r.astype(np.int64)); score=(int(np.count_nonzero(r)),int(ar.sum()),int(np.dot(ar,ar)))
                if bs is None or score<bs: bs=score; best=(m,q,r)
            m,q,r=best; M[i,j]=m; Q[i,j]=q; R[i,j]=r
    return Q,R,M

def rebuild_q(R,M):
    NI,NX,NT=R.shape; idx=np.arange(NT); sp=specs(); Q=np.empty_like(R)
    def sh(a,d): return a[np.clip(idx+d,0,NT-1)]
    def pred(i,j,s):
        k,d=s
        if k=='zero': return np.zeros(NT,np.int32)
        if k=='x': return sh(Q[i,j-1],d)
        if k=='i': return sh(Q[i-1,j],d)
        if k=='x2': return 2*sh(Q[i,j-1],d)-sh(Q[i,j-2],d)
        if k=='i2': return 2*sh(Q[i-1,j],d)-sh(Q[i-2,j],d)
        return sh(Q[i,j-1],d)+sh(Q[i-1,j],d)-sh(Q[i-1,j-1],d)
    for i in range(NI):
        for j in range(NX): Q[i,j]=pred(i,j,sp[int(M[i,j])])+R[i,j]
    return Q

def encode_array(X,eps,C=3):
    NI,NX,NT=X.shape; Q,R,M=legal_predict(X,eps)
    mb,mbits,MS=ac_mag_enc(R,C,max(1024,int(R.size*2))); mb=mb[:(mbits+7)//8]
    sb,sbits=ac_sign_enc(R,max(1024,int(R.size//2+1024))); sb=sb[:(sbits+7)//8]
    tb=int(tailbits(R,C)); tbuff,tused=tail_enc(R,C,tb); assert int(tused)==tb
    modez=zlib.compress(M.tobytes(),6)
    h=struct.pack('<4sBHHHdBIQQQ',b'GCA4',4,NI,NX,NT,float(eps),C,len(modez),int(mbits),int(sbits),tb)
    blob=h+bytes(64-len(h))+modez+mb.tobytes()+sb.tobytes()+tbuff.tobytes()
    return blob, {'Q':Q,'R':R,'M':M,'zero_fraction':float(np.mean(R==0)),'abs_le_2_fraction':float(np.mean(np.abs(R.astype(np.int64))<=2)),
                  'mag_bytes':len(mb),'sign_bytes':len(sb),'tail_bytes':len(tbuff),'mode_bytes':len(modez)}

def decode_array(blob):
    fmt='<4sBHHHdBIQQQ'; n=struct.calcsize(fmt); magic,ver,NI,NX,NT,eps,C,nmode,mbits,sbits,tbits=struct.unpack(fmt,blob[:n])
    if magic!=b'GCA4' or ver!=4: raise ValueError('bad GCA4 stream')
    off=64; M=np.frombuffer(zlib.decompress(blob[off:off+nmode]),np.uint8).reshape(NI,NX); off+=nmode
    mbytes=(mbits+7)//8; mb=np.frombuffer(blob[off:off+mbytes],np.uint8); off+=mbytes
    sbytes=(sbits+7)//8; sb=np.frombuffer(blob[off:off+sbytes],np.uint8); off+=sbytes
    tbuff=np.frombuffer(blob[off:],np.uint8)
    MS,_=ac_mag_dec(mb,int(mbits),NI,NX,NT,C); SG,_=ac_sign_dec(sb,int(sbits),MS)
    nt=int(np.count_nonzero(MS==C+1)); tv,_=tail_dec(tbuff,int(tbits),nt)
    R=np.zeros((NI,NX,NT),np.int32); ti=0
    for t in range(NT):
        for i in range(NI):
            for j in range(NX):
                m=int(MS[i,j,t])
                if m==0: continue
                a=m
                if m==C+1: a=C+int(tv[ti]); ti+=1
                R[i,j,t]=a*int(SG[i,j,t])
    Q=rebuild_q(R,M); return Q.astype(np.float64)*eps, {'Q':Q,'R':R,'M':M,'epsilon':eps}

def run(path,stream=None,json_path=None):
    X,src=load_regular_ieee_segy(path); std=float(X.astype(np.float64).std()); eps=.1*std
    t=time.time(); blob,em=encode_array(X,eps); enc=time.time()-t
    t=time.time(); Y,dm=decode_array(blob); dec=time.time()-t
    if not np.array_equal(em['Q'],dm['Q']) or not np.array_equal(em['R'],dm['R']): raise RuntimeError('decoder mismatch')
    me=float(np.max(np.abs(X.astype(np.float64)-Y)))
    if me>eps*(1+3e-7): raise RuntimeError(('hard bound',me,eps))
    out={'engine':'gca_factor_context_v4','source':src,'shape':list(X.shape),'samples':int(X.size),'numeric_bytes':int(X.nbytes),'std':std,'epsilon':eps,
         'gca4_bytes':len(blob),'gca4_bps':8*len(blob)/X.size,'numeric_ratio':X.nbytes/len(blob),'maxerr':me,'decoder_valid':True,
         'encode_seconds':enc,'decode_seconds':dec,'zero_fraction':em['zero_fraction'],'abs_le_2_fraction':em['abs_le_2_fraction'],
         'component_bytes':{k:em[k] for k in ('mag_bytes','sign_bytes','tail_bytes','mode_bytes')},'dataset_label_used_for_routing':False}
    if stream: Path(stream).write_bytes(blob)
    txt=json.dumps(out,indent=2); print(txt)
    if json_path: Path(json_path).write_text(txt)
    return out

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('segy'); ap.add_argument('--stream'); ap.add_argument('--json'); a=ap.parse_args(); run(a.segy,a.stream,a.json)
