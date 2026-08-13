import json,sys,math
import h5py,numpy as np
from scipy.special import ndtri
from scipy.spatial import cKDTree
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;END=8192;L=8;STEP=267
TARGET_CH=np.arange(0,128,4,dtype=np.int64)
N=1<<22; NTARGET=512; MIX=4
MASK=np.uint64(0xffffffffffffffff)

def splitmix64(x):
    x=(x+np.uint64(0x9E3779B97F4A7C15))&MASK
    z=x.copy();z=((z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9))&MASK
    z=((z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB))&MASK
    return z^(z>>np.uint64(31))

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/STEP).astype(np.int64);R[:,t]=pred+STEP*k
    if float(np.max(np.abs(X[:,:TRAIN]-R)))>eps*(1+1e-10):raise RuntimeError('prefix hard')
    return int(mb),cd,R

def openloop(state,co):
    s=state.astype(np.int64).copy();base=np.empty(L,np.int64)
    for i in range(L):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*s[-1-j]
        y=int(np.rint(v));base[i]=y;s[:-1]=s[1:];s[-1]=y
    return base

def train_vectors(X,R,co):
    out=[]
    for c in range(C):
        for t in range(P,TRAIN-L+1,L):out.append(X[c,t:t+L]-openloop(R[c,t-P:t],co))
    return np.asarray(out,np.float64)

def heldout_vectors(X,R0,co,eps):
    V=[]
    for c in TARGET_CH:
        state=R0[c,-P:].copy()
        for t in range(TRAIN,END,L):
            base=openloop(state,co);src=X[c,t:t+L];V.append(src-base)
            for q in range(L):
                vv=float(co[-1])
                for j in range(P):vv+=float(co[j])*state[-1-j]
                pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/STEP));rr=pred+STEP*k
                if abs(float(src[q])-rr)>eps*(1+1e-10):raise RuntimeError('incumbent hard')
                state[:-1]=state[1:];state[-1]=rr
    V=np.asarray(V,np.float64)
    sel=np.linspace(0,len(V)-1,NTARGET,dtype=np.int64)
    return V,V[sel],sel

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError('sz hard')
        z=(int(b.size),me,'T' if tr else 'CT')
        if best is None or z[0]<best[0]:best=z
    return best
