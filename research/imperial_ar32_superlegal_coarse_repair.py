import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;FINE=267;TB=1024;MODEL_BYTES=177
STEPS=(268,269,272,276,280,288,300,320,336,384,400,448,512,534,640,768,1024)

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run(X,coef,coarse):
 R=np.zeros(X.shape,np.int32);Q=np.zeros(X.shape,np.int32);F=np.zeros(X.shape,np.int32)
 a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   e=float(X[c,t])-p
   q=int(np.rint(e/coarse));r0=p+coarse*q
   f=int(np.rint((float(X[c,t])-r0)/FINE));r=r0+FINE*f
   if abs(float(X[c,t])-r)>FINE/2+1e-9:raise RuntimeError(('repair rounding',coarse,c,t,X[c,t],p,q,f,r))
   Q[c,t]=q;F[c,t]=f;R[c,t]=r
 return R,Q,F

def enc(A):
 n,rep,D=m.encode_k(A)
 if not np.array_equal(A,D):raise RuntimeError(('decode',rep))
 return n,rep

def total_bytes(Q,F):
 total=MODEL_BYTES;qr={};fr={};detail=[]
 for t0 in range(0,Q.shape[1],TB):
  qn,qrep=enc(Q[:,t0:t0+TB]);fn,frep=enc(F[:,t0:t0+TB]);total+=qn+fn+12
  qr[qrep]=qr.get(qrep,0)+1;fr[frep]=fr.get(frep,0)+1
  detail.append({'t0':t0,'q_bytes':qn,'q_rep':qrep,'repair_bytes':fn,'repair_rep':frep,'repair_nonzero':int(np.count_nonzero(F[:,t0:t0+TB]))})
 return total,qr,fr,detail

def base_bytes(K):
 total=MODEL_BYTES;reps={}
 for t0 in range(0,K.shape[1],TB):
  n,rep=enc(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
 return total,reps

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X)
   R0,K0,F0=run(X,coef,FINE)
   if np.count_nonzero(F0):raise RuntimeError(('baseline repair unexpectedly nonzero',name))
   base,breps=base_bytes(K0);baseerr=float(np.max(np.abs(X-R0.astype(np.float64))))
   if baseerr>eps*(1+1e-12):raise RuntimeError((name,'base hard',baseerr,eps))
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   cand=[]
   for s in STEPS:
    R,Q,F=run(X,coef,s);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((name,s,'hard',me,eps))
    n,qr,fr,detail=total_bytes(Q,F);nz=int(np.count_nonzero(F));N=F.size
    cand.append({'coarse_step':s,'bytes':n,'bps':8*n/N,'gain_vs_step267':base/n,'gain_vs_sz3':sz/n,
                 'repair_nonzero_fraction':nz/N,'repair_nonzero':nz,'q_std':float(Q.std()),'q_zero_fraction':float(np.mean(Q==0)),
                 'repair_reps':fr,'q_reps':qr,'maxerr':me,'detail':detail})
   cand.sort(key=lambda x:x['bytes']);best=cand[0]
   row={'region':name,'c0':c0,'samples':int(X.size),'baseline_step267':{'bytes':base,'bps':8*base/X.size,'gain_vs_sz3':sz/base,'maxerr':baseerr,'reps':breps},
        'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'top8':[{k:v for k,v in x.items() if k!='detail'} for x in cand[:8]],'maxerr':best['maxerr']}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'fine_repair_step':FINE,'coarse_steps':list(STEPS),'rows':rows,
      'scope':'Real-byte mixed-radix distortion experiment on the current shared AR32 state. Instead of requiring the primary lattice itself to satisfy epsilon, a coarser step S=268..1024 first carries most of each innovation. Only samples whose coarse reconstruction misses the source by more than the legal range receive an exact secondary step267 repair innovation; the repaired reconstruction drives all future AR state. Q and repair F are independently serialized and byte-decoded with the incumbent encode_k backend, per-frame stream/framing overhead is charged, the final source-domain max error is verified, and matched SZ3 is rerun on identical full 128x8192 regions. S=267 is rerun as the exact incumbent control. Purpose: test whether a slightly/super-legally coarse primary alphabet plus a sparse repair layer beats one dense legal lattice; no oracle byte estimates. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_ar32_superlegal_coarse_repair.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
