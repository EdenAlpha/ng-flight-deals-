import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);Pred=np.zeros(X.shape,np.int32)
 a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));Pred[c,t]=p;K[c,t]=k;R[c,t]=p+STEP*k
 return R,K,Pred

def entropy_idx(idx):
 _,n=np.unique(np.asarray(idx).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def conditional_entropy(target,ctx):
 y=np.asarray(target).ravel();c=np.asarray(ctx).ravel()
 _,yi=np.unique(y,return_inverse=True);cu,ci,cnt=np.unique(c,return_inverse=True,return_counts=True)
 A=int(yi.max())+1;j=ci.astype(np.int64)*A+yi.astype(np.int64)
 h=entropy_idx(j)-entropy_idx(ci)
 return h,int(cu.size),float(np.mean(cnt==1)),float(np.max(cnt)/cnt.sum())

def slog(a,cap=15):
 a=np.asarray(a,np.int64);mag=np.minimum(np.floor(np.log2(np.abs(a)+1)).astype(np.int64),cap)
 # zero=0, positive odd, negative even; <=31 states at cap15
 return np.where(a==0,0,np.where(a>0,2*mag+1,2*mag+2)).astype(np.int64)

def clipcode(a,r):return np.clip(np.asarray(a,np.int64),-r,r)+r

def combine(a,b,base_b):return np.asarray(a,np.int64)*int(base_b)+np.asarray(b,np.int64)

def audit(target,contexts,baseline_name='H_K'):
 base=entropy_idx(target);rows=[]
 for name,ctx in contexts:
  h,nctx,single,maxfrac=conditional_entropy(target,ctx)
  rows.append({'context':name,'baseline_entropy_bps':base,'conditional_entropy_bps':h,'oracle_saving_bps':base-h,'context_states_seen':nctx,'singleton_context_fraction':single,'largest_context_fraction':maxfrac})
 rows.sort(key=lambda x:x['conditional_entropy_bps'])
 return base,rows

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;outrows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K,Pred=run_ar(X,coef)
   me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,me,eps))
   H=K[:,TRAIN:];prev=K[:,TRAIN-1:NT-1];prev2=K[:,TRAIN-2:NT-2]
   pp=Pred[:,TRAIN:];pr=R[:,TRAIN-1:NT-1];dr=R[:,TRAIN-1:NT-1].astype(np.int64)-R[:,TRAIN-2:NT-2].astype(np.int64)
   cp1=clipcode(prev,1);cp2=clipcode(prev,2);cp4=clipcode(prev,4);cp8=clipcode(prev,8)
   phase=np.mod(pp,STEP).astype(np.int64);plog=slog(pp);rlog=slog(pr);dlog=slog(dr)
   chan=np.broadcast_to(np.arange(C,dtype=np.int64)[:,None],H.shape)
   tmod8=np.broadcast_to((np.arange(TRAIN,NT,dtype=np.int64)%8)[None,:],H.shape)
   contexts=[
    ('prev_clip1',cp1),('prev_clip2',cp2),('prev_clip4',cp4),('prev_clip8',cp8),('prev_exact',prev),
    ('prev2_clip4',combine(cp4,clipcode(prev2,4),9)),
    ('predictor_phase267',phase),('predictor_signed_log',plog),('prev_recon_signed_log',rlog),('prev_velocity_signed_log',dlog),
    ('channel_id',chan),('time_mod8',tmod8),
    ('prev4_plus_predictor_log',combine(cp4,plog,40)),
    ('prev4_plus_velocity_log',combine(cp4,dlog,40)),
    ('channel_plus_prev4',combine(chan,cp4,9)),
   ]
   base,cr=audit(H,contexts)
   # spatially causal contexts: channel c-1 at current time is free if innovations decode time-major.
   Ys=H[1:];left=H[:-1];diag=prev[:-1];own=prev[1:];left4=clipcode(left,4);own4=clipcode(own,4);diag4=clipcode(diag,4)
   spcontexts=[
    ('left_current_clip4',left4),('left_current_exact',left),('diag_left_prev_clip4',diag4),
    ('ownprev4_plus_left4',combine(own4,left4,9)),
    ('ownprev4_left4_diag4',combine(combine(own4,left4,9),diag4,9)),
   ]
   spbase,spr=audit(Ys,spcontexts)
   actual=MODEL_BYTES;reps={};sz=0
   for t0 in range(TRAIN,NT,TB):
    n,rep,Kd=m.encode_k(K[:,t0:t0+TB]);actual+=n;reps[rep]=reps.get(rep,0)+1
    if not np.array_equal(Kd,K[:,t0:t0+TB]):raise RuntimeError('K decode')
    b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=b
   ns=H.size;actual_bps=8*actual/ns;szbps=8*sz/ns;target=szbps/2
   row={'region':region,'c0':c0,'samples':ns,'actual_ar32_bps':actual_bps,'actual_ar32_bytes':actual,'actual_reps':reps,'matched_sz3_bps':szbps,'two_x_target_bps':target,'missing_bps_actual_to_2x':actual_bps-target,'zero_order_K_entropy_bps':base,'best_decoder_free_contexts':cr[:8],'all_decoder_free_contexts':cr,'spatial_sample_baseline_entropy_bps':spbase,'best_spatial_contexts':spr,'maxerr':me}
   outrows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'order':P,'step':STEP,'train_samples':TRAIN,'heldout_samples':NT-TRAIN,'rows':outrows,'scope':'Optimistic conditional-entropy spectroscope on the exact decoder-real AR32 step267 innovation K. The predictor is fit only from t<1024 and frozen. On held-out t>=1024, exact empirical H(K|context) is measured for contexts that require zero transmitted state because the decoder already knows them: previous innovations, predictor phase/magnitude, prior reconstruction/velocity, channel/time index, and causal current-left spatial innovations. These empirical heldout distributions are target-trained oracle diagnostics, NOT compression claims and intentionally optimistic; context model transmission/estimation is not charged. Their purpose is to upper-screen possible savings: if even oracle decoder-free contexts cannot approach the bps missing to strict 2x SZ3, building a complex context coder is unjustified. Actual self-decoding AR32 bytes, matched SZ3 and hard-error verification are rerun on identical heldout frames. No AI. Do not merge.'}
 json.dump(out,open('imperial_ar32_decoder_state_context_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
