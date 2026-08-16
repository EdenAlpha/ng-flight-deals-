import json,sys,math,struct
import h5py,numpy as np
from numba import njit
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

T0=14488
C=32
T=1024
P=32
TRAIN=256
AR_STEP=267
C0=512
HFACS=(1.0,1.25,1.5)
NTAPS=20
ROUNDS=2
PASSES=2
INITS=(0,1)
SCALE=4096
HEADER=48
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
def _pred(Q,c,t,dts,dcs,co,intercept,scale):
    num=np.int64(intercept)
    for j in range(dts.size):
        dt=int(dts[j]);dc=int(dcs[j]);tt=t-dt;cc=c+dc
        if tt<0 or cc<0 or cc>=Q.shape[0]:continue
        num+=np.int64(co[j])*np.int64(Q[cc,tt])
    return _rdiv(num,scale)

@njit(cache=True)
def _defect(Q,c,t,dts,dcs,co,intercept,scale):
    return int(Q[c,t])-_pred(Q,c,t,dts,dcs,co,intercept,scale)

@njit(cache=True)
def _all_defects(Q,dts,dcs,co,intercept,scale):
    D=np.empty(Q.shape,np.int32)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):D[c,t]=_defect(Q,c,t,dts,dcs,co,intercept,scale)
    return D

@njit(cache=True)
def _best_shared(D):
    Cc,Tt=D.shape;H=np.zeros(Tt,np.int32)
    for t in range(Tt):
        best=np.int64(1<<60);bh=0
        z=0
        for c in range(Cc):z+=_eglen(int(D[c,t]))
        if z<best:best=z;bh=0
        for j in range(Cc):
            h=int(D[j,t]);cost=0
            for c in range(Cc):cost+=_eglen(int(D[c,t])-h)
            if cost<best:best=cost;bh=h
        H[t]=bh
    return H

@njit(cache=True)
def _d_cost(Q,c,t,H,dts,dcs,co,intercept,scale,use_shared):
    if c<0 or c>=Q.shape[0] or t<0 or t>=Q.shape[1]:return 0
    z=_defect(Q,c,t,dts,dcs,co,intercept,scale)
    if use_shared:z-=int(H[t])
    return _eglen(z)

@njit(cache=True)
def _local_cost(Q,c,t,H,dts,dcs,co,intercept,scale,use_shared):
    # Own defect plus every future/same-time causal target whose prediction uses q[c,t].
    s=_d_cost(Q,c,t,H,dts,dcs,co,intercept,scale,use_shared)
    for j in range(dts.size):
        dt=int(dts[j]);dc=int(dcs[j]);tc=t+dt;cc=c-dc
        if tc<0 or tc>=Q.shape[1] or cc<0 or cc>=Q.shape[0]:continue
        s+=_d_cost(Q,cc,tc,H,dts,dcs,co,intercept,scale,use_shared)
    return s

@njit(cache=True)
def _initial(lo,hi,kind):
    Q=np.empty_like(lo)
    for c in range(Q.shape[0]):
        for t in range(Q.shape[1]):
            a=int(lo[c,t]);b=int(hi[c,t])
            Q[c,t]=(a+b)//2 if kind==0 else (a if ((c*131+t*17)&1)==0 else b)
    return Q

@njit(cache=True)
def _optimize_from(Q,lo,hi,dts,dcs,co,intercept,scale,use_shared,passes):
    D=_all_defects(Q,dts,dcs,co,intercept,scale)
    H=_best_shared(D) if use_shared else np.zeros(Q.shape[1],np.int32)
    changes=0
    for ps in range(passes):
        changed=0;rev=ps&1
        for t in range(Q.shape[1]):
            for kk in range(Q.shape[0]):
                c=kk if rev==0 else Q.shape[0]-1-kk
                old=int(Q[c,t]);bestq=old;best=INF
                for q in range(int(lo[c,t]),int(hi[c,t])+1):
                    Q[c,t]=q
                    z=_local_cost(Q,c,t,H,dts,dcs,co,intercept,scale,use_shared)
                    if z<best:best=z;bestq=q
                Q[c,t]=bestq
                if bestq!=old:changed+=1;changes+=1
        D=_all_defects(Q,dts,dcs,co,intercept,scale)
        if use_shared:H=_best_shared(D)
        if changed==0:break
    D=_all_defects(Q,dts,dcs,co,intercept,scale)
    if use_shared:H=_best_shared(D)
    score=0;nz=0
    for c in range(D.shape[0]):
        for t in range(D.shape[1]):
            e=int(D[c,t])-(int(H[t]) if use_shared else 0)
            score+=_eglen(e)
            if e!=0:nz+=1
    return Q,D,H,score,nz,changes

