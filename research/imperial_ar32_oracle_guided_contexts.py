import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;TB=1024;W=8
REGIONS=(('hard',512),('easy',2304))
MODES={
 'p8l4':(8,4,1,1),
 'p8l8':(8,8,1,1),
 'p4l4_activity6':(4,4,6,1),
 'p8l4_activity6':(8,4,6,1),
 'p8l4_class4':(8,4,1,4),
 'p8l4_class8':(8,4,1,8),
 'p8l4_activity6_class4':(8,4,6,4),
}

def clipn(x,n):return int(max(-n,min(n,int(x))))+n

def activity(sumabs,count):
 if count<=0:return 0
 z=2*int(sumabs)
 for i,q in enumerate((1,3,7,15,31)):
  if z<=q*count:return i
 return 5

def derive_classes(K,nclass):
 if nclass<=1:return np.zeros(C,np.int16)
 # Decoder-deterministic sensor classes: stable rank by prefix mean |K|, channel index breaks ties.
 score=np.sum(np.abs(K[:,:TRAIN].astype(np.int64)),axis=1)
 order=np.lexsort((np.arange(C,dtype=np.int64),score))
 lab=np.empty(C,np.int16)
 for rank,c in enumerate(order):lab[c]=min(nclass-1,(rank*nclass)//C)
 return lab

def ctx(prev,left,pos,pref,nb,cp,cl,extra,nextra):
 return ((((clipn(prev,cp)*(2*cl+1)+clipn(left,cl))*nb+pos)*4+pref)*nextra+extra)

def nctx(nb,cp,cl,nextra):return (2*cp+1)*(2*cl+1)*nb*4*nextra

def arithmetic_mode(K,mode):
 cp,cl,nact,nclass=MODES[mode];nextra=nact*nclass
 u=a.zig(K);nb=max(1,int(u.max()).bit_length());E=a.AE(nctx(nb,cp,cl,nextra))
 labels=derive_classes(K,nclass);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
 for t in range(NT):
  posring=t%W;cnt=min(t,W)
  for c in range(C):
   ac=activity(sums[c],cnt) if nact>1 else 0;cc=int(labels[c]) if t>=TRAIN and nclass>1 else 0;ex=ac*nclass+cc
   prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
   for bp in range(nb-1,-1,-1):
    b=(val>>bp)&1;p=nb-1-bp;E.put(b,ctx(prev,left,p,pref,nb,cp,cl,ex,nextra));pref=((pref<<1)|b)&3
   old=int(ring[c,posring]);new=abs(int(K[c,t]));ring[c,posring]=new;sums[c]+=new-old
 bb,nbit=E.finish();D=a.AD(bb,nbit,nctx(nb,cp,cl,nextra));Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64);labels_d=np.zeros(C,np.int16)
 for t in range(NT):
  if t==TRAIN:labels_d=derive_classes(Kd,nclass)
  posring=t%W;cnt=min(t,W)
  for c in range(C):
   ac=activity(sums[c],cnt) if nact>1 else 0;cc=int(labels_d[c]) if t>=TRAIN and nclass>1 else 0;ex=ac*nclass+cc
   prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
   for bp in range(nb-1,-1,-1):
    p=nb-1-bp;b=D.get(ctx(prev,left,p,pref,nb,cp,cl,ex,nextra));val=(val<<1)|b;pref=((pref<<1)|b)&3
   k=(val>>1)^-(val&1);Kd[c,t]=int(k);old=int(ring[c,posring]);new=abs(int(k));ring[c,posring]=new;sums[c]+=new-old
 if not np.array_equal(Kd,K):raise RuntimeError((mode,'K decode'))
 return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd,labels

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);base,_,_,Kbd=a.arithmetic(K)
   if not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'base replay'))
   candidates=[]
   for mode in MODES:
    n,bits,nb,Kd,lab=arithmetic_mode(K,mode);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,mode,'hard',me,eps))
    candidates.append({'mode':mode,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'class_counts':np.bincount(lab.astype(np.int64),minlength=MODES[mode][3]).tolist(),'maxerr':me})
   sz=0
   for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
   for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
   best=min(candidates,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps(row,indent=2),flush=True)
  json.dump({'global_std':gstd,'eps':eps,'train':TRAIN,'window':W,'modes':MODES,'rows':rows,'scope':'Oracle-guided but fully decoder-real entropy refinement on the unchanged Huber AR32 step267 K field. Motivated by PR #382, candidates preserve previous-K magnitude to +/-8 instead of +/-4, optionally widen left-K context, retain the independently positive rolling activity6 state, and/or specialize by 4/8 sensor classes derived deterministically after the first 1024 decoded K samples. Sensor classes are stable quantiles of prefix sum|K|, so no class map or probability model is transmitted; t<1024 uses shared contexts. Exact arithmetic decode, full recursive source replay, unchanged hard error, one selector byte and matched SZ3 are enforced. Hard/easy fast gate. No AI.'},open('imperial_ar32_oracle_guided_contexts.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
