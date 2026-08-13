import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32;STEP=267;TRAIN=1024;END=8192;C=128
QS=(0,1,4,5,8)
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
m.STEP=STEP

def ar_pred(R,c,t,co):
    if t<P:return 0
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(R[c,t-1-j])
    if not math.isfinite(v) or abs(v)>1e12:raise RuntimeError(('ar pred',c,t,v))
    return int(np.rint(v))

def build_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int64)
    for c in range(C):
        for t in range(TRAIN):
            p=ar_pred(R,c,t,cd);k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError(('prefix hard',c,t))
            R[c,t]=y;K[c,t]=k
    kb,rep,kd=m.encode_k(K);kd=np.asarray(kd,np.int64).reshape(K.shape)
    if not np.array_equal(kd,K):raise RuntimeError('prefix K decode')
    return cd,R,K,int(mb+kb+20),{'prefix_model_bytes':int(mb),'prefix_k_bytes':int(kb+20),'prefix_rep':rep}

def fit_arx(X,R,K,q):
    if q==0:return r.fit_shared(X[:,:TRAIN],P)
    t0=max(P,q);n=C*(TRAIN-t0);A=np.empty((n,P+q+1),np.float64);Y=X[:,t0:TRAIN].reshape(-1).astype(np.float64)
    for j in range(P):A[:,j]=R[:,t0-1-j:TRAIN-1-j].reshape(-1)
    for j in range(q):A[:,P+j]=(STEP*K[:,t0-1-j:TRAIN-1-j]).reshape(-1)
    A[:,-1]=1.0
    return np.linalg.lstsq(A,Y,rcond=1e-8)[0].astype(np.float32)

def xpred(stateR,stateK,co,q):
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(stateR[-1-j])
    for j in range(q):v+=float(co[P+j])*float(STEP*stateK[-1-j])
    if not math.isfinite(v) or abs(v)>1e12:raise RuntimeError(('unstable',q,v))
    return int(np.rint(v))

