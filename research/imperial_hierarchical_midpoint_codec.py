import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
STRIDES=(2,4,8,16,32,64)
C=128;TRAIN=1024;T=1024;P=32;STEP=267;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def ar_target(prefix,target,co):
 X=np.concatenate([prefix,target],axis=1);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for c in range(C):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 A=K[:,TRAIN:];n,rep,D=m.encode_k(A)
 if not np.array_equal(A,D):raise RuntimeError('ar K decode')
 me=float(np.max(np.abs(target-R[:,TRAIN:].astype(np.float64))))
 return MODEL_BYTES+n,n,rep,me

def ipred(a,b,num,den):
 # deterministic nearest integer interpolation with float64 only on modest int32 states
 return np.rint((a.astype(np.float64)*(den-num)+b.astype(np.float64)*num)/den).astype(np.int32)

def tree_codec(X,stride):
 R=np.zeros(X.shape,np.int32);filled=np.zeros(T,bool);anchors=list(range(0,T,stride))
 if anchors[-1]!=T-1:anchors.append(T-1)
 Q=np.rint(X[:,anchors]/STEP).astype(np.int32);R[:,anchors]=STEP*Q;filled[anchors]=True
 nb,rep,Qd=m.encode_k(Q)
 if not np.array_equal(Qd,Q):raise RuntimeError(('anchor decode',stride))
 Rd=np.zeros_like(R);Rd[:,anchors]=STEP*Qd
 total=nb+48;parts=[{'kind':'anchors','count':len(anchors),'bytes':nb,'rep':rep}]
 intervals=[(anchors[i],anchors[i+1]) for i in range(len(anchors)-1) if anchors[i+1]-anchors[i]>1]
 level=0
 while intervals:
  nodes=[];children=[]
  for lo,hi in intervals:
   mid=(lo+hi)//2;nodes.append((lo,mid,hi))
   if mid-lo>1:children.append((lo,mid))
   if hi-mid>1:children.append((mid,hi))
  mids=[x[1] for x in nodes];Klev=np.zeros((C,len(nodes)),np.int32)
  for j,(lo,mid,hi) in enumerate(nodes):
   p=ipred(R[:,lo],R[:,hi],mid-lo,hi-lo);Klev[:,j]=np.rint((X[:,mid].astype(np.float64)-p.astype(np.float64))/STEP).astype(np.int32);R[:,mid]=p+STEP*Klev[:,j]
  n,rep,D=m.encode_k(Klev)
  if not np.array_equal(D,Klev):raise RuntimeError(('level K',stride,level))
  for j,(lo,mid,hi) in enumerate(nodes):
   p=ipred(Rd[:,lo],Rd[:,hi],mid-lo,hi-lo);Rd[:,mid]=p+STEP*D[:,j]
  total+=n+12;parts.append({'kind':'level','level':level,'count':len(nodes),'bytes':n,'rep':rep});intervals=children;level+=1
 if not np.array_equal(Rd,R):raise RuntimeError(('tree decode',stride))
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 return total,parts,me,float(np.mean(Q==0))

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   prefix=np.asarray(d[:TRAIN,c0:c0+C],np.float64).T;X=np.asarray(d[TRAIN:TRAIN+T,c0:c0+C],np.float64).T;co=fit_shared_ar(prefix);arb,arinnov,arrep,arme=ar_target(prefix,X,co)
   if arme>eps*(1+1e-12):raise RuntimeError(('AR hard',region,arme,eps))
   sz,_=m.szrun(X,eps);cand=[]
   for s in STRIDES:
    b,parts,me,z=tree_codec(X,s)
    if me>eps*(1+1e-12):raise RuntimeError(('tree hard',region,s,me,eps))
    cand.append({'stride':s,'bytes':b,'bps':8*b/X.size,'gain_vs_sz3':sz/b,'gain_vs_ar32':arb/b,'parts':parts,'anchor_zero_fraction':z,'maxerr':me})
    print(json.dumps({'region':region,'candidate':cand[-1]},indent=2),flush=True)
   cand.sort(key=lambda x:x['bytes']);rows.append({'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'ar32_bytes':arb,'ar32_bps':8*arb/X.size,'ar32_rep':arrep,'best_tree':cand[0],'candidates':cand})
 out={'global_std':gstd,'eps':eps,'step':STEP,'tile_time':[TRAIN,TRAIN+T],'strides':list(STRIDES),'rows':rows,'scope':'Real-byte noncausal temporal hierarchy gate. Each independent 128x1024 target tile transmits exact step267 anchor states at a fixed stride plus recursively ordered midpoint corrections. A midpoint predictor uses only already-decoded left/right endpoint reconstructions; each correction k=round((X-P)/267) is exact-byte encoded through the existing self-decoding backend, then decoder reconstruction is regenerated and max error checked. Anchor indices/tree topology are deterministic from stride and tile length; conservative per-level framing is charged. The current prefix-trained persistent AR32 target frame and matched SZ3 are rerun on the identical tile. This tests whether bidirectional interpolation captures band-limited temporal structure that a causal AR law cannot. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_hierarchical_midpoint_codec.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
