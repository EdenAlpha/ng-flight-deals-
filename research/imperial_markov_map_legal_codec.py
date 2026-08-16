import json,sys,math,struct
from collections import Counter,defaultdict
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

T0=14488;C0=512;C=32;T=1024
HFACTORS=(1.5,1.0,0.75)
ALPHA=8
SAFETY=1-1e-6
FROZEN_STANDALONE_HYBRID=23018
TOP=(1<<64)-1;HALF=1<<63;Q1=1<<62;Q3=3<<62
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

class BW:
 def __init__(self):self.b=bytearray();self.cur=0;self.used=0;self.n=0
 def put(self,x):
  if x:self.cur|=1<<self.used
  self.used+=1;self.n+=1
  if self.used==8:self.b.append(self.cur);self.cur=0;self.used=0
 def finish(self):
  if self.used:self.b.append(self.cur)
  return bytes(self.b),self.n
class BR:
 def __init__(self,b,n):self.b=b;self.n=int(n);self.p=0
 def get(self):
  if self.p>=self.n:self.p+=1;return 0
  i=self.p;self.p+=1;return (self.b[i>>3]>>(i&7))&1
class AE:
 def __init__(self):self.lo=0;self.hi=TOP;self.pending=0;self.w=BW()
 def emit(self,b):
  self.w.put(b);q=1-b
  for _ in range(self.pending):self.w.put(q)
  self.pending=0
 def put(self,cum,freq,total):
  cum=int(cum);freq=int(freq);total=int(total);rng=self.hi-self.lo+1;old=self.lo
  self.lo=old+(rng*cum)//total;self.hi=old+(rng*(cum+freq))//total-1
  if self.hi<self.lo:raise RuntimeError(('range collapse',cum,freq,total,rng))
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&TOP;self.hi=((self.hi<<1)&TOP)|1
 def finish(self):self.pending+=1;self.emit(0 if self.lo<Q1 else 1);return self.w.finish()
class AD:
 def __init__(self,b,n):
  self.lo=0;self.hi=TOP;self.r=BR(b,n);self.code=0
  for _ in range(64):self.code=((self.code<<1)|self.r.get())&TOP
 def target(self,total):
  rng=self.hi-self.lo+1;return ((self.code-self.lo+1)*int(total)-1)//rng
 def take(self,cum,freq,total):
  cum=int(cum);freq=int(freq);total=int(total);rng=self.hi-self.lo+1;old=self.lo
  self.lo=old+(rng*cum)//total;self.hi=old+(rng*(cum+freq))//total-1
  while True:
   if self.hi<HALF:pass
   elif self.lo>=HALF:self.lo-=HALF;self.hi-=HALF;self.code-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.lo-=Q1;self.hi-=Q1;self.code-=Q1
   else:break
   self.lo=(self.lo<<1)&TOP;self.hi=((self.hi<<1)&TOP)|1;self.code=((self.code<<1)&TOP)|self.r.get()

