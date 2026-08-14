import json,sys
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=128;NT=30000;TRAIN=1024;P=32;STEP=267;TB=1024;C0=2304
WIDTHS=(64,127);ORDERS=('natural','parity','multiscale')
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def order_vec(name):
    if name=='natural':return np.arange(C,dtype=np.int32)
    if name=='parity':return np.r_[np.arange(0,C,2),np.arange(1,C,2)].astype(np.int32)
    out=[0,C-1];seen=set(out);q=[(0,C-1)]
    while q:
        l,r=q.pop(0)
        if r-l<=1:continue
        mid=(l+r)//2
        if mid not in seen:out.append(mid);seen.add(mid)
        q.append((l,mid));q.append((mid,r))
    for c in range(C):
        if c not in seen:out.append(c)
    if len(out)!=C or len(set(out))!=C:raise RuntimeError(('order',name,len(out)))
    return np.asarray(out,np.int32)

def feature_matrix(order,width):
    F=np.full((C,width),-1,np.int32);seen=[]
    for c0 in order:
        c=int(c0)
        if seen:
            p=np.asarray(seen,np.int32);idx=np.argsort(np.abs(p-c),kind='stable')[:width];ff=p[idx]
            F[c,:len(ff)]=ff
        seen.append(c)
    return F

def fit_model(X,TP,ER,F,width):
    B=np.zeros((C,width+1),np.float32)
    for c in range(C):
        ff=F[c];ff=ff[ff>=0]
        y=X[c,:TRAIN].astype(np.float64)-TP[c,:TRAIN].astype(np.float64)
        if len(ff)==0:
            B[c,0]=np.float32(np.mean(y));continue
        A=np.column_stack((np.ones(TRAIN),ER[ff,:TRAIN].T)).astype(np.float64)
        G=A.T@A;lam=1e-5*float(np.trace(G))/max(1,A.shape[1])+1e-8
        co=np.linalg.solve(G+lam*np.eye(A.shape[1]),A.T@y)
        B[c,:len(co)]=co.astype(np.float32)
    raw=np.ascontiguousarray(B).astype('<f4').tobytes();blob=Z.compress(raw)
    Bd=np.frombuffer(ZD.decompress(blob),'<f4').reshape(B.shape).copy()
    if not np.array_equal(Bd,B):raise RuntimeError('model decode')
    return Bd,len(blob)+32

@njit(cache=True)
def run_codec(X,ar,B,order,F,width):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);TP=np.zeros((C,NT),np.int32);ER=np.zeros((C,NT),np.int32)
    a=float(ar[0]);b=ar[1:].astype(np.float32)
    for t in range(NT):
        for oi in range(C):
            c=int(order[oi]);tp=0
            if t>=P:
                s=a
                for j in range(P):s+=float(b[j])*float(R[c,t-1-j])
                tp=int(np.rint(s))
            TP[c,t]=tp;sc=float(B[c,0])
            for j in range(width):
                f=int(F[c,j])
                if f<0:break
                sc+=float(B[c,j+1])*float(ER[f,t])
            pred=tp+int(np.rint(sc));k=int(np.rint((X[c,t]-pred)/STEP));K[c,t]=k
            rv=pred+STEP*k;R[c,t]=rv;ER[c,t]=rv-tp
    return R,K,TP,ER

@njit(cache=True)
def decode_codec(K,ar,B,order,F,width):
    R=np.zeros((C,NT),np.int32);ER=np.zeros((C,NT),np.int32);a=float(ar[0]);b=ar[1:].astype(np.float32)
    for t in range(NT):
        for oi in range(C):
            c=int(order[oi]);tp=0
            if t>=P:
                s=a
                for j in range(P):s+=float(b[j])*float(R[c,t-1-j])
                tp=int(np.rint(s))
            sc=float(B[c,0])
            for j in range(width):
                f=int(F[c,j])
                if f<0:break
                sc+=float(B[c,j+1])*float(ER[f,t])
            pred=tp+int(np.rint(sc));rv=pred+STEP*int(K[c,t]);R[c,t]=rv;ER[c,t]=rv-tp
    return R

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;X=np.asarray(d[:,C0:C0+C],np.float64).T
        _,ar=h.fits(X);R0,K0=h.run_ar(X,ar);base_backend,_=h.backend_bytes(K0);base_arith,_,_,K0d=h.arithmetic(K0);R0d=h.decode_source(K0d,ar)
        if not np.array_equal(R0,R0d):raise RuntimeError('baseline decode')
        TP0=R0.astype(np.int64)-STEP*K0.astype(np.int64);ER0=R0.astype(np.int64)-TP0
        sz=0
        for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:min(NT,t0+TB)],eps);sz+=int(bb)
        cand=[];keep={}
        # Warm JIT on a real candidate; compilation is not part of byte accounting.
        for oname in ORDERS:
            order=order_vec(oname)
            for width in WIDTHS:
                F=feature_matrix(order,width);B,model=fit_model(X,TP0,ER0,F,width)
                R,K,TP,ER=run_codec(X,ar,B,order,F,width)
                B,model=fit_model(X,TP,ER,F,width);R,K,TP,ER=run_codec(X,ar,B,order,F,width)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((oname,width,'hard',me,eps))
                bb,reps=h.backend_bytes(K);screen=bb+model+2
                z={'order':oname,'width':width,'model_bytes':model,'screen_bytes':int(screen),'screen_bps':8*screen/X.size,'gain_screen_vs_baseline':float(base_backend/screen),'k_zero':float(np.mean(K==0)),'k_std':float(np.std(K)),'maxerr':me,'reps':reps}
                cand.append(z);keep[(oname,width)]=(B,order,F,R,K);print(json.dumps({'candidate':{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
        best=min(cand,key=lambda z:z['screen_bytes']);B,order,F,R,K=keep[(best['order'],best['width'])]
        cab,_,_,Kd=h.arithmetic(K);cab+=best['model_bytes']+2;Rd=decode_codec(Kd,ar,B,order,F,best['width']);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError(('final decode',me,eps))
        final={'order':best['order'],'width':best['width'],'bytes':int(cab),'bps':8*cab/X.size,'model_bytes':best['model_bytes'],'gain_vs_step267':float(base_arith/cab),'gain_vs_sz3':float(sz/cab),'ratio_to_2x':float(cab/(sz/2)),'k_zero':float(np.mean(K==0)),'maxerr':me}
        out={'eps':eps,'region':'easy','c0':C0,'samples':int(X.size),'step267_bytes':int(base_arith),'step267_bps':8*base_arith/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':final,'candidates':cand,'scope':'Full 30,000-sample easy-block source-coordinate spatial Cholesky gate designed to amortize broad model cost. The Huber AR32 temporal predictor is unchanged. Three deterministic spatial decode orders are tested: natural, parity-first, and breadth-first multiscale. Each channel adds a prefix-only ridge correction from the nearest up to 64 or all 127 already decoded current-time reconstructed temporal residual channels under that order. Float32 coefficient matrices are Zstd-compressed, byte-decoded and fully charged; one redesign round uses candidate decoded-prefix geometry. Candidate K is screened losslessly, the winner is cold-start-arithmetic decoded, and the full source is replayed with unchanged hard-error verification. This is a deployable full-length test of whether PR #437 broad easy-region linear headroom was being hidden by short-pilot model overhead or one-sided/local spatial order. No AI. Draft/do not merge.'}
        print(json.dumps({'summary':out},indent=2),flush=True);json.dump(out,open('imperial_easy_fullwidth_spatial_cholesky.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])