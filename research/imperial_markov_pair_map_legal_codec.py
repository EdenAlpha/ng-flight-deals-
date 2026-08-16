import json,sys,math,struct,bisect
from collections import Counter,defaultdict
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_markov_map_legal_codec_v2 as s

T0=14488;C0=512;C=32;T=1024;NPAIR=C//2
HFACTORS=(1.5,1.0,0.75);ALPHA=8;SAFETY=1-1e-6
FROZEN_STANDALONE_HYBRID=23018
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

class PairModel:
 def __init__(self,seqs):
  marg=Counter();tr=defaultdict(Counter);out=Counter();N=0
  for a in seqs:
   q=np.asarray(a,np.int32);ss=[(int(x),int(y)) for x,y in q];marg.update(ss);N+=len(ss)
   for x,y in zip(ss[:-1],ss[1:]):tr[x][y]+=1;out[x]+=1
  self.states=sorted(marg);self.idx={v:i for i,v in enumerate(self.states)};self.marg=np.asarray([marg[v] for v in self.states],np.int64);self.mc=np.cumsum(self.marg,dtype=np.int64);self.N=int(N);self.tr=tr;self.out=out;self.tc={}
 def logp0(self,b):
  i=self.idx.get(tuple(b));return -math.inf if i is None else math.log(int(self.marg[i])/self.N)
 def logpt(self,a,b):
  b=tuple(b);i=self.idx.get(b)
  if i is None:return -math.inf
  aa=tuple(a);num=int(self.tr[aa].get(b,0))*self.N+ALPHA*int(self.marg[i]);den=(int(self.out.get(aa,0))+ALPHA)*self.N;return math.log(num/den)
 def trans_arrays(self,a):
  a=tuple(a);z=self.tc.get(a)
  if z is not None:return z
  pairs=sorted((self.idx[b],int(n)) for b,n in self.tr[a].items() if b in self.idx);ids=[x for x,_ in pairs];cum=[];ss=0
  for _,n in pairs:ss+=n;cum.append(ss)
  z=(ids,cum);self.tc[a]=z;return z
 def tr_through(self,a,i):
  ids,cum=self.trans_arrays(a);p=bisect.bisect_right(ids,int(i))-1;return 0 if p<0 else int(cum[p])
 def tr_before(self,a,i):
  ids,cum=self.trans_arrays(a);p=bisect.bisect_left(ids,int(i))-1;return 0 if p<0 else int(cum[p])
 def cumfreq(self,a,b):
  b=tuple(b);i=self.idx[b]
  if a is None:
   cum=0 if i==0 else int(self.mc[i-1]);freq=int(self.marg[i]);return cum,freq,self.N
  aa=tuple(a);cum=ALPHA*(0 if i==0 else int(self.mc[i-1]))+self.N*self.tr_before(aa,i);freq=ALPHA*int(self.marg[i])+self.N*int(self.tr[aa].get(b,0));total=(int(self.out.get(aa,0))+ALPHA)*self.N;return cum,freq,total
 def cdf_end(self,a,i):
  if a is None:return int(self.mc[i])
  aa=tuple(a);return ALPHA*int(self.mc[i])+self.N*self.tr_through(aa,i)
 def total(self,a):return self.N if a is None else (int(self.out.get(tuple(a),0))+ALPHA)*self.N
 def decode_index(self,a,target):
  lo=0;hi=len(self.states)-1
  while lo<hi:
   mid=(lo+hi)//2
   if self.cdf_end(a,mid)>target:hi=mid
   else:lo=mid+1
  return lo

def pair_candidates(model,lo,hi,t):
 out=[]
 for a in range(int(lo[t,0]),int(hi[t,0])+1):
  for b in range(int(lo[t,1]),int(hi[t,1])+1):
   q=(a,b)
   if q in model.idx:out.append(q)
 return out

