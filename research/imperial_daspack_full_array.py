import json,sys,time,importlib.metadata
import h5py,numpy as np
from daspack import DASCoder,Quantizer
import imperial_decoder_phase_automaton as m

C=128;BS=(128,2048);LEVELS=1;ORDER=1
PR339_BYTES=71839378;PR339_SZ3_BYTES=80604844;RAW_BYTES=414720000

def main(path):
 version=importlib.metadata.version('daspack-dev')
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;q=Quantizer.Uniform(step=2*eps);coder=DASCoder(threads=4)
  if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
  rows=[];total=0;worst=0.0;tenc=tdec=0.0
  for c0 in range(0,d.shape[1],C):
   # PR #400 found channel x time, blocksize 128x2048, levels1/order1 is best on all four precommitted regimes.
   X=np.ascontiguousarray(np.asarray(d[:,c0:c0+C],np.float64).T)
   t=time.perf_counter();stream=coder.encode(X,q,blocksize=BS,levels=LEVELS,order=ORDER);et=time.perf_counter()-t
   t=time.perf_counter();R=np.asarray(coder.decode(stream),np.float64);dt=time.perf_counter()-t
   if R.shape!=X.shape:raise RuntimeError(('decode shape',c0,R.shape,X.shape))
   me=float(np.max(np.abs(X-R)))
   if me>eps*(1+1e-10):raise RuntimeError(('hard error',c0,me,eps))
   n=len(stream);total+=n;worst=max(worst,me);tenc+=et;tdec+=dt
   row={'c0':c0,'channels':C,'samples':int(X.size),'bytes':n,'bps':8*n/X.size,'ratio_from_int16':2*X.size/n,'maxerr':me,'encode_seconds':et,'decode_seconds':dt}
   rows.append(row);print(json.dumps(row),flush=True)
 out={'daspack_distribution':'daspack-dev','daspack_version':version,'global_std':gstd,'eps':eps,'uniform_step':2*eps,'orientation':'channel_x_time','blocksize':list(BS),'levels':LEVELS,'order':ORDER,
      'samples':int(d.size),'raw_numeric_bytes':RAW_BYTES,'daspack_bytes':total,'daspack_bps':8*total/d.size,'daspack_ratio':RAW_BYTES/total,'maxerr':worst,'sum_encode_seconds':tenc,'sum_decode_seconds':tdec,'blocks':rows,
      'verified_pr339_reference':{'ours_bytes':PR339_BYTES,'ours_bps':8*PR339_BYTES/d.size,'ours_ratio':RAW_BYTES/PR339_BYTES,'sz3_bytes':PR339_SZ3_BYTES,'sz3_bps':8*PR339_SZ3_BYTES/d.size,'sz3_ratio':RAW_BYTES/PR339_SZ3_BYTES,'daspack_over_ours_bytes':total/PR339_BYTES,'sz3_over_daspack_bytes':PR339_SZ3_BYTES/total},
      'scope':'Complete canonical Imperial Acoustic array DASPack baseline after PR #400 selected one common configuration on hard/easy/medium/far without full-array tuning: channel x time orientation, blocksize 128x2048, levels1/order1. All 54 contiguous 128-channel blocks cover all 6912x30000 samples. Each complete self-describing DASPack stream is counted independently (therefore even paying 54 stream headers), byte-decoded, and hard-error verified at Uniform(step=2*epsilon). PR #339 incumbent and matched-SZ3 aggregate byte counts are reused only as already-verified comparison references on this exact array/error contract; this script does not silently re-estimate them. No AI. Diagnostic baseline; do not merge.'}
 print(json.dumps({k:v for k,v in out.items() if k!='blocks'},indent=2),flush=True);json.dump(out,open('imperial_daspack_full_array.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
