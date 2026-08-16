import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

T0=14488
C=32
T=1024
TRAIN=256
P=32
AR_STEP=267
REGIONS=(('hard',512),('easy',2304))
HFACS=(0.75,1.0,1.25,1.5)
# name, temporal mode (1=q_t, 2=2q_t-q_tm1), spatial p/den
LAWS=(
 ('hold',1,0,1),
 ('velocity',2,0,1),
 ('wave_1_32',2,1,32),
 ('wave_1_16',2,1,16),
 ('wave_1_8',2,1,8),
 ('wave_1_4',2,1,4),
 ('wave_1_2',2,1,2),
 ('antiwave_1_16',2,-1,16),
 ('antiwave_1_8',2,-1,8),
)
INITS=(0,1)
PASSES=3
HEADER=72
INF=np.int64(1<<60)

@njit(cache=True)
def _rdiv(n,d):
    if n>=0:return (n+d//2)//d
    return -((-n+d//2)//d)

@njit(cache=True)
def _eglen(v):
    if v>=0:u=2*v
    else:u=-2*v-1
    n=u+1;lg=0
    while n>1:n//=2;lg+=1
    return 2*lg+1

@njit(cache=True)
def _pred(Q,c,t,mode,p,den):
    qt=int(Q[c,t]);qm=int(Q[c,t-1])
    base=qt if mode==1 else 2*qt-qm
    if p:
        lap=int(Q[c-1,t])-2*qt+int(Q[c+1,t])
        base+=_rdiv(p*lap,den)
    return base

@njit(cache=True)
def _defect(Q,c,t,mode,p,den):
    return int(Q[c,t+1])-_pred(Q,c,t,mode,p,den)

@njit(cache=True)
def _all_defects(Q,mode,p,den):
    Cc,Tt=Q.shape
    D=np.empty((Cc-2,Tt-2),np.int32)
    for c in range(1,Cc-1):
        for t in range(1,Tt-1):D[c-1,t-1]=_defect(Q,c,t,mode,p,den)
    return D

@njit(cache=True)
def _best_shared(D):
    nc,nt=D.shape;H=np.zeros(nt,np.int32)
    for t in range(nt):
        best=np.int64(1<<60);bh=0
        # Exact search over observed defect values plus zero for the signed-EG objective.
        z=0
        for i in range(nc):z+=_eglen(int(D[i,t]))
        if z<best:best=z;bh=0
        for j in range(nc):
            h=int(D[j,t]);cost=0
            for i in range(nc):cost+=_eglen(int(D[i,t])-h)
            if cost<best:best=cost;bh=h
        H[t]=bh
    return H

@njit(cache=True)
def _cell_cost(Q,c,t,H,mode,p,den,use_shared):
    if c<=0 or c>=Q.shape[0]-1 or t<=0 or t>=Q.shape[1]-1:return 0
    d=_defect(Q,c,t,mode,p,den)
    h=int(H[t-1]) if use_shared else 0
    return _eglen(d-h)

@njit(cache=True)
def _local_cost(Q,c,t,H,mode,p,den,use_shared):
    s=0
    # q[c,t] participates in the next-state defect at t-1,
    # the current-time stencil at c-1,c,c+1, and the t+1 recurrence.
    if t-1>=1:s+=_cell_cost(Q,c,t-1,H,mode,p,den,use_shared)
    if t<=Q.shape[1]-2:
        s+=_cell_cost(Q,c,t,H,mode,p,den,use_shared)
        s+=_cell_cost(Q,c-1,t,H,mode,p,den,use_shared)
        s+=_cell_cost(Q,c+1,t,H,mode,p,den,use_shared)
    if t+1<=Q.shape[1]-2:s+=_cell_cost(Q,c,t+1,H,mode,p,den,use_shared)
    return s

@njit(cache=True)
def _initial(lo,hi,kind):
    Cc,Tt=lo.shape;Q=np.empty_like(lo)
    for c in range(Cc):
        for t in range(Tt):
            a=int(lo[c,t]);b=int(hi[c,t])
            if kind==0:Q[c,t]=(a+b)//2
            else:Q[c,t]=a if ((c*131+t*17)&1)==0 else b
    return Q

@njit(cache=True)
def _optimize(lo,hi,mode,p,den,use_shared,init_kind,passes):
    Q=_initial(lo,hi,init_kind)
    # Keep the causal certificate boundaries fixed; optimize every interior legal state.
    D=_all_defects(Q,mode,p,den)
    H=_best_shared(D) if use_shared else np.zeros(D.shape[1],np.int32)
    changes=0
    for _pass in range(passes):
        changed=0
        # checkerboard alternation reduces deterministic scan bias
        parity=_pass&1
        for t in range(2,Q.shape[1]):
            for cc in range(1,Q.shape[0]-1):
                c=cc if parity==0 else Q.shape[0]-1-cc
                old=int(Q[c,t]);bestq=old;best=INF
                for q in range(int(lo[c,t]),int(hi[c,t])+1):
                    Q[c,t]=q;z=_local_cost(Q,c,t,H,mode,p,den,use_shared)
                    if z<best:best=z;bestq=q
                Q[c,t]=bestq
                if bestq!=old:changed+=1;changes+=1
        D=_all_defects(Q,mode,p,den)
        if use_shared:H=_best_shared(D)
        if changed==0:break
    D=_all_defects(Q,mode,p,den)
    if use_shared:H=_best_shared(D)
    score=0;nz=0
    for c in range(D.shape[0]):
        for t in range(D.shape[1]):
            e=int(D[c,t])-(int(H[t]) if use_shared else 0)
            score+=_eglen(e)
            if e!=0:nz+=1
    return Q,D,H,score,nz,changes

def legal_q(X,eps,h):
    b=eps*(1-2e-12)
    lo=np.ceil((X-b)/h).astype(np.int32);hi=np.floor((X+b)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal interval')
    return lo,hi

def frame(A):
    fr=m.encode_k(np.ascontiguousarray(A,np.int32))
    return int(fr[0]),fr[1],np.asarray(fr[2],np.int32)

def materialize(X,eps,h,Q,D,H,law,use_shared):
    lname,mode,p,den=law
    # Certificate: first two complete time slices + two spatial side traces.
    ib,ir,IQ=frame(Q[:,:2])
    side=np.vstack([Q[0,2:],Q[-1,2:]])
    sb,sr,SQ=frame(side)
    E=D-H[None,:] if use_shared else D
    eb,er,EQ=frame(E)
    if use_shared:
        hb,hr,HQ=frame(H[None,:]);Hd=HQ[0]
    else:
        hb=0;hr='none';Hd=np.zeros(T-2,np.int32)
    Qd=np.empty_like(Q);Qd[:,:2]=IQ;Qd[0,2:]=SQ[0];Qd[-1,2:]=SQ[1]
    Dd=EQ+Hd[None,:]
    for t in range(1,T-1):
        for c in range(1,C-1):
            Qd[c,t+1]=_pred(Qd,c,t,mode,p,den)+int(Dd[c-1,t-1])
    if not np.array_equal(Qd,Q):raise RuntimeError(('certificate replay',lname,use_shared))
    R=Qd.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',lname,use_shared,me,eps))
    total=ib+sb+eb+hb+HEADER
    return {'bytes':int(total),'bps':8*total/X.size,'init_bytes':ib,'init_rep':ir,'side_bytes':sb,'side_rep':sr,'defect_bytes':eb,'defect_rep':er,'forcing_bytes':hb,'forcing_rep':hr,'maxerr':me,'defect_zero_fraction':float(np.mean(E==0)),'defect_std':float(E.std()),'forcing_nonzero_fraction':float(np.mean(H!=0)) if use_shared else 0.0}

def ar32_baseline(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(C):
        for t in range(T):
            pred=ar.predict_hist(R,c,t,cd,P,'shared');k=int(np.rint((float(X[c,t])-pred)/AR_STEP));R[c,t]=pred+AR_STEP*k;K[c,t]=k
    kb,kr,Kd=frame(K);Rd=np.zeros_like(R)
    for c in range(C):
        for t in range(T):Rd[c,t]=ar.predict_hist(Rd,c,t,cd,P,'shared')+AR_STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('ar replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('ar hard',me,eps))
    total=int(mb)+kb+32
    return {'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'innovation_bytes':kb,'rep':kr,'maxerr':me}

def solve_region(name,X,eps):
    szb,ori=m.szrun(X,eps);arb=ar32_baseline(X,eps);rows=[]
    for fac in HFACS:
        h=float(eps*fac);lo,hi=legal_q(X,eps,h)
        legal_mean=float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1));legal_max=int(np.max(hi-lo+1))
        for law in LAWS:
            lname,mode,p,den=law
            for shared in (False,True):
                candidates=[]
                for init in INITS:
                    Q,D,H,score,nz,changes=_optimize(lo,hi,mode,p,den,shared,init,PASSES)
                    mat=materialize(X,eps,h,Q,D,H,law,shared)
                    mat.update({'law':lname,'temporal_mode':mode,'spatial_num':p,'spatial_den':den,'shared_forcing':bool(shared),'hfac':fac,'h':h,'init_kind':init,'surrogate_bits':int(score),'defect_nonzeros':int(nz),'optimizer_changes':int(changes),'mean_legal_states':legal_mean,'max_legal_states':legal_max,'gain_vs_sz3':szb/mat['bytes'],'gain_vs_ar32':arb['bytes']/mat['bytes']})
                    candidates.append(mat)
                rows.append(min(candidates,key=lambda r:r['bytes']))
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    return {'region':name,'shape':[C,T],'samples':int(X.size),'local_std':float(X.std()),'eps':eps,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'best':best,'top':rows[:16],'configs':len(rows)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=m.stats(d);eps=.1*std;outrows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[T0:T0+T,c0:c0+C],np.float64).T
            r=solve_region(name,X,eps);outrows.append(r);print(json.dumps(r,indent=2),flush=True)
    out={'global_std':std,'eps':eps,'t0':T0,'shape':[C,T],'training_for_ar32':TRAIN,'h_factors':list(HFACS),'laws':[list(x) for x in LAWS],'passes':PASSES,'rows':outrows,'scope':'Decoder-real global hard-box compression-resonance gate. Unlike predictor+innovation experiments, the encoder jointly changes the reconstruction lattice state of every interior sample inside its exact +/-epsilon source interval to minimize a shared causal-law defect address. Candidate laws are tiny public integer/dyadic wave recurrences; no fitted law coefficients are hidden. The certificate contains only two initial time slices, two spatial boundary traces, the optimized interior defect field, and optionally one shared forcing/interrogator-state scalar per time. Every component is passed through the existing exact byte-counted representation menu and independently decoded. The decoder regenerates all interior samples causally from law+boundaries+defects, exact Q equality is checked, and source-domain hard error is verified. Matched SZ3 and a charged shared AR32 step267 baseline are rerun on the identical tile. This is the field-data version of the uploaded compression_resonance_proof_v0.1 principle, but with a concrete integer bitstream and no ideal/oracle rate.'}
    json.dump(out,open('imperial_resonant_global_defect_address.json','w'),indent=2)
    print(json.dumps({'summary':[{'region':r['region'],'resonance_bytes':r['best']['bytes'],'ar32_bytes':r['ar32']['bytes'],'sz3_bytes':r['sz3']['bytes'],'gain_ar32':r['best']['gain_vs_ar32'],'gain_sz3':r['best']['gain_vs_sz3'],'law':r['best']['law'],'hfac':r['best']['hfac'],'shared':r['best']['shared_forcing'],'defect_zero_fraction':r['best']['defect_zero_fraction']} for r in outrows]},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
