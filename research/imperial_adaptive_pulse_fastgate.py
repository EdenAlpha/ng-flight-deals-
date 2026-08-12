import json,sys,importlib.util
import h5py,numpy as np
spec=importlib.util.spec_from_file_location('pulse','research/imperial_adaptive_pulse_tracking.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
CHANNELS=(0,2304,4606,6880)
def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
  for c in CHANNELS:
   x=np.asarray(d[:,c],np.float64);sb=m.szrun(x[:,None],eps);best=None
   for bf in m.BASE_F:
    for uf in m.UP_F:
     for df in m.DOWN_F:
      for dm in m.DEMODS:
       for pol in m.POLICIES:
        r=m.pulse_encode(x,eps,bf,uf,df,dm,pol);key=(r['bytes'],bf,uf,df,dm,pol,r)
        if best is None or key[0]<best[0]:best=key
   b,bf,uf,df,dm,pol,r=best;b+=1
   rr=dict(r);rr.update({'channel':c,'base_over_eps':bf,'up':uf,'down':df,'nyquist_demod':dm,'policy':pol,'bytes_with_selector':b,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/x.size,'gain_vs_sz3':sb[0]/b});rows.append(rr)
  n=sum(30000 for _ in rows);pb=sum(r['bytes_with_selector'] for r in rows);szb=sum(r['sz3_bytes'] for r in rows)
  out={'std':std,'eps':eps,'channels':list(CHANNELS),'aggregate':{'samples':n,'pulse_bytes':pb,'sz3_bytes':szb,'pulse_bps':8*pb/n,'sz3_bps':8*szb/n,'gain_vs_sz3':szb/pb,'reset_fraction':sum(r['resets'] for r in rows)/n,'strict_2x_target_bps':3.331839158950617/2},'rows':rows,'scope':'Fast four-channel gate for the exact PR266 adaptive pulse-state mechanism. Same 96-member fixed menu, actual 2-bit pulse packing + Zstd, serialized reset states, one selector byte per channel, unchanged global 10%-std hard bound and matched SZ3.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_adaptive_pulse_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
