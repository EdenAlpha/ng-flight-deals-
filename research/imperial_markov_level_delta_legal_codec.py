import json,sys,math,struct
from collections import Counter,defaultdict
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_markov_map_legal_codec_v2 as s

T0=14488;C0=512;C=32;T=1024;NPAIR=C//2
HFACTORS=(1.5,1.0,0.75);ALPHA=8;BETA=1;SAFETY=1-1e-6
FROZEN_STANDALONE_HYBRID=23018

class FullMarkov:
 def __init__(self,seqs,lo,hi):
  self.lo=int(lo);self.hi=int(hi);self.states=np.arange(self.lo,self.hi+1,dtype=np.int32);n=len(self.states);obs=np.zeros(n,np.int64);self.tr=defaultdict(Counter);self.out=Counter()
  for seq in seqs:
   a=np.asarray(seq,np.int32);idx=a-self.lo
   if np.any(idx<0) or np.any(idx>=n):raise RuntimeError(('support',self.lo,self.hi,int(a.min()),int(a.max())))
   obs+=np.bincount(idx,minlength=n).astype(np.int64)
   for x,y in zip(a[:-1],a[1:]):self.tr[int(x)][int(y)]+=1;self.out[int(x)]+=1
  self.marg=obs+BETA;self.N=int(self.marg.sum());self.mc=np.cumsum(self.marg,dtype=np.int64);self.cdfcache={None:self.mc}
 def idx(self,v):
  i=int(v)-self.lo
  if i<0 or i>=len(self.states):raise RuntimeError(('idx',v,self.lo,self.hi))
  return i
 def logp0(self,v):return math.log(int(self.marg[self.idx(v)])/self.N)
 def logpt(self,a,b):
  i=self.idx(b);num=int(self.tr[int(a)].get(int(b),0))*self.N+ALPHA*int(self.marg[i]);den=(int(self.out.get(int(a),0))+ALPHA)*self.N;return math.log(num/den)
 def cdf(self,a):
  key=None if a is None else int(a);z=self.cdfcache.get(key)
  if z is not None:return z
  w=(ALPHA*self.marg).astype(np.int64)
  for b,n in self.tr[key].items():w[self.idx(b)]+=self.N*int(n)
  z=np.cumsum(w,dtype=np.int64);self.cdfcache[key]=z;return z
 def decode_index(self,c,target):return int(np.searchsorted(c,int(target),'right'))

def support_for_h(h,phi,bound):
 qlo=int(math.floor((-32768-bound-phi)/h))-2;qhi=int(math.ceil((32767+bound-phi)/h))+2;return qlo,qhi

def viterbi(X,mq,md,bound,h,phi):
 lo,hi=s.legal(np.asarray(X,np.float64),bound,h,phi);cand=[];back=[];mx=[];sm=[]
 def states_at(t):
  z=[]
  for q1 in range(int(lo[t,0]),int(hi[t,0])+1):
   for q2 in range(int(lo[t,1]),int(hi[t,1])+1):z.append((q1,q2-q1))
  return z
 q=states_at(0);a=np.asarray([mq.logp0(x)+md.logp0(d) for x,d in q]);cand.append(q);back.append(None);mx.append(a);sm.append(a.copy())
 for t in range(1,len(X)):
  qq=states_at(t);pq=cand[-1];pm=mx[-1];ps=sm[-1];nm=np.full(len(qq),-np.inf);ns=np.full(len(qq),-np.inf);bp=np.zeros(len(qq),np.int32)
  for j,(bq,bd) in enumerate(qq):
   vm=[];vs=[]
   for i,(aq,ad) in enumerate(pq):
    lp=mq.logpt(aq,bq)+md.logpt(ad,bd);vm.append(float(pm[i])+lp);vs.append(float(ps[i])+lp)
   k=int(np.argmax(vm));nm[j]=vm[k];bp[j]=k;ns[j]=s.lse(vs)
  cand.append(qq);back.append(bp);mx.append(nm);sm.append(ns)
 j=int(np.argmax(mx[-1]));Q=np.empty((len(X),2),np.int32)
 for t in range(len(X)-1,-1,-1):
  q1,d=cand[t][j];Q[t,0]=q1;Q[t,1]=q1+d
  if t>0:j=int(back[t][j])
 logmap=float(np.max(mx[-1]));logmass=s.lse(sm[-1]);joint=float(np.mean((hi[:,0]-lo[:,0]+1).astype(np.int64)*(hi[:,1]-lo[:,1]+1).astype(np.int64)))
 return Q,-logmap/math.log(2),-logmass/math.log(2),joint

