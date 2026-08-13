import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;TB=1024
FEATURES={
 't1':('t1',),
 'left':('left',),
 't1_left':('t1','left'),
 't1_left_diag':('t1','left','diag'),
 't1_t2_left_diag':('t1','t2','left','diag'),
 't1_t2_left_diag_left2':('t1','t2','left','diag','left2'),
}

def getv(K,c,t,name):
 if name=='t1':return int(K[c,t-1]) if t>0 else 0
 if name=='t2':return int(K[c,t-2]) if t>1 else 0
 if name=='left':return int(K[c-1,t]) if c>0 else 0
 if name=='diag':return int(K[c-1,t-1]) if c>0 and t>0 else 0
 if name=='left2':return int(K[c-2,t]) if c>1 else 0
 raise ValueError(name)

def design(K,names,tmax):
 rows=[];ys=[]
 for t in range(tmax):
  for c in range(C):
   if t==0 and c==0:continue
   rows.append([getv(K,c,t,n) for n in names]);ys.append(int(K[c,t]))
 return np.asarray(rows,np.float64),np.asarray(ys,np.float64)

def fit(K,names,tmax):
 A,y=design(K,names,tmax)
 if A.shape[1]==0:return np.empty(0,np.float32)
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 return np.clip(co,-4,4).astype(np.float32)

def transform(K,names,co):
 J=np.zeros_like(K)
 for t in range(K.shape[1]):
  for c in range(C):
   p=0 if not names else int(np.rint(sum(float(co[i])*getv(K,c,t,n) for i,n in enumerate(names))))
   J[c,t]=int(K[c,t])-p
 return J

def inverse(J,names,co):
 K=np.zeros_like(J)
 for t in range(J.shape[1]):
  for c in range(C):
   p=0 if not names else int(np.rint(sum(float(co[i])*getv(K,c,t,n) for i,n in enumerate(names))))
   K[c,t]=int(J[c,t])+p
 return K

def encode(A,model_bytes):
 total=model_bytes;reps={};frames=[]
 for t0 in range(0,A.shape[1],TB):
  Q=A[:,t0:min(t0+TB,A.shape[1])];n,rep,D=m.encode_k(Q)
  if not np.array_equal(Q,D):raise RuntimeError(('frame decode',t0,rep))
  total+=n;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'bytes':n,'rep':rep})
 return total,reps,frames

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;ls,hu=h.fits(X);Rh,Kh=h.run_ar(X,hu);me=float(np.max(np.abs(X-Rh.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,'source hard',me,eps))
   base,breps,bframes=encode(Kh,h.MODEL_BYTES);cand=[]
   for name,names in FEATURES.items():
    for scope,tmax in (('prefix',TRAIN),('target',NT)):
     co=fit(Kh,names,tmax);raw=np.asarray(co,'<f4').tobytes();cd=np.frombuffer(raw,'<f4').copy();J=transform(Kh,names,cd);Kd=inverse(J,names,cd)
     if not np.array_equal(Kd,Kh):raise RuntimeError((region,name,scope,'inverse'))
     n,reps,frames=encode(J,h.MODEL_BYTES+len(raw)+24)
     cand.append({'feature':name,'fit_scope':scope,'coefficients':[float(x) for x in cd],'bytes':n,'bps':8*n/X.size,'gain_vs_huber_k':base/n,'j_std':float(J.std()),'j_zero_fraction':float(np.mean(J==0)),'reps':reps,'frames':frames})
   cand.sort(key=lambda x:x['bytes']);best=cand[0]
   # Decode through the complete Huber AR source path after inverse K.
   J=transform(Kh,FEATURES[best['feature']],np.asarray(best['coefficients'],np.float32));Kd=inverse(J,FEATURES[best['feature']],np.asarray(best['coefficients'],np.float32));Rd=h.decode_source(Kd,hu);berr=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if berr>eps*(1+1e-12):raise RuntimeError((region,'best hard',berr,eps))
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   for q in cand:q['gain_vs_sz3']=sz/q['bytes']
   row={'region':region,'c0':c0,'samples':int(X.size),'huber_k_baseline':{'bytes':base,'bps':8*base/X.size,'gain_vs_sz3':sz/base,'reps':breps},'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'top8':[{k:v for k,v in q.items() if k!='frames'} for q in cand[:8]],'maxerr':berr}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'shape':[C,NT],'step':h.STEP,'features':{k:list(v) for k,v in FEATURES.items()},'rows':rows,'scope':'Exact reversible second-stage predictor on the Huber-AR32 step267 innovation indices K. K and the source reconstruction are unchanged. Candidate predictors use only already decoded K neighbors (same-channel t-1/t-2, current left, diagonal and left2), with small float32 coefficients fit either from the allowed first1024 prefix or, in a separately labeled legal target-fit variant, from all K and explicitly transmitted/charged. The encoder stores J=K-round(linear prediction); the decoder scans time-major to recover exact K before regenerating the Huber AR32 source. Every J frame is byte-decoded through the incumbent representation menu; coefficient/model/framing bytes are charged and source hard error is rechecked. Purpose: exploit the ~0.2 spatial and lag1 dependence in K by recentering symbols rather than only conditioning entropy probabilities. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_huber_ar32_reversible_k_predictor.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