def H(a):
 _,c=np.unique(np.asarray(a).ravel(),return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def nearest(x,h,phi):return np.rint((x-phi)/h).astype(np.int32)
def legal(x,bound,h,phi):
 lo=np.ceil((x-bound-phi)/h-1e-12).astype(np.int32);hi=np.floor((x+bound-phi)/h+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal interval')
 return lo,hi
def choose_phase(prev,h):
 tt=np.linspace(0,prev[0].shape[0]-1,512,dtype=np.int32);cc=np.linspace(0,prev[0].shape[1]-1,128,dtype=np.int32);best=None
 for k in range(8):
  phi=h*k/8;hs=[]
  for d in prev:
   x=np.asarray(d[tt,:],np.float64)[:,cc].ravel();hs.append(H(nearest(x,h,phi)))
  v=float(np.mean(hs))
  if best is None or v<best[0]:best=(v,phi,k)
 return best

def lse(v):
 if not v:return -math.inf
 z=max(v)
 if not math.isfinite(z):return -math.inf
 return z+math.log(sum(math.exp(x-z) for x in v))

class Markov:
 def __init__(self,seqs):
  allq=np.concatenate([np.asarray(s,np.int32) for s in seqs]);vals,cnt=np.unique(allq,return_counts=True)
  self.states=vals.astype(np.int32);self.marg=cnt.astype(np.int64);self.N=int(self.marg.sum());self.idx={int(v):i for i,v in enumerate(self.states)}
  self.tr=defaultdict(Counter);self.out=Counter()
  for s in seqs:
   a=np.asarray(s,np.int32)
   for x,y in zip(a[:-1],a[1:]):self.tr[int(x)][int(y)]+=1;self.out[int(x)]+=1
  self.cache={None:self.marg.astype(np.int64)}
 def logp0(self,b):
  i=self.idx.get(int(b));return -math.inf if i is None else math.log(int(self.marg[i])/self.N)
 def logpt(self,a,b):
  i=self.idx.get(int(b))
  if i is None:return -math.inf
  num=int(self.tr[int(a)].get(int(b),0))*self.N+ALPHA*int(self.marg[i]);den=(int(self.out.get(int(a),0))+ALPHA)*self.N
  return math.log(num/den)
 def weights(self,a):
  key=None if a is None else int(a);w=self.cache.get(key)
  if w is not None:return w
  w=(ALPHA*self.marg).astype(np.int64)
  for b,n in self.tr[key].items():
   i=self.idx.get(int(b))
   if i is not None:w[i]+=self.N*int(n)
  self.cache[key]=w;return w
 def cdf(self,a):return np.cumsum(self.weights(a),dtype=np.int64)

def legal_support(model,lo,hi):
 i0=int(np.searchsorted(model.states,int(lo),'left'));i1=int(np.searchsorted(model.states,int(hi),'right'));return model.states[i0:i1]

def map_path(x,model,bound,h,phi):
 lo,hi=legal(np.asarray(x,np.float64),bound,h,phi);cand=[];back=[];mx=[];sm=[]
 q=legal_support(model,lo[0],hi[0])
 if len(q)==0:return None
 a=np.asarray([model.logp0(int(v)) for v in q],np.float64);cand.append(q);back.append(None);mx.append(a);sm.append(a.copy())
 for t in range(1,len(x)):
  qq=legal_support(model,lo[t],hi[t])
  if len(qq)==0:return None
  pm=mx[-1];ps=sm[-1];pq=cand[-1];nm=np.full(len(qq),-np.inf,np.float64);ns=np.full(len(qq),-np.inf,np.float64);bp=np.zeros(len(qq),np.int32)
  for j,b in enumerate(qq):
   vm=[];vs=[]
   for i,aa in enumerate(pq):
    lp=model.logpt(int(aa),int(b));vm.append(float(pm[i])+lp);vs.append(float(ps[i])+lp)
   k=int(np.argmax(vm));nm[j]=vm[k];bp[j]=k;ns[j]=lse(vs)
  cand.append(qq);back.append(bp);mx.append(nm);sm.append(ns)
 j=int(np.argmax(mx[-1]));path=np.empty(len(x),np.int32)
 for t in range(len(x)-1,-1,-1):
  path[t]=int(cand[t][j])
  if t:j=int(back[t][j])
 logmap=float(np.max(mx[-1]));logmass=lse([float(v) for v in sm[-1]])
 return path,-logmap/math.log(2),-logmass/math.log(2),float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))

def arithmetic_encode(path,model):
 e=AE();prev=None
 for q in np.asarray(path,np.int32):
  c=model.cdf(prev);i=model.idx[int(q)];cum=0 if i==0 else int(c[i-1]);freq=int(c[i]-cum);e.put(cum,freq,int(c[-1]));prev=int(q)
 return e.finish()
def arithmetic_decode(blob,nbits,n,model):
 d=AD(blob,nbits);out=np.empty(n,np.int32);prev=None
 for t in range(n):
  c=model.cdf(prev);target=int(d.target(int(c[-1])));i=int(np.searchsorted(c,target,'right'));cum=0 if i==0 else int(c[i-1]);freq=int(c[i]-cum);d.take(cum,freq,int(c[-1]));q=int(model.states[i]);out[t]=q;prev=q
 return out

def fallback(x,h,phi):
 q=nearest(np.asarray(x,np.float64),h,phi);raw=np.ascontiguousarray(q.astype('<i4')).tobytes();blob=Z.compress(raw);qd=np.frombuffer(D.decompress(blob),dtype='<i4').astype(np.int32)
 if not np.array_equal(qd,q):raise RuntimeError('fallback replay')
 return q,blob