def encode_target(X,eps,prefixR,prefixK,co,q):
    Kout=np.empty((C,END-TRAIN),np.int64);Rout=np.empty_like(Kout)
    for c in range(C):
        sr=prefixR[c,-P:].astype(np.int64).copy();sk=prefixK[c,-max(1,q):].astype(np.int64).copy() if q else np.empty(0,np.int64)
        for ii,t in enumerate(range(TRAIN,END)):
            if q==0:
                v=float(co[-1])
                for j in range(P):v+=float(co[j])*float(sr[-1-j])
                p=int(np.rint(v))
            else:p=xpred(sr,sk,co,q)
            k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError(('target hard',q,c,t,X[c,t],p,k,y))
            Kout[c,ii]=k;Rout[c,ii]=y
            sr[:-1]=sr[1:];sr[-1]=y
            if q:
                sk[:-1]=sk[1:];sk[-1]=k
    kb,rep,kd=m.encode_k(Kout);kd=np.asarray(kd,np.int64).reshape(Kout.shape)
    if not np.array_equal(kd,Kout):raise RuntimeError(('target K decode',q))
    # exact decoder replay
    D=np.empty_like(Rout)
    for c in range(C):
        sr=prefixR[c,-P:].astype(np.int64).copy();sk=prefixK[c,-max(1,q):].astype(np.int64).copy() if q else np.empty(0,np.int64)
        for ii in range(END-TRAIN):
            if q==0:
                v=float(co[-1])
                for j in range(P):v+=float(co[j])*float(sr[-1-j])
                p=int(np.rint(v))
            else:p=xpred(sr,sk,co,q)
            y=p+STEP*int(kd[c,ii]);D[c,ii]=y;sr[:-1]=sr[1:];sr[-1]=y
            if q:sk[:-1]=sk[1:];sk[-1]=int(kd[c,ii])
    if not np.array_equal(D,Rout):raise RuntimeError(('replay',q))
    me=float(np.max(np.abs(X[:,TRAIN:END]-D)))
    if me>eps*(1+1e-10):raise RuntimeError(('final hard',q,me,eps))
    return {'innovation_bytes':int(kb+20),'innovation_bps':8*(kb+20)/(C*(END-TRAIN)),'rep':rep,'maxerr':me,
            'k_zero_fraction':float(np.mean(Kout==0)),'k_abs1_fraction':float(np.mean(np.abs(Kout)==1)),'k_std':float(Kout.std())}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;baseco,PR,PK,prefix_bytes,pmeta=build_prefix(X,eps)
            regs=[]
            for q in QS:
                try:
                    co=baseco.copy() if q==0 else fit_arx(X,PR,PK,q);mb,cd=r.model_frame(co);z=encode_target(X,eps,PR,PK,cd,q)
                    total=prefix_bytes+mb+z['innovation_bytes']+24
                    row={'region':name,'c0':c0,'q':q,'bytes':int(total),'bps':8*total/(C*END),'prefix_bytes':prefix_bytes,'extension_model_bytes':int(mb),**z,**pmeta}
                except Exception as e:row={'region':name,'c0':c0,'q':q,'error':repr(e)}
                regs.append(row);rows.append(row);print(json.dumps(row),flush=True)
            ok={z['q']:z for z in regs if 'bytes' in z}
            if 0 in ok:
                for q,z in ok.items():z['gain_vs_ar32_q0']=ok[0]['bytes']/z['bytes'];z['heldout_gain_vs_ar32_q0']=ok[0]['innovation_bytes']/z['innovation_bytes']
                print(json.dumps({'region':name,'gains':{str(q):{'full':z['gain_vs_ar32_q0'],'heldout':z['heldout_gain_vs_ar32_q0']} for q,z in ok.items()}}),flush=True)
    combos=[]
    for q in QS:
        rr=[z for z in rows if z.get('q')==q and 'bytes' in z]
        if len(rr)==len(SPECS):
            b=sum(z['bytes'] for z in rr);ib=sum(z['innovation_bytes'] for z in rr);n=C*END*len(rr);hn=C*(END-TRAIN)*len(rr)
            combos.append({'q':q,'bytes':b,'bps':8*b/n,'heldout_innovation_bytes':ib,'heldout_innovation_bps':8*ib/hn,'extension_model_bytes':sum(z['extension_model_bytes'] for z in rr)})
    combos.sort(key=lambda z:z['bytes'])
    base=next((z for z in combos if z['q']==0),None)
    for z in combos:
        if base:z['gain_vs_ar32_q0']=base['bytes']/z['bytes'];z['heldout_gain_vs_ar32_q0']=base['heldout_innovation_bytes']/z['heldout_innovation_bytes']
    out={'global_std':std,'eps':eps,'step':STEP,'ar_order':P,'innovation_memory_orders':list(QS),'training_samples':TRAIN,'end_sample':END,'regions':[list(x) for x in SPECS],
         'combos':combos,'rows':rows,
         'scope':'Instrument-memory ARX/ARMA-style gate. A shared AR32 prefix model is fit only on t<1024 and used to produce decoder-real reconstructed samples R and innovations K. Candidate predictors then regress the same prefix source on 32 past reconstructed samples plus q past decoded innovation amplitudes (q=1/4/5/8), serialize the float32 coefficients, and freeze them for held-out t=1024..8191. q=5 is the direct finite-memory hypothesis motivated by the actual HDF5 metadata P=5 with five unit coefficients; q=4 matches Time Decimation=4. Decoder knows past K exactly, so the MA/innovation state is causal and costs no side stream beyond the transmitted coefficients. Target innovations use unchanged legal step267 and identical self-decoding backend; prefix, model, innovations and framing are fully counted and hard-error replay verified. This does not assert proprietary Silixa semantics; it tests whether a finite innovation-memory zero exists in the recorded stream. No AI.'}
    print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_ar32_innovation_memory.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
