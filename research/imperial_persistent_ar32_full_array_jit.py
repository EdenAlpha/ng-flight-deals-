import sys,numpy as np
from numba import njit
import imperial_persistent_ar16_full_array as m
m.P=32

@njit(cache=True)
def _build(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    for c in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            pred=int(np.rint(v));k=int(np.rint((X[c,t]-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    return R,K
@njit(cache=True)
def _decode(K,co,p,step):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int32)
    for c in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            R[c,t]=int(np.rint(v))+step*int(K[c,t])
    return R

def build(X,coef):return _build(np.ascontiguousarray(X,np.float64),np.ascontiguousarray(coef,np.float32),m.P,m.m.STEP)
def decode(K,coef):return _decode(np.ascontiguousarray(K,np.int32),np.ascontiguousarray(coef,np.float32),m.P,m.m.STEP)
m.build_continuous_k=build;m.decode_continuous=decode
if __name__=='__main__':m.main(sys.argv[1],sys.argv[2])
