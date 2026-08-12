import json,math,os,sys
import numpy as np,segyio,zstandard as zstd
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from research.garner_valley_das_full_benchmark import enc_int,sz3_best,SAFETY,TIME

Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor();FS=200.0
KVALUES=(8,32,128,512);LAM=(1e-8,1e-6,1e-4,1e-2);QBITS=(8,16);SUPPORT=('shared','perchannel');SOURCE=('ideal','anchor')

def phase_cycles(t):
 x=np.asarray(t,np.float64);p=np.zeros_like(x);a=(x>=0)&(x<=30);p[a]=x[a]*x[a]/6.0;b=(x>30)&(x<=60);p[b]=20*x[b]-300.0-x[b]*x[b]/6.0;p[x>60]=300.0;return p

def source_signal(A,mode):
 ns=A.shape[1]
 if mode=='ideal':
  t=np.arange(ns)/FS;s=np.sin(2*np.pi*phase_cycles(t)).astype(np.float64);s[t>60]=0.;return s,32,{'mode':'ideal','anchor':None}
 e=np.sum(A.astype(np.float64)**2,axis=1);j=int(np.argmax(e));s=A[j].astype(np.float64);peak=max(float(np.max(np.abs(s))),1e-30);q=(s/peak).astype(np.float16);b=Z.compress(q.tobytes());qr=np.frombuffer(D.decompress(b),np.float16,count=ns).astype(np.float64);sd=qr*peak
 if not np.all(np.isfinite(sd)):raise RuntimeError('source decode')
 return sd,len(b)+72,{'mode':'anchor','anchor':j,'source_blob_bytes':len(b),'peak':peak}

def matched_sz3(A,eps):
 total=0;mx=0.
 for t0 in range(0,A.shape[1],TIME):
  W=np.ascontiguousarray(A[:,t0:min(A.shape[1],t0+TIME)]);b,ori,me=sz3_best(np.ascontiguousarray(W.T),eps);total+=b;mx=max(mx,me)
 return total,mx

def corr_bytes(A,P,eps):
 step=2*eps*SAFETY;total=0;mx=0.;nz=0;n=0;reps={}
 for t0 in range(0,A.shape[1],TIME):
  X=A[:,t0:min(A.shape[1],t0+TIME)].astype(np.float64);R=P[:,t0:min(A.shape[1],t0+TIME)].astype(np.float64);K=np.rint((X-R)/step).astype(np.int32);b,rep,Kd=enc_int(K);F=R+step*Kd;me=float(np.max(np.abs(X-F)))
  if not np.all(np.isfinite(F)) or not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
  total+=b;mx=max(mx,me);nz+=int(np.count_nonzero(K));n+=K.size;reps[rep]=reps.get(rep,0)+1
 return total,mx,nz/n,reps

