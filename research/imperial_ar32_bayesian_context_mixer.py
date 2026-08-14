import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;TB=1024;W=8;TOT=1<<16
REGIONS=(('hard',512),('easy',2304))

class PE:
 def __init__(self):self.lo=0;self.hi=a.MAX;self.pending=0;self.o=a.BO()
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending):self.o.put(1-b)
  self.pending=0
 def put(self,b,p0q):
  p0q=max(1,min(TOT-1,int(p0q)));rng=self.hi-self.lo+1;sp=self.lo+(rng*p0q//TOT)-1
  if b==0:self.hi=sp
  else:self.lo=sp+1
  while True:
   if self.hi<a.HALF:self.emit(0)
   elif self.lo>=a.HALF:self.emit(1);self.lo-=a.HALF;self.hi-=a.HALF
   elif self.lo>=a.Q1 and self.hi<a.Q3:self.pending+=1;self.lo-=a.Q1;self.hi-=a.Q1
   else:break
   self.lo=(self.lo<<1)&a.MAX;self.hi=((self.hi<<1)&a.MAX)|1
 def finish(self):
  self.pending+=1;self.emit(0 if self.lo<a.Q1 else 1);return self.o.finish()
class PD:
 def __init__(self,d,n):
  self.lo=0;self.hi=a.MAX;self.i=a.BI(d,n);self.v=0
  for _ in range(32):self.v=((self.v<<1)&a.MAX)|self.i.get()
 def get(self,p0q):
  p0q=max(1,min(TOT-1,int(p0q)));rng=self.hi-self.lo+1;sp=self.lo+(rng*p0q//TOT)-1
  if self.v<=sp:b=0;self.hi=sp
  else:b=1;self.lo=sp+1
  while True:
   if self.hi<a.HALF:pass
   elif self.lo>=a.HALF:self.lo-=a.HALF;self.hi-=a.HALF;self.v-=a.HALF
   elif self.lo>=a.Q1 and self.hi<a.Q3:self.lo-=a.Q1;self.hi-=a.Q1;self.v-=a.Q1
   else:break
   self.lo=(self.lo<<1)&a.MAX;self.hi=((self.hi<<1)&a.MAX)|1;self.v=((self.v<<1)&a.MAX)|self.i.get()
  return b

def clipn(x,n):return int(max(-n,min(n,int(x))))+n
def activity(sumabs,count):
 if count<=0:return 0
 z=2*int(sumabs)
 for i,q in enumerate((1,3,7,15,31)):
  if z<=q*count:return i
 return 5

def make_counts(nb):
 base=np.ones((a.nctx(nb),2),np.int32)
 act=np.ones((a.nctx(nb)*6,2),np.int32)
 wide=np.ones((17*9*nb*4,2),np.int32)
 chan=np.ones((C*17*nb*4,2),np.int32)
 return [base,act,wide,chan]
def ids(c,prev,left,pos,pref,nb,ac):
 base=a.ctx(prev,left,pos,pref,nb)
 act=base*6+ac
 wide=(((clipn(prev,8)*9+clipn(left,4))*nb+pos)*4+pref)
 chan=(((c*17+clipn(prev,8))*nb+pos)*4+pref)
 return (base,act,wide,chan)
def probs(counts,idxs):
 out=[]
 for tab,ix in zip(counts,idxs):
  c0=int(tab[ix,0]);c1=int(tab[ix,1]);out.append(c0/(c0+c1))
 return np.asarray(out,np.float64)
def update_counts(counts,idxs,b):
 for tab,ix in zip(counts,idxs):
  tab[ix,b]+=1
  if int(tab[ix].sum())>16384:tab[ix]=(tab[ix]+1)//2

def mix_prob(weights,pos,pref,p0s,nactive):
 w=weights[pos,pref,:nactive];s=float(w.sum());p=float(np.dot(w,p0s[:nactive])/s)
 return max(1,min(TOT-1,int(np.rint(p*TOT))))
def update_weights(weights,pos,pref,p0s,nactive,b):
 w=weights[pos,pref,:nactive];obs=p0s[:nactive] if b==0 else (1.0-p0s[:nactive]);w*=np.maximum(obs,1e-12);s=float(w.sum())
 if not np.isfinite(s) or s<=0:w[:]=1.0/nactive
 else:w/=s

def arithmetic_mix(K):
 u=a.zig(K);nb=max(1,int(u.max()).bit_length());counts=make_counts(nb);weights=np.ones((nb,4,4),np.float64);E=PE();ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(NT):
  if t==TRAIN:weights[:]=1.0
  nactive=3 if t<TRAIN else 4;pr=t%W;cnt=min(t,W)
  for c in range(C):
   ac=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;ix=ids(c,prev,left,pos,pref,nb,ac);p0s=probs(counts,ix);q=mix_prob(weights,pos,pref,p0s,nactive);E.put(b,q);update_weights(weights,pos,pref,p0s,nactive,b);update_counts(counts,ix,b);pref=((pref<<1)|b)&3
   old=int(ring[c,pr]);new=abs(int(K[c,t]));ring[c,pr]=new;sums[c]+=new-old
 bb,nbit=E.finish();counts=make_counts(nb);weights_d=np.ones((nb,4,4),np.float64);D=PD(bb,nbit);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(NT):
  if t==TRAIN:weights_d[:]=1.0
  nactive=3 if t<TRAIN else 4;pr=t%W;cnt=min(t,W)
  for c in range(C):
   ac=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;ix=ids(c,prev,left,pos,pref,nb,ac);p0s=probs(counts,ix);q=mix_prob(weights_d,pos,pref,p0s,nactive);b=D.get(q);val=(val<<1)|b;update_weights(weights_d,pos,pref,p0s,nactive,b);update_counts(counts,ix,b);pref=((pref<<1)|b)&3
   Kd[c,t]=int((val>>1)^-(val&1));old=int(ring[c,pr]);new=abs(int(Kd[c,t]));ring[c,pr]=new;sums[c]+=new-old
 if not np.array_equal(Kd,K):raise RuntimeError('mixed K decode')
 return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd,weights

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);base,_,_,Kbd=a.arithmetic(K);mix,bits,nb,Kd,w=arithmetic_mix(K);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'base replay'))
   if me>eps*(1+1e-12):raise RuntimeError((region,'mix hard',me,eps))
   sz=0
   for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
   row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'mixer_bytes':int(mix),'mixer_bps':8*mix/X.size,'gain_vs_baseline':base/mix,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'gain_vs_sz3':sz/mix,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'final_expert_weights':w.tolist(),'maxerr':me};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='final_expert_weights'},indent=2),flush=True)
  json.dump({'global_std':gstd,'eps':eps,'train':TRAIN,'rows':rows,'scope':'Non-neural Bayesian bit-probability mixer on the unchanged Huber AR32 step267 K stream. Four adaptive experts are maintained independently: incumbent prev4+left4, the positive rolling activity6 specialization, wider prev8+left4, and exact channel+prev8. Before t=1024 the first three experts are mixed while the per-channel expert is silently trained from already emitted/decoded K; at t=1024 expert weights reset and all four participate. Mixture weights are maintained separately by bit position and two-bit prefix and updated online by Bayesian likelihood, so experts are combined without multiplying their context spaces or transmitting any model. The same probability quantization drives a fully implemented arithmetic encoder/decoder; exact K and source replay plus unchanged max error are verified. Hard/easy gate. No AI.'},open('imperial_ar32_bayesian_context_mixer.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
