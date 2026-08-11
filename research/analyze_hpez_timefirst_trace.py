import json,numpy as np,zstandard as zstd
meta=json.load(open('data/forge_subcube_meta.json'));eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(64,64,512).astype(np.float64)
R=np.fromfile('diagnostic_rec.bin','<f4').reshape(64,64,512).astype(np.float64)
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64);center=32768
phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Qh=phys.reshape(64,64,512);Z=zstd.ZstdCompressor(level=19)

def H(a):
 _,c=np.unique(a,return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def zs(a):
 a=np.asarray(a);lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dt=np.int8 if lo>=-128 and hi<=127 else np.int16 if lo>=-32768 and hi<=32767 else np.int32
 raw=len(Z.compress(a.astype(dt).tobytes()));m=a!=0;mv=len(Z.compress(np.packbits(m,bitorder='little').tobytes()+a[m].astype(dt).tobytes()));return min(raw,mv),raw,mv
def metric(Y,P,coeff_bytes=0):
 Q=np.rint((Y-P)/(2*eps)).astype(np.int16);rec=P+Q*(2*eps);b,raw,mv=zs(Q)
 return {'n':int(Q.size),'zero_frac':float(np.mean(Q==0)),'H0':H(Q),'stream_bytes':b,'raw_zstd':raw,'maskval_zstd':mv,'model_bytes':int(coeff_bytes),'total_bytes':int(b+coeff_bytes),'maxerr':float(np.max(np.abs(Y-rec)))}
def get_traces(kind):
 # Exclude final one-sided spatial boundary: targets 1..61 odd, orthogonal coordinate 0..62 even. Parents are previous spatial grid and become full-time after legal time-first p1 refinement.
 if kind=='x':
  I=np.arange(1,62,2);J=np.arange(0,64,2);Y=X[I[:,None],J[None,:],:].reshape(-1,512);L=R[(I-1)[:,None],J[None,:],:].reshape(-1,512);RR=R[(I+1)[:,None],J[None,:],:].reshape(-1,512)
  # Far coarse parents where available; use nearest primary duplicate at boundaries so dimensionality stays fixed.
  im3=np.maximum(I-3,0);ip3=np.minimum(I+3,62);L3=R[im3[:,None],J[None,:],:].reshape(-1,512);R3=R[ip3[:,None],J[None,:],:].reshape(-1,512)
  Qbase=Qh[I[:,None],J[None,:],:].reshape(-1,512)
 else:
  I=np.arange(0,64,2);J=np.arange(1,62,2);Y=X[I[:,None],J[None,:],:].reshape(-1,512);L=R[I[:,None],(J-1)[None,:],:].reshape(-1,512);RR=R[I[:,None],(J+1)[None,:],:].reshape(-1,512)
  jm3=np.maximum(J-3,0);jp3=np.minimum(J+3,62);L3=R[I[:,None],jm3[None,:],:].reshape(-1,512);R3=R[I[:,None],jp3[None,:],:].reshape(-1,512)
  Qbase=Qh[I[:,None],J[None,:],:].reshape(-1,512)
 return Y,L,RR,L3,R3,Qbase

def fir_fit(Y,L,RR,L3,R3,radius,family):
 ntr,N=Y.shape;offs=np.arange(-radius,radius+1);valid=np.arange(radius,N-radius);cols=[];names=[]
 for k in offs:
  A=.5*(L[:,valid+k]+RR[:,valid+k]);cols.append(A.ravel());names.append(f'A1{k}')
  if 'diff' in family:cols.append(.5*(RR[:,valid+k]-L[:,valid+k]).ravel());names.append(f'D1{k}')
 if 'far' in family:
  for k in offs:
   cols.append(.5*(L3[:,valid+k]+R3[:,valid+k]).ravel());names.append(f'A3{k}')
   if 'diff' in family:cols.append(.5*(R3[:,valid+k]-L3[:,valid+k]).ravel());names.append(f'D3{k}')
 cols.append(np.ones(ntr*len(valid)));names.append('bias');A=np.stack(cols,1);yy=Y[:,valid].ravel();G=A.T@A;rhs=A.T@yy
 # Very light deterministic ridge for conditioning; bias unregularized.
 scale=np.trace(G)/len(names);reg=1e-8*scale*np.eye(len(names));reg[-1,-1]=0
 w=np.linalg.solve(G+reg,rhs);P=np.empty_like(Y);P[:]=.5*(L+RR);P[:,valid]=(A@w).reshape(ntr,-1)
 # Search one transmitted scalar phase/bias shift against actual compressed bytes.
 best=None
 for frac in np.linspace(-1,1,17):
  pp=P+frac*eps;r=metric(Y,pp,4*len(w)+36)
  r['phase_frac_eps']=float(frac)
  if best is None or r['total_bytes']<best['total_bytes']:best=r
 return best,w,names

def freq_wiener(Y,L,RR,L3,R3,use_far=False):
 FY=np.fft.rfft(Y,axis=1);FL=np.fft.rfft(L,axis=1);FR=np.fft.rfft(RR,axis=1);FL3=np.fft.rfft(L3,axis=1);FR3=np.fft.rfft(R3,axis=1);nf=FY.shape[1];Pspec=np.empty_like(FY);co=[]
 for k in range(nf):
  feats=[.5*(FL[:,k]+FR[:,k]),.5*(FR[:,k]-FL[:,k])]
  if use_far:feats += [.5*(FL3[:,k]+FR3[:,k]),.5*(FR3[:,k]-FL3[:,k])]
  A=np.stack(feats,1);G=A.conj().T@A;rhs=A.conj().T@FY[:,k];lam=1e-7*np.trace(G).real/max(1,G.shape[0]);w=np.linalg.solve(G+lam*np.eye(G.shape[0]),rhs);Pspec[:,k]=A@w;co.append(w)
 P=np.fft.irfft(Pspec,n=512,axis=1).real
 # Complex64 coefficients transmitted exactly enough for deterministic decoder model accounting. (Actual implementation later must define coefficient quantization.)
 model_bytes=sum(len(w) for w in co)*8+64
 return metric(Y,P,model_bytes),co

def phase_mid(Y,L,RR,mode):
 FL=np.fft.rfft(L,axis=1);FR=np.fft.rfft(RR,axis=1);al=np.abs(FL);ar=np.abs(FR);cross=FR*np.conj(FL);d=np.unwrap(np.angle(cross),axis=1);phase=np.angle(FL)+.5*d
 amp=np.sqrt(al*ar) if mode=='geom' else .5*(al+ar)
 P=np.fft.irfft(amp*np.exp(1j*phase),n=512,axis=1).real
 return metric(Y,P,32)
rows=[]
for kind in ['x','y']:
 Y,L,RR,L3,R3,Qbase=get_traces(kind);baseq=np.where(Qbase==0,0,Qbase-center).astype(np.int16);bb,br,bm=zs(baseq)
 rows.append({'kind':kind,'method':'existing_HPEZ_same_full_traces','metrics':{'n':int(baseq.size),'center_frac':float(np.mean(Qbase==center)),'H0':H(baseq),'stream_bytes':bb,'raw_zstd':br,'maskval_zstd':bm}})
 rows.append({'kind':kind,'method':'simple_average_full_parents','metrics':metric(Y,.5*(L+RR),32)})
 for rad in [2,4,6,8,12]:
  for fam in ['avg','avg_diff','avg_far','avg_diff_far']:
   m,w,names=fir_fit(Y,L,RR,L3,R3,rad,fam);rows.append({'kind':kind,'method':f'FIR_r{rad}_{fam}','metrics':m,'features':len(w)})
 for far in [False,True]:
  m,_=freq_wiener(Y,L,RR,L3,R3,far);rows.append({'kind':kind,'method':'freq_wiener_far' if far else 'freq_wiener_near','metrics':m})
 for mode in ['geom','arith']:
  rows.append({'kind':kind,'method':f'global_phase_mid_{mode}','metrics':phase_mid(Y,L,RR,mode)})
for kind in ['x','y']:
 sub=[r for r in rows if r['kind']==kind and 'total_bytes' in r['metrics']];sub.sort(key=lambda r:r['metrics']['total_bytes']);print('TIMEFIRST_BEST',kind,json.dumps(sub[:15],indent=2),flush=True)
out={'eps':eps,'rows':rows};json.dump(out,open('hpez_timefirst_trace_analysis.json','w'),indent=2)
