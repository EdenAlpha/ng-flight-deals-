import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
SEGS=(128,256,512,1024,2048)
C=128;NT=8192;TRAIN=1024;P=32;STEP2=536;TB=1024;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(C):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def densest_origin(e):
 s=np.sort(np.asarray(e,np.int64));n=len(s);j=0;bestn=-1;besti=0
 for i in range(n):
  if j<i:j=i
  while j+1<n and s[j+1]-s[i]<=267:j+=1
  nn=j-i+1
  if nn>bestn:bestn=nn;besti=i
 return int(2*int(s[besti])+267)

def choose(E):return np.asarray([densest_origin(E[c]) for c in range(C)],np.int32)

def init_temp(R2,t0,L):
 T=np.zeros((C,P+L),np.int32)
 if t0>=P:T[:,:P]=R2[:,t0-P:t0]
 elif t0>0:T[:,P-t0:P]=R2[:,:t0]
 return T

def simulate_temp(X,co,R2,t0,t1,O):
 L=t1-t0;T=init_temp(R2,t0,L);E=np.empty((C,L),np.int32);K=np.empty((C,L),np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for j,t in enumerate(range(t0,t1)):
  if t<P:p=np.zeros(C,np.int64)
  else:
   # Per-channel np.dot preserves the incumbent predictor arithmetic definition.
   p=np.empty(C,np.int64)
   for c in range(C):p[c]=int(np.rint(a+float(np.dot(b,T[c,j:j+P][::-1].astype(np.float32)))))
  e=X[:,t].astype(np.int64)-p;d=2*e-O.astype(np.int64);k=(d+268)//STEP2;r=2*p+O.astype(np.int64)+STEP2*k
  E[:,j]=e.astype(np.int32);K[:,j]=k.astype(np.int32);T[:,P+j]=r.astype(np.int32)
 return T[:,P:],E,K

def dynamic(X,co,seg):
 R2=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);orig=[];prev=np.ones(C,np.int32);masses=[]
 for t0 in range(0,NT,seg):
  t1=min(NT,t0+seg)
  # Probe with the previous segment's legal origin, then transmit a new origin chosen from this source segment.
  _,Ep,_=simulate_temp(X,co,R2,t0,t1,prev);O=choose(Ep)
  Rseg,E,Kseg=simulate_temp(X,co,R2,t0,t1,O);R2[:,t0:t1]=Rseg;K[:,t0:t1]=Kseg;orig.append(O.copy());prev=O
  masses.append(float(np.mean(Kseg==0)))
 Omap=np.stack(orig,axis=1);return R2,K,Omap,masses

def common(X,co):
 R2=np.zeros((C,NT),np.int32);O=np.ones(C,np.int32);Rseg,E,K=simulate_temp(X,co,R2,0,NT,O);return Rseg,K,O[:,None]

def frame_bytes(K):
 total=0;reps={}
 for t0 in range(0,NT,TB):
  n,rep,D=m.encode_k(K[:,t0:t0+TB]);total+=n;reps[rep]=reps.get(rep,0)+1
  if not np.array_equal(D,K[:,t0:t0+TB]):raise RuntimeError(('K decode',t0))
 return total,reps

def origin_bytes(O):
 n,D,dt=m.signed_blob(np.asarray(O,np.int32))
 if not np.array_equal(D,np.asarray(O,np.int32)):raise RuntimeError('origin decode')
 return n+16,dt

def score(X,R2,K,O,eps,label):
 me=float(np.max(np.abs(2*X-R2.astype(np.float64))*.5))
 if me>eps*(1+1e-12):raise RuntimeError((label,me,eps))
 kb,reps=frame_bytes(K);ob,dt=origin_bytes(O);total=MODEL_BYTES+ob+kb
 return {'mode':label,'bytes':int(total),'bps':float(8*total/X.size),'innovation_bytes':int(kb),'origin_bytes':int(ob),'origin_shape':list(O.shape),'origin_dtype':dt,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'reps':reps,'maxerr':me}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;co=fit_shared_ar(X);Rc,Kc,Oc=common(X,co);base=score(X,Rc,Kc,Oc,eps,'common_half268')
   sz=0
   for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
   cand=[base]
   for seg in SEGS:
    R,K,O,zm=dynamic(X,co,seg);q=score(X,R,K,O,eps,f'dynamic_origin_seg{seg}');q.update({'segment':seg,'mean_segment_zero_fraction':float(np.mean(zm))});cand.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
   cand.sort(key=lambda x:x['bytes']);best=cand[0]
   for q in cand:q['gain_vs_sz3']=float(sz/q['bytes']);q['gain_vs_common_half268']=float(base['bytes']/q['bytes'])
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':int(sz),'sz3_bps':float(8*sz/X.size),'common_half268':base,'best':best,'candidates':cand};rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'halfgrid_step':268,'segments':list(SEGS),'shape':[C,NT],'rows':rows,'scope':'Real-byte dynamic quantization-phase codec. Integer source values make every half-integer lattice origin at spacing268 universally legal (max error133.5). A single shared AR32+intercept is fit only from t<1024. For each fixed time segment and each sensor, the encoder probes with the previous legal origin, chooses the half-integer origin whose 268-consecutive-integer window captures the most residuals, then replays the segment with that origin. Every chosen origin is transmitted in a compressed signed origin map before decoding; no adaptation is hidden. Decoder state is the repaired half-integer state itself, K frames byte-decode exactly, all model/origin/framing bytes are charged, matched SZ3 is rerun identically, and source max error is verified. Segment lengths 128/256/512/1024/2048 expose the rate-versus-origin-map tradeoff. No AI. Draft/do not merge.'}
 json.dump(out,open('imperial_ar32_dynamic_halfgrid_phase.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
