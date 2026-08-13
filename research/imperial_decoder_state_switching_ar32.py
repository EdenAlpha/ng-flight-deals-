import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32;STEP=267;TRAIN=1024;END=8192;C=128
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
SCHEMES=('global','sign_slope4','sign_slope_amp8')
m.STEP=STEP

def global_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int64)
    for c in range(C):
        for t in range(TRAIN):
            if t<P:p=0
            else:
                v=float(cd[-1])
                for j in range(P):v+=float(cd[j])*float(R[c,t-1-j])
                p=int(np.rint(v))
            k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError('prefix hard')
            R[c,t]=y;K[c,t]=k
    kb,rep,kd=m.encode_k(K);kd=np.asarray(kd,np.int64).reshape(K.shape)
    if not np.array_equal(kd,K):raise RuntimeError('prefix decode')
    return cd,R,K,int(mb+kb+20),{'prefix_model_bytes':int(mb),'prefix_k_bytes':int(kb+20),'prefix_rep':rep}

def threshold(R):return float(np.median(np.abs(R[:,P:TRAIN])))

def ctx_from_hist(hist,scheme,thr):
    x1=int(hist[-1]) if len(hist) else 0;x2=int(hist[-2]) if len(hist)>1 else x1
    s=1 if x1>=0 else 0;d=1 if x1-x2>=0 else 0
    if scheme=='global':return 0
    if scheme=='sign_slope4':return (s<<1)|d
    a=1 if abs(x1)>=thr else 0
    return (s<<2)|(d<<1)|a

def nctx(scheme):return {'global':1,'sign_slope4':4,'sign_slope_amp8':8}[scheme]

def fit_bank(X,R,scheme,thr):
    nc=nctx(scheme);rows=[[] for _ in range(nc)];ys=[[] for _ in range(nc)]
    for c in range(C):
        for t in range(P,TRAIN):
            q=ctx_from_hist(R[c,:t],scheme,thr);rows[q].append([float(R[c,t-1-j]) for j in range(P)]+[1.0]);ys[q].append(float(X[c,t]))
    g=r.fit_shared(X[:,:TRAIN],P).astype(np.float32);bank=np.empty((nc,P+1),np.float32);counts=[]
    for q in range(nc):
        counts.append(len(ys[q]))
        if len(ys[q])<4*(P+1):bank[q]=g;continue
        A=np.asarray(rows[q],np.float64);Y=np.asarray(ys[q],np.float64);bank[q]=np.linalg.lstsq(A,Y,rcond=1e-8)[0].astype(np.float32)
    return bank,counts

def predict(hist,bank,scheme,thr):
    if len(hist)<P:return 0
    q=ctx_from_hist(hist,scheme,thr);co=bank[q];v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(hist[-1-j])
    if not math.isfinite(v) or abs(v)>1e12:raise RuntimeError(('unstable',scheme,q,v))
    return int(np.rint(v))

