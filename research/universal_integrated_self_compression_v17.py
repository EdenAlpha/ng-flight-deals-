#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_integrated_latent_oracle_v13 as o
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

STEP=267
FACTORS=(0.5,1,2,4,8,16,32,64,128)
TOP_EXACT=4
MAGIC=b'IS17'


def sz_latent_encode(Y,tol,tr):
    A=np.ascontiguousarray((Y.T if tr else Y).astype(np.float32))
    cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(tol)
    b,_=sz.compress(A,cfg);payload=np.asarray(b,np.uint8).tobytes()
    blob=struct.pack('<4sBI',MAGIC,1 if tr else 0,len(payload))+payload
    R=sz_latent_decode(blob,Y.shape)
    return blob,R


def sz_latent_decode(blob,shape):
    magic,tr,n=struct.unpack_from('<4sBI',blob,0)
    if magic!=MAGIC or 9+n!=len(blob):raise RuntimeError('latent header')
    bb=np.frombuffer(blob,dtype=np.uint8,count=n,offset=9).copy()
    ashape=(shape[1],shape[0]) if tr else shape
    R,_=sz.decompress(bb,np.float32,ashape);R=np.asarray(R,np.float64)
    return R.T if tr else R


def recursive(X,offs,cod,C):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=u.sample_pred(R,c,t,cod,offs)+int(np.rint(C[c,t]))
            k=int(np.rint((float(X[c,t])-float(p))/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);target=szb/2.0
    offs,co,sbest,shist=u.search_sample(X);base_total,R0,K0,mb,ob,cod=sbest
    P0=R0.astype(np.float64)-STEP*K0.astype(np.float64);E0=X-P0
    Y=o.integrate(E0,0)
    overhead=fair.COMMON_HEADER+1+len(ob)+len(mb)
    rows=[]
    for factor in FACTORS:
        tol=float(eps*factor)
        for tr in (False,True):
            blob,Yh=sz_latent_encode(Y,tol,tr);C=o.differentiate(Yh,0);R,K=recursive(X,offs,cod,C)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('hard',factor,tr,me,eps))
            fast=int(m.encode_k(K)[0]);total=overhead+len(blob)+fast
            row={'factor':factor,'latent_abs_error':tol,'latent_orientation':'T' if tr else 'CT','latent_bytes':len(blob),'fast_field_bytes':fast,'fast_total_bytes':int(total),'fast_gain_vs_sz3':float(szb/total),'zero_fraction':float(np.mean(K==0)),'maxerr':me}
            rows.append((total,row,blob,C,K,R));print('SCREEN',json.dumps(row),flush=True)
    order=np.argsort([x[0] for x in rows])[:TOP_EXACT];exact=[]
    for ii in order:
        _,row,blob,C,K,R=rows[int(ii)];fb,Kd,detail=v7.super_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError('K replay')
        Yd=sz_latent_decode(blob,Y.shape);Cd=o.differentiate(Yd,0);Rd=np.zeros_like(K)
        for t in range(K.shape[1]):
            for c in range(K.shape[0]):
                p=u.sample_pred(Rd,c,t,cod,offs)+int(np.rint(Cd[c,t]));Rd[c,t]=p+STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R):raise RuntimeError('source replay')
        me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=overhead+len(blob)+int(fb)
        z={**row,'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':float(szb/total),'crosses_2x':bool(total<=target),'maxerr':me};exact.append(z);print('EXACT',json.dumps(z),flush=True)
    best=min(exact,key=lambda z:z['bytes'])
    out={'kind':'universal-integrated-self-compression-v17','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'base_bytes':int(base_total),'base_offsets':[list(x) for x in offs],'best':best,'exact':exact,'screens':[x[1] for x in rows],
         'principle':'Keep the SZ-style predictor/quantizer skeleton but recursively compress a transformed version of its own prediction error. The encoder cumulatively integrates the causal prediction-error field across channels, compresses that smooth latent field coarsely with an ordinary error-bounded SZ stream, physically charges every latent byte, differentiates the decoded latent into a predictor correction, and then encodes only the remaining exact step-267 correction indices. Decoder replays the latent stream, correction, residual indices, and source reconstruction with the unchanged hard error bound.'}
    json.dump(out,open('universal_integrated_self_compression_v17.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
