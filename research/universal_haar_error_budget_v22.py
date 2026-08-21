#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

LEVELS=(1,2,3,4,5)
POWERS=(0.0,0.5,1.0,1.5)
SAFETY=.98
HEADER_BASE=16
BAND_HEADER=12

def fwd(A,axis,L):
    a=np.asarray(A,np.float64);details=[]
    for _ in range(L):
        even=np.take(a,np.arange(0,a.shape[axis],2),axis=axis);odd=np.take(a,np.arange(1,a.shape[axis],2),axis=axis)
        details.append(even-odd);a=(even+odd)/2.0
    return a,details

def inv(a,details,axis):
    x=np.asarray(a,np.float64)
    for d in details[::-1]:
        even=x+d/2.0;odd=x-d/2.0;shape=list(x.shape);shape[axis]*=2;y=np.empty(shape,np.float64)
        sl0=[slice(None)]*y.ndim;sl1=[slice(None)]*y.ndim;sl0[axis]=slice(0,None,2);sl1[axis]=slice(1,None,2);y[tuple(sl0)]=even;y[tuple(sl1)]=odd;x=y
    return x

def sz_one(A,tol):
    best=None
    for tr in (False,True):
        B=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(tol)
        b,_=sz.compress(B,cfg);payload=np.asarray(b,np.uint8).tobytes()
        if best is None or len(payload)<best[0]:best=(len(payload),tr,payload,B.shape)
    n,tr,payload,shape=best;R,_=sz.decompress(np.frombuffer(payload,np.uint8).copy(),np.float32,shape);R=np.asarray(R,np.float64);return n+(BAND_HEADER), (R.T if tr else R),tr

def weights_for(a,details,p):
    sizes=np.asarray([a.size]+[d.size for d in details],np.float64);w=sizes**p;w=SAFETY*w/w.sum();return w

def run_case(X,eps,axis,L,p):
    a,details=fwd(X,axis,L);w=weights_for(a,details,p);bands=[a]+details;rb=[];sizes=[];ors=[];tols=[]
    for j,b in enumerate(bands):
        tol=float(eps*w[j]) if j==0 else float(2*eps*w[j]);n,r,tr=sz_one(b,tol);sizes.append(n);rb.append(r);ors.append(bool(tr));tols.append(tol)
    R=inv(rb[0],rb[1:],axis);me=float(np.max(np.abs(X-R)));guarantee=float(tols[0]+.5*sum(tols[1:]));total=HEADER_BASE+sum(sizes)
    if guarantee>eps*(1+1e-12):raise RuntimeError(('guarantee',guarantee,eps))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',axis,L,p,me,eps))
    return {'axis':'time' if axis==1 else 'channel','levels':L,'allocation_power':p,'bytes':int(total),'band_bytes':[int(x) for x in sizes],'band_tolerances':tols,'orientations_T':ors,'analytic_error_ceiling':guarantee,'maxerr':me}

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);rows=[]
    for axis in (1,0):
        maxL=int(np.log2(X.shape[axis]));
        for L in LEVELS:
            if L>maxL:continue
            for p in POWERS:
                r=run_case(X,eps,axis,L,p);r['gain_vs_sz3']=float(szb/r['bytes']);r['crosses_2x']=bool(r['bytes']<=szb/2);rows.append(r);print('ROW',json.dumps(r),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-haar-error-budget-v22','shape':list(X.shape),'eps':eps,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':szb/2.0,'best':best,'rows':rows,'principle':'Apply a reversible multilevel Haar lifting transform before ordinary SZ coding. For each level a=(even+odd)/2 and d=even-odd, so source reconstruction error is bounded analytically by error(a)+0.5*sum(error(details)). Allocate 98% of the original epsilon across transformed bands, compress each band with ordinary ABS-error SZ3, charge conservative per-band headers, invert the transform, and verify the original max-error bound. No AI, no oracle information, and no seismic-specific rule.'}
    json.dump(out,open('universal_haar_error_budget_v22.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
