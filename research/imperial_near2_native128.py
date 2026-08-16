import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAC=1.9995
C0=512
T0=14488
C=128
T=1024


def fit_model_dyn(Q,ntaps=g.NTAPS):
    Q=np.asarray(Q,np.float64);offs=g.candidate_offsets();maxdt=64
    Cc,Tt=Q.shape
    ts=np.arange(maxdt,Tt,4,dtype=np.int32);cs=np.arange(8,Cc-8,dtype=np.int32)
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
    co=np.rint(beta[1:]*g.SCALE).astype(np.int32);intercept=int(np.rint(beta[0]*g.SCALE))
    return dts,dcs,co,intercept


def build(X,eps):
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(g.ROUNDS):
        dt,dc,co,it=fit_model_dyn(Q);Q,D,H,s,n,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    dt,dc,co,it=fit_model_dyn(Q);Q,D,H,s,n,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
    return h,lo,hi,np.ascontiguousarray(Q),D,dt,dc,co,it,changes


def validate(X,eps,h,Q,D,dt,dc,co,it):
    db,rep,Ed,detail=rr.restricted_rank_frame(D);mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it)
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):Qd[c,t]=g._pred(Qd,c,t,ddt,ddc,dco,dit,g.SCALE)+int(Ed[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('native128 Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('native128 hard',me,eps))
    total=int(mb)+int(db)+g.HEADER
    return {'bytes':total,'model_bytes':int(mb),'defect_bytes':int(db),'bps':8*total/X.size,'maxerr':me,'defect_rep':rep,'model_rep':mrep,'detail':detail}


def ar32_dyn(X,eps):
    Cc,Tt=X.shape;co=g.ar.fit_shared(X[:,:min(g.TRAIN,Tt)],g.P);mb,cd=g.ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(Cc):
        for t in range(Tt):
            pred=g.ar.predict_hist(R,c,t,cd,g.P,'shared');k=int(np.rint((float(X[c,t])-pred)/g.AR_STEP));R[c,t]=pred+g.AR_STEP*k;K[c,t]=k
    kb,kr,Kd=g.frame(K);Rd=np.zeros_like(R)
    for c in range(Cc):
        for t in range(Tt):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+g.AR_STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError('native128 AR replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('native128 AR hard',me,eps))
    total=int(mb)+int(kb)+32
    return {'bytes':total,'model_bytes':int(mb),'innovation_bytes':int(kb),'bps':8*total/X.size,'maxerr':me,'rep':kr}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    sz,ori=m.szrun(X,eps);ar=ar32_dyn(X,eps);h,lo,hi,Q,D,dt,dc,co,it,gchg=build(X,eps)
    lc=a.logcomb_table(X.size);Q,D,_,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES);D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE));ours=validate(X,eps,h,Q,D,dt,dc,co,it)
    out={'shape':[C,T],'samples':int(X.size),'c0':C0,'t0':T0,'hfac':FAC,'eps':eps,'ours':{k:v for k,v in ours.items() if k!='detail'},'ar32':ar,'sz3':{'bytes':int(sz),'orientation':ori},'gain_ar32':ar['bytes']/ours['bytes'],'gain_sz3':sz/ours['bytes'],'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'generator_changes':int(gchg),'address_changes':int(achg),'scope':'Native 128x1024 hard-block test. One shared learned sparse causal generator and one exact restricted-rank defect address cover channels 512:640 jointly, rather than four 32-channel codec instances. Model and address are fully charged and independently replayed. For fairness AR32 is generalized to the same native 128x1024 object with one charged shared model, and SZ3 is rerun natively on the same object. No sum of smaller comparator tiles is used.'};json.dump(out,open('imperial_near2_native128.json','w'),indent=2);print(json.dumps({'summary':{'ours':ours['bytes'],'ar32':ar['bytes'],'sz3':int(sz),'gain_ar32':out['gain_ar32'],'gain_sz3':out['gain_sz3']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
