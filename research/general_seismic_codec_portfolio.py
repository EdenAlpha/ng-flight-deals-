import json, math, struct
import numpy as np
import zstandard as zstd

ZC=zstd.ZstdCompressor(level=19); ZD=zstd.ZstdDecompressor()
MAX=(1<<32)-1; HALF=1<<31; Q1=1<<30; Q3=3<<30

class BO:
 def __init__(self): self.a=[]
 def put(self,b): self.a.append(int(b))
 def finish(self):
  out=bytearray((len(self.a)+7)//8)
  for i,b in enumerate(self.a):
   if b: out[i>>3]|=1<<(7-(i&7))
  return bytes(out),len(self.a)
class BI:
 def __init__(self,d,n): self.d=d; self.n=int(n); self.i=0
 def get(self):
  if self.i>=self.n:return 0
  b=(self.d[self.i>>3]>>(7-(self.i&7)))&1; self.i+=1; return b
class AE:
 def __init__(self,nctx): self.lo=0;self.hi=MAX;self.pending=0;self.o=BO();self.c=np.ones((int(nctx),2),np.int32)
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending): self.o.put(1-b)
  self.pending=0
 def put(self,b,ctx):
  c0=int(self.c[ctx,0]);c1=int(self.c[ctx,1]);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if b==0:self.hi=sp
  else:self.lo=sp+1
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1
  self.c[ctx,b]+=1
  if int(self.c[ctx].sum())>16384:self.c[ctx]=(self.c[ctx]+1)//2
 def finish(self):
  self.pending+=1; self.emit(0 if self.lo<Q1 else 1); return self.o.finish()