def encode_candidate(prev,target,eps,hf):
 bound=eps*SAFETY;h=hf*bound;_,phi,pidx=choose_phase(prev,h);header=bytearray(struct.pack('<4sBBHH',b'MAP1',HFACTORS.index(hf),int(pidx),C,T));rows=[];R=np.empty((C,T),np.float64)
 for ci in range(C):
  ch=C0+ci;seqs=[nearest(np.asarray(d[:,ch],np.float64),h,phi) for d in prev];model=Markov(seqs);x=np.asarray(target[T0:T0+T,ch],np.float64);res=map_path(x,model,bound,h,phi)
  if res is None:
   q,blob=fallback(x,h,phi);nbits=0;mode=1;mapbits=massbits=None;mls=None
  else:
   q,mapbits,massbits,mls=res;blob,nbits=arithmetic_encode(q,model);qd=arithmetic_decode(blob,nbits,T,model)
   if not np.array_equal(qd,q):raise RuntimeError(('MAP arithmetic replay',hf,ch));mode=0
  R[ci]=phi+h*q;me=float(np.max(np.abs(x-R[ci])))
  if me>eps*(1+5e-6):raise RuntimeError(('MAP source hard',hf,ch,me,eps))
  header.extend(struct.pack('<BII',mode,int(nbits),len(blob)));header.extend(blob)
  rows.append({'channel':ch,'mode':'map' if mode==0 else 'fallback','bytes':len(blob)+9,'map_nll_bits':mapbits,'legal_mass_bits':massbits,'map_minus_mass_bits':(mapbits-massbits) if mapbits is not None else None,'mean_legal_lattice_states':mls,'maxerr':me,'support':len(model.states)})
 buf=bytes(header);off=10;RR=np.empty_like(R)
 # Full independent container replay. The decoder owns the same two prior records.
 for ci in range(C):
  ch=C0+ci;mode,nbits,nbytes=struct.unpack_from('<BII',buf,off);off+=9;blob=buf[off:off+nbytes];off+=nbytes;seqs=[nearest(np.asarray(d[:,ch],np.float64),h,phi) for d in prev];model=Markov(seqs)
  if mode==0:q=arithmetic_decode(blob,nbits,T,model)
  else:q=np.frombuffer(D.decompress(blob),dtype='<i4').astype(np.int32)
  if len(q)!=T:raise RuntimeError(('decoded length',len(q),T));RR[ci]=phi+h*q
 if off!=len(buf):raise RuntimeError(('container trailing',off,len(buf)))
 X=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;me=float(np.max(np.abs(X-RR)))
 if me>eps*(1+5e-6):raise RuntimeError(('container hard',hf,me,eps))
 return {'h_over_eps_approx':hf,'phase_index':int(pidx),'phase':float(phi),'bytes':len(buf),'bps':8*len(buf)/(C*T),'maxerr':me,'map_channels':sum(r['mode']=='map' for r in rows),'fallback_channels':sum(r['mode']=='fallback' for r in rows),'mean_map_nll_bps':float(np.mean([r['map_nll_bits']/T for r in rows if r['map_nll_bits'] is not None])) if any(r['map_nll_bits'] is not None for r in rows) else None,'mean_legal_mass_bps':float(np.mean([r['legal_mass_bits']/T for r in rows if r['legal_mass_bits'] is not None])) if any(r['legal_mass_bits'] is not None for r in rows) else None,'mean_map_mass_gap_bps':float(np.mean([(r['map_nll_bits']-r['legal_mass_bits'])/T for r in rows if r['map_nll_bits'] is not None])) if any(r['map_nll_bits'] is not None for r in rows) else None,'rows':rows}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  prev=[fs[0]['Acoustic'],fs[1]['Acoustic']];target=fs[2]['Acoustic'];_,std=m.stats(target);eps=.1*std;X=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;szb,ori=m.szrun(X,eps);rows=[]
  for hf in HFACTORS:
   z=encode_candidate(prev,target,eps,hf);z['gain_vs_sz3']=szb/z['bytes'];z['gain_vs_frozen_standalone_hybrid']=FROZEN_STANDALONE_HYBRID/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='rows'},indent=2),flush=True)
  rows.sort(key=lambda z:z['bytes']);best=rows[0]
  out={'protocol':'CONDITIONAL / STREAMING SIDE-INFORMATION GATE — NOT a standalone-file SOTA claim','previous_records':2,'target_shape':[C,T],'c0':C0,'t0':T0,'samples':C*T,'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'bps':8*szb/(C*T),'orientation':ori},'frozen_standalone_hybrid_bytes':FROZEN_STANDALONE_HYBRID,'rows':rows,'best':best,'scope':'Constructive version of PR242 random-codebook mass. Two previous Imperial records are decoder-known side information and define, independently per channel, the same first-order lattice Markov generator used by the old existence diagnostic. For each target sample the unchanged +/-epsilon interval defines the complete legal lattice-state set. Viterbi selects the single highest-probability complete legal path under that shared generator; a real 64-bit arithmetic container then transmits that selected path with the exact same integer-smoothed transition law. The decoder never sees the target, only the previous records and the physical arithmetic stream; it reproduces every q and source reconstruction and hard error is checked. The old -log(total legal probability mass) is reported only as a diagnostic beside the actual MAP path and never counted as achieved bytes. If a target channel has no path within the previous-record state support it falls back to an explicitly stored Zstd int32 lattice path. Header, per-channel mode, lengths and arithmetic payload are real bytes. This is conditional/streaming evidence only because the two previous records are free side information; any standalone promotion requires self-bootstrap or full side-information accounting.'}
  json.dump(out,open('imperial_markov_map_legal_codec.json','w'),indent=2);print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_h':best['h_over_eps_approx'],'best_bps':best['bps'],'sz3_bytes':int(szb),'frozen_standalone_hybrid':FROZEN_STANDALONE_HYBRID,'gain_vs_sz3':int(szb)/best['bytes'],'gain_vs_standalone_hybrid':FROZEN_STANDALONE_HYBRID/best['bytes'],'map_channels':best['map_channels'],'fallback_channels':best['fallback_channels'],'map_nll_bps':best['mean_map_nll_bps'],'legal_mass_bps_diagnostic':best['mean_legal_mass_bps'],'map_mass_gap_bps':best['mean_map_mass_gap_bps']}},indent=2),flush=True)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
