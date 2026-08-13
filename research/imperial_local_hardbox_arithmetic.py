import bisect,json,math,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TB=1024;TRAIN=1024;P=32;STEP=267;AR_MODEL_BYTES=177
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30

class BO:
 def __init__(self):self.a=[]
 def put(self,b):self.a.append(int(b))
 def finish(self):
  z=bytearray((len(self.a)+7)//8)
  for i,b in enumerate(self.a):
   if b:z[i>>3]|=1<<(7-(i&7))
  return bytes(z),len(self.a)
class BI:
 def __init__(self,d,n):self.d=d;self.n=n;self.i=0
 def get(self):
  if self.i>=self.n:return 0
  b=(self.d[self.i>>3]>>(7-(self.i&7)))&1;self.i+=1;return b

class AE:
 def __init__(self,cum):self.lo=0;self.hi=MAX;self.pending=0;self.o=BO();self.cum=cum;self.tot=int(cum[-1])
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending):self.o.put(1-b)
  self.pending=0
 def put(self,s):
  rng=self.hi-self.lo+1;cl=int(self.cum[s]);ch=int(self.cum[s+1]);self.hi=self.lo+(rng*ch//self.tot)-1;self.lo=self.lo+(rng*cl//self.tot)
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1
 def finish(self):
  self.pending+=1
  if self.lo<Q1:self.emit(0)
  else:self.emit(1)
  return self.o.finish()
class AD:
 def __init__(self,d,n,cum):
  self.lo=0;self.hi=MAX;self.i=BI(d,n);self.v=0;self.cum=[int(x) for x in cum];self.tot=self.cum[-1]
  for _ in range(32):self.v=((self.v<<1)&MAX)|self.i.get()
 def get(self):
  rng=self.hi-self.lo+1;scaled=((self.v-self.lo+1)*self.tot-1)//rng;s=bisect.bisect_right(self.cum,scaled)-1
  cl=self.cum[s];ch=self.cum[s+1];self.hi=self.lo+(rng*ch//self.tot)-1;self.lo=self.lo+(rng*cl//self.tot)
  while True:
   if self.hi<HALF:pass
   elif self.lo>=HALF:self.lo-=HALF;self.hi-=HALF;self.v-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.lo-=Q1;self.hi-=Q1;self.v-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1;self.v=((self.v<<1)&MAX)|self.i.get()
  return s

def fit_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)
def run_ar(X,ar):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def optimal_partition(x,eps):
 counts=np.bincount((np.asarray(x,np.int16).astype(np.int32)+32768).ravel(),minlength=65536)
 vals=np.flatnonzero(counts).astype(np.int32)-32768;c=counts[counts>0].astype(np.int64);nval=len(vals);pref=np.zeros(nval+1,np.int64);pref[1:]=np.cumsum(c)
 dp=np.full(nval+1,-np.inf,np.float64);prev=np.full(nval+1,-1,np.int32);dp[0]=0.0;width=2.0*float(eps)
 for end in range(nval):
  lo=int(np.searchsorted(vals,vals[end]-width-1e-12,side='left'));starts=np.arange(lo,end+1,dtype=np.int32);n=(pref[end+1]-pref[starts]).astype(np.float64);score=dp[starts]+n*np.log2(n);j=int(np.argmax(score));dp[end+1]=score[j];prev[end+1]=int(starts[j])
 groups=[];e=nval
 while e>0:
  s=int(prev[e]);groups.append((int(vals[s]),int(vals[e-1]),int(pref[e]-pref[s])));e=s
 groups.reverse();return groups

def encode_tile(X,eps):
 groups=optimal_partition(X,eps);his=np.asarray([g[1] for g in groups],np.int32);centers2=np.asarray([g[0]+g[1] for g in groups],np.int32);counts=np.asarray([g[2] for g in groups],np.uint32)
 ids=np.searchsorted(his,np.asarray(X,np.int32).ravel(),side='left').astype(np.int32);cum=np.r_[0,np.cumsum(counts,dtype=np.uint64)]
 enc=AE(cum)
 for s in ids:enc.put(int(s))
 bb,nbit=enc.finish()
 # The target-adaptive static distribution is legal only because centers and exact counts are transmitted.
 modelraw=centers2.astype('<i4').tobytes()+counts.astype('<u4').tobytes();model=Z.compress(modelraw);total=len(model)+len(bb)+48
 mr=D.decompress(model);G=len(groups);c2=np.frombuffer(mr[:4*G],'<i4',count=G).astype(np.int32);cnt=np.frombuffer(mr[4*G:8*G],'<u4',count=G).astype(np.uint64);cd=np.r_[0,np.cumsum(cnt,dtype=np.uint64)]
 dec=AD(bb,nbit,cd);idd=np.empty(ids.size,np.int32)
 for i in range(ids.size):idd[i]=dec.get()
 if not np.array_equal(idd,ids):raise RuntimeError('arithmetic id decode')
 Rd=(c2[idd].astype(np.float64)*0.5).reshape(X.shape);me=float(np.max(np.abs(np.asarray(X,np.float64)-Rd)))
 if me>eps*(1+1e-12):raise RuntimeError(('hardbox arithmetic hard',me,eps))
 p=counts.astype(np.float64)/counts.sum();H=float(-np.sum(p*np.log2(p)))
 return {'bytes':int(total),'bps':float(8*total/X.size),'groups':G,'model_bytes':len(model)+32,'payload_bytes':len(bb)+16,'arithmetic_bits':int(nbit),'empirical_entropy_bps':H,'coding_over_entropy_bps':float(nbit/X.size-H),'maxerr':me}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T;XF=X.astype(np.float64);ar=fit_ar(XF);R,K=run_ar(XF,ar);me=float(np.max(np.abs(XF-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'AR hard',me,eps))
   arbytes=AR_MODEL_BYTES;art=[];scalar=[];sz=0
   for t0 in range(0,NT,TB):
    A=K[:,t0:t0+TB];n,rep,Kd=m.encode_k(A)
    if not np.array_equal(A,Kd):raise RuntimeError('AR K decode')
    arbytes+=n;art.append({'t0':t0,'bytes':n,'rep':rep})
    S=X[:,t0:t0+TB];q=encode_tile(S,eps);q['t0']=t0;scalar.append(q)
    b,_=m.szrun(S.astype(np.float64),eps);sz+=int(b)
   sb=sum(x['bytes'] for x in scalar);winner=min(arbytes,sb);row={'region':region,'c0':c0,'samples':int(X.size),'ar32':{'bytes':int(arbytes),'bps':float(8*arbytes/X.size),'gain_vs_sz3':float(sz/arbytes),'maxerr':me,'tiles':art},'local_hardbox_arithmetic':{'bytes':int(sb),'bps':float(8*sb/X.size),'gain_vs_sz3':float(sz/sb),'gain_vs_ar32':float(arbytes/sb),'tiles':scalar},'sz3_bytes':int(sz),'sz3_bps':float(8*sz/X.size),'winner':'scalar_arithmetic' if sb<arbytes else 'ar32','winner_bytes':int(winner),'winner_gain_vs_sz3':float(sz/winner)}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'tile_shape':[C,TB],'rows':rows,'scope':'Real-byte arithmetic follow-up to PR #398. Every 128x1024 source tile gets the exact target-adaptive entropy-minimizing contiguous scalar hard-box partition under the unchanged epsilon. Unlike Huffman, the symbol IDs are encoded by a real 32-bit static arithmetic coder using the exact empirical group counts. Because those probabilities are target-adaptive, both half-integer reconstruction centers and every group count are compressed, transmitted, byte-decoded and charged. The arithmetic stream is decoded back to exact IDs, the source reconstruction is hard-error verified, and model/payload/framing bytes are all counted. Persistent AR32 step267 and matched SZ3 are rerun on identical complete 128x8192 regions. Purpose: test whether the local scalar oracle survives without Huffman integer-length loss and can become a useful adaptive second codec language. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_local_hardbox_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
