import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGIONS=(('easy',2304),('medium',4608));C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
STRIDES=(4,8,16,32)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def make_schedule(stride):
    anchors=list(range(0,C,stride))
    if anchors[-1]!=C-1:anchors.append(C-1)
    order=list(anchors);parents={};anchor_set=set(anchors)
    def fill(l,r):
        if r-l<=1:return
        q=(l+r)//2
        if q==l or q==r:return
        parents[q]=(l,r);order.append(q)
        fill(l,q);fill(q,r)
    for l,r in zip(anchors[:-1],anchors[1:]):fill(l,r)
    if len(order)!=C or len(set(order))!=C:raise RuntimeError(('schedule',stride,len(order),len(set(order))))
    return order,parents,anchor_set

def fit_weights(X,TP,ER,parents):
    B=np.zeros((C,3),np.float32)
    for c,(l,r) in parents.items():
        y=X[c,:TRAIN].astype(np.float64)-TP[c,:TRAIN].astype(np.float64)
        A=np.column_stack((np.ones(TRAIN),ER[l,:TRAIN],ER[r,:TRAIN])).astype(np.float64)
        G=A.T@A;lam=1e-5*float(np.trace(G))/3.0+1e-8
        co=np.linalg.solve(G+lam*np.eye(3),A.T@y)
        B[c]=co.astype(np.float32)
    raw=np.ascontiguousarray(B).astype('<f4').tobytes();blob=Z.compress(raw)
    Bd=np.frombuffer(ZD.decompress(blob),'<f4').reshape(C,3).copy()
    if not np.array_equal(Bd,B):raise RuntimeError('weight decode')
    return Bd,len(blob)+24

def initial_weights(X,R0,K0,parents):
    TP0=R0.astype(np.int64)-STEP*K0.astype(np.int64)
    ER0=R0.astype(np.int64)-TP0
    return fit_weights(X,TP0,ER0,parents)

def run_codec(X,ar,B,order,parents):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);TP=np.zeros((C,NT),np.int32);ER=np.zeros((C,NT),np.int32)
    a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
    for t in range(NT):
        for c in order:
            tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            TP[c,t]=tp
            if c in parents:
                l,r=parents[c];co=B[c]
                sc=float(co[0])+float(co[1])*float(ER[l,t])+float(co[2])*float(ER[r,t])
                pred=tp+int(np.rint(sc))
            else:pred=tp
            k=int(np.rint((float(X[c,t])-pred)/STEP))
            if k<np.iinfo(np.int32).min or k>np.iinfo(np.int32).max:raise RuntimeError(('K overflow',c,t,k))
            K[c,t]=k;rv=pred+STEP*k
            if rv<np.iinfo(np.int32).min or rv>np.iinfo(np.int32).max:raise RuntimeError(('R overflow',c,t,rv))
            R[c,t]=rv;ER[c,t]=rv-tp
    return R,K,TP,ER

def decode_codec(K,ar,B,order,parents):
    R=np.zeros(K.shape,np.int32);ER=np.zeros(K.shape,np.int32);a=float(ar[0]);b=np.asarray(ar[1:],np.float32)
    for t in range(K.shape[1]):
        for c in order:
            tp=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            if c in parents:
                l,r=parents[c];co=B[c]
                pred=tp+int(np.rint(float(co[0])+float(co[1])*float(ER[l,t])+float(co[2])*float(ER[r,t])))
            else:pred=tp
            rv=pred+STEP*int(K[c,t]);R[c,t]=rv;ER[c,t]=rv-tp
    return R

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,ar=h.fits(X)
            R0,K0=h.run_ar(X,ar);base_backend,_=h.backend_bytes(K0);base_arith,_,_,K0d=h.arithmetic(K0);R0d=h.decode_source(K0d,ar)
            if not np.array_equal(R0,R0d):raise RuntimeError((region,'baseline decode'))
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            cand=[];keep={}
            for stride in STRIDES:
                order,parents,anchors=make_schedule(stride)
                B,model=initial_weights(X,R0,K0,parents)
                R,K,TP,ER=run_codec(X,ar,B,order,parents)
                # One decoder-real redesign on the candidate's actual prefix geometry.
                B,model=fit_weights(X,TP,ER,parents)
                R,K,TP,ER=run_codec(X,ar,B,order,parents)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,stride,'hard',me,eps))
                bb,reps=h.backend_bytes(K);screen=bb+model+1
                z={'stride':stride,'anchors':len(anchors),'model_bytes':model,'screen_bytes':int(screen),'screen_bps':8*screen/X.size,'gain_screen_vs_base':base_backend/screen,'k_zero':float(np.mean(K==0)),'k_std':float(np.std(K)),'maxerr':me,'reps':reps}
                cand.append(z);keep[stride]=(B,order,parents,R,K);print(json.dumps({'region':region,'candidate':{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
            best=min(cand,key=lambda z:z['screen_bytes']);B,order,parents,R,K=keep[best['stride']]
            cab,nbits,sbits,Kd=h.arithmetic(K);cab+=best['model_bytes']+1
            Rd=decode_codec(Kd,ar,B,order,parents);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,'final decode',me,eps))
            final={'stride':best['stride'],'anchors':best['anchors'],'bytes':int(cab),'bps':8*cab/X.size,'model_bytes':best['model_bytes'],'gain_vs_step267':float(base_arith/cab),'gain_vs_sz3':float(sz/cab),'ratio_to_2x':float(cab/(sz/2)),'k_zero':float(np.mean(K==0)),'maxerr':me}
            row={'region':region,'samples':int(X.size),'step267_bytes':int(base_arith),'step267_bps':8*base_arith/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':final,'candidates':cand};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Deployable source-coordinate two-sided spatial hierarchy on easy/medium Imperial. All sparse anchor channels are decoded first at each time using the incumbent decoder-real Huber AR32 temporal prediction. Between each adjacent anchor pair, channels are then recursively decoded in midpoint order. Every nonanchor channel uses a transmitted prefix-only 3-coefficient linear correction from the two already decoded bracketing channels current-time reconstructed temporal residuals. Coefficients are float32, Zstd-compressed, byte-decoded and charged; one stride selector byte is charged. A single redesign round fits on the candidate actual decoded-prefix residual geometry. Every sample still carries exact step267 correction, so max error is unchanged. K is independently cold-start-arithmetic decoded in the incumbent natural order before source replay, so entropy coding does not depend on the source reconstruction schedule. Complete source is regenerated and hard-error checked. No AI. Draft/do not merge.'},open('imperial_ar32_hierarchical_spatial_midpoints.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])