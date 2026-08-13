import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;MAXLAG=2048

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)

def run_ar(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def mi2(n00,n01,n10,n11):
 n=float(n00+n01+n10+n11)
 if n<=0:return 0.0
 M=np.asarray([[n00,n01],[n10,n11]],np.float64)/n;px=M.sum(axis=1);py=M.sum(axis=0);v=0.0
 for i in range(2):
  for j in range(2):
   if M[i,j]>0:v+=M[i,j]*math.log2(M[i,j]/(px[i]*py[j]))
 return float(v)

def lag_spectrum(B,maxlag):
 B=np.asarray(B,np.float64);T=B.shape[1];nfft=1
 while nfft<2*T:nfft*=2
 F=np.fft.rfft(B,n=nfft,axis=1);ac=np.fft.irfft(F*np.conj(F),n=nfft,axis=1).sum(axis=0)
 s=B.sum(axis=0);cs=np.r_[0.0,np.cumsum(s)];rows=[]
 for lag in range(1,min(maxlag,T-1)+1):
  n=B.shape[0]*(T-lag);n11=int(np.rint(ac[lag]));prev1=int(cs[T-lag]);cur1=int(cs[T]-cs[lag]);n10=cur1-n11;n01=prev1-n11;n00=n-n11-n10-n01
  rows.append((lag,mi2(n00,n01,n10,n11),n11/n if n else 0.0))
 return rows

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;outs=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K=run_ar(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((region,me,eps))
   A=K[:,TRAIN:];u=((A.astype(np.int64)<<1)^(A.astype(np.int64)>>63)).astype(np.uint64)
   feats={'zero':A==0,'positive':A>0,'abs_ge2':np.abs(A)>=2,'abs_ge4':np.abs(A)>=4,'zig_bit0':(u&1)!=0,'zig_bit1':((u>>1)&1)!=0,'zig_bit2':((u>>2)&1)!=0}
   fr={};cons=np.zeros(MAXLAG,np.float64)
   for name,B in feats.items():
    rr=lag_spectrum(B,MAXLAG);arr=np.asarray([[a,b,c] for a,b,c in rr],np.float64);cons+=arr[:,1]
    top=sorted(rr,key=lambda x:x[1],reverse=True)[:20]
    beyond={str(k):max((x for x in rr if x[0]>=k),key=lambda x:x[1]) for k in (2,8,32,64,128,256,512,1024)}
    fixed=[]
    for lag in (1,2,4,8,16,32,64,128,256,512,1024,2048):
     if lag<=len(rr):fixed.append(rr[lag-1])
    fr[name]={'top20':[{'lag':int(x[0]),'mi_bps':x[1],'p11':x[2]} for x in top],'best_beyond':{k:{'lag':int(v[0]),'mi_bps':v[1]} for k,v in beyond.items()},'fixed':[{'lag':int(x[0]),'mi_bps':x[1]} for x in fixed]}
   order=np.argsort(cons)[::-1][:30];ctop=[{'lag':int(i+1),'sum_feature_mi_bps':float(cons[i]),'mean_feature_mi_bps':float(cons[i]/len(feats))} for i in order]
   outs.append({'region':region,'c0':c0,'samples':int(A.size),'features':fr,'consensus_top30':ctop,'maxerr':me});print(json.dumps({'region':region,'consensus_top10':ctop[:10]},indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'heldout':[TRAIN,NT],'max_lag':MAXLAG,'rows':outs,'scope':'Long-range temporal dependency diagnostic on the exact decoder-real AR32 step267 innovations. One shared AR32 model is fit only from t<1024 and frozen. Seven nonlinear binary views of held-out K are autocorrelated at every temporal lag 1..2048, aggregating exact pair counts across 128 channels; binary mutual information is computed with overlap-correct marginals. This is not a compression claim. It asks whether AR32 left a sharp periodic/long-memory temporal dependency that short local contexts and 1024-sample framing missed. A strong stable lag would motivate an exact lag transform/context coder; a featureless spectrum would further constrain the remaining joint-dependence route. No AI. Do not merge.'}
 json.dump(out,open('imperial_ar32_temporal_lag_spectroscope.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