def encode_ir(A,s,K,lam,qbits,support):
 ns=A.shape[1];S=np.fft.rfft(s);den=np.abs(S)**2;reg=lam*max(float(den.max()),1e-30);Y=np.fft.rfft(A.astype(np.float64),axis=1);H=Y*np.conj(S)[None,:]/(den[None,:]+reg);h=np.fft.irfft(H,n=ns,axis=1)
 if support=='shared':
  en=np.sum(h*h,axis=0);idx=np.argsort(en)[-K:];idx=np.sort(idx);indices=np.broadcast_to(idx[None,:],(A.shape[0],K)).copy();ib=Z.compress(idx.astype('<u2').tobytes());idxd=np.frombuffer(D.decompress(ib),np.dtype('<u2'),count=K).astype(np.int32);indicesd=np.broadcast_to(idxd[None,:],indices.shape)
 else:
  indices=np.argpartition(np.abs(h),-K,axis=1)[:,-K:];indices=np.sort(indices,axis=1).astype(np.uint16);delta=indices.copy();delta[:,1:]-=indices[:,:-1];ib=Z.compress(delta.astype('<u2').tobytes());dr=np.frombuffer(D.decompress(ib),np.dtype('<u2'),count=indices.size).reshape(indices.shape).astype(np.int32);indicesd=np.cumsum(dr,axis=1,dtype=np.int32)
 vals=np.take_along_axis(h,indices.astype(np.int64),axis=1);lim=127 if qbits==8 else 32767;dt=np.int8 if qbits==8 else np.int16;scale=np.maximum(np.max(np.abs(vals),axis=1)/lim,1e-30).astype(np.float32);q=np.rint(vals/scale[:,None]).clip(-lim,lim).astype(dt);qb=Z.compress(q.tobytes());sb=Z.compress(scale.tobytes());qd=np.frombuffer(D.decompress(qb),dtype=dt,count=q.size).reshape(q.shape);sd=np.frombuffer(D.decompress(sb),np.float32,count=scale.size);vd=qd.astype(np.float64)*sd[:,None]
 hd=np.zeros_like(h);np.put_along_axis(hd,indicesd.astype(np.int64),vd,axis=1);P=np.fft.irfft(np.fft.rfft(hd,axis=1)*S[None,:],n=ns,axis=1)
 if not np.all(np.isfinite(P)):raise RuntimeError('prediction nonfinite')
 return P,len(ib)+len(qb)+len(sb)+96,{'index_bytes':len(ib),'value_bytes':len(qb),'scale_bytes':len(sb),'K':K,'lambda':lam,'qbits':qbits,'support':support,'ir_energy_fraction':float(np.sum(np.take_along_axis(h*h,indices.astype(np.int64),axis=1))/np.sum(h*h)) if np.sum(h*h)>0 else 1.0}

def main(path):
 with segyio.open(path,'r',ignore_geometry=True) as f:
  f.mmap();ntr=f.tracecount;ns=len(f.samples);full=np.stack([np.asarray(f.trace[i],np.float32) for i in range(ntr)])
 std=float(full.std(dtype=np.float64));eps=.1*std;chs=np.linspace(0,ntr-1,32,dtype=np.int32);A=np.ascontiguousarray(full[chs]);szb,szme=matched_sz3(A,eps);rows=[]
 for sm in SOURCE:
  s,sbytes,sd=source_signal(A,sm)
  for K in KVALUES:
   for lam in LAM:
    for qb in QBITS:
     for support in SUPPORT:
      P,mb,md=encode_ir(A,s,K,lam,qb,support);cb,me,nzf,reps=corr_bytes(A,P,eps);total=sbytes+mb+cb+64;rows.append({'source':sm,'K':K,'lambda':lam,'qbits':qb,'support':support,'bytes':total,'source_bytes':sbytes,'model_bytes':mb,'correction_bytes':cb,'matched_sz3_bytes':szb,'gain_vs_sz3':szb/total,'bps':8*total/A.size,'correction_nonzero':nzf,'maxerr':me,'source_detail':sd,'model_detail':md,'correction_reps':reps})
 rows.sort(key=lambda r:r['bytes']);out={'full_shape':[ntr,ns],'channels_tested':chs.astype(int).tolist(),'tested_shape':list(A.shape),'full_array_std':std,'eps':eps,'matched_sz3':{'bytes':szb,'bps':8*szb/A.size,'maxerr':szme},'best':rows[:20],'rows':rows,'scope':'Controlled-source deconvolution diagnostic. A deterministic triangular shaker sweep or one explicitly transmitted anchor trace is treated as common excitation. Each DAS channel is represented by a sparse circular impulse response recovered by ridge deconvolution, with shared or per-channel tap support, int8/int16 tap values and transmitted scales. Decoder reconstructs the entire raw sweep by convolution and receives only exact 2epsilon corrections in 1024-sample blocks. Every model/side stream is actually compressed/decoded and final hard error is verified using the full-array 10%-std epsilon. Thirty-two deterministic channels spanning the full cable; diagnostic only before full-array integration.'};print(json.dumps({'best':rows[:20]},indent=2),flush=True);json.dump(out,open('garner_source_deconvolution_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
