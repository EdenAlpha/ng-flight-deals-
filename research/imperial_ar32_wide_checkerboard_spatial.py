import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGION=('easy',2304);C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
WIDTHS=(2,4,8,16,32);PARITIES=(0,1)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def geometry(parity,width):
    anchors=np.arange(parity,C,2,dtype=np.int32)
    aset=set(int(x) for x in anchors);deps=np.asarray([c for c in range(C) if c not in aset],np.int32)
    feats={}
    for c in deps:
        d=np.abs(anchors-int(c));o=np.argsort(d,kind='stable')[:width];feats[int(c)]=anchors[o].astype(np.int32)
    order=[int(x) for x in anchors]+[int(x) for x in deps]
    return order,aset,feats

def fit_weights(X,TP,ER,feats,width):
    B=np.zeros((C,width+1),np.float32)
    for c,ff in feats.items():
        y=X[c,:TRAIN].astype(np.float64)-TP[c,:TRAIN].astype(np.float64)
        A=np.column_stack([np.ones(TRAIN)]+[ER[int(q),:TRAIN] for q in ff]).astype(np.float64)
        G=A.T@A;lam=1e-5*float(np.trace(G))/max(1,width+1)+1e-8
        co=np.linalg.solve(G+lam*np.eye(width+1),A.T@y);B[c]=co.astype(np.float32)
    raw=np.ascontiguousarray(B).astype('<f4').tobytes();blob=Z.compress(raw)
    Bd=np.frombuffer(ZD.decompress(blob),'<f4').reshape(B.shape).copy()
    if not np.array_equal(Bd,B):raise RuntimeError('model decode')
    return Bd,len(blob)+24

def initial_weights(X,R0,K0,feats,width):
    TP=R0.astype(np.int64)-STEP*K0.astype(np.int64);ER=R0.astype(np.int64)-TP
    return fit_weights(X,TP,ER,feats,width)

def run_codec(X,ar,B,order,feats):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);TP=np.zeros((C,NT),np.int32);ER=np.zeros((C,NT),np.int32)
    a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
    for t in range(NT):
        for c in order:
            tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            TP[c,t]=tp
            ff=feats.get(c)
            if ff is None:pred=tp
            else:
                co=B[c];sc=float(co[0])+float(np.dot(co[1:].astype(np.float32),ER[ff,t].astype(np.float32)))
                pred=tp+int(np.rint(sc))
            k=int(np.rint((float(X[c,t])-pred)/STEP));K[c,t]=k;rv=pred+STEP*k;R[c,t]=rv;ER[c,t]=rv-tp
    return R,K,TP,ER

def decode_codec(K,ar,B,order,feats):
    R=np.zeros(K.shape,np.int32);ER=np.zeros(K.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
    for t in range(K.shape[1]):
        for c in order:
            tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            ff=feats.get(c)
            if ff is None:pred=tp
            else:
                co=B[c];pred=tp+int(np.rint(float(co[0])+float(np.dot(co[1:].astype(np.float32),ER[ff,t].astype(np.float32)))))
            rv=pred+STEP*int(K[c,t]);R[c,t]=rv;ER[c,t]=rv-tp
    return R

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;region,c0=REGION
        X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,ar=h.fits(X);R0,K0=h.run_ar(X,ar)
        base_backend,_=h.backend_bytes(K0);base_arith,_,_,K0d=h.arithmetic(K0);R0d=h.decode_source(K0d,ar)
        if not np.array_equal(R0,R0d):raise RuntimeError('baseline decode')
        sz=0
        for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
        cand=[];keep={}
        for parity in PARITIES:
            for width in WIDTHS:
                order,anchors,feats=geometry(parity,width);B,model=initial_weights(X,R0,K0,feats,width)
                R,K,TP,ER=run_codec(X,ar,B,order,feats)
                B,model=fit_weights(X,TP,ER,feats,width);R,K,TP,ER=run_codec(X,ar,B,order,feats)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((parity,width,'hard',me,eps))
                bb,reps=h.backend_bytes(K);screen=bb+model+2
                z={'parity':parity,'width':width,'anchors':len(anchors),'model_bytes':model,'screen_bytes':int(screen),'screen_bps':8*screen/X.size,'gain_screen_vs_base':base_backend/screen,'k_zero':float(np.mean(K==0)),'k_std':float(np.std(K)),'maxerr':me,'reps':reps};cand.append(z);keep[(parity,width)]=(B,order,feats,R,K);print(json.dumps({'candidate':{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
        best=min(cand,key=lambda z:z['screen_bytes']);B,order,feats,R,K=keep[(best['parity'],best['width'])]
        cab,_,_,Kd=h.arithmetic(K);cab+=best['model_bytes']+2;Rd=decode_codec(Kd,ar,B,order,feats);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError(('final decode',me,eps))
        final={'parity':best['parity'],'width':best['width'],'bytes':int(cab),'bps':8*cab/X.size,'model_bytes':best['model_bytes'],'gain_vs_step267':float(base_arith/cab),'gain_vs_sz3':float(sz/cab),'ratio_to_2x':float(cab/(sz/2)),'k_zero':float(np.mean(K==0)),'maxerr':me}
        out={'eps':eps,'region':region,'samples':int(X.size),'step267_bytes':int(base_arith),'step267_bps':8*base_arith/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':final,'candidates':cand,'scope':'Deployable wide symmetric parity spatial predictor on easy Imperial. One sensor parity is decoded first at each time using the incumbent Huber AR32 temporal predictor. Every opposite-parity sensor is then predicted from the nearest 2/4/8/16/32 already decoded anchor-parity reconstructed temporal residuals on both sides, with a prefix-only per-channel ridge linear model. Float32 model bytes are Zstd-compressed, byte-decoded and charged; one decoder-real redesign round is performed. The exact step267 K stream is independently cold-start-arithmetic decoded in natural order before source replay, so entropy coding is unchanged. Full source regeneration and max-error verification are mandatory. This is the implementable broad two-sided linear approximation to the positive all-neighbor easy-region oracle in PR #437. No AI. Draft/do not merge.'}
        print(json.dumps({'summary':out},indent=2),flush=True);json.dump(out,open('imperial_ar32_wide_checkerboard_spatial.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])