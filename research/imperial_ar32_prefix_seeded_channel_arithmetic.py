import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;TB=1024
REGIONS=(('hard',512),('easy',2304))
MODES={
 'channel_prev4':(4,0),
 'channel_prev8':(8,0),
 'channel_prev4_left4':(4,4),
 'channel_prev8_left4':(8,4),
}

def clipn(x,n):return int(max(-n,min(n,int(x))))+n

def target_nctx(nb,cp,cl):
 if cl<=0:return C*(2*cp+1)*nb*4
 return C*(2*cp+1)*(2*cl+1)*nb*4

def target_ctx(c,prev,left,pos,pref,nb,cp,cl):
 if cl<=0:return (((c*(2*cp+1)+clipn(prev,cp))*nb+pos)*4+pref)
 return ((((c*(2*cp+1)+clipn(prev,cp))*(2*cl+1)+clipn(left,cl))*nb+pos)*4+pref)

def seed_target_counts(counts,offset,K,nb,cp,cl):
 u=a.zig(K)
 for t in range(TRAIN):
  for c in range(C):
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    bit=(val>>bp)&1;pos=nb-1-bp;cx=offset+target_ctx(c,prev,left,pos,pref,nb,cp,cl);counts[cx,bit]+=1;pref=((pref<<1)|bit)&3

def arithmetic_mode(K,mode):
 cp,cl=MODES[mode];u=a.zig(K);nb=max(1,int(u.max()).bit_length());baseN=a.nctx(nb);targetN=target_nctx(nb,cp,cl);offset=baseN
 E=a.AE(baseN+targetN);seeded=False
 for t in range(NT):
  if t==TRAIN:
   seed_target_counts(E.c,offset,K,nb,cp,cl);seeded=True
  for c in range(C):
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    bit=(val>>bp)&1;pos=nb-1-bp
    cx=a.ctx(prev,left,pos,pref,nb) if t<TRAIN else offset+target_ctx(c,prev,left,pos,pref,nb,cp,cl)
    E.put(bit,cx);pref=((pref<<1)|bit)&3
 bb,nbit=E.finish();D=a.AD(bb,nbit,baseN+targetN);Kd=np.zeros_like(K)
 for t in range(NT):
  if t==TRAIN:seed_target_counts(D.c,offset,Kd,nb,cp,cl)
  for c in range(C):
   prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    pos=nb-1-bp;cx=a.ctx(prev,left,pos,pref,nb) if t<TRAIN else offset+target_ctx(c,prev,left,pos,pref,nb,cp,cl)
    bit=D.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
   Kd[c,t]=int((val>>1)^-(val&1))
 if not np.array_equal(Kd,K):raise RuntimeError((mode,'K decode'))
 return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd,targetN

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);base,_,_,Kbd=a.arithmetic(K)
   if not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'base replay'))
   candidates=[]
   for mode in MODES:
    n,bits,nb,Kd,nc=arithmetic_mode(K,mode);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,mode,'hard',me,eps))
    candidates.append({'mode':mode,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'target_binary_contexts':int(nc),'maxerr':me})
   sz=0
   for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
   for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
   best=min(candidates,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps(row,indent=2),flush=True)
  json.dump({'global_std':gstd,'eps':eps,'train':TRAIN,'modes':MODES,'rows':rows,'scope':'Direct deployable implementation of PR #382 channel+previous-K oracle signal. The first 1024 K samples are encoded with the incumbent shared cold-start context. At t=1024 the decoder already knows that exact prefix, so encoder and decoder deterministically seed 128 separate sensor-specific binary probability tables by replaying the prefix without emitting any bits. The remaining K samples use per-channel previous-K contexts at +/-4 or +/-8, optionally retaining current-left K +/-4. No channel map or probability tables are transmitted. Exact K decode, full recursive source replay, unchanged hard error, one selector byte and matched SZ3 are enforced on hard/easy 128x8192 regions. No AI.'},open('imperial_ar32_prefix_seeded_channel_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
