import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
BANK=((1,0),(2,0),(3,0),(4,0),(6,0),(8,0),(12,0),(16,0),(24,0),(32,0),(48,0),(64,0),
      (0,-1),(0,-2),(0,-4),(0,-8),(1,-1),(1,1),(1,-2),(1,2),(1,-4),(1,4),(1,-8),(1,8),
      (2,-1),(2,1),(2,-2),(2,2),(4,-1),(4,1))
SIZES=(8,16,30)

def shift_field(K,dt,dc,t0,t1):
    out=np.zeros((C,t1-t0),np.float64)
    for j,t in enumerate(range(t0,t1)):
        s=t-dt
        if s<0: continue
        if dc<0: out[-dc:,j]=K[:C+dc,s]
        elif dc>0: out[:C-dc,j]=K[dc:,s]
        else: out[:,j]=K[:,s]
    return out

def robust_fit(A,y):
    lam=1e-4
    G=A.T@A + lam*np.eye(A.shape[1]); rhs=A.T@y
    co=np.linalg.solve(G,rhs)
    for _ in range(5):
        r=y-A@co; sc=1.4826*np.median(np.abs(r-np.median(r)))+1e-6
        w=np.minimum(1.0,(1.5*sc)/np.maximum(np.abs(r),1e-12))
        G=A.T@(A*w[:,None]) + lam*np.eye(A.shape[1]); rhs=A.T@(y*w)
        co=np.linalg.solve(G,rhs)
    return co

def fit_models(X,Rb,Kb):
    t0=P;t1=TRAIN
    pred=Rb[:,t0:t1].astype(np.float64)-STEP*Kb[:,t0:t1].astype(np.float64)
    y=((X[:,t0:t1]-pred)/STEP).ravel(order='F')
    cols=[]
    for dt,dc in BANK: cols.append(shift_field(Kb,dt,dc,t0,t1).ravel(order='F'))
    A=np.column_stack(cols)
    co=robust_fit(A,y)
    score=np.abs(co)*np.std(A,axis=0)
    order=np.argsort(score)[::-1]
    models=[]
    for n in SIZES:
        ids=np.sort(order[:n]); As=A[:,ids]; cs=robust_fit(As,y).astype(np.float32)
        models.append((ids.astype(np.uint8),cs,float(np.sqrt(np.mean((y-As@cs.astype(np.float64))**2)))))
    return models

def shifted_vec(K,t,dt,dc):
    v=np.zeros(C,np.float64);s=t-dt
    if s<0:return v
    if dc<0:v[-dc:]=K[:C+dc,s]
    elif dc>0:v[:C-dc]=K[dc:,s]
    else:v[:]=K[:,s]
    return v

def run_model(X,arco,ids,co):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    a0=float(arco[0]);b=np.asarray(arco[1:],np.float32)
    taps=[BANK[int(i)] for i in ids]
    lag=[(j,tap) for j,tap in enumerate(taps) if tap[0]>0]
    same=[(j,tap) for j,tap in enumerate(taps) if tap[0]==0]
    for t in range(NT):
        if t<P: tp=np.zeros(C,np.int32)
        else: tp=np.rint(a0+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
        basecorr=np.zeros(C,np.float64)
        if t>=TRAIN:
            for j,(dt,dc) in lag: basecorr += float(co[j])*shifted_vec(K,t,dt,dc)
        for c in range(C):
            s=basecorr[c]
            if t>=TRAIN:
                for j,(dt,dc) in same:
                    cc=c+dc
                    if 0<=cc<C:s+=float(co[j])*float(K[cc,t])
            pred=int(tp[c])+int(np.rint(STEP*s))
            k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;R[c,t]=pred+STEP*k
    return R,K

def decode_model(K,arco,ids,co):
    R=np.zeros(K.shape,np.int32);a0=float(arco[0]);b=np.asarray(arco[1:],np.float32)
    taps=[BANK[int(i)] for i in ids];lag=[(j,tap) for j,tap in enumerate(taps) if tap[0]>0];same=[(j,tap) for j,tap in enumerate(taps) if tap[0]==0]
    for t in range(K.shape[1]):
        if t<P:tp=np.zeros(K.shape[0],np.int32)
        else:tp=np.rint(a0+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
        basecorr=np.zeros(K.shape[0],np.float64)
        if t>=TRAIN:
            for j,(dt,dc) in lag:basecorr+=float(co[j])*shifted_vec(K,t,dt,dc)
        for c in range(K.shape[0]):
            s=basecorr[c]
            if t>=TRAIN:
                for j,(dt,dc) in same:
                    cc=c+dc
                    if 0<=cc<K.shape[0]:s+=float(co[j])*float(K[cc,t])
            pred=int(tp[c])+int(np.rint(STEP*s));R[c,t]=pred+STEP*int(K[c,t])
    return R

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu)
            base_bytes,base_bits,base_nb,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,hu)
            if not np.array_equal(Rbd,Rb):raise RuntimeError((region,'base decode'))
            models=fit_models(X,Rb,Kb);cands=[]
            for ids,co,train_rmse in models:
                R,K=run_model(X,hu,ids,co);me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,'hard',len(ids),me,eps))
                nbit,sbits,snb,Kd=a.arithmetic(K);extra=16+5*len(ids);total=int(nbit+extra)
                Rd=decode_model(Kd,hu,ids,co)
                if not np.array_equal(Rd,R):raise RuntimeError((region,'source replay',len(ids)))
                if float(np.max(np.abs(X-Rd.astype(np.float64))))>eps*(1+1e-12):raise RuntimeError((region,'decode hard'))
                cands.append({'taps':len(ids),'tap_ids':[int(i) for i in ids],'tap_offsets':[list(BANK[int(i)]) for i in ids],'coefficients':[float(x) for x in co],'train_rmse_k':train_rmse,'bytes':total,'bps':8*total/X.size,'extra_model_bytes':extra,'gain_vs_arithmetic':base_bytes/total,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'maxerr':me})
            sz=0
            for t0 in range(0,NT,TB):sb,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(sb)
            for q in cands:q['gain_vs_sz3']=sz/q['bytes']
            best=min(cands,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base_bytes),'baseline_bps':8*base_bytes/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':cands};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'step':STEP,'train':TRAIN,'bank':[list(x) for x in BANK],'rows':rows,'scope':'Prefix-trained nonlocal decoder-real residual stencil stacked on Huber AR32. The first 1024 samples use the unchanged AR32 path. Encoder fits a robust linear correction in K units from a fixed 30-tap bank reaching 64 time samples and +/-8 channels; target variants transmit selected tap IDs and float32 coefficients. After the prefix, decoder adds STEP times the correction formed only from already decoded K: lagged taps may use both spatial directions, same-time taps are left-only. The corrected prediction is quantized at exact step267, its reconstructed source becomes future AR state, K is exactly cold-start arithmetic decoded, and the complete source is replayed under unchanged max error. 8/16/30 tap variants are compared by actual final bytes. No AI.'};json.dump(out,open('imperial_ar32_nonlocal_residual_stencil.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
