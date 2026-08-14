import json,math,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
C=128;NT=30000;TB=1024;BPS=8*80604844/(30000*6912);TARGET=BPS/2

def wf(e,D):
 e=np.maximum(np.asarray(e,np.float64).ravel(),0);lo=0.;hi=float(e.max())
 if D>=float(e.mean()):return 0.
 for _ in range(90):
  th=(lo+hi)/2
  if float(np.mean(np.minimum(e,th)))<D:lo=th
  else:hi=th
 th=(lo+hi)/2;z=e>th
 return float(np.sum(.5*np.log2(e[z]/th))/e.size)

def main(path,slot):
 slot=int(slot);rows=[]
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs
  for cb in range(slot*6,min(54,(slot+1)*6)):
   X=np.asarray(d[:,cb*C:(cb+1)*C],np.float64).T;P=None;n=0
   for t0 in range(0,NT-TB+1,TB):
    A=X[:,t0:t0+TB];A=A-A.mean(1,keepdims=True);A=A-A.mean(0,keepdims=True)+A.mean();Q=np.abs(np.fft.fft2(A,norm='ortho'))**2;P=Q if P is None else P+Q;n+=1
   P/=n;R=wf(P,eps*eps);sd=float(X.std());q=(X-X.mean())/max(sd,1e-30)
   r={'cb':cb,'c0':cb*C,'rd_bps':R,'rd_over_2x':R/TARGET,'local_std':sd,'eps_over_local_std':eps/sd,'flatness':float(np.exp(np.mean(np.log(P+1e-30)))/(P.mean()+1e-30)),'kurtosis':float(np.mean(q**4)-3)};rows.append(r);print(json.dumps(r),flush=True)
 mean=float(np.mean([r['rd_bps'] for r in rows]));out={'slot':slot,'rows':rows,'mean_rd_bps':mean,'rd_over_2x':mean/TARGET,'full_sz3_bps':BPS,'target_2x_bps':TARGET,'eps':eps};json.dump(out,open(f'imperial_full_array_gaussian_rd_map_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