class AD:
 def __init__(self,d,n,nctx):
  self.lo=0;self.hi=MAX;self.i=BI(d,n);self.v=0;self.c=np.ones((int(nctx),2),np.int32)
  for _ in range(32):self.v=((self.v<<1)&MAX)|self.i.get()
 def get(self,ctx):
  c0=int(self.c[ctx,0]);c1=int(self.c[ctx,1]);tot=c0+c1;rng=self.hi-self.lo+1;sp=self.lo+(rng*c0//tot)-1
  if self.v<=sp:b=0;self.hi=sp
  else:b=1;self.lo=sp+1
  while True:
   if self.hi<HALF:pass
   elif self.lo>=HALF:self.lo-=HALF;self.hi-=HALF;self.v-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.lo-=Q1;self.hi-=Q1;self.v-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1;self.v=((self.v<<1)&MAX)|self.i.get()
  self.c[ctx,b]+=1
  if int(self.c[ctx].sum())>16384:self.c[ctx]=(self.c[ctx]+1)//2
  return b

NZERO=9*9*6; NSIGN=3*3*6; NPREF=6*6*16; NSUFF=16*16*6
OFF_SIGN=NZERO; OFF_PREF=OFF_SIGN+NSIGN; OFF_SUFF=OFF_PREF+NPREF; NCTX=OFF_SUFF+NSUFF

def clip4(x):return int(max(-4,min(4,int(x))))+4
def ac_state(sumabs,count):
 if count<=0:return 0
 z=2*int(sumabs)
 for i,q in enumerate((1,3,7,15,31)):
  if z<=q*count:return i
 return 5
def sgncat(x):x=int(x);return 0 if x<0 else (2 if x>0 else 1)
def magbin(x):
 x=abs(int(x))
 if x==0:return 0
 if x==1:return 1
 if x==2:return 2
 if x<=4:return 3
 if x<=8:return 4
 return 5
def zero_ctx(prev,left,ac):return ((clip4(prev)*9+clip4(left))*6+ac)
def sign_ctx(prev,left,ac):return OFF_SIGN+((sgncat(prev)*3+sgncat(left))*6+ac)
def pref_ctx(prev,ac,qpos):return OFF_PREF+((magbin(prev)*6+ac)*16+min(qpos,15))
def suff_ctx(q,bitpos,ac):return OFF_SUFF+((min(q,15)*16+min(bitpos,15))*6+ac)

def encode_zsm(K,W):
 K=np.asarray(K,np.int32);nr,nt=K.shape;W=int(W);E=AE(NCTX);ring=np.zeros((nr,W),np.int32);sums=np.zeros(nr,np.int64)
 for t in range(nt):
  rp=t%W;cnt=min(t,W)
  for c in range(nr):
   ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;k=int(K[c,t]);iszero=1 if k==0 else 0
   E.put(iszero,zero_ctx(prev,left,ac))
   if not iszero:
    E.put(1 if k<0 else 0,sign_ctx(prev,left,ac));mag=abs(k);q=mag.bit_length()-1
    for j in range(q):E.put(0,pref_ctx(prev,ac,j))
    E.put(1,pref_ctx(prev,ac,q));rem=mag-(1<<q)
    for bp in range(q-1,-1,-1):E.put((rem>>bp)&1,suff_ctx(q,q-1-bp,ac))
   old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
 return E.finish()

def decode_zsm(bb,nbit,W,shape):
 nr,nt=map(int,shape);W=int(W);D=AD(bb,nbit,NCTX);K=np.zeros((nr,nt),np.int32);ring=np.zeros((nr,W),np.int32);sums=np.zeros(nr,np.int64)
 for t in range(nt):
  rp=t%W;cnt=min(t,W)
  for c in range(nr):
   ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;iszero=D.get(zero_ctx(prev,left,ac))
   if iszero:k=0
   else:
    neg=D.get(sign_ctx(prev,left,ac));q=0
    while True:
     b=D.get(pref_ctx(prev,ac,q))
     if b:break
     q+=1
     if q>30:raise RuntimeError(('gamma overflow',c,t))
    rem=0
    for pos in range(q):rem=(rem<<1)|D.get(suff_ctx(q,pos,ac))
    mag=(1<<q)+rem;k=-mag if neg else mag
   K[c,t]=int(k);old=int(ring[c,rp]);new=abs(int(k));ring[c,rp]=new;sums[c]+=new-old
 return K

AR_MAGIC=b'GSARZSM1'; AR_HDR='<8sBBHIIIIdQQ'; AR_HSZ=struct.calcsize(AR_HDR)
def design_ar(X,p,train):
 X=np.asarray(X,np.float64);nr,nt=X.shape;train=min(int(train),nt)
 if train<=p:raise ValueError('not enough samples for AR fit')
 A=np.empty((nr*(train-p),p+1),np.float64);y=np.empty(nr*(train-p),np.float64);j=0
 for c in range(nr):
  x=X[c,:train]
  for t in range(p,train):A[j,0]=1.;A[j,1:]=x[t-p:t][::-1];y[j]=x[t];j+=1
 return A,y
def fit_huber_ar(X,p=32,train=1024,delta=1.,iterations=6):
 A,y=design_ar(X,p,train);co=np.linalg.lstsq(A,y,rcond=None)[0];delta=max(float(delta),np.finfo(np.float64).tiny)
 for _ in range(int(iterations)):
  r=y-A@co;w=np.minimum(1.,delta/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 return np.asarray(co,np.float32)
def ar_step(eps,source_integer):
 eps=float(eps)
 if not np.isfinite(eps) or eps<=0:raise ValueError('epsilon must be finite and positive')
 s=int(math.floor(2.*eps))
 if source_integer and s>=1:return 1,float(s)
 return 0,float(np.nextafter(2.*eps,0.))
def ar_quantize(X,co,p,step,integer_mode):
 X=np.asarray(X,np.float64);nr,nt=X.shape;K=np.zeros((nr,nt),np.int32);R=np.zeros((nr,nt),np.int64 if integer_mode else np.float64);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(nt):
  if t<p:pred=np.zeros(nr,np.float64)
  else:
   pred=a+np.asarray(R[:,t-p:t][:,::-1],np.float32)@b
   if integer_mode:pred=np.rint(pred)
  k=np.rint((X[:,t]-pred)/step).astype(np.int64)
  if np.any(k<np.iinfo(np.int32).min) or np.any(k>np.iinfo(np.int32).max):raise OverflowError('AR correction exceeds int32')
  K[:,t]=k.astype(np.int32)
  if integer_mode:R[:,t]=pred.astype(np.int64)+int(round(step))*k
  else:R[:,t]=pred+step*k
 return R,K
def ar_reconstruct(K,co,p,step,integer_mode):
 K=np.asarray(K,np.int32);nr,nt=K.shape;R=np.zeros((nr,nt),np.int64 if integer_mode else np.float64);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(nt):
  if t<p:pred=np.zeros(nr,np.float64)
  else:
   pred=a+np.asarray(R[:,t-p:t][:,::-1],np.float32)@b
   if integer_mode:pred=np.rint(pred)
  if integer_mode:R[:,t]=pred.astype(np.int64)+int(round(step))*K[:,t].astype(np.int64)
  else:R[:,t]=pred+step*K[:,t].astype(np.float64)
 return R
def encode_ar_zsm(X,eps,W,p=32,train=1024,iterations=6,source_integer=False):
 X=np.asarray(X);nr,nt=X.shape;mode,step=ar_step(eps,bool(source_integer));co=fit_huber_ar(X,p,min(train,nt),step,iterations);R,K=ar_quantize(X,co,p,step,mode==1);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
 if me>float(eps):raise RuntimeError(('AR hard bound',me,float(eps)))
 bb,nbit=encode_zsm(K,int(W));cob=np.asarray(co,dtype='<f4').tobytes();hdr=struct.pack(AR_HDR,AR_MAGIC,1,mode,int(p),int(nr),int(nt),int(min(train,nt)),int(W),float(step),int(nbit),len(bb))
 return hdr+cob+bb,{'maxerr':me,'zero_fraction':float(np.mean(K==0)),'step':step}
def decode_ar_zsm(blob):
 magic,ver,mode,p,nr,nt,train,W,step,nbit,plen=struct.unpack(AR_HDR,blob[:AR_HSZ])
 if magic!=AR_MAGIC or ver!=1:raise RuntimeError('bad AR stream')
 pos=AR_HSZ;cbytes=4*(int(p)+1);co=np.frombuffer(blob[pos:pos+cbytes],dtype='<f4').copy();pos+=cbytes;bb=blob[pos:pos+plen]
 if len(bb)!=plen or pos+plen!=len(blob):raise RuntimeError('AR length mismatch')
 return ar_reconstruct(decode_zsm(bb,nbit,W,(nr,nt)),co,int(p),float(step),int(mode)==1)

SP_MAGIC=b'GSTOPN01'; SP_HDR='<8sBIIIIIdBBQQQQQ'; SP_HSZ=struct.calcsize(SP_HDR); IDT={1:np.dtype('<i1'),2:np.dtype('<i2'),3:np.dtype('<i4')}
def z(b):return ZC.compress(b)
def pack_int(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;code=1 if lo>=-128 and hi<=127 else 2 if lo>=-32768 and hi<=32767 else 3
 return code,z(np.ascontiguousarray(a.astype(IDT[code],copy=False)).tobytes())
def unpack_int(blob,code,n):
 a=np.frombuffer(ZD.decompress(blob),dtype=IDT[int(code)],count=int(n))
 if a.size!=int(n):raise RuntimeError('int stream mismatch')
 return a.astype(np.int32,copy=False)
def fwd(W):return np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
def inv(F,B):return np.fft.irfft(np.fft.ifft(F,axis=0),n=int(B),axis=1).real.astype(np.float32)
def encode_spectral_topn(X,eps,B,frac):
 X=np.asarray(X,np.float32);nr,nt=X.shape;B=int(B);frac=float(frac);nblk=(nt+B-1)//B;step=float(np.nextafter(2.*float(eps),0.));idxs=[];vals=[];scales=[];P=np.zeros_like(X);N=None
 for bi in range(nblk):
  t0=bi*B;m=min(B,nt-t0);W=np.zeros((nr,B),np.float32);W[:,:m]=X[:,t0:t0+m];F=fwd(W);flat=F.reshape(-1);NN=max(1,min(flat.size,int(round(frac*flat.size))));N=NN if N is None else N
  if NN!=N:raise RuntimeError('N changed')
  ix=np.argpartition(np.abs(flat),-N)[-N:];ix=np.sort(ix).astype(np.uint32);v=flat[ix];comp=np.stack([v.real,v.imag],axis=1);sd=np.float32(max(float(np.max(np.abs(comp)))/127.,1e-30));q=np.clip(np.rint(comp/sd),-127,127).astype(np.int8);vq=(q[:,0].astype(np.float32)+1j*q[:,1].astype(np.float32))*sd;fq=np.zeros(flat.size,np.complex64);fq[ix.astype(np.int64)]=vq;rec=inv(fq.reshape(F.shape),B);P[:,t0:t0+m]=rec[:,:m];idxs.append(ix);vals.append(q);scales.append(sd)
 iz=z(np.concatenate(idxs).astype('<u4',copy=False).tobytes());vz=z(np.concatenate(vals,axis=0).astype(np.int8,copy=False).tobytes());szb=z(np.asarray(scales,dtype='<f4').tobytes());Q=np.rint((X.astype(np.float64)-P.astype(np.float64))/step).astype(np.int64)
 if np.any(Q<np.iinfo(np.int32).min) or np.any(Q>np.iinfo(np.int32).max):raise OverflowError('spectral correction exceeds int32')
 Q=Q.astype(np.int32);opts=[];dc,a=pack_int(Q);opts.append((len(a),0,dc,a,b''));K=Q.copy();K[:,1:]-=Q[:,:-1];dc,a=pack_int(K);opts.append((len(a),1,dc,a,b''));mask=K!=0;mz=z(np.packbits(mask.ravel(),bitorder='little').tobytes());dc,vv=pack_int(K[mask]);opts.append((len(mz)+len(vv),2,dc,mz,vv));_,cm,dc,ca,cb=min(opts,key=lambda q:(q[0],q[1]));hdr=struct.pack(SP_HDR,SP_MAGIC,1,int(nr),int(nt),int(B),int(N),int(nblk),float(step),int(cm),int(dc),len(iz),len(vz),len(szb),len(ca),len(cb));blob=hdr+iz+vz+szb+ca+cb;R=decode_spectral_topn(blob);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
 if me>float(eps):raise RuntimeError(('spectral hard bound',me,float(eps)))
 return blob,{'maxerr':me,'event_fraction':float(mask.mean()),'step':step}
def decode_spectral_topn(blob):
 vals=struct.unpack(SP_HDR,blob[:SP_HSZ]);magic,ver,nr,nt,B,N,nblk,step,cm,dc,*lens=vals
 if magic!=SP_MAGIC or ver!=1:raise RuntimeError('bad spectral stream')
 pos=SP_HSZ;ss=[]
 for L in lens:ss.append(blob[pos:pos+L]);pos+=L
 if pos!=len(blob):raise RuntimeError('spectral length mismatch')
 iz,vz,szb,ca,cb=ss;count=int(nblk)*int(N);ix=np.frombuffer(ZD.decompress(iz),dtype='<u4',count=count);q=np.frombuffer(ZD.decompress(vz),dtype=np.int8,count=2*count).reshape(count,2);sc=np.frombuffer(ZD.decompress(szb),dtype='<f4',count=int(nblk));P=np.zeros((int(nr),int(nt)),np.float32);shape=(int(nr),int(B)//2+1);M=int(np.prod(shape))
 for bi in range(int(nblk)):
  sl=slice(bi*int(N),(bi+1)*int(N));ii=ix[sl].astype(np.int64);qq=q[sl];v=(qq[:,0].astype(np.float32)+1j*qq[:,1].astype(np.float32))*np.float32(sc[bi]);F=np.zeros(M,np.complex64);F[ii]=v;rec=inv(F.reshape(shape),int(B));t0=bi*int(B);m=min(int(B),int(nt)-t0);P[:,t0:t0+m]=rec[:,:m]
 total=int(nr)*int(nt)
 if int(cm)==0:Q=unpack_int(ca,dc,total).reshape(int(nr),int(nt))
 elif int(cm)==1:Q=np.cumsum(unpack_int(ca,dc,total).reshape(int(nr),int(nt)),axis=1,dtype=np.int32)
 elif int(cm)==2:
  mask=np.unpackbits(np.frombuffer(ZD.decompress(ca),np.uint8),bitorder='little',count=total).astype(bool);vv=unpack_int(cb,dc,int(mask.sum()));K=np.zeros(total,np.int32);K[mask]=vv;Q=np.cumsum(K.reshape(int(nr),int(nt)),axis=1,dtype=np.int32)
 else:raise RuntimeError('bad correction mode')
 return P.astype(np.float64)+Q.astype(np.float64)*float(step)

def load_config(path):return json.load(open(path))
def candidate_blob(X,eps,cand,source_integer):
 if cand['engine']=='ar32_zsm':return encode_ar_zsm(X,eps,int(cand['zsm_window']),int(cand.get('ar_order',32)),int(cand.get('train_samples',1024)),int(cand.get('huber_iterations',6)),bool(source_integer))
 if cand['engine']=='spectral_topn':return encode_spectral_topn(X,eps,int(cand['time_block']),float(cand['fraction']))
 raise ValueError(cand['engine'])
def screen_candidates(X,eps,cfg,source_integer=False):
 X=np.asarray(X);ns=min(int(cfg['selector']['screen_samples']),X.shape[1]);P=X[:,:ns]
 if ns<=32:raise ValueError('screen prefix too short')
 rows=[]
 for cand in sorted(cfg['candidates'],key=lambda c:int(c['id'])):
  try:
   bb,meta=candidate_blob(P,eps,cand,source_integer);rows.append({'id':int(cand['id']),'engine':cand['engine'],'bytes':len(bb),'samples':int(P.size),'bps':8.*len(bb)/P.size,'valid':True,'meta':meta})
  except Exception as e:rows.append({'id':int(cand['id']),'engine':cand['engine'],'bytes':None,'samples':int(P.size),'bps':float('inf'),'valid':False,'error':repr(e)})
 valid=[r for r in rows if r['valid']]
 if not valid:raise RuntimeError(('no valid candidate',rows))
 return min(valid,key=lambda r:(r['bps'],r['id'])),rows
def encode_portfolio(X,eps,cfg,source_integer=False):
 best,screen=screen_candidates(X,eps,cfg,source_integer);cand={int(c['id']):c for c in cfg['candidates']}[int(best['id'])];body,meta=candidate_blob(X,eps,cand,source_integer);blob=bytes([int(best['id'])])+body;R=decode_portfolio(blob);me=float(np.max(np.abs(np.asarray(X,np.float64)-np.asarray(R,np.float64))))
 if me>float(eps):raise RuntimeError(('portfolio hard bound',me,float(eps)))
 return blob,{'selected_id':int(best['id']),'selected_engine':cand['engine'],'screen':screen,'maxerr':me,'engine_meta':meta}
def decode_portfolio(blob):
 if not blob:raise RuntimeError('empty stream')
 body=blob[1:]
 if body.startswith(AR_MAGIC):return decode_ar_zsm(body)
 if body.startswith(SP_MAGIC):return decode_spectral_topn(body)
 raise RuntimeError(('unknown stream',int(blob[0]),body[:8]))
def self_test(config_path):
 cfg=load_config(config_path);rng=np.random.default_rng(12345);t=np.linspace(0,24*np.pi,4096);base=np.sin(t)+.35*np.sin(.19*t+.2);smooth=np.stack([base+.002*c+.02*rng.standard_normal(t.size) for c in range(16)]).astype(np.float32);ar=np.zeros((16,4096),np.int16);noise=rng.normal(0,35,ar.shape)
 for j in range(1,ar.shape[1]):ar[:,j]=np.clip(np.rint(.94*ar[:,j-1]+noise[:,j]),-30000,30000).astype(np.int16)
 out=[]
 for name,X,isint in [('smooth_float',smooth,False),('ar_integer',ar,True)]:
  eps=.1*float(np.asarray(X,np.float64).std());bb,meta=encode_portfolio(X,eps,cfg,isint);R=decode_portfolio(bb);me=float(np.max(np.abs(np.asarray(X,np.float64)-np.asarray(R,np.float64))))
  if me>eps:raise RuntimeError((name,me,eps))
  out.append({'name':name,'shape':list(X.shape),'eps':eps,'bytes':len(bb),'bps':8.*len(bb)/X.size,'selected_id':meta['selected_id'],'selected_engine':meta['selected_engine'],'maxerr':me,'screen':meta['screen']})
 return out
if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser();ap.add_argument('--self-test',action='store_true');ap.add_argument('--config',default='benchmarks/general_seismic_codec_portfolio_v1.json');args=ap.parse_args()
 if args.self_test:print(json.dumps(self_test(args.config),indent=2))
