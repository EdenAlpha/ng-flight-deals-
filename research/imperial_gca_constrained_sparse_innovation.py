import json, math, sys
import h5py
import numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_gca_sparse_intervention as sp

C=128;NT=30000;C0=512;P=32;RAD=133;HEADER=64
INC=2468803;MATCHED_SZ3=2767977

@njit(cache=True)
def bitcost(e,lam):
    a=abs(int(e))
    if a==0:return 0.0
    q=0
    while a>1:q+=1;a//=2
    return float(lam + 2*q + 2)

@njit(cache=True)
def init_q(R,co):
    Cc,T=R.shape;Q=np.zeros((Cc,T),np.float64)
    for c in range(Cc):
        for t in range(T):
            if t<P:Q[c,t]=0.0
            else:
                z=float(co[0])
                for j in range(P):z += float(co[j+1])*float(R[c,t-1-j])
                Q[c,t]=z
    return Q

@njit(cache=True)
def objective(R,Q,lam):
    s=0.0
    for c in range(R.shape[0]):
        for t in range(R.shape[1]):s+=bitcost(int(R[c,t])-int(np.rint(Q[c,t])),lam)
    return s/R.size

@njit(cache=True)
def optimize(Xi,co,R,lam,sweeps):
    Q=init_q(R,co);T=R.shape[1]
    hist=np.zeros(sweeps+1,np.float64);hist[0]=objective(R,Q,lam)
    b=np.asarray(co[1:],np.float64)
    for sw in range(sweeps):
        if sw%2==0:
            start=0;stop=T;step=1
        else:
            start=T-1;stop=-1;step=-1
        t=start
        while t!=stop:
            for c in range(C):
                old=int(R[c,t]);x=int(Xi[c,t]);lo=x-RAD;hi=x+RAD
                best=1e300;bestr=old
                # 7 public grid points plus clipped current predictor and old value.
                for qi in range(9):
                    if qi<7:cand=lo+(266*qi)//6
                    elif qi==7:
                        cand=int(np.rint(Q[c,t]));
                        if cand<lo:cand=lo
                        elif cand>hi:cand=hi
                    else:cand=old
                    delta=cand-old;sc=0.0
                    hend=min(P,T-1-t)
                    for h in range(hend+1):
                        ss=t+h
                        qn=Q[c,ss] if h==0 else Q[c,ss]+b[h-1]*delta
                        pp=int(np.rint(qn));ee=(cand if h==0 else int(R[c,ss]))-pp
                        sc+=bitcost(ee,lam)
                    if sc<best:
                        best=sc;bestr=cand
                if bestr!=old:
                    delta=bestr-old;R[c,t]=bestr;hend=min(P,T-1-t)
                    for h in range(1,hend+1):Q[c,t+h]+=b[h-1]*delta
            t+=step
        hist[sw+1]=objective(R,Q,lam)
    return R,hist

@njit(cache=True)
def exact_innovation(R,co):
    E=np.zeros(R.shape,np.int32)
    for c in range(R.shape[0]):
        for t in range(R.shape[1]):
            p=sp.pred(co,R,c,t);E[c,t]=int(R[c,t])-p
    return E

def physical_size(E,model):
    mz,cb,cc,nev,_=sp.pack_j(E);return HEADER+len(model)+len(mz)+len(cb),mz,cb,cc,nev

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if int(math.floor(eps))!=RAD or np.max(np.abs(X-Xi))>1e-6:raise RuntimeError(('source/eps',eps))
    _,co=ah.fits(X);model,cod=cg.model_frame(co)
    # Public prefix chooses the event penalty; no full-object oracle selection.
    screenT=4096;Xs=Xi[:,:screenT]
    Rbase_s,_,_=sp.encode_policy(Xs if False else Xi,cod,0,0)  # compile shared controller
    # Rebuild a compact prefix greedy start locally from the full greedy result.
    rows=[]
    for lam in (1,2,4,8):
        R0=np.asarray(Rbase_s[:,:screenT],np.int32).copy();Rs,h=optimize(Xs,cod,R0,lam,1);Es=exact_innovation(Rs,cod)
        ev=float(np.mean(Es!=0));hz=sp.h0(Es);score=hz+ev
        r={'lambda':lam,'prefix_event_fraction':ev,'prefix_innovation_h0':hz,'prefix_score':score,'objective_history':[float(x) for x in h]};rows.append(r);print(json.dumps({'screen':r}),flush=True)
    lam=min(rows,key=lambda r:r['prefix_score'])['lambda']
    R0,_,_=sp.encode_policy(Xi,cod,0,0);R,h=optimize(Xi,cod,R0,int(lam),2);E=exact_innovation(R,cod)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total,mz,cb,cc,nev=physical_size(E,model);Ed=sp.unpack_j(mz,cb,cc,nev,C*NT);Rd=sp.decode_j(Ed,cod)
    if not np.array_equal(Ed,E):raise RuntimeError('innovation replay')
    if not np.array_equal(Rd,R):raise RuntimeError('reconstruction replay')
    me2=float(np.max(np.abs(X-Rd.astype(np.float64))))
    out={'bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'matched_sz3_bytes':MATCHED_SZ3,'gain_vs_sz3':MATCHED_SZ3/total,'two_x_target_bytes':MATCHED_SZ3/2.0,'bytes_above_2x_target':total-MATCHED_SZ3/2.0,'lambda':int(lam),'event_count':int(nev),'event_fraction':float(nev/(C*NT)),'innovation_h0_bps':sp.h0(E),'mask_zstd_bytes':len(mz),'correction_zstd_bytes':len(cb),'correction_codec':int(cc),'objective_history':[float(x) for x in h],'maxerr':me2,'model_bytes':len(model),'header_bytes':HEADER,'prefix_screens':rows,'scope':'Globally constrained sparse-innovation GCA search. Reconstruction samples may take any integer value inside their source ±133 interval. Coordinate descent moves each legal reconstruction value to reduce the joint code-cost surrogate of its own AR32 innovation and all next 32 innovations it influences. The optimization policy is encoder-only and costs no decoder bits; decoder receives only the serialized AR32 model plus a physical compressed exact innovation field, independently replays all 3.84M samples, and verifies the unchanged hard-error bound.'}
    json.dump(out,open('imperial_gca_constrained_sparse_innovation.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
