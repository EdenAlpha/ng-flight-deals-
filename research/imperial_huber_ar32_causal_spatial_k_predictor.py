import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
SCHEMES={
 'left1':('left1',),
 'left1_left2':('left1','left2'),
 'left1_diag':('left1','diag'),
 'left1_ownprev':('left1','ownprev'),
 'left1_left2_diag_ownprev':('left1','left2','diag','ownprev'),
}

def feat(K,c,t,name):
 if name=='left1':return float(K[c-1,t]) if c>=1 else 0.0
 if name=='left2':return float(K[c-2,t]) if c>=2 else 0.0
 if name=='diag':return float(K[c-1,t-1]) if c>=1 and t>=1 else 0.0
 if name=='ownprev':return float(K[c,t-1]) if t>=1 else 0.0
 raise ValueError(name)

def fit_spatial(X,R,K,names):
 # Fit only from t<1024. Target is the continuous temporal-AR residual in units of STEP,
 # before scalar quantization. Features are already-decoded innovation indices.
 rows=[];ys=[]
 for t in range(1,TRAIN):
  for c in range(C):
   if ('left1' in names or 'diag' in names) and c<1:continue
   if 'left2' in names and c<2:continue
   temporal_pred=float(R[c,t]-STEP*K[c,t])
   y=(float(X[c,t])-temporal_pred)/STEP
   rows.append([feat(K,c,t,n) for n in names]);ys.append(y)
 A=np.asarray(rows,np.float64);y=np.asarray(ys,np.float64)
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 # robustify against the very heavy-tailed hard-region innovations
 for _ in range(5):
  r=y-A@co;w=np.minimum(1.0,1.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 return np.asarray(co,np.float32)

def correction(K,c,t,names,co):
 s=0.0
 for j,n in enumerate(names):s+=float(co[j])*feat(K,c,t,n)
 return int(np.rint(STEP*s))

def run_spatial(X,arco,names,sco):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a0=float(arco[0]);b=np.asarray(arco[1:],np.float32)
 # time-major scan makes current-left K explicitly causal/decoder-known
 for t in range(NT):
  for c in range(C):
   if t<P:tp=0
   else:tp=int(np.rint(a0+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   pred=tp+correction(K,c,t,names,sco)
   k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;R[c,t]=pred+STEP*k
 return R,K

def decode_spatial(K,arco,names,sco):
 R=np.zeros(K.shape,np.int32);a0=float(arco[0]);b=np.asarray(arco[1:],np.float32)
 for t in range(K.shape[1]):
  for c in range(K.shape[0]):
   if t<P:tp=0
   else:tp=int(np.rint(a0+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   pred=tp+correction(K,c,t,names,sco);R[c,t]=pred+STEP*int(K[c,t])
 return R

def backend(K,extra_model=0):
 total=MODEL_BYTES+extra_model;reps={}
 for t0 in range(0,NT,TB):
  n,rep,D=a.m.encode_k(K[:,t0:min(t0+TB,NT)])
  if not np.array_equal(D,K[:,t0:min(t0+TB,NT)]):raise RuntimeError(('backend decode',t0))
  total+=int(n);reps[rep]=reps.get(rep,0)+1
 return total,reps

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu)
   bme=float(np.max(np.abs(X-Rb.astype(np.float64))))
   if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))
   bb,brep=backend(Kb);base_arith,base_bits,base_nb,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,hu)
   if not np.array_equal(Rbd,Rb):raise RuntimeError((region,'baseline arithmetic source decode'))
   candidates=[]
   for name,names in SCHEMES.items():
    sco=fit_spatial(X,Rb,Kb,names);extra=16+4*len(sco)+1
    R,K=run_spatial(X,hu,names,sco);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,name,'hard',me,eps))
    b,reps=backend(K,extra)
    Kd=None
    candidates.append({'scheme':name,'features':list(names),'coefficients':sco.tolist(),'extra_model_bytes':extra,'backend_bytes':b,'backend_bps':8*b/X.size,'gain_backend_vs_huber':bb/b,'reps':reps,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'_K':K,'_R':R})
   candidates.sort(key=lambda q:q['backend_bytes'])
   # Only the best source predictor pays the expensive exact arithmetic rerun.
   best=candidates[0];extra=best['extra_model_bytes'];cab,nbit,nb,Kd=a.arithmetic(best['_K']);cab+=extra
   Rd=decode_spatial(Kd,hu,SCHEMES[best['scheme']],np.asarray(best['coefficients'],np.float32));cme=float(np.max(np.abs(X-Rd.astype(np.float64))))
   if not np.array_equal(Rd,best['_R']):raise RuntimeError((region,'candidate arithmetic source decode'))
   if cme>eps*(1+1e-12):raise RuntimeError((region,'candidate arithmetic hard',cme,eps))
   sz=0
   for t0 in range(0,NT,TB):sb,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=sb
   clean=[]
   for q in candidates:
    q={k:v for k,v in q.items() if not k.startswith('_')};q['gain_backend_vs_sz3']=sz/q['backend_bytes'];clean.append(q)
   row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
        'huber_ar32_backend':{'bytes':bb,'bps':8*bb/X.size,'gain_vs_sz3':sz/bb,'reps':brep},
        'huber_ar32_coldstart_arithmetic':{'bytes':base_arith,'bps':8*base_arith/X.size,'gain_vs_sz3':sz/base_arith,'arithmetic_bits':base_bits,'symbol_bits':base_nb},
        'best_spatial_backend':clean[0],
        'best_spatial_plus_arithmetic':{'scheme':best['scheme'],'bytes':cab,'bps':8*cab/X.size,'gain_vs_huber_arithmetic':base_arith/cab,'gain_vs_sz3':sz/cab,'arithmetic_bits':nbit,'symbol_bits':nb,'maxerr':cme},
        'candidates':clean}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'rows':rows,
       'scope':'Causal 2-D source-predictor gate stacked on the real prefix-only Huber AR32 candidate. The ordinary predictor treats all sensors independently in source space even though post-AR32 innovations retain immediate-neighbor dependence. This branch fits only on t<1024 a tiny robust linear correction from already-decoded innovation indices (current-left, left2, diagonal-left-previous, own-previous combinations). During a time-major scan the decoder first forms its temporal Huber-AR32 prediction, then adds STEP times the fixed spatial innovation correction, rounds to an integer predictor, receives the exact step267 K, and carries the reconstructed source into future AR state. Current-left K is causal because channel c-1 at the same time has already decoded. Every correction coefficient is float32 and explicitly charged with framing; exact K backend decode and full source replay are verified under the unchanged hard error. All schemes are first gated with the incumbent backend; only the best is rerun through PR #402 cold-start contextual arithmetic, with matched SZ3 on identical complete 128x8192 regions. This is source-domain spatiotemporal prediction, not the already-failed lossless spatial delta/bitplane transforms on a fixed K field. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_huber_ar32_causal_spatial_k_predictor.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
