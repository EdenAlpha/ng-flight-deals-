import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5
APERTURES=(1.0,2.5)
RANKS=(2,4,8,16)
ROUNDS=(0,2,6)
FACTOR_MODES=('q8','q16')
SPECS=(('early_bad',0,0),('early_easy',0,2304),('early_mid',0,4606),('early_far',0,6784),('mid_bad',14488,0),('mid_easy',14488,2304),('mid_mid',14488,4606),('mid_far',14488,6784))
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz error',me,eps))
  row=(int(b.size),'T' if tr else 'C',me)
  if best is None or row[0]<best[0]:best=row
 return best

def gauge_H(ap):
 f=np.fft.fftfreq(C)
 return 2j*np.sin(np.pi*f*ap)

def forward(U,H):
 G=np.fft.ifft(np.fft.fft(U,axis=0)*H[:,None],axis=0).real
 X=np.empty_like(G);X[:,0]=G[:,0];X[:,1:]=G[:,1:]-G[:,:-1]
 return X

def inverse(X,H):
 G=np.cumsum(X,axis=1);F=np.fft.fft(G,axis=0);a=np.abs(H)**2;lam=1e-5*max(1.0,float(a.max()));inv=np.conj(H)/(a+lam);inv[0]=0
 return np.fft.ifft(F*inv[:,None],axis=0).real

def rankproj(U,k):
 G=U@U.T;w,Q=np.linalg.eigh(G);Q=Q[:,-k:];W=Q.T@U
 return Q,W,Q@W

def encode_mean(M):
 a=np.asarray(M,np.float32);b=Z.compress(a.tobytes());r=np.frombuffer(ZD.decompress(b),dtype=np.float32).astype(np.float64)
 if not np.array_equal(a,r.astype(np.float32)):raise RuntimeError('mean roundtrip')
 return len(b)+16,r

def encode_factors(Q,W,mode):
 q16=np.asarray(Q,np.float16);qb=Z.compress(q16.tobytes());Qd=np.frombuffer(ZD.decompress(qb),dtype=np.float16).reshape(Q.shape).astype(np.float64)
 mx=np.max(np.abs(W),axis=1);den=127. if mode=='q8' else 32767.;sc=np.where(mx>0,mx/den,1.0).astype(np.float32);dt=np.int8 if mode=='q8' else np.dtype('<i2')
 A=np.rint(W/sc[:,None]).clip(-den,den).astype(dt);ab=Z.compress(A.tobytes());Ad=np.frombuffer(ZD.decompress(ab),dtype=dt).reshape(W.shape).astype(np.float64);Wd=Ad*sc.astype(np.float64)[:,None]
 sb=Z.compress(sc.tobytes());sd=np.frombuffer(ZD.decompress(sb),dtype=np.float32)
 if not np.array_equal(sd,sc):raise RuntimeError('scale roundtrip')
 return len(qb)+len(ab)+len(sb)+40,Qd@Wd

def mindtype(A):
 mn=int(A.min());mx=int(A.max())
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:return dt
 raise RuntimeError('int overflow')

def transforms(K):
 yield 'raw',K
 D=K.copy();D[:,1:]=K[:,1:]-K[:,:-1];yield 'time',D
 D=K.copy();D[1:]=K[1:]-K[:-1];yield 'space',D
 D=K.copy();D[0,1:]=K[0,1:]-K[0,:-1];D[1:,0]=K[1:,0]-K[:-1,0];D[1:,1:]=K[1:,1:]-K[:-1,1:]-K[1:,:-1]+K[:-1,:-1];yield 'lorenzo',D

def invtransform(A,mode):
 if mode=='raw':return A
 if mode=='time':return np.cumsum(A,axis=1,dtype=np.int64).astype(np.int32)
 if mode=='space':return np.cumsum(A,axis=0,dtype=np.int64).astype(np.int32)
 if mode=='lorenzo':return np.cumsum(np.cumsum(A,axis=0,dtype=np.int64),axis=1,dtype=np.int64).astype(np.int32)
 raise ValueError(mode)

