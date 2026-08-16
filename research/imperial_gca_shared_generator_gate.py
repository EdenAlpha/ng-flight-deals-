import json,sys,time
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_zero_sign_magnitude_arithmetic as z

C=128;NT=30000;TB=1024
REGIONS=(('hard',512),('easy',2304))
WINDOWS=(4,8,64)
# Generic 1-D DAS shared generators: previous reconstructed fiber channels + time shifts.
CONFIGS={
 'gca9':((1,(-2,-1,0,1,2)),(2,(-1,0,1)),(3,(0,))),
 'gca16':((1,(-3,-2,-1,0,1,2,3)),(2,(-2,-1,0,1,2)),(3,(-1,0,1)),(4,(0,))),
 'gca24':((1,(-4,-3,-2,-1,0,1,2,3,4)),(2,(-3,-2,-1,0,1,2,3)),(3,(-2,-1,0,1,2)),(4,(-1,0,1))),
}
RIDGE=1e-2; FIT_STRIDE=4; GCA_HEADER=84

def sh(x,d):
    y=np.zeros_like(x,dtype=np.float64)
    if d==0:y[:]=x
    elif d>0:y[d:]=x[:-d]
    else:y[:d]=x[-d:]
    return y

def feat(R,c,cfg):
    cols=[]
    for off,ds in cfg:
        x=R[c-off].astype(np.float64)
        cols.extend(sh(x,d) for d in ds)
    return np.stack(cols,axis=1)

def reconstruct(X,eps,cfg,K=None):
    step=2.0*float(eps)*(1.0-1e-4)
    R=np.zeros(X.shape,np.float32)
    Q=np.zeros(X.shape,np.int32) if K is None else np.asarray(K,np.int32)
    maxoff=max(x[0] for x in cfg); nf=sum(len(x[1]) for x in cfg)
    fit_idx=np.arange(4,NT-4,FIT_STRIDE,dtype=np.int64)
    for c in range(C):
        pred=None
        if c>=maxoff+1:
            # Decoder-visible local translation fit: learn how the previous channel was generated
            # from its own causal neighborhood, then apply those coefficients one channel forward.
            Ft=feat(R,c-1,cfg); yt=R[c-1].astype(np.float64)
            A=Ft[fit_idx]; b=yt[fit_idx]
            G=A.T@A; h=A.T@b
            try:co=np.linalg.solve(G+RIDGE*np.eye(nf),h)
            except np.linalg.LinAlgError:co=np.linalg.lstsq(G+RIDGE*np.eye(nf),h,rcond=None)[0]
            pred=feat(R,c,cfg)@co
        if pred is None:
            pred=R[c-1].astype(np.float64) if c else np.zeros(NT,np.float64)
        if K is None:
            q=np.rint((X[c].astype(np.float64)-pred)/step).astype(np.int32);Q[c]=q
        else:q=Q[c]
        R[c]=(pred+step*q.astype(np.float64)).astype(np.float32)
    return R,Q,step

def zstd_bytes(Q):
    # Screening only; selector is transmitted in the exact stream later.
    raw=np.asarray(Q,np.int32).tobytes()
    return len(zstd.ZstdCompressor(level=9).compress(raw))

def exact_zsm(Q):
    z.C=C;z.NT=NT;a.C=C;a.NT=NT
    rows=[]
    for W in WINDOWS:
        bb,nbit=z.encode_zsm(Q,W);Kd=z.decode_zsm(bb,nbit,W,Q.shape)
        if not np.array_equal(Kd,Q):raise RuntimeError(('GCA ZSM K decode',W))
        rows.append((len(bb)+GCA_HEADER,W,nbit,Kd))
    return min(rows,key=lambda x:x[0]),rows