def code_scalar(path,model):
 e=s.AE();prev=None
 for v in np.asarray(path,np.int32):
  c=model.cdf(prev);i=model.idx(int(v));cum=0 if i==0 else int(c[i-1]);freq=int(c[i]-cum);e.put(cum,freq,int(c[-1]));prev=int(v)
 return e.finish()
def decode_scalar(blob,nbits,n,model):
 d=s.AD(blob,nbits);out=np.empty(n,np.int32);prev=None
 for t in range(n):
  c=model.cdf(prev);target=d.target(int(c[-1]));i=model.decode_index(c,target)
  if i>=len(c):raise RuntimeError('decode index')
  cum=0 if i==0 else int(c[i-1]);freq=int(c[i]-cum);d.take(cum,freq,int(c[-1]));v=int(model.states[i]);out[t]=v;prev=v
 return out

def run(prev,target,eps,hf):
 bound=eps*SAFETY;h=hf*bound;_,phi,pidx=s.choose_phase(prev,h);qlo,qhi=support_for_h(h,phi,bound);dlo=qlo-qhi;dhi=qhi-qlo;buf=bytearray(struct.pack('<4sBBHH',b'LDEL',HFACTORS.index(hf),int(pidx),NPAIR,T));rows=[];RR=np.empty((C,T),np.float64)
 for pi in range(NPAIR):
  c=C0+2*pi;Qprev=[s.nearest(np.asarray(d[:,c:c+2],np.float64),h,phi) for d in prev];Lseq=[q[:,0] for q in Qprev];Dseq=[q[:,1]-q[:,0] for q in Qprev];mq=FullMarkov(Lseq,qlo,qhi);md=FullMarkov(Dseq,dlo,dhi);X=np.asarray(target[T0:T0+T,c:c+2],np.float64);Q,mapbits,massbits,joint=viterbi(X,mq,md,bound,h,phi);lvl=Q[:,0];delta=Q[:,1]-Q[:,0];lb,ln=code_scalar(lvl,mq);db,dn=code_scalar(delta,md);ld=decode_scalar(lb,ln,T,mq);dd=decode_scalar(db,dn,T,md);Qd=np.column_stack([ld,ld+dd]).astype(np.int32)
  if not np.array_equal(Qd,Q):raise RuntimeError(('level-delta replay',hf,c))
  R=phi+h*Qd;me=float(np.max(np.abs(X-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('level-delta hard',hf,c,me,eps))
  buf.extend(struct.pack('<IIII',int(ln),len(lb),int(dn),len(db)));buf.extend(lb);buf.extend(db);RR[2*pi:2*pi+2]=R.T;rows.append({'pair':[c,c+1],'bytes':16+len(lb)+len(db),'level_bytes':len(lb),'delta_bytes':len(db),'map_nll_bits':mapbits,'legal_mass_bits':massbits,'map_minus_mass_bits':mapbits-massbits,'mean_legal_joint_states':joint,'maxerr':me,'level_support':[qlo,qhi],'delta_support':[dlo,dhi]})
 raw=bytes(buf);off=10;RR2=np.empty_like(RR)
 for pi in range(NPAIR):
  c=C0+2*pi;ln,ll,dn,dl=struct.unpack_from('<IIII',raw,off);off+=16;lb=raw[off:off+ll];off+=ll;db=raw[off:off+dl];off+=dl;Qprev=[s.nearest(np.asarray(d[:,c:c+2],np.float64),h,phi) for d in prev];mq=FullMarkov([q[:,0] for q in Qprev],qlo,qhi);md=FullMarkov([q[:,1]-q[:,0] for q in Qprev],dlo,dhi);ld=decode_scalar(lb,ln,T,mq);dd=decode_scalar(db,dn,T,md);RR2[2*pi:2*pi+2]=(phi+h*np.column_stack([ld,ld+dd])).T
 if off!=len(raw):raise RuntimeError(('level-delta trailing',off,len(raw)))
 XX=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;me=float(np.max(np.abs(XX-RR2)))
 if me>eps*(1+5e-6):raise RuntimeError(('level-delta container hard',hf,me,eps))
 return {'h_over_eps_approx':hf,'phase_index':int(pidx),'phase':float(phi),'bytes':len(raw),'bps':8*len(raw)/(C*T),'maxerr':me,'mean_map_nll_bps':float(np.mean([r['map_nll_bits']/(2*T) for r in rows])),'mean_legal_mass_bps':float(np.mean([r['legal_mass_bits']/(2*T) for r in rows])),'mean_map_mass_gap_bps':float(np.mean([r['map_minus_mass_bits']/(2*T) for r in rows])),'mean_level_bytes':float(np.mean([r['level_bytes'] for r in rows])),'mean_delta_bytes':float(np.mean([r['delta_bytes'] for r in rows])),'rows':rows}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  prev=[fs[0]['Acoustic'],fs[1]['Acoustic']];target=fs[2]['Acoustic'];_,std=m.stats(target);eps=.1*std;X=np.asarray(target[T0:T0+T,C0:C0+C],np.float64).T;szb,ori=m.szrun(X,eps);rows=[]
  for hf in HFACTORS:
   z=run(prev,target,eps,hf);z['gain_vs_sz3']=szb/z['bytes'];z['gain_vs_standalone_hybrid']=FROZEN_STANDALONE_HYBRID/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='rows'},indent=2),flush=True)
  rows.sort(key=lambda z:z['bytes']);best=rows[0];out={'protocol':'CONDITIONAL level+spatial-delta shared-model gate — NOT standalone SOTA','previous_records':2,'target_shape':[C,T],'samples':C*T,'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'bps':8*szb/(C*T),'orientation':ori},'standalone_hybrid_bytes':FROZEN_STANDALONE_HYBRID,'rows':rows,'best':best,'scope':'Full-support spatiotemporal factorization of adjacent channels. Each pair is represented as absolute lattice level q1 and spatial difference d=q2-q1. Two previous decoder-known records train independent first-order Markov chains for level and delta with a +1 full-support prior over the public int16-derived lattice ranges, so no legal target state can disappear merely because an exact pair was unseen. Viterbi searches all hard-error-legal (q1,q2) combinations under the product temporal model. Real 64-bit arithmetic streams transmit the chosen q1 and delta paths separately; decoder rebuilds both models, reconstructs q2=q1+d, and verifies the unchanged hard error. Total legal-set mass is diagnostic only. Result remains conditional because prior records are free side information.'};json.dump(out,open('imperial_markov_level_delta_legal_codec.json','w'),indent=2);print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_h':best['h_over_eps_approx'],'best_bps':best['bps'],'sz3_bytes':int(szb),'standalone_hybrid':FROZEN_STANDALONE_HYBRID,'gain_vs_sz3':int(szb)/best['bytes'],'gain_vs_standalone_hybrid':FROZEN_STANDALONE_HYBRID/best['bytes'],'map_nll_bps':best['mean_map_nll_bps'],'legal_mass_bps_diagnostic':best['mean_legal_mass_bps'],'map_mass_gap_bps':best['mean_map_mass_gap_bps'],'mean_level_bytes':best['mean_level_bytes'],'mean_delta_bytes':best['mean_delta_bytes']}},indent=2),flush=True)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
