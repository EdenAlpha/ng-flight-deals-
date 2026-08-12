import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as r
import imperial_decoder_phase_automaton as m

P=16;C=128;T=1024
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
TIMES=(0,14488,28900)

def encode_fixed_model(X,eps,cd):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   pred=r.predict_hist(R,c,t,cd,P,'shared');k=int(np.rint((float(X[c,t])-pred)/m.STEP));R[c,t]=pred+m.STEP*k;K[c,t]=k
 frame=m.encode_k(K);Kd=frame[2];Rd=np.zeros_like(R)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):Rd[c,t]=r.predict_hist(Rd,c,t,cd,P,'shared')+m.STEP*int(Kd[c,t])
 if not np.array_equal(Rd,R):raise RuntimeError('decode mismatch')
 me=float(np.max(np.abs(X-Rd.astype(float))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',me,eps))
 return {'k_bytes':frame[0],'rep':frame[1],'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];regions=[]
  for name,c0 in REGIONS:
   train=np.asarray(d[TIMES[0]:TIMES[0]+T,c0:c0+C],np.float64).T;co=r.fit_shared(train,P);model_bytes,cd=r.model_frame(co);reg={'region':name,'c0':c0,'model_bytes_once':model_bytes,'coefficients':cd.tolist(),'times':[]}
   stable_sum=local_sum=fixed_sum=sz_sum=0
   for ti,t0 in enumerate(TIMES):
    X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb,ori=m.szrun(X,eps);base=m.encode_source(X,eps,'fixed0');stable=encode_fixed_model(X,eps,cd);local=r.encode(X,eps,P,'shared')
    # local includes its own model bytes; stable model is charged once per region below.
    st_bytes=stable['k_bytes']+20;stable_sum+=st_bytes;local_sum+=local['bytes'];fixed_sum+=base['bytes'];sz_sum+=sb
    row={'region':name,'c0':c0,'time_index':ti,'t0':t0,'sz3_bytes':sb,'fixed0_bytes':base['bytes'],'stable_kplusframe_bytes':st_bytes,'local_refit_bytes':local['bytes'],'stable_gain_vs_sz3_before_once_model':sb/st_bytes,'local_gain_vs_sz3':sb/local['bytes'],'stable_vs_local':local['bytes']/st_bytes,'fixed_gain_vs_sz3':sb/base['bytes'],'stable_k_std':stable['k_std'],'stable_zero_fraction':stable['k_zero_fraction'],'local_model_coefficients':local['coefficients'],'maxerr':stable['maxerr']};rows.append(row);reg['times'].append(row);print(json.dumps({k:v for k,v in row.items() if k not in ('local_model_coefficients',)},indent=2),flush=True)
   stable_total=stable_sum+model_bytes;reg.update({'stable_total_bytes':stable_total,'local_refit_total_bytes':local_sum,'fixed0_total_bytes':fixed_sum,'sz3_total_bytes':sz_sum,'stable_gain_vs_sz3':sz_sum/stable_total,'local_refit_gain_vs_sz3':sz_sum/local_sum,'fixed0_gain_vs_sz3':sz_sum/fixed_sum,'stable_vs_local_refit':local_sum/stable_total,'model_bps_amortized':8*model_bytes/(C*T*len(TIMES))});regions.append(reg)
  sz=sum(x['sz3_total_bytes'] for x in regions);stable=sum(x['stable_total_bytes'] for x in regions);local=sum(x['local_refit_total_bytes'] for x in regions);fixed=sum(x['fixed0_total_bytes'] for x in regions);n=C*T*len(TIMES)*len(REGIONS)
  out={'std':std,'eps':eps,'order':P,'times':list(TIMES),'regions':regions,'rows':rows,'aggregate':{'samples':n,'stable_model_bytes':stable,'local_refit_bytes':local,'fixed0_bytes':fixed,'sz3_bytes':sz,'stable_bps':8*stable/n,'local_refit_bps':8*local/n,'fixed0_bps':8*fixed/n,'sz3_bps':8*sz/n,'stable_gain_vs_sz3':sz/stable,'local_refit_gain_vs_sz3':sz/local,'fixed0_gain_vs_sz3':sz/fixed,'stable_vs_local_refit':local/stable,'min_region_stable_gain':min(x['stable_gain_vs_sz3'] for x in regions)},'scope':'Cross-time stability screen for PR301 shared AR16 dyadic state model. One float32 AR16+intercept is fitted only on the earliest 128x1024 window of each fixed cable region, serialized once, byte-decoded, then reused without retuning on early/middle/late windows. Only 256-step innovations are transmitted and recursively decoded with <=128 hard error. A locally refitted AR16 and fixed-phase dyadic baseline are separately charged for comparison; matched SZ3 is rerun on every identical tile. The stable model cost is paid exactly once per region and amortized over its three windows. No AI.'};print(json.dumps(out['aggregate'],indent=2));json.dump(out,open('imperial_resonator_cross_time_stability.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