def candidate_offsets():
    ds=(1,2,3,4,6,8,12,16,24,32,48,64)
    cs=(-8,-4,-2,-1,0,1,2,4,8)
    out=[(dt,dc) for dt in ds for dc in cs]
    out += [(0,-1),(0,-2),(0,-4),(0,-8)]
    return out

def fit_model(Q,ntaps=NTAPS):
    Q=np.asarray(Q,np.float64);offs=candidate_offsets();maxdt=64
    ts=np.arange(maxdt,T,4,dtype=np.int32);cs=np.arange(8,C-8,dtype=np.int32)
    tt=np.repeat(ts,cs.size);cc=np.tile(cs,ts.size);y=Q[cc,tt]
    A=np.empty((y.size,len(offs)),np.float64)
    for j,(dt,dc) in enumerate(offs):A[:,j]=Q[cc+dc,tt-dt]
    ym=float(y.mean());y0=y-ym;means=A.mean(axis=0);scales=A.std(axis=0)+1e-8;An=(A-means)/scales
    selected=[];avail=np.ones(An.shape[1],bool);resid=y0.copy()
    for _ in range(ntaps):
        corr=np.abs(An.T@resid);corr[~avail]=-1;j=int(np.argmax(corr));selected.append(j);avail[j]=False
        B=An[:,selected];beta=np.linalg.lstsq(B,y0,rcond=1e-4)[0];resid=y0-B@beta
    B=A[:,selected];M=np.column_stack([np.ones(B.shape[0]),B]);ridge=1e-5*np.eye(M.shape[1]);ridge[0,0]=0
    beta=np.linalg.solve(M.T@M+ridge,M.T@y)
    dts=np.asarray([offs[j][0] for j in selected],np.int16);dcs=np.asarray([offs[j][1] for j in selected],np.int16)
    co=np.rint(beta[1:]*SCALE).astype(np.int32);intercept=int(np.rint(beta[0]*SCALE))
    return dts,dcs,co,intercept

def model_frame(dts,dcs,co,intercept):
    raw=bytearray(struct.pack('<iiH',int(intercept),SCALE,len(co)))
    for dt,dc,a in zip(dts,dcs,co):raw.extend(struct.pack('<bbi',int(dt),int(dc),int(a)))
    raw=bytes(raw);z=m.Z.compress(raw);stored=z if len(z)<len(raw) else raw;rep='zstd' if len(z)<len(raw) else 'raw';rr=m.D.decompress(stored) if rep=='zstd' else stored
    off=0;inter2,scale2,n=struct.unpack_from('<iiH',rr,off);off+=10;ddt=[];ddc=[];aa=[]
    for _ in range(n):
        dt,dc,a=struct.unpack_from('<bbi',rr,off);off+=6;ddt.append(dt);ddc.append(dc);aa.append(a)
    if inter2!=intercept or scale2!=SCALE or not np.array_equal(np.asarray(ddt,np.int16),dts) or not np.array_equal(np.asarray(ddc,np.int16),dcs) or not np.array_equal(np.asarray(aa,np.int32),co):raise RuntimeError('model roundtrip')
    return len(stored)+24,rep,np.asarray(ddt,np.int16),np.asarray(ddc,np.int16),np.asarray(aa,np.int32),int(inter2)

