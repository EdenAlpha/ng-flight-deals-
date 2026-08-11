import json, subprocess, os, numpy as np
meta=json.load(open('data/forge_subcube_meta.json'));X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape']);eps=float(meta['eps_10pct_std']);raw=X.nbytes;N=X.shape[-1];F=np.fft.rfft(X,axis=2)
BIN=os.environ['HPEZ_BIN']
def z(a):return len(subprocess.run(['zstd','-q','-f','-19','-T0','-c'],input=np.ascontiguousarray(a).tobytes(),stdout=subprocess.PIPE,check=True).stdout)
def si(a):
 lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0
 return a.astype(np.int8) if lo>=-128 and hi<=127 else a.astype(np.int16) if lo>=-32768 and hi<=32767 else a.astype(np.int32)
def make_core(K,Nc):
 G=np.zeros(X.shape[:2]+(Nc//2+1,),np.complex64);G[:,:,:K+1]=F[:,:,:K+1].astype(np.complex64)*(Nc/N);return np.fft.irfft(G,n=Nc,axis=2).astype('<f4')
def up(C,K):
 Fc=np.fft.rfft(C,axis=2);G=np.zeros(X.shape[:2]+(N//2+1,),np.complex64);G[:,:,:K+1]=Fc[:,:,:K+1].astype(np.complex64)*(N/C.shape[-1]);return np.fft.irfft(G,n=N,axis=2).astype(np.float32)
def cert(M):
 Q=np.rint((X-M)/(2*eps)).astype(np.int16);R=M+Q.astype(np.float32)*(2*eps);m=Q!=0;opts=[z(si(Q)),z(si(np.transpose(Q,(2,0,1))))]
 for A in [Q,np.transpose(Q,(2,0,1))]:
  mm=A!=0;vv=A[mm];opts.append(z(np.packbits(mm.ravel(),bitorder='little'))+(z(si(vv)) if vv.size else 0))
 E=np.diff(Q,axis=2,prepend=Q[:,:,:1]);opts += [z(si(E)),z(si(np.transpose(E,(2,0,1))))]
 return min(opts),float(m.mean()),float(np.max(np.abs(X-R)))
rows=[]
for K,Nc in [(72,160),(80,176),(80,192),(88,208),(96,224)]:
 C=make_core(K,Nc);C.tofile('core.bin')
 for beta in [.25,.5,1.0,2.0,4.0]:
  cb=f'c_{K}_{Nc}_{beta}.hpez';out=f'o_{K}_{Nc}_{beta}.bin';bound=beta*eps
  subprocess.run([BIN,'-f','-i','core.bin','-z',cb,'-3',str(Nc),'64','64','-M','ABS',str(bound),'-q','4'],check=True,stdout=subprocess.DEVNULL)
  subprocess.run([BIN,'-f','-z',cb,'-o',out,'-3',str(Nc),'64','64'],check=True,stdout=subprocess.DEVNULL)
  D=np.fromfile(out,'<f4').reshape(64,64,Nc);M=up(D,K);cc,nz,me=cert(M);coreb=os.path.getsize(cb);total=coreb+cc+64
  r={'K':K,'Nc':Nc,'beta':beta,'bytes':total,'ratio':raw/total,'core_bytes':coreb,'cert_bytes':cc,'cert_nz':nz,'maxerr':me};rows.append(r);print('HPEZ_BAND',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['bytes']);open('forge_bandcore_hpez_results.json','w').write(json.dumps({'eps':eps,'raw':raw,'best':rows[:30]},indent=2));print('BEST',json.dumps(rows[:15],indent=2),flush=True)
