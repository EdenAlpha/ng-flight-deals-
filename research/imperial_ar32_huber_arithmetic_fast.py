import sys
import numpy as np
import imperial_ar32_channel_prev_arithmetic as a

def robust_fit(X):
 n=a.C*(a.TRAIN-a.P);A=np.empty((n,a.P+1),np.float64);y=np.empty(n,np.float64);j=0
 for c in range(a.C):
  x=np.asarray(X[c,:a.TRAIN],np.float64)
  for t in range(a.P,a.TRAIN):A[j,0]=1.;A[j,1:]=x[t-a.P:t][::-1];y[j]=x[t];j+=1
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 for _ in range(6):
  r=y-A@co;w=np.minimum(1.0,267.0/np.maximum(np.abs(r),1e-12));sw=np.sqrt(w);co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
 return np.asarray(co,np.float32)

a.fit_shared_ar=robust_fit
a.SPECS=(('hard',512),)
a.NT=4096
a.MODES=('prev4_left4','channel_prev4')
if __name__=='__main__':a.main(sys.argv[1])