def legal_q(X,eps,h):
    b=eps*(1-2e-12);lo=np.ceil((X-b)/h).astype(np.int32);hi=np.floor((X+b)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal')
    return lo,hi

def frame(A):
    fr=m.encode_k(np.ascontiguousarray(A,np.int32));return int(fr[0]),fr[1],np.asarray(fr[2],np.int32)

def materialize(X,eps,h,Q,D,H,dts,dcs,co,intercept,use_shared):
    mb,mrep,ddt,ddc,dco,dinter=model_frame(dts,dcs,co,intercept)
    E=D-H[None,:] if use_shared else D
    eb,erep,Ed=frame(E)
    if use_shared:hb,hrep,Hd0=frame(H[None,:]);Hd=Hd0[0]
    else:hb=0;hrep='none';Hd=np.zeros(T,np.int32)
    Dd=Ed+Hd[None,:];Qd=np.empty_like(Q)
    for t in range(T):
        for c in range(C):Qd[c,t]=_pred(Qd,c,t,ddt,ddc,dco,dinter,SCALE)+int(Dd[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('learned-law certificate replay')
    R=Qd.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=mb+eb+hb+HEADER
    return {'bytes':int(total),'bps':8*total/X.size,'model_bytes':mb,'model_rep':mrep,'defect_bytes':eb,'defect_rep':erep,'forcing_bytes':hb,'forcing_rep':hrep,'maxerr':me,'defect_zero_fraction':float(np.mean(E==0)),'defect_std':float(E.std()),'forcing_nonzero_fraction':float(np.mean(H!=0)) if use_shared else 0.0,'taps':[[int(a),int(b)] for a,b in zip(dts,dcs)],'coef_q12':[int(x) for x in co],'intercept_q12':int(intercept)}

def ar32_baseline(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(C):
        for t in range(T):
            pred=ar.predict_hist(R,c,t,cd,P,'shared');k=int(np.rint((float(X[c,t])-pred)/AR_STEP));R[c,t]=pred+AR_STEP*k;K[c,t]=k
    kb,kr,Kd=frame(K);Rd=np.zeros_like(R)
    for c in range(C):
        for t in range(T):Rd[c,t]=ar.predict_hist(Rd,c,t,cd,P,'shared')+AR_STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('ar replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('ar hard',me,eps))
    total=int(mb)+kb+32;return {'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'innovation_bytes':kb,'rep':kr,'maxerr':me}

def run_candidate(X,eps,fac,use_shared,init_kind):
    h=float(eps*fac);lo,hi=legal_q(X,eps,h);Q=_initial(lo,hi,init_kind);rounds=[];changes=0
    dts=dcs=co=None;intercept=0;D=H=None;score=0;nz=0
    for rd in range(ROUNDS):
        dts,dcs,co,intercept=fit_model(Q)
        Q,D,H,score,nz,ch=_optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,use_shared,PASSES);changes+=int(ch)
        rounds.append({'round':rd,'surrogate_bits':int(score),'defect_nonzeros':int(nz),'changes':int(ch)})
    # one final refit to the optimized reconstruction, then optimize once under the exact final transmitted model
    dts,dcs,co,intercept=fit_model(Q)
    Q,D,H,score,nz,ch=_optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,use_shared,PASSES);changes+=int(ch)
    mat=materialize(X,eps,h,Q,D,H,dts,dcs,co,intercept,use_shared)
    mat.update({'hfac':fac,'h':h,'shared_forcing':bool(use_shared),'init_kind':init_kind,'surrogate_bits':int(score),'defect_nonzeros':int(nz),'optimizer_changes':changes,'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'max_legal_states':int(np.max(hi-lo+1)),'rounds':rounds})
    return mat

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=ar32_baseline(X,eps);rows=[]
    for fac in HFACS:
        for shared in (False,True):
            for init in INITS:
                r=run_candidate(X,eps,fac,shared,init);r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];rows.append(r);print(json.dumps({k:v for k,v in r.items() if k not in ('taps','coef_q12','rounds')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);out={'region':'hard','c0':C0,'t0':T0,'shape':[C,T],'samples':int(X.size),'local_std':float(X.std()),'global_std':std,'eps':eps,'ntaps':NTAPS,'rounds':ROUNDS,'passes':PASSES,'h_factors':list(HFACS),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'best':rows[0],'top':rows[:8],'scope':'Favorable but decoder-real learned-generator resonance gate. For each public h/epsilon lattice, the encoder starts from a legal reconstruction, learns a sparse causal space-time law from that reconstruction using a fixed OMP tap grammar, quantizes the selected coefficients to Q12 fixed point, then coordinate-optimizes every legal sample to minimize the exact signed-Exp-Golomb defect objective. The law is relearned and the legal field reoptimized, so generator search and reconstruction selection are coupled. Final tap coordinates, fixed-point coefficients and intercept are actually serialized/decoded and charged. The full defect witness, plus optional one-scalar-per-time shared forcing, is encoded through the existing exact byte-counted representation menu. Decoder causally regenerates every Q sample from the transmitted law+defect stream; exact Q replay and source hard error are mandatory. Target-trained law selection is deliberately favorable but legal because every final model bit is charged. Matched SZ3 and charged AR32 step267 are rerun on the identical hard tile. This tests whether NOVA-style generator search plus compression-resonant legal-set projection has material headroom before attempting a shared procedural seed family.'}
    json.dump(out,open('imperial_resonant_learned_law_address.json','w'),indent=2)
    b=rows[0];print(json.dumps({'summary':{'bytes':b['bytes'],'ar32_bytes':arb['bytes'],'sz3_bytes':int(szb),'gain_ar32':b['gain_vs_ar32'],'gain_sz3':b['gain_vs_sz3'],'hfac':b['hfac'],'shared':b['shared_forcing'],'defect_zero_fraction':b['defect_zero_fraction'],'model_bytes':b['model_bytes'],'defect_bytes':b['defect_bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
