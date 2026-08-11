import json, subprocess, numpy as np
from pysz import sz,szConfig,szErrorBoundMode
meta=json.load(open('data/forge_subcube_meta.json'))
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape'])
eps=float(meta['eps_10pct_std']);raw=X.nbytes;N=X.shape[-1]

def z(a):
    return len(subprocess.run(['zstd','-q','-f','-19','-c'],input=np.ascontiguousarray(a).tobytes(),stdout=subprocess.PIPE,check=True).stdout)
def si(a):
    lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0
    return a.astype(np.int8) if lo>=-128 and hi<=127 else a.astype(np.int16) if lo>=-32768 and hi<=32767 else a.astype(np.int32)
def comp(A,e):
    A=np.ascontiguousarray(A,dtype=np.float32);c=szConfig();c.errorBoundMode=szErrorBoundMode.ABS;c.absErrorBound=float(e);b,_=sz.compress(A,c);D,_=sz.decompress(b,np.float32,A.shape);return int(b.size),D

def make_core(K,Nc):
    F=np.fft.rfft(X,axis=2)
    G=np.zeros(X.shape[:2]+(Nc//2+1,),np.complex64)
    kk=min(K,G.shape[-1]-2)
    # Scale DFT coefficients for inverse transform of length Nc.
    G[:,:,:kk+1]=F[:,:,:kk+1].astype(np.complex64)*(Nc/N)
    C=np.fft.irfft(G,n=Nc,axis=2).astype(np.float32)
    return C,kk

def upsample(C,kk):
    Fc=np.fft.rfft(C,axis=2)
    G=np.zeros(X.shape[:2]+(N//2+1,),np.complex64)
    G[:,:,:kk+1]=Fc[:,:,:kk+1].astype(np.complex64)*(N/C.shape[-1])
    return np.fft.irfft(G,n=N,axis=2).astype(np.float32)

def cert(carrier):
    Q=np.rint((X-carrier)/(2*eps)).astype(np.int16);R=carrier+Q.astype(np.float32)*(2*eps);m=Q!=0
    opts=[z(si(Q)),z(si(np.transpose(Q,(2,0,1)))),z(si(np.transpose(Q,(0,2,1))))]
    for A in [Q,np.transpose(Q,(2,0,1)),np.transpose(Q,(0,2,1))]:
        mm=A!=0;vv=A[mm];opts.append(z(np.packbits(mm.ravel(),bitorder='little'))+(z(si(vv)) if vv.size else 0))
    # Event/time-difference form per trace can be better for sparse high-frequency excursions.
    E=np.diff(Q,axis=2,prepend=Q[:,:,:1]);opts += [z(si(E)),z(si(np.transpose(E,(2,0,1))))]
    return min(opts),float(m.mean()),float(np.max(np.abs(X-R))),int(Q.min()),int(Q.max())

b,D=comp(X,eps);print('BASE',json.dumps({'bytes':b,'ratio':raw/b,'maxerr':float(np.max(np.abs(X-D)))}),flush=True)
rows=[]
configs=[]
for Nc in [96,112,128,144,160,176,192,224,256]:
    ny=Nc//2
    for margin in [1,4,8,12]:
        K=ny-margin
        if K>=20:configs.append((K,Nc))
configs=sorted(set(configs))
for K,Nc in configs:
    C,kk=make_core(K,Nc)
    exact=upsample(C,kk);tail=float(np.mean(np.abs(X-exact)>eps));rmse=float(np.sqrt(np.mean((X-exact).astype(np.float64)**2)))
    for beta in [.125,.25,.5,1,2,4,8]:
        cb,Cd=comp(C,beta*eps);carrier=upsample(Cd,kk);corr,nz,me,qmin,qmax=cert(carrier);total=cb+corr+64
        r={'K':kk,'Nc':Nc,'beta':beta,'bytes':total,'ratio':raw/total,'core_bytes':cb,'cert_bytes':corr,'cert_nz':nz,'maxerr':me,'qmin':qmin,'qmax':qmax,'ideal_tail_gt_eps':tail,'ideal_core_rmse':rmse};rows.append(r);print('BANDCORE',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['bytes']);best=rows[:30];print('BEST',json.dumps(best,indent=2),flush=True)
open('forge_bandcore_results.json','w').write(json.dumps({'eps':eps,'raw':raw,'best':best},indent=2))
