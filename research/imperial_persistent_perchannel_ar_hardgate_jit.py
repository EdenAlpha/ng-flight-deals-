import sys,numpy as np
from numba import njit
import imperial_persistent_perchannel_ar as m

@njit(cache=True)
def _build_shared(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int64);K=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        for c in range(nc):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            if v>2.0e9:v=2.0e9
            elif v< -2.0e9:v=-2.0e9
            pred=int(np.rint(v));k=int(np.rint((X[c,t]-pred)/step));K[c,t]=k;R[c,t]=pred+step*k
    return R,K

@njit(cache=True)
def _build_per(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int64);K=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        for c in range(nc):
            v=0.0
            if t>=p:
                v=float(co[c,p])
                for j in range(p):v+=float(co[c,j])*float(R[c,t-1-j])
            if v>2.0e9:v=2.0e9
            elif v< -2.0e9:v=-2.0e9
            pred=int(np.rint(v));k=int(np.rint((X[c,t]-pred)/step));K[c,t]=k;R[c,t]=pred+step*k
    return R,K

@njit(cache=True)
def _decode_shared(K,co,p,step):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        for c in range(nc):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            if v>2.0e9:v=2.0e9
            elif v< -2.0e9:v=-2.0e9
            pred=int(np.rint(v));R[c,t]=pred+step*K[c,t]
    return R

@njit(cache=True)
def _decode_per(K,co,p,step):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int64)
    for t in range(nt):
        for c in range(nc):
            v=0.0
            if t>=p:
                v=float(co[c,p])
                for j in range(p):v+=float(co[c,j])*float(R[c,t-1-j])
            if v>2.0e9:v=2.0e9
            elif v< -2.0e9:v=-2.0e9
            pred=int(np.rint(v));R[c,t]=pred+step*K[c,t]
    return R

def build_k_jit(X,cd,p,kind):
    X=np.ascontiguousarray(X,np.float64);co=np.ascontiguousarray(cd,np.float32)
    R,K=(_build_shared(X,co,p,m.m.STEP) if kind=='shared' else _build_per(X,co,p,m.m.STEP))
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>128.000001:raise RuntimeError(('construction hard error',p,kind,me))
    return R,K,me

def decode_k_jit(K,cd,p,kind):
    K=np.ascontiguousarray(K,np.int64);co=np.ascontiguousarray(cd,np.float32)
    return _decode_shared(K,co,p,m.m.STEP) if kind=='shared' else _decode_per(K,co,p,m.m.STEP)

m.build_k=build_k_jit;m.decode_k=decode_k_jit;m.SPECS=(('hard',512),)
if __name__=='__main__':m.main(sys.argv[1])