def map_path(X,model,bound,h,phi):
 lo,hi=s.legal(np.asarray(X,np.float64),bound,h,phi);cand=[];back=[];mx=[];sm=[];q=pair_candidates(model,lo,hi,0)
 if not q:return None
 a=np.asarray([model.logp0(v) for v in q]);cand.append(q);back.append(None);mx.append(a);sm.append(a.copy())
 for t in range(1,len(X)):
  qq=pair_candidates(model,lo,hi,t)
  if not qq:return None
  pq=cand[-1];pm=mx[-1];ps=sm[-1];nm=np.full(len(qq),-np.inf);ns=np.full(len(qq),-np.inf);bp=np.zeros(len(qq),np.int32)
  for j,b in enumerate(qq):
   vm=[];vs=[]
   for i,aa in enumerate(pq):
    lp=model.logpt(aa,b);vm.append(float(pm[i])+lp);vs.append(float(ps[i])+lp)
   k=int(np.argmax(vm));nm[j]=vm[k];bp[j]=k;ns[j]=s.lse(vs)
  cand.append(qq);back.append(bp);mx.append(nm);sm.append(ns)
 j=int(np.argmax(mx[-1]));path=[None]*len(X)
 for t in range(len(X)-1,-1,-1):
  path[t]=cand[t][j]
  if t>0:j=int(back[t][j])
 logmap=float(np.max(mx[-1]));logmass=s.lse(sm[-1]);mls=float(np.mean((hi[:,0]-lo[:,0]+1).astype(np.int64)*(hi[:,1]-lo[:,1]+1).astype(np.int64)))
 return np.asarray(path,np.int32),-logmap/math.log(2),-logmass/math.log(2),mls

def enc(path,model):
 e=s.AE();prev=None
 for row in np.asarray(path,np.int32):
  q=(int(row[0]),int(row[1]));cum,freq,total=model.cumfreq(prev,q);e.put(cum,freq,total);prev=q
 return e.finish()
def dec(blob,nbits,n,model):
 d=s.AD(blob,nbits);out=np.empty((n,2),np.int32);prev=None
 for t in range(n):
  total=model.total(prev);target=int(d.target(total));i=model.decode_index(prev,target);q=model.states[i];cum,freq,total2=model.cumfreq(prev,q);d.take(cum,freq,total2);out[t]=q;prev=q
 return out

def fallback(X,h,phi):
 q=s.nearest(np.asarray(X,np.float64),h,phi);blob=Z.compress(np.ascontiguousarray(q.astype('<i4')).tobytes());qd=np.frombuffer(D.decompress(blob),dtype='<i4').reshape(q.shape)
 if not np.array_equal(qd,q):raise RuntimeError('pair fallback replay')
 return q,blob

