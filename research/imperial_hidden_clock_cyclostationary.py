import json,sys,math
import h5py
import numpy as np
import zstandard as zstd

NCH=64;MAXLAG=15000;ZC=zstd.ZstdCompressor(level=19)
COMMON=(2,3,4,5,6,7,8,9,10,12,16,20,24,25,32,40,50,60,64,75,80,100,120,125,128,150,160,200,240,250,256,300,400,500,512,600,625,750,800,1000,1024,1200,1250,1500,2000,2500,3000,4000,5000,6000,7500,10000,15000)
PHASE_COMMON=(2,4,8,16,20,25,32,40,50,64,100,125,128,250,256,500,512,1000)

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))

def H(a):
 _,c=np.unique(np.asarray(a).ravel(),return_counts=True);p=c.astype(np.float64)/c.sum();return float(-(p*np.log2(p)).sum())

def ac_scan(A):
 X=A.astype(np.float64);X-=X.mean(axis=0,keepdims=True);n=X.shape[0];L=1
 while L<2*n:L*=2
 F=np.fft.rfft(X,n=L,axis=0);R=np.fft.irfft(F*np.conj(F),n=L,axis=0)[:MAXLAG+1]
 var=R[0].copy();var[var==0]=1
 corr=R/(var[None,:]);corr*=n/np.maximum(1,n-np.arange(MAXLAG+1))[:,None]
 signed=np.mean(corr,axis=1);ab=np.mean(np.abs(corr),axis=1);medabs=np.median(np.abs(corr),axis=1)
 return signed,ab,medabs

def phase_entropy(q,P):
 n=q.shape[0];tot=0.0
 for r in range(P):
  x=q[r:n:P]
  if x.size:tot+=x.size*H(x)
 return tot/n

def delta_rows(q,P,sgn):
 d=q[P:].astype(np.int32)-int(sgn)*q[:-P].astype(np.int32)
 hd=H(d);zero=float(np.mean(d==0));h0=H(q[:P]) if P>0 else 0
 ideal=(P*h0+d.shape[0]*hd)/q.shape[0]
 mn=int(d.min());mx=int(d.max());cands=[]
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
   b=ZC.compress(np.ascontiguousarray(d).astype(dt).tobytes());cands.append((len(b),dt.str))
 zb=min(cands)[0]+2*P*q.shape[1]
 return hd,zero,ideal,8*zb/q.size,min(cands)[1]

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];shape=list(d.shape);dtype=str(d.dtype);_,std=stats(d);eps=.1*std;step=2*eps
  channels=np.linspace(0,d.shape[1]-1,NCH,dtype=np.int32);A=np.asarray(d[:,channels],dtype=np.float64)
 signed,ab,med=ac_scan(A)
 candidates=[];strong=[]
 for arr in (ab,signed,-signed):
  order=np.argsort(arr[1:])[::-1]+1;chosen=[]
  for p in order:
   if all(abs(int(p)-q)>2 for q in chosen):
    chosen.append(int(p))
    if len(chosen)>=20:break
  candidates.extend(chosen);strong.extend(chosen[:8])
 cand=sorted(set(candidates+list(COMMON)))
 phase_set=set(PHASE_COMMON)|{p for p in strong if p<=1000}
 q=np.rint(A/step).astype(np.int32);h0=float(np.mean([H(q[:,j]) for j in range(q.shape[1])]))
 rows=[]
 for P in cand:
  if P>=q.shape[0]:continue
  sgn=1 if signed[P]>=0 else -1;hd,zero,ideal,zbps,dt=delta_rows(q,P,sgn)
  ph=float(np.mean([phase_entropy(q[:,j],P) for j in range(q.shape[1])])) if P in phase_set else None
  rows.append({'lag':P,'signed_corr':float(signed[P]),'mean_abs_corr':float(ab[P]),'median_abs_corr':float(med[P]),'predictor_sign':sgn,'delta_entropy_bps':hd,'delta_zero_fraction':zero,'ideal_seed_plus_delta_bps':ideal,'zstd_seed_plus_delta_bps':zbps,'delta_dtype':dt,'phase_conditioned_scalar_bps':ph})
 rows_by_corr=sorted(rows,key=lambda r:r['mean_abs_corr'],reverse=True);rows_by_ideal=sorted(rows,key=lambda r:r['ideal_seed_plus_delta_bps']);phase_rows=sorted([r for r in rows if r['phase_conditioned_scalar_bps'] is not None],key=lambda r:r['phase_conditioned_scalar_bps'])
 out={'shape':shape,'dtype':dtype,'channels_tested':channels.tolist(),'global_std':std,'eps':eps,'step':step,'nearest_lattice_mean_channel_H0_bps':h0,'lag1_signed_corr':float(signed[1]),'top_lags_by_abs_corr':rows_by_corr[:30],'top_lags_by_periodic_delta_rate':rows_by_ideal[:30],'top_periods_by_phase_conditioned_entropy':phase_rows[:30],'two_x_fullfile_sz3_target_bps':(8*86361271/(30000*6912))/2,'scope':'Full-60-second hidden-clock/cyclostationarity diagnostic on 64 deterministic channels. FFT scans every temporal lag 1..15000. Detailed phase entropy is evaluated only for strongest peaks and physically meaningful short periods.'}
 print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_hidden_clock_cyclostationary.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
