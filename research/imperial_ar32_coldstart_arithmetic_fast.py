import json,sys
import h5py,numpy as np
import imperial_ar32_channel_prev_arithmetic as a

MODES=('prev4_left4','channel_prev4')

def arithmetic_all(K,mode,nb):
 init=np.ones((a.nctx(mode,nb),2),np.int32);enc=a.AE(a.nctx(mode,nb),init);u=a.zig(K)
 for t in range(K.shape[1]):
  for c in range(a.C):
   prev=int(K[c,t-1]) if t>0 else 0;left=int(K[c-1,t]) if c>0 else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;pos=nb-1-bp;cx=a.ctxid(mode,c,prev,left,pos,pref,nb);enc.put(b,cx);pref=((pref<<1)|b)&3
 bb,nbit=enc.finish();Kd=np.zeros_like(K);dec=a.AD(bb,nbit,a.nctx(mode,nb),init)
 for t in range(K.shape[1]):
  for c in range(a.C):
   prev=int(Kd[c,t-1]) if t>0 else 0;left=int(Kd[c-1,t]) if c>0 else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=a.ctxid(mode,c,prev,left,pos,pref,nb);b=dec.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
   Kd[c,t]=int(a.unzig(np.asarray([val],np.uint64))[0])
 if not np.array_equal(Kd,K):raise RuntimeError(('cold decode',mode))
 return len(bb)+16,nbit,Kd

def main(path):
 a.NT=4096
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;X=np.asarray(d[:a.NT,512:512+a.C],np.float64).T;coef=a.fit_shared_ar(X);R,K=a.build_k(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
  if me>eps*(1+1e-12):raise RuntimeError(('hard',me,eps))
  incumbent=a.MODEL_BYTES
  for t0 in range(0,a.NT,1024):n,_,D=a.m.encode_k(K[:,t0:t0+1024]);incumbent+=n
  umax=int(a.zig(K).max());nb=max(1,umax.bit_length());cand=[]
  for mode in MODES:
   ab,nbit,Kd=arithmetic_all(K,mode,nb);total=a.MODEL_BYTES+ab+32;Rd=a.decode_source(Kd,coef);err=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if err>eps*(1+1e-12):raise RuntimeError((mode,'hard',err))
   cand.append({'mode':mode,'bytes':total,'bps':8*total/X.size,'gain_vs_incumbent':incumbent/total,'arithmetic_bytes':ab,'arithmetic_bits':nbit,'nbits_per_symbol':nb,'maxerr':err})
  sz=0
  for t0 in range(0,a.NT,1024):b,_=a.m.szrun(X[:,t0:t0+1024],eps);sz+=b
  for x in cand:x['gain_vs_sz3']=sz/x['bytes']
  cand.sort(key=lambda x:x['bytes']);out={'global_std':gstd,'eps':eps,'region':'hard','samples':int(X.size),'incumbent_bytes':incumbent,'incumbent_bps':8*incumbent/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':cand[0],'candidates':cand,'scope':'Hard-region fast gate that removes the ordinary 1024-sample seed frame from PR #394. The exact same decoder-real AR32 step267 K is arithmetic-coded from t=0 with unit probability priors and fully decoder-known previous/current-left contexts; counts learn online, so no probability table or seed K frame is transmitted. Exact K and the complete source trajectory are decoded and hard-error checked; AR model and framing are charged. No AI.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_ar32_coldstart_arithmetic_fast.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