def run(prev,target,eps,hf):
 bound=eps*SAFETY;h=hf*bound;_,phi,pidx=s.choose_phase(prev,h);buf=bytearray(struct.pack('<4sBBHH',b'PMAP',HFACTORS.index(hf),int(pidx),NPAIR,T));rows=[]
 for pi in range(NPAIR):
  c=C0+2*pi;seqs=[s.nearest(np.asarray(d[:,c:c+2],np.float64),h,phi) for d in prev];model=PairModel(seqs);X=np.asarray(target[T0:T0+T,c:c+2],np.float64);res=map_path(X,model,bound,h,phi)
  if res is None:q,blob=fallback(X,h,phi);nbits=0;mode=1;mb=lb=gap=mls=None
  else:
   q,mb,lb,mls=res;blob,nbits=enc(q,model);qd=dec(blob,nbits,T,model)
   if not np.array_equal(qd,q):raise RuntimeError(('pair arithmetic replay',hf,c))
   mode=0;gap=mb-lb
  R=phi+h*q;me=float(np.max(np.abs(X-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('pair hard',hf,c,me,eps))
  buf.extend(struct.pack('<BII',mode,int(nbits),len(blob)));buf.extend(blob);rows.append({'pair':[c,c+1],'mode':'map' if mode==0 else 'fallback','bytes':len(blob)+9,'map_nll_bits':mb,'legal_mass_bits':lb,'map_minus_mass_bits':gap,'mean_legal_joint_states':mls,'maxerr':me,'support':len(model.states)})
 raw=bytes(buf);off=10;RR=np.empty((C,T),np.float64)
 for pi in range(NPAIR):
  c=C0+2*pi;mode,nbits,nbytes=struct.unpack_from('<BII',raw,off);off+=9;blob=raw[off:off+nbytes];off+=nbytes;seqs=[s.nearest(np.asarray(d[:,c:c+2],np.float64),h,phi) for d in prev];model=PairModel(seqs)
  if mode==0:q=dec(blob,nbits,T,model)
  else:q=np.frombuffer(D.decompress(blob),dtype='<i4').reshape(T,2).astype(np.int32)
  RR[2*pi:2*pi+2]=((phi+h*q).T)
 X=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;me=float(np.max(np.abs(X-RR)))
 if off!=len(raw):raise RuntimeError(('pair trailing',off,len(raw)))
 if me>eps*(1+5e-6):raise RuntimeError(('pair container hard',hf,me,eps))
 maps=[r for r in rows if r['map_nll_bits'] is not None]
 return {'h_over_eps_approx':hf,'phase_index':int(pidx),'phase':float(phi),'bytes':len(raw),'bps':8*len(raw)/(C*T),'maxerr':me,'map_pairs':len(maps),'fallback_pairs':NPAIR-len(maps),'mean_map_nll_bps':float(np.mean([r['map_nll_bits']/(2*T) for r in maps])) if maps else None,'mean_legal_mass_bps':float(np.mean([r['legal_mass_bits']/(2*T) for r in maps])) if maps else None,'mean_map_mass_gap_bps':float(np.mean([r['map_minus_mass_bits']/(2*T) for r in maps])) if maps else None,'rows':rows}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  prev=[fs[0]['Acoustic'],fs[1]['Acoustic']];target=fs[2]['Acoustic'];_,std=m.stats(target);eps=.1*std;X=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;szb,ori=m.szrun(X,eps);rows=[]
  for hf in HFACTORS:
   z=run(prev,target,eps,hf);z['gain_vs_sz3']=szb/z['bytes'];z['gain_vs_standalone_hybrid']=FROZEN_STANDALONE_HYBRID/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='rows'},indent=2),flush=True)
  rows.sort(key=lambda z:z['bytes']);best=rows[0];out={'protocol':'CONDITIONAL adjacent-pair shared-side-information gate — NOT standalone SOTA','previous_records':2,'target_shape':[C,T],'samples':C*T,'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'bps':8*szb/(C*T),'orientation':ori},'standalone_hybrid_bytes':FROZEN_STANDALONE_HYBRID,'rows':rows,'best':best,'scope':'Constructive adjacent-pair extension of PR242. Each two-channel lattice tuple is one Markov state derived entirely from two previous decoder-known Imperial records. The target hard-error box induces a Cartesian set of legal joint states at every time. Viterbi chooses the highest-probability complete legal spatiotemporal path. A real 64-bit arithmetic stream encodes that exact pair-state path under the same sparse integer-smoothed joint Markov law; decoder independently rebuilds the model, decodes every tuple and verifies source hard error. Total legal-set mass remains diagnostic only. Missing-support pairs explicitly fall back to stored Zstd lattice tuples. Results remain conditional because prior records are free side information.'};json.dump(out,open('imperial_markov_pair_map_legal_codec.json','w'),indent=2);print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_h':best['h_over_eps_approx'],'best_bps':best['bps'],'sz3_bytes':int(szb),'standalone_hybrid':FROZEN_STANDALONE_HYBRID,'gain_vs_sz3':int(szb)/best['bytes'],'gain_vs_standalone_hybrid':FROZEN_STANDALONE_HYBRID/best['bytes'],'map_pairs':best['map_pairs'],'fallback_pairs':best['fallback_pairs'],'map_nll_bps':best['mean_map_nll_bps'],'legal_mass_bps_diagnostic':best['mean_legal_mass_bps'],'map_mass_gap_bps':best['mean_map_mass_gap_bps']}},indent=2),flush=True)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