def old_ar32(X,eps):
    a.C=C;a.NT=NT;z.C=C;z.NT=NT
    _,co=a.fits(X);R,K=a.run_ar(X,co)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError(('AR32 hard',me,eps))
    cand=[]
    for W in WINDOWS:
        bb,nbit=z.encode_zsm(K,W);Kd=z.decode_zsm(bb,nbit,W,K.shape)
        if not np.array_equal(Kd,K):raise RuntimeError(('AR32 ZSM decode',W))
        Rd=a.decode_source(Kd,co)
        if not np.array_equal(Rd,R):raise RuntimeError(('AR32 source replay',W))
        cand.append((len(bb)+a.MODEL_BYTES+33,W,nbit))
    return min(cand),float(np.mean(K==0)),me

def sz3_bytes(X,eps):
    n=0
    for t0 in range(0,NT,TB):
        b,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);n+=int(b)
    return n

def main(path):
    t0=time.time();out={'regions':[]}
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*float(gstd)
        out.update(global_std=float(gstd),eps=float(eps),shape=list(d.shape))
        for name,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            sz=sz3_bytes(X,eps)
            old,oldzero,olderr=old_ar32(X,eps)
            screens=[];cache={}
            for cname,cfg in CONFIGS.items():
                ts=time.time();R,Q,step=reconstruct(X,eps,cfg);me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps:raise RuntimeError((name,cname,'hard',me,eps))
                zb=zstd_bytes(Q);row={'config':cname,'features':sum(len(x[1]) for x in cfg),'zero_fraction':float(np.mean(Q==0)),'pm2_fraction':float(np.mean(np.abs(Q)<=2)),'q_std':float(np.std(Q.astype(np.float64))),'zstd_screen_bytes':int(zb),'maxerr':me,'seconds':time.time()-ts}
                screens.append(row);cache[cname]=(R,Q,step);print(json.dumps({'screen':name,**row}),flush=True)
            bestscreen=min(screens,key=lambda r:r['zstd_screen_bytes']);cname=bestscreen['config'];R,Q,step=cache[cname]
            best,allz=exact_zsm(Q);gbytes,W,nbit,Kd=best
            Rd,Qd,_=reconstruct(X,eps,CONFIGS[cname],Kd)
            if not np.array_equal(Qd,Q):raise RuntimeError((name,'Q replay'))
            if not np.array_equal(Rd,R):raise RuntimeError((name,'source replay'))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps:raise RuntimeError((name,'GCA hard',me,eps))
            row={'region':name,'c0':c0,'samples':int(X.size),'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'old_ar32_zsm':{'bytes':int(old[0]),'bps':8*old[0]/X.size,'window':int(old[1]),'zero_fraction':oldzero,'maxerr':olderr,'gain_vs_sz3':sz/old[0]},'gca_shared':{'config':cname,'bytes':int(gbytes),'bps':8*gbytes/X.size,'window':int(W),'step':float(step),'zero_fraction':float(np.mean(Q==0)),'pm2_fraction':float(np.mean(np.abs(Q)<=2)),'maxerr':me,'gain_vs_sz3':sz/gbytes,'gain_vs_old_ar32_zsm':old[0]/gbytes,'zsm_candidates':[{'window':int(w),'bytes':int(n),'bits':int(nb)} for n,w,nb,_ in allz]},'screens':screens}
            out['regions'].append(row);print(json.dumps({'RESULT':row},indent=2),flush=True)
    out['seconds']=time.time()-t0
    out['scope']='Imperial DAS generalization gate for GCA. The predictor carries zero fitted coefficients: encoder and decoder deterministically infer the local spatial-temporal model from already reconstructed fiber channels. Three fixed generic feature families are screened; one selector is covered by the charged 84-byte GCA header. The exact correction sequence is encoded/decoded by the existing adaptive zero/sign/gamma arithmetic address language, followed by full shared-predictor source replay and strict max-error validation. Old Huber AR32+ZSM and matched SZ3 are rerun on the identical 128x30000 objects and global epsilon. No dataset labels route the codec.'
    json.dump(out,open('imperial_gca_shared_gate.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
