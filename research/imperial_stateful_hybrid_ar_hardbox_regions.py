import bisect,json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TB=1024;P=32;STEP=267;MODEL_BYTES=h.MODEL_BYTES
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30

class SAE:
 def __init__(self,cum):self.lo=0;self.hi=MAX;self.pending=0;self.o=h.BO();self.cum=[int(x) for x in cum];self.tot=self.cum[-1]
 def emit(self,b):
  self.o.put(b)
  for _ in range(self.pending):self.o.put(1-b)
  self.pending=0
 def put(self,s):
  rng=self.hi-self.lo+1;cl=self.cum[s];ch=self.cum[s+1];self.hi=self.lo+(rng*ch//self.tot)-1;self.lo=self.lo+(rng*cl//self.tot)
  while True:
   if self.hi<HALF:self.emit(0)
   elif self.lo>=HALF:self.emit(1);self.lo-=HALF;self.hi-=HALF
   elif self.lo>=Q1 and self.hi<Q3:self.pending+=1;self.lo-=Q1;self.hi-=Q1
   else:break
   self.lo=(self.lo<<1)&MAX;self.hi=((self.hi<<1)&MAX)|1
 def finish(self):
  self.pending+=1;self.emit(0 if self.lo<Q1 else 1);return self.o.finish()

class SAD:
 def __init__(self,d,n,cum):
  self.lo=0;self.hi=MAX;self.i=h.BI(d,n);self.v=0;self.cum=[int(x) for x in cum];self.tot=self.cum[-1]
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

def optimal_integer_partition(X,eps):
 # Integer reconstruction centers must keep every source integer within epsilon.
 # Therefore a group diameter <= 2*floor(eps) is always safe (266 here).
 maxdiam=2*int(np.floor(float(eps)))
 counts=np.bincount((np.asarray(X,np.int16).astype(np.int32)+32768).ravel(),minlength=65536)
 vals=np.flatnonzero(counts).astype(np.int32)-32768;c=counts[counts>0].astype(np.int64);nval=len(vals)
 pref=np.zeros(nval+1,np.int64);pref[1:]=np.cumsum(c);dp=np.full(nval+1,-np.inf,np.float64);prev=np.full(nval+1,-1,np.int32);dp[0]=0.0
 for end in range(nval):
  lo=int(np.searchsorted(vals,vals[end]-maxdiam,side='left'));starts=np.arange(lo,end+1,dtype=np.int32);n=(pref[end+1]-pref[starts]).astype(np.float64)
  score=dp[starts]+n*np.log2(n);j=int(np.argmax(score));dp[end+1]=score[j];prev[end+1]=int(starts[j])
 groups=[];e=nval
 while e>0:
  s=int(prev[e]);lo=int(vals[s]);hi=int(vals[e-1]);center=(lo+hi)//2;groups.append((lo,hi,center,int(pref[e]-pref[s])));e=s
 groups.reverse();return groups

def scalar_tile(X,eps):
 groups=optimal_integer_partition(X,eps);his=np.asarray([g[1] for g in groups],np.int32);centers=np.asarray([g[2] for g in groups],np.int32);counts=np.asarray([g[3] for g in groups],np.uint32)
 ids=np.searchsorted(his,np.asarray(X,np.int32).ravel(),side='left').astype(np.int32);cum=np.r_[0,np.cumsum(counts,dtype=np.uint64)]
 E=SAE(cum)
 for s in ids:E.put(int(s))
 bb,nbit=E.finish();modelraw=centers.astype('<i4').tobytes()+counts.astype('<u4').tobytes();model=Z.compress(modelraw);total=len(model)+len(bb)+48
 mr=D.decompress(model);G=len(groups);cc=np.frombuffer(mr[:4*G],'<i4',count=G).astype(np.int32);cnt=np.frombuffer(mr[4*G:8*G],'<u4',count=G).astype(np.uint64);cd=np.r_[0,np.cumsum(cnt,dtype=np.uint64)]
 DD=SAD(bb,nbit,cd);idd=np.empty(ids.size,np.int32)
 for i in range(ids.size):idd[i]=DD.get()
 if not np.array_equal(idd,ids):raise RuntimeError('scalar arithmetic decode')
 R=cc[idd].reshape(X.shape).astype(np.int32);me=float(np.max(np.abs(np.asarray(X,np.float64)-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('scalar hard',me,eps))
 return {'bytes':int(total),'groups':G,'model_bytes':len(model)+32,'payload_bytes':len(bb)+16,'bits':int(nbit),'maxerr':me},R

def ar_tile_from_state(X,Rstate,co,t0,t1):
 R=np.array(Rstate,copy=True);K=np.zeros((C,t1-t0),np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(t0,t1):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t-t0]=k;R[c,t]=p+STEP*k
 return R,K

def ar_stream(K):
 u=h.zig(K);nb=max(1,int(u.max()).bit_length());E=h.AE(h.nctx(nb))
 nt=K.shape[1]
 for t in range(nt):
  for c in range(C):
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    bit=(val>>bp)&1;pos=nb-1-bp;cx=h.ctx(prev,left,pos,pref,nb);E.put(bit,cx);pref=((pref<<1)|bit)&3
 bb,nbit=E.finish();D0=h.AD(bb,nbit,h.nctx(nb));Kd=np.zeros_like(K)
 for t in range(nt):
  for c in range(C):
   prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=h.ctx(prev,left,pos,pref,nb);bit=D0.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
   Kd[c,t]=int(h.unzig(np.asarray([val],np.uint64))[0])
 if not np.array_equal(Kd,K):raise RuntimeError('AR tile arithmetic decode')
 return {'bytes':len(bb)+32,'payload_bytes':len(bb),'bits':int(nbit),'symbol_bits':nb},Kd

def decode_ar_tile(K,Rstate,co,t0,t1):
 R=np.array(Rstate,copy=True);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(t0,t1):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   R[c,t]=p+STEP*int(K[c,t-t0])
 return R

def main(path):
 h.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T;XF=X.astype(np.float64);_,co=h.fits(XF)
   Rb,Kb=h.run_ar(XF,co);base,nbit,nb,Kbd=h.arithmetic(Kb);Rbd=h.decode_source(Kbd,co);berr=float(np.max(np.abs(XF-Rbd.astype(np.float64))))
   if berr>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',berr,eps))
   R=np.zeros((C,NT),np.int32);selector=[];tiles=[];hybrid=MODEL_BYTES
   for t0 in range(0,NT,TB):
    t1=min(NT,t0+TB);Rar,Ka=ar_tile_from_state(XF,R,co,t0,t1);aq,Kd=ar_stream(Ka);Rard=decode_ar_tile(Kd,R,co,t0,t1)
    if not np.array_equal(Rard[:,t0:t1],Rar[:,t0:t1]):raise RuntimeError((region,t0,'AR source decode'))
    sq,Rs=scalar_tile(X[:,t0:t1],eps)
    # One explicit selector byte per tile is conservatively charged.
    if sq['bytes']<aq['bytes']:
     choice='scalar';R[:,t0:t1]=Rs;cost=sq['bytes']
    else:
     choice='ar';R[:,t0:t1]=Rard[:,t0:t1];cost=aq['bytes']
    hybrid+=cost+1;selector.append(choice);tiles.append({'t0':t0,'choice':choice,'chosen_bytes':cost+1,'ar_bytes':aq['bytes'],'scalar_bytes':sq['bytes'],'ar_bits':aq['bits'],'scalar_bits':sq['bits'],'scalar_groups':sq['groups']})
   herr=float(np.max(np.abs(XF-R.astype(np.float64))))
   if herr>eps*(1+1e-12):raise RuntimeError((region,'hybrid hard',herr,eps))
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(XF[:,t0:min(NT,t0+TB)],eps);sz+=int(b)
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
        'huber_full_arithmetic':{'bytes':base,'bps':8*base/X.size,'gain_vs_sz3':sz/base,'maxerr':berr,'arithmetic_bits':nbit,'symbol_bits':nb},
        'stateful_hybrid':{'bytes':hybrid,'bps':8*hybrid/X.size,'gain_vs_sz3':sz/hybrid,'gain_vs_huber':base/hybrid,'maxerr':herr,'selectors':selector,'scalar_tiles':selector.count('scalar'),'ar_tiles':selector.count('ar'),'tiles':tiles}}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'tile_time':TB,'step':STEP,'rows':rows,
       'scope':'Representation-level stateful hybrid gate. One shared prefix-only Huber AR32+intercept is transmitted once. Each 128x1024 time tile is evaluated sequentially from the exact current decoder state. The AR language transmits exact step267 innovations through a fully decoded cold-start contextual arithmetic stream. The alternate language solves the exact entropy-minimizing contiguous scalar hard-box partition but restricts group diameter to 2*floor(epsilon), allowing integer reconstruction centers with <=floor(epsilon) hard error; centers and empirical counts are Zstd-compressed, transmitted, arithmetic-decoded and charged. The smaller real byte language is selected with one conservative selector byte, its decoded reconstruction becomes the actual decoder state, and all future AR predictions use that state. Thus there is no oracle state or hidden reset. Huber full-stream arithmetic and matched SZ3 are rerun on the identical regions. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_stateful_hybrid_ar_hardbox_regions.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