def encode_target(X,eps,PR,bank,scheme,thr):
    K=np.empty((C,END-TRAIN),np.int64);RR=np.empty_like(K);ctxcnt=np.zeros(nctx(scheme),np.int64)
    for c in range(C):
        h=PR[c,-P:].astype(np.int64).tolist()
        for ii,t in enumerate(range(TRAIN,END)):
            q=ctx_from_hist(h,scheme,thr);ctxcnt[q]+=1;p=predict(h,bank,scheme,thr);k=int(np.rint((float(X[c,t])-p)/STEP));y=p+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError(('hard',scheme,c,t,X[c,t],p,k,y))
            K[c,ii]=k;RR[c,ii]=y;h.append(y);h=h[-P:]
    kb,rep,kd=m.encode_k(K);kd=np.asarray(kd,np.int64).reshape(K.shape)
    if not np.array_equal(kd,K):raise RuntimeError('K decode')
    D=np.empty_like(RR)
    for c in range(C):
        h=PR[c,-P:].astype(np.int64).tolist()
        for ii in range(END-TRAIN):
            p=predict(h,bank,scheme,thr);y=p+STEP*int(kd[c,ii]);D[c,ii]=y;h.append(y);h=h[-P:]
    if not np.array_equal(D,RR):raise RuntimeError('state replay')
    me=float(np.max(np.abs(X[:,TRAIN:END]-D)))
    if me>eps*(1+1e-10):raise RuntimeError(('final hard',scheme,me,eps))
    return {'innovation_bytes':int(kb+20),'innovation_bps':8*(kb+20)/(C*(END-TRAIN)),'rep':rep,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'context_fractions':(ctxcnt/ctxcnt.sum()).tolist()}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;gco,PR,PK,prefix_bytes,pmeta=global_prefix(X,eps);thr=threshold(PR);regs=[]
            for scheme in SCHEMES:
                try:
                    if scheme=='global':bank=gco.reshape(1,-1);counts=[C*(TRAIN-P)]
                    else:bank,counts=fit_bank(X,PR,scheme,thr)
                    mb,bd=r.model_frame(bank);z=encode_target(X,eps,PR,bd,scheme,thr);total=prefix_bytes+mb+z['innovation_bytes']+24
                    row={'region':name,'c0':c0,'scheme':scheme,'threshold_abs_state':thr,'bytes':int(total),'bps':8*total/(C*END),'bank_model_bytes':int(mb),'training_context_counts':counts,**z,**pmeta}
                except Exception as e:row={'region':name,'c0':c0,'scheme':scheme,'error':repr(e)}
                regs.append(row);rows.append(row);print(json.dumps(row),flush=True)
            ok={z['scheme']:z for z in regs if 'bytes' in z}
            if 'global' in ok:
                for s,z in ok.items():z['gain_vs_global_full']=ok['global']['bytes']/z['bytes'];z['gain_vs_global_heldout']=ok['global']['innovation_bytes']/z['innovation_bytes']
                print(json.dumps({'region':name,'gains':{s:{'full':z['gain_vs_global_full'],'heldout':z['gain_vs_global_heldout']} for s,z in ok.items()}}),flush=True)
    combos=[]
    for s in SCHEMES:
        rr=[z for z in rows if z.get('scheme')==s and 'bytes' in z]
        if len(rr)==len(SPECS):
            b=sum(z['bytes'] for z in rr);ib=sum(z['innovation_bytes'] for z in rr);n=C*END*len(rr);hn=C*(END-TRAIN)*len(rr)
            combos.append({'scheme':s,'bytes':b,'bps':8*b/n,'heldout_innovation_bytes':ib,'heldout_innovation_bps':8*ib/hn,'bank_model_bytes':sum(z['bank_model_bytes'] for z in rr)})
    base=next((z for z in combos if z['scheme']=='global'),None)
    for z in combos:
        if base:z['gain_vs_global_full']=base['bytes']/z['bytes'];z['gain_vs_global_heldout']=base['heldout_innovation_bytes']/z['heldout_innovation_bytes']
    combos.sort(key=lambda z:z['bytes'])
    out={'global_std':std,'eps':eps,'step':STEP,'order':P,'training_samples':TRAIN,'end_sample':END,'schemes':list(SCHEMES),'regions':[list(x) for x in SPECS],'combos':combos,'rows':rows,
         'scope':'Decoder-state-selected switching AR32 gate. A normal shared AR32 prefix is fit/decoded on t<1024. Subsequent context is a deterministic function of already-decoded state only: sign of last state, sign of last slope, and optionally whether |state| exceeds the decoder-derived prefix median. Separate AR32 banks are fitted from prefix samples for 4 or 8 contexts, float32 serialized/decoded, then frozen for held-out t=1024..8191. No target selector bits or target-derived thresholds exist. The global AR32 baseline uses the same prefix, legal step267, innovation backend and accounting. Prefix + bank + innovations + framing are counted and full recursive hard-error replay is verified. This tests piecewise-linear nonlinear dynamics without AI.'}
    print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_decoder_state_switching_ar32.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
