import json, math, subprocess, numpy as np, segyio
from numba import njit
from pysz import sz, szConfig, szErrorBoundMode
p='2018-19 Reflection Processing/3D Survey/Forge3d_ANI_PSDM_Stack_UnEnh.segy'
with segyio.open(p,'r',strict=False,ignore_geometry=True) as f:
    tr=np.asarray(f.trace.raw[:],dtype=np.float32)
X=np.ascontiguousarray(tr.reshape(170,213,1001)); del tr
raw=X.nbytes; std=float(np.std(X,dtype=np.float64)); eps=.1*std

def z(a):
    return len(subprocess.run(['zstd','-q','-f','-19','-T0','-c'],input=np.ascontiguousarray(a).tobytes(),stdout=subprocess.PIPE,check=True).stdout)
def si(q):
    mn=int(q.min()) if q.size else 0; mx=int(q.max()) if q.size else 0
    return q.astype(np.int8) if mn>=-128 and mx<=127 else q.astype(np.int16) if mn>=-32768 and mx<=32767 else q.astype(np.int32)
def arcoef(P):
    S=X[::4,::4].astype(np.float64); den=float(np.sum(S*S)); r=[1.0]
    for k in range(1,P+1): r.append(float(np.sum(S[:,:,k:]*S[:,:,:-k])/den))
    T=np.empty((P,P),float)
    for i in range(P):
        for j in range(P): T[i,j]=r[abs(i-j)]
    return np.linalg.solve(T,np.asarray(r[1:P+1])).astype(np.float64),r

@njit(cache=True)
def encode(X,eps,alpha,A):
    ni,nj,nt=X.shape; P=len(A); step=alpha*eps
    Q=np.empty((ni,nj,nt),np.int32); R=np.empty((ni,nj,nt),np.float32); H=np.zeros((ni,nj,nt),np.int16)
    for i in range(ni):
        for j in range(nj):
            for t in range(nt):
                temp=0.0
                for k in range(P):
                    tt=t-k-1
                    if tt>=0: temp += A[k]*Q[i,j,tt]
                boundary=(i==0 or j==0 or t<P)
                if boundary: pf=X[i,j,t]/step
                else: pf=temp+R[i-1,j,t]+R[i,j-1,t]-R[i-1,j-1,t]
                q=int(round(pf)); lo=math.ceil((X[i,j,t]-eps)/step-1e-7); hi=math.floor((X[i,j,t]+eps)/step+1e-7)
                if q<lo: q=lo
                elif q>hi: q=hi
                Q[i,j,t]=q; R[i,j,t]=q-temp
                if not boundary: H[i,j,t]=q-int(round(pf))
    return Q,H,step

cfg=szConfig(); cfg.errorBoundMode=szErrorBoundMode.ABS; cfg.absErrorBound=eps
sb,_=sz.compress(X,cfg); SZ,_=sz.decompress(sb,np.float32,X.shape)
print('SZ3',json.dumps({'bytes':int(sb.size),'ratio':raw/int(sb.size),'maxerr':float(np.max(np.abs(X-SZ)))}),flush=True)
rows=[]
for P in [1,2,3,4,6,8]:
    A,r=arcoef(P); print('AR',P,'A',A.tolist(),'r',r,flush=True)
    for alpha in [1.95,1.9,1.75,1.5,1.25]:
        Q,H,step=encode(X,eps,alpha,A)
        bd=np.concatenate((Q[0].reshape(-1),Q[1:,0].reshape(-1),Q[1:,1:,:P].reshape(-1)))
        bbytes=z(si(bd)); Z=H[1:,1:,P:]; m=Z!=0
        dense=min(z(si(Z)),z(si(np.transpose(Z,(2,0,1)))),z(si(np.transpose(Z,(0,2,1)))))
        sparse=z(np.packbits(m.reshape(-1),bitorder='little'))+(z(si(Z[m])) if m.any() else 0)
        syndrome=min(dense,sparse); model=4*P+32; total=bbytes+syndrome+model
        me=float(np.max(np.abs(X-Q.astype(np.float32)*step)))
        row={'P':P,'A':A.tolist(),'alpha':alpha,'bytes':total,'ratio':raw/total,'boundary':bbytes,'syndrome':syndrome,'nonzero':float(m.mean()),'maxerr':me,'model':model}
        rows.append(row); print('WAVEANN',json.dumps(row),flush=True)
rows.sort(key=lambda r:r['bytes']); print('BEST',json.dumps(rows[:15],indent=2),flush=True)
open('forge_waveann.json','w').write(json.dumps(rows[:30],indent=2))
