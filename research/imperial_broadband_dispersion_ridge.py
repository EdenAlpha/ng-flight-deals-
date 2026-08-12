import json,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py
import numpy as np
import zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
from research.imperial_valley_frozen_brady_transfer import correction_candidates,decode_correction,SAFETY

C=128;T=1024;BS=(256,512,1024);KS=(1,2,4,8)
TPOS=(0,14488,28976);CPOS=(0,3392,6784)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  bb,_=sz.compress(A,cfg);R,_=sz.decompress(bb,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
  if best is None or int(bb.size)<best['bytes']:best={'bytes':int(bb.size),'ratio':A.nbytes/int(bb.size),'orientation':'T' if tr else 'CT','maxerr':me}
 return best

def comp(a):return ZC.compress(np.ascontiguousarray(a).tobytes())
def decomp(blob,dtype,shape):return np.frombuffer(ZD.decompress(blob),dtype=dtype).reshape(shape)

def ridge_model(X,B,K):
 nb=T//B;all_idx=[];all_q=[];all_sc=[];P=np.zeros_like(X,dtype=np.float32);energy=[]
 for bi in range(nb):
  W=X[:,bi*B:(bi+1)*B].astype(np.float32,copy=False);nf=B//2+1
  S=np.fft.fft(np.fft.rfft(W,axis=1),axis=0)
  mag=np.abs(S)
  # exactly K spatial modes at every temporal frequency: broadband support is implicit.
  idx=np.argpartition(mag,-K,axis=0)[-K:,:].T.astype(np.uint8) # nf x K
  idx.sort(axis=1)
  vals=np.empty((nf,K),np.complex128)
  for fi in range(nf):vals[fi]=S[idx[fi].astype(np.int64),fi]
  xy=np.stack([vals.real,vals.imag],axis=-1)
  scales=np.maximum(np.max(np.abs(xy),axis=(1,2))/127.0,1e-30).astype(np.float32)
  q=np.clip(np.rint(xy/scales[:,None,None]),-127,127).astype(np.int8)
  all_idx.append(idx);all_q.append(q);all_sc.append(scales)
  # decoder path uses only transmitted quantized values/scales/indices.
  Sq=np.zeros_like(S,dtype=np.complex128)
  vv=(q[...,0].astype(np.float32)+1j*q[...,1].astype(np.float32))*scales[:,None]
  for fi in range(nf):Sq[idx[fi].astype(np.int64),fi]=vv[fi]
  P[:,bi*B:(bi+1)*B]=np.fft.irfft(np.fft.ifft(Sq,axis=0),n=B,axis=1).real.astype(np.float32)
  denom=float(np.sum(mag*mag));num=0.0
  for fi in range(nf):num+=float(np.sum(mag[idx[fi].astype(np.int64),fi]**2))
  energy.append(num/denom if denom else 1.0)
 # Self-described flat frames; B,K/array sizes are top-level constants in screen and pessimistic 64-byte directory is charged.
 I=np.concatenate([x.reshape(-1) for x in all_idx]).astype(np.uint8)
 Q=np.concatenate([x.reshape(-1,2) for x in all_q],axis=0).astype(np.int8)
 S=np.concatenate(all_sc).astype('<f4')
 ib=comp(I);qb=comp(Q);sb=comp(S)
 # exact lossless roundtrip audit of model streams
 if not np.array_equal(decomp(ib,np.uint8,I.shape),I):raise RuntimeError('idx roundtrip')
 if not np.array_equal(decomp(qb,np.int8,Q.shape),Q):raise RuntimeError('q roundtrip')
 if not np.array_equal(decomp(sb,np.dtype('<f4'),S.shape),S):raise RuntimeError('scale roundtrip')
 return P,{'index_bytes':len(ib),'coefficient_bytes':len(qb),'scale_bytes':len(sb),'directory_bytes':64,'model_bytes':len(ib)+len(qb)+len(sb)+64,'median_frequencywise_energy_capture':float(np.median(energy)),'block_energy_capture':energy}

def encode_candidate(X,eps,B,K):
 P,md=ridge_model(X,B,K);internal=eps*SAFETY;step=2*internal
 Q=np.rint((X.astype(np.float64)-P.astype(np.float64))/step).astype(np.int32)
 best,allcorr=correction_candidates(Q);cb,mode,c,b1,b2=best
 # correction_candidates tuple is (cost,mode,dtypecode,b1,b2)
 Q2=decode_correction(mode,c,b1,b2,Q.shape)
 if not np.array_equal(Q2,Q):raise RuntimeError(('correction roundtrip',B,K,mode))
 R=P+Q2.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard error',B,K,me,eps))
 corr_bytes=len(b1)+len(b2)+16
 total=md['model_bytes']+corr_bytes
 return {'B':B,'K_per_frequency':K,'bytes':total,'model_bytes':md['model_bytes'],'correction_bytes':corr_bytes,'corr_mode':int(mode),'correction_nonzero_fraction':float(np.mean(Q!=0)),'maxerr':me,'index_bytes':md['index_bytes'],'coefficient_bytes':md['coefficient_bytes'],'scale_bytes':md['scale_bytes'],'median_block_energy_capture':md['median_frequencywise_energy_capture'],'correction_candidates':allcorr}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for ti,t0 in enumerate(TPOS):
   for ci,c0 in enumerate(CPOS):
    X=np.asarray(d[t0:t0+T,c0:c0+C],dtype=np.float32).T;tid=f't{ti}c{ci}';sz3=szrun(X,eps);tiles.append({'tile':tid,'t0':t0,'c0':c0,'raw_bytes':X.nbytes,'local_std':float(X.std()),'sz3':sz3})
    for B in BS:
     for K in KS:
      r=encode_candidate(X,eps,B,K);r.update({'tile':tid,'raw_bytes':X.nbytes,'sz3_bytes':sz3['bytes'],'gain_vs_sz3':sz3['bytes']/r['bytes'],'ratio_raw':X.nbytes/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r);print(json.dumps({k:r[k] for k in ['tile','B','K_per_frequency','bytes','gain_vs_sz3','bps','correction_nonzero_fraction','model_bytes','correction_bytes']},sort_keys=True),flush=True)
 # Freeze one B,K across all nine tiles.
 combos=[]
 for B in BS:
  for K in KS:
   rr=[r for r in rows if r['B']==B and r['K_per_frequency']==K];tot=sum(r['bytes'] for r in rr);sz=sum(r['sz3_bytes'] for r in rr);raw=sum(r['raw_bytes'] for r in rr);combos.append({'B':B,'K_per_frequency':K,'bytes':tot,'sz3_bytes':sz,'gain_vs_sz3':sz/tot,'ratio_raw':raw/tot,'bps':8*tot/(raw/2),'median_correction_nonzero_fraction':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'median_model_bytes':float(np.median([r['model_bytes'] for r in rr])),'median_correction_bytes':float(np.median([r['correction_bytes'] for r in rr]))})
 combos.sort(key=lambda x:x['bytes'])
 out={'std':std,'eps':eps,'shape_per_tile':[C,T],'tiles':tiles,'fixed_broadband_ridge_combos':combos,'best_fixed':combos[:8],'rows':rows,'two_x_fullfile_sz3_target_bps':(8*86361271/(30000*6912))/2,'scope':'Structured broadband f-k ridge screen: every temporal frequency is implicit and receives exactly K strongest spatial modes, avoiding arbitrary 32-bit top-N frequency indices. Per-frequency scales + int8 complex coefficients + uint8 wavenumber indices are losslessly framed; exact hard-error correction is self-decoded and fully counted. Nine fixed full-resolution tiles; no per-tile B/K tuning in aggregate.'}
 print('BEST',json.dumps(combos[:8],indent=2),flush=True);json.dump(out,open('imperial_broadband_dispersion_ridge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