def encode_K(K):
 best=None
 for mode,A in transforms(K):
  dt=mindtype(A);b=Z.compress(np.ascontiguousarray(A).astype(dt).tobytes());row=(len(b)+24,mode,dt.str,b,A.shape)
  if best is None or row[0]<best[0]:best=row
 n,mode,dts,b,shape=best;A=np.frombuffer(ZD.decompress(b),dtype=np.dtype(dts)).reshape(shape).astype(np.int32);Kd=invtransform(A,mode)
 if not np.array_equal(Kd,K):raise RuntimeError(('K roundtrip',mode))
 return n,mode,Kd

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;b=eps*SAFETY;step=2*b;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);mb,M=encode_mean(X.mean(axis=0));X0=X-M[None,:];tiles.append({'tile':name,'sz3_bytes':sb[0],'local_std':float(X.std()),'mean_bytes':mb})
   for ap in APERTURES:
    H=gauge_H(ap);U0=inverse(X0,H)
    for k in RANKS:
     for rounds in ROUNDS:
      U=U0.copy()
      for _ in range(rounds):
       _,_,L=rankproj(U,k);P=M[None,:]+forward(L,H);Y=np.clip(P,X-b,X+b);U=inverse(Y-M[None,:],H)
      Q,W,L=rankproj(U,k)
      for fm in FACTOR_MODES:
       fb,Ld=encode_factors(Q,W,fm);P=M[None,:]+forward(Ld,H);K=np.rint((X-P)/step).astype(np.int32);kb,krep,Kd=encode_K(K);R=P+step*Kd;me=float(np.max(np.abs(X-R)))
       if not np.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('hard error',name,ap,k,rounds,fm,me,eps))
       total=mb+fb+kb+64;rows.append({'tile':name,'aperture_channels':ap,'rank':k,'projection_rounds':rounds,'factor_mode':fm,'bytes':total,'bps':8*total/X.size,'gain_vs_sz3':sb[0]/total,'sz3_bytes':sb[0],'mean_bytes':mb,'factor_bytes':fb,'correction_bytes':kb,'correction_rep':krep,'correction_nonzero_fraction':float(np.mean(K!=0)),'model_rmse_over_eps':float(np.sqrt(np.mean((X-P)**2))/eps),'maxerr':me})
  combos=[]
  for ap in APERTURES:
   for k in RANKS:
    for rounds in ROUNDS:
     for fm in FACTOR_MODES:
      rr=[r for r in rows if r['aperture_channels']==ap and r['rank']==k and r['projection_rounds']==rounds and r['factor_mode']==fm];tot=sum(r['bytes'] for r in rr);szb=sum(r['sz3_bytes'] for r in rr);n=len(rr)*C*T
      combos.append({'aperture_channels':ap,'rank':k,'projection_rounds':rounds,'factor_mode':fm,'bytes':tot,'sz3_bytes':szb,'bps':8*tot/n,'gain_vs_sz3':szb/tot,'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'median_model_rmse_over_eps':float(np.median([r['model_rmse_over_eps'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda r:r['bytes']);out={'std':std,'eps':eps,'gauge_length_m':10.0,'channel_spacing_m':4.0,'physical_aperture_channels':2.5,'control_adjacent_aperture_channels':1.0,'tiles':tiles,'best_fixed':combos[:12],'combos':combos,'rows':rows,'scope':'Physical gauge-operator latent codec screen. aperture=1 is the previously implicit adjacent-channel finite difference control; aperture=2.5 implements the 10m/4m DAS gauge separation as a Fourier fractional finite-difference operator. A per-time spatial mean is explicitly transmitted because the gauge operator has a DC nullspace. The encoder alternates low-rank latent projection with the exact measurement-domain hard-error box, quantizes/byte-decodes latent factors, forward-applies gauge plus temporal derivative, serializes/byte-decodes the exact 2epsilon correction, and verifies final unchanged 10%-global-std max error. Fixed definitions aggregate eight precommitted tiles. No AI.'}
  print(json.dumps({'best':combos[:12]},indent=2),flush=True);json.dump(out,open('imperial_physical_gauge_operator.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
