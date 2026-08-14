import json,math,sys
import h5py,numpy as np

C=128; TB=1024; NCB=54
# Audited slot-level real codec rates from PR #409, six 128-channel blocks per slot.
REAL_SLOT_BPS=(3.12702,1.69515,1.55356,1.60948,2.27620,3.06512,3.13548,3.42293,3.96296)
SZ3_FULL_BPS=3.1097546296296297
TARGET_2X_BPS=SZ3_FULL_BPS/2
GAUSS_MSE_RD_FULL_BPS=1.576240
SHAPE_GAP=0.5*math.log2(2*math.pi*math.e)-1.0

def global_std(d):
 s=ss=0.0;n=0
 for t0 in range(0,d.shape[0],2048):
  x=np.asarray(d[t0:min(d.shape[0],t0+2048)],np.float64)
  s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return math.sqrt(max(0.0,ss/n-m*m))

def psd2(X):
 ps=[]
 for t0 in range(0,X.shape[1]-TB+1,TB):
  A=np.asarray(X[:,t0:t0+TB],np.float64)
  A=A-A.mean(axis=1,keepdims=True)
  A=A-A.mean(axis=0,keepdims=True)+A.mean()
  F=np.fft.fft2(A,norm='ortho');ps.append(np.abs(F)**2)
 return np.mean(ps,axis=0)

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic']; assert tuple(d.shape)==(30000,6912)
  eps=.1*global_std(d); rows=[]
  for cb in range(NCB):
   c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T;P=psd2(X)
   # Stationary-Gaussian differential entropy-rate reference under the circulant PSD model.
   # For an L-infinity distortion ball, volume per dimension is 2*eps. At high resolution,
   # h_rate-log2(2eps) is the Gaussian hard-box Shannon-lower-bound reference. This is a
   # model diagnostic, not a theorem for the fixed non-Gaussian Imperial file.
   floor=max(float(P.mean())*1e-18,1e-30)
   Pe=np.maximum(P,floor)
   hrate=float(0.5*np.mean(np.log2(2*math.pi*math.e*Pe)))
   hard=max(0.0,hrate-math.log2(2*eps))
   slot=cb//6; real=REAL_SLOT_BPS[slot]
   rows.append({'cb':cb,'c0':c0,'slot':slot,'gaussian_entropy_rate_bps':hrate,'gaussian_hardbox_reference_bps':hard,'real_slot_bps':real,'real_minus_reference_bps':real-hard,'reference_over_2x_target':hard/TARGET_2X_BPS})
  hardmean=float(np.mean([r['gaussian_hardbox_reference_bps'] for r in rows]))
  hmean=float(np.mean([r['gaussian_entropy_rate_bps'] for r in rows]))
  realmean=float(np.mean([r['real_slot_bps'] for r in rows]))
  slots=[]
  for s in range(9):
   q=[r for r in rows if r['slot']==s]
   slots.append({'slot':s,'hardbox_reference_bps':float(np.mean([r['gaussian_hardbox_reference_bps'] for r in q])),'real_bps':REAL_SLOT_BPS[s],'gap_bps':REAL_SLOT_BPS[s]-float(np.mean([r['gaussian_hardbox_reference_bps'] for r in q]))})
  out={'eps':eps,'shape_gap_gaussian_mse_to_hardbox_highres_bps':SHAPE_GAP,'verified_gaussian_mse_rd_full_bps':GAUSS_MSE_RD_FULL_BPS,'mse_rd_plus_shape_gap_bps':GAUSS_MSE_RD_FULL_BPS+SHAPE_GAP,'gaussian_entropy_rate_mean_bps':hmean,'gaussian_hardbox_reference_mean_bps':hardmean,'real_pr409_mean_bps':realmean,'two_x_sz3_target_bps':TARGET_2X_BPS,'real_minus_hardbox_reference_bps':realmean-hardmean,'hardbox_reference_over_2x_target':hardmean/TARGET_2X_BPS,'slots':slots,'rows':rows,'scope':'Information-geometry diagnostic only. The same stationary 2-D Gaussian/circulant PSD model used by the prior reverse-waterfilling audit is converted to a high-resolution L-infinity hard-box reference via Gaussian differential entropy rate minus log2(2*epsilon), the per-dimension log-volume of the exact source-domain +/-epsilon cube. This is a Shannon-lower-bound/high-resolution model reference, not a rigorous impossibility theorem for the fixed non-Gaussian Imperial file. The exact analytic Gaussian shape gap 0.5log2(2*pi*e)-1 is reported alongside the prior Gaussian MSE RD result and the audited real PR409 slot rates.'}
  print(json.dumps({k:v for k,v in out.items() if k not in ('rows',)},indent=2),flush=True)
  json.dump(out,open('imperial_gaussian_hardbox_rate_audit.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
