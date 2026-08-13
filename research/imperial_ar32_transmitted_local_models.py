import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_OVERHEAD=45
SEGMENTS=(512,1024,2048,3584,7168)

def fit_range(X,t0,t1):
 n=C*(t1-t0);A=np.empty((n,P+1),np.float32);y=np.empty(n,np.float32);j=0
 for c in range(C):
  x=np.asarray(X[c],np.float32)
  for t in range(t0,t1):
   A[j,0]=1.;A[j,1:]=x[t-P:t][::-1];y[j]=x[t];j+=1
 co=np.linalg.lstsq(A.astype(np.float64),y.astype(np.float64),rcond=None)[0].astype('<f4')
 raw=co.tobytes();cd=np.frombuffer(raw,dtype='<f4').copy()
 if not np.array_equal(co.view(np.uint32),cd.view(np.uint32)):raise RuntimeError('model decode')
 return cd,len(raw)+MODEL_OVERHEAD

def pred_from(R,c,t,co):
 return int(np.rint(float(co[0])+float(np.dot(np.asarray(co[1:],np.float32),R[c,t-P:t][::-1].astype(np.float32))))) if t>=P else 0

def build_prefix(X,co):
 R=np.zeros((C,TRAIN),np.int32);K=np.zeros((C,TRAIN),np.int32)
 for c in range(C):
  for t in range(TRAIN):
   p=pred_from(R,c,t,co);k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def build_held(X,prefix_R,spec):
 # spec is list (t0,t1,coef,model_bytes); decoder knows each transmitted model before its segment.
 R=np.zeros((C,NT),np.int32);R[:,:TRAIN]=prefix_R;K=np.zeros((C,NT),np.int32)
 si=0
 for c in range(C):
  si=0
  for t in range(TRAIN,NT):
   while not (spec[si][0] <= t < spec[si][1]):si+=1
   co=spec[si][2];p=pred_from(R,c,t,co);k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def make_spec(X,seg):
 out=[]
 for t0 in range(TRAIN,NT,seg):
  t1=min(NT,t0+seg);co,mb=fit_range(X,t0,t1);out.append((t0,t1,co,mb))
 return out

def main(path):
 m.STEP=STEP
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T
   pco,pmb=fit_range(X,P,TRAIN);prefix_R,prefix_K=build_prefix(X,pco)
   sz=0
   for t0 in range(TRAIN,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   ns=C*(NT-TRAIN);cands=[]
   # persistent baseline reuses prefix model for all held-out samples
   persistent=[(TRAIN,NT,pco,0)]
   for label,spec in [('persistent',persistent)]+[(f'local_{s}',make_spec(X,s)) for s in SEGMENTS]:
    R,K=build_held(X,prefix_R,spec);me=float(np.max(np.abs(X[:,TRAIN:]-R[:,TRAIN:].astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((name,label,me,eps))
    mb=pmb+sum(x[3] for x in spec);total=mb;reps={}
    for t0 in range(TRAIN,NT,TB):
     n,rep,Kd=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
     if not np.array_equal(Kd,K[:,t0:t0+TB]):raise RuntimeError(('K decode',name,label,t0))
    cands.append({'mode':label,'model_bytes':mb,'n_local_models':0 if label=='persistent' else len(spec),'bytes':total,'bps':8*total/ns,'gain_vs_sz3':sz/total,'k_std':float(K[:,TRAIN:].std()),'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'reps':reps,'maxerr':me})
    print(json.dumps({'region':name,'candidate':cands[-1]},indent=2),flush=True)
   cands.sort(key=lambda x:x['bytes']);base=[x for x in cands if x['mode']=='persistent'][0];best=cands[0]
   rows.append({'region':name,'c0':c0,'samples':ns,'sz3_bytes':sz,'sz3_bps':8*sz/ns,'persistent':base,'best':best,'gain_best_vs_persistent':base['bytes']/best['bytes'],'candidates':cands})
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'prefix_model_range':[P,TRAIN],'heldout':[TRAIN,NT],'local_segment_lengths':list(SEGMENTS),'rows':rows,'scope':'Real-byte source-adaptive model test. A common AR32 prefix model is fitted from the first 1024 source samples, transmitted as float32 and used to construct the decoder state through t<1024. For held-out t>=1024, the baseline keeps that model frozen. Each local candidate instead fits one shared AR32+intercept directly to each target segment of length 512/1024/2048/3584/7168 and TRANSMITS every float32 coefficient vector before that segment, so target adaptation is legal and fully charged rather than hidden. The decoder switches models on the same schedule, recursively generates its own state, and receives only exact step267 innovations. All model bytes plus conservative framing are charged; K frames byte-decode exactly; source max error and matched SZ3 on identical held-out tiles are verified. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_transmitted_local_models.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
