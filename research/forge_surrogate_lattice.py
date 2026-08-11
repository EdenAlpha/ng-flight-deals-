import json
import numpy as np
from pysz import sz, szConfig, szErrorBoundMode

meta=json.load(open('data/forge_subcube_meta.json'))
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(meta['shape'])
eps=float(meta['eps_10pct_std']); raw=X.nbytes

def comp(A,e):
    A=np.ascontiguousarray(A,dtype=np.float32)
    c=szConfig(); c.errorBoundMode=szErrorBoundMode.ABS; c.absErrorBound=float(e)
    b,_=sz.compress(A,c); D,_=sz.decompress(b,np.float32,A.shape)
    return int(b.size),D

def quant(A,qstep,phase):
    return (phase+np.rint((A-phase)/qstep)*qstep).astype(np.float32)

def lorenzo_cost(A):
    H=A[1:,1:,1:]-A[:-1,1:,1:]-A[1:,:-1,1:]-A[1:,1:,:-1]+A[:-1,:-1,1:]+A[:-1,1:,:-1]+A[1:,:-1,:-1]-A[:-1,:-1,:-1]
    return float(np.mean(np.abs(H)))

def tv_cost(A):
    return float(np.mean(np.abs(np.diff(A,axis=0)))+np.mean(np.abs(np.diff(A,axis=1)))+np.mean(np.abs(np.diff(A,axis=2))))

def shape_blocks(df,bs,P,metric):
    delta=df*eps; qstep=2*delta; Y=np.empty_like(X); phases=np.arange(P)*qstep/P
    bi,bj,bt=bs
    for i in range(0,X.shape[0],bi):
      for j in range(0,X.shape[1],bj):
       for t in range(0,X.shape[2],bt):
        B=X[i:i+bi,j:j+bj,t:t+bt]; best=None
        for ph in phases:
            Q=quant(B,qstep,float(ph)); cost=lorenzo_cost(Q) if metric==0 else tv_cost(Q)
            if best is None or cost<best[0]: best=(cost,Q)
        Y[i:i+B.shape[0],j:j+B.shape[1],t:t+B.shape[2]]=best[1]
    return Y,float(np.max(np.abs(Y-X)))

b,D=comp(X,eps)
print('BASE',json.dumps({'bytes':b,'ratio':raw/b,'maxerr':float(np.max(np.abs(X-D)))}),flush=True)
rows=[]
for df in [.1,.2,.3,.4,.5,.6,.7,.8,.9]:
    delta=df*eps; qstep=2*delta; e2=eps-delta
    for P in [4,8,16]:
        local=[]
        for ph in np.arange(P)*qstep/P:
            Y=quant(X,qstep,float(ph)); bb,Z=comp(Y,e2)
            r={'kind':'global','delta_frac':df,'P':P,'phase_frac':float(ph/qstep),'bytes':bb+16,'ratio':raw/(bb+16),'morph_max':float(np.max(np.abs(X-Y))),'final_maxerr':float(np.max(np.abs(X-Z)))}
            rows.append(r); local.append(r)
        print('GLOBAL',json.dumps(min(local,key=lambda r:r['bytes'])),flush=True)
for df in [.2,.35,.5,.65,.8]:
  for bs in [(8,8,32),(8,8,64),(16,16,64),(16,16,128),(32,32,128)]:
   for P in [4,8,16]:
    for metric in [0,1]:
        Y,mm=shape_blocks(df,bs,P,metric); bb,Z=comp(Y,eps-df*eps)
        r={'kind':'block','delta_frac':df,'bs':bs,'P':P,'metric':metric,'bytes':bb+24,'ratio':raw/(bb+24),'morph_max':mm,'final_maxerr':float(np.max(np.abs(X-Z)))}
        rows.append(r); print('BLOCK',json.dumps(r),flush=True)
rows.sort(key=lambda r:r['bytes'])
print('BEST',json.dumps(rows[:25],indent=2),flush=True)
