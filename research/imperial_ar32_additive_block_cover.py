import json,sys,math,warnings
import h5py,numpy as np,zstandard as zstd
from scipy.cluster.vq import kmeans2
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512; C=128; P=32; TRAIN=1024; END=8192; L=8; STEP=267
TARGET_CH=np.arange(0,128,4,dtype=np.int64)  # 32 hard-zone channels
BEAM=8; N3S=(64,256); SAFETY=1-1e-9
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/STEP).astype(np.int64);R[:,t]=pred+STEP*k
    me=float(np.max(np.abs(X[:,:TRAIN]-R)))
    if me>eps*(1+1e-10):raise RuntimeError(('prefix hard',me,eps))
    return int(mb),cd,R

def openloop(state,co):
    s=state.astype(np.int64).copy();base=np.empty(L,np.int64)
    for i in range(L):
        v=float(co[-1])
        for j in range(P):v+=float(co[j])*s[-1-j]
        y=int(np.rint(v));base[i]=y;s[:-1]=s[1:];s[-1]=y
    return base

def training_vectors(X,R,co):
    V=[]
    for c in range(C):
        for t in range(P,TRAIN-L+1,L):
            base=openloop(R[c,t-P:t],co);V.append(X[c,t:t+L].astype(np.float64)-base)
    return np.asarray(V,np.float64)

def nearest(V,CEN):
    out=np.empty(len(V),np.int32)
    for s in range(0,len(V),2048):
        a=V[s:s+2048]
        d=((a[:,None,:]-CEN[None,:,:])**2).sum(axis=2)
        out[s:s+len(a)]=np.argmin(d,axis=1)
    return out

def train_stage(V,k,seed):
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        CEN,_=kmeans2(V,k,iter=8,minit='++',seed=seed,check_finite=False)
    CEN=np.rint(CEN).astype(np.int32)
    idx=nearest(V,CEN);res=V-CEN[idx]
    return CEN,res,idx

def train_codebooks(V):
    c1,res1,_=train_stage(V,256,101)
    c2,res2,_=train_stage(res1,256,202)
    c3,res3,i3=train_stage(res2,256,303)
    cnt=np.bincount(i3,minlength=256);order=np.argsort(-cnt,kind='stable');c3=c3[order]
    return c1,c2,c3

def topk(scores,k):
    k=min(k,len(scores))
    if k==len(scores):return np.argsort(scores,kind='stable')
    q=np.argpartition(scores,k-1)[:k]
    return q[np.argsort(scores[q],kind='stable')]

def search(y,c1,c2,c3):
    e1=np.max(np.abs(y[None,:]-c1.astype(np.float64)),axis=1);i1=topk(e1,BEAM)
    sums=(c1[i1,None,:].astype(np.int64)+c2[None,:,:].astype(np.int64)).reshape(-1,L)
    e2=np.max(np.abs(y[None,:]-sums),axis=1);q2=topk(e2,BEAM)
    b1=(q2//len(c2)).astype(np.int64);i2=(q2%len(c2)).astype(np.int64);i1b=i1[b1];s2=sums[q2]
    s3=(s2[:,None,:]+c3[None,:,:].astype(np.int64)).reshape(-1,L)
    e3=np.max(np.abs(y[None,:]-s3),axis=1);q=int(np.argmin(e3));b=q//len(c3);i3=q%len(c3)
    return int(i1b[b]),int(i2[b]),int(i3),s3[q],float(e3[q])

def dtype_for(a):
    mn=int(np.min(a));mx=int(np.max(a))
    for dt in (np.dtype('i2'),np.dtype('i4'),np.dtype('i8')):
        z=np.iinfo(dt)
        if mn>=z.min and mx<=z.max:return dt
    return np.dtype('i8')

def codebook_frame(c1,c2,c3):
    arr=np.concatenate([c1.ravel(),c2.ravel(),c3.ravel()]).astype(np.int64);dt=dtype_for(arr)
    blob=ZC.compress(arr.astype(dt).tobytes());dec=np.frombuffer(ZD.decompress(blob),dtype=dt).astype(np.int32)
    n1=c1.size;n2=c2.size
    d1=dec[:n1].reshape(c1.shape);d2=dec[n1:n1+n2].reshape(c2.shape);d3=dec[n1+n2:].reshape(c3.shape)
    if not (np.array_equal(d1,c1) and np.array_equal(d2,c2) and np.array_equal(d3,c3)):raise RuntimeError('codebook decode')
    return len(blob)+32,d1,d2,d3,dt.str

def pack_fixed(vals,bits):
    vals=np.asarray(vals,np.uint64).ravel();out=bytearray();acc=0;nb=0;mask=(1<<bits)-1
    for v in vals:
        acc|=(int(v)&mask)<<nb;nb+=bits
        while nb>=8:out.append(acc&255);acc>>=8;nb-=8
    if nb:out.append(acc&255)
    return bytes(out)

def unpack_fixed(buf,bits,n):
    out=np.empty(n,np.uint16);acc=0;nb=0;j=0;mask=(1<<bits)-1
    for b in buf:
        acc|=int(b)<<nb;nb+=8
        while nb>=bits and j<n:
            out[j]=acc&mask;acc>>=bits;nb-=bits;j+=1
    if j!=n:raise RuntimeError(('short fixed stream',j,n))
    return out

def kframe(vals):
    vals=np.asarray(vals,np.int64).ravel()
    if vals.size==0:return 0,'empty',vals.copy()
    b,rep,dec=m.encode_k(vals.reshape(1,-1));return int(b)+20,rep,np.asarray(dec,np.int64).ravel()

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
        row=(int(b.size),me,'T' if tr else 'CT')
        if best is None or row[0]<best[0]:best=row
    return best

def baseline(X,co,R0,eps):
    Ks=[];Rs=[]
    for c in TARGET_CH:
        state=R0[c,-P:].copy();kk=[];rr=[]
        for t in range(TRAIN,END):
            v=float(co[-1])
            for j in range(P):v+=float(co[j])*state[-1-j]
            pred=int(np.rint(v));k=int(np.rint((float(X[c,t])-pred)/STEP));y=pred+STEP*k
            if abs(float(X[c,t])-y)>eps*(1+1e-10):raise RuntimeError('baseline hard')
            kk.append(k);rr.append(y);state[:-1]=state[1:];state[-1]=y
        Ks.append(kk);Rs.append(rr)
    K=np.asarray(Ks,np.int64);Rr=np.asarray(Rs,np.int64);kb,rep,kd=kframe(K)
    if not np.array_equal(kd.reshape(K.shape),K):raise RuntimeError('baseline k decode')
    seed=R0[TARGET_CH,-P:].astype(np.int32);sb=ZC.compress(seed.tobytes());sd=np.frombuffer(ZD.decompress(sb),np.int32).reshape(seed.shape)
    if not np.array_equal(seed,sd):raise RuntimeError('seed decode')
    return {'bytes':kb+len(sb)+32,'k_bytes':kb,'seed_bytes':len(sb)+32,'rep':rep,'maxerr':float(np.max(np.abs(X[TARGET_CH,TRAIN:END]-Rr)))}

def run_config(X,co,R0,eps,c1,c2,c3,n3,model_bytes):
    c3=c3[:n3].copy();cb,d1,d2,d3,dt=codebook_frame(c1,c2,c3);bits3=int(math.ceil(math.log2(n3)))
    mode=[];ids1=[];ids2=[];ids3=[];fallback=[];covered_err=[];allR=[]
    for c in TARGET_CH:
        state=R0[c,-P:].copy();rr=[]
        for t in range(TRAIN,END,L):
            base=openloop(state,co);src=X[c,t:t+L].astype(np.float64);y=src-base
            a,b,g,v,err=search(y,d1,d2,d3)
            if err<=eps*(1+1e-10):
                rec=base+v.astype(np.int64);mode.append(1);ids1.append(a);ids2.append(b);ids3.append(g);covered_err.append(float(np.max(np.abs(src-rec))))
            else:
                rec=np.empty(L,np.int64);ks=[];s=state.copy()
                for q in range(L):
                    vv=float(co[-1])
                    for j in range(P):vv+=float(co[j])*s[-1-j]
                    pred=int(np.rint(vv));k=int(np.rint((float(src[q])-pred)/STEP));z=pred+STEP*k
                    if abs(float(src[q])-z)>eps*(1+1e-10):raise RuntimeError(('fallback hard',c,t,q))
                    rec[q]=z;ks.append(k);s[:-1]=s[1:];s[-1]=z
                mode.append(0);fallback.extend(ks)
            rr.extend(rec.tolist())
            for z in rec:state[:-1]=state[1:];state[-1]=int(z)
        allR.append(rr)
    mode=np.asarray(mode,np.uint8);ids1=np.asarray(ids1,np.uint8);ids2=np.asarray(ids2,np.uint8);ids3=np.asarray(ids3,np.uint16)
    mb=ZC.compress(np.packbits(mode,bitorder='little').tobytes());mdec=np.unpackbits(np.frombuffer(ZD.decompress(mb),np.uint8),bitorder='little')[:len(mode)].astype(np.uint8)
    if not np.array_equal(mode,mdec):raise RuntimeError('mode decode')
    b1=ZC.compress(ids1.tobytes());dids1=np.frombuffer(ZD.decompress(b1),np.uint8)
    b2=ZC.compress(ids2.tobytes());dids2=np.frombuffer(ZD.decompress(b2),np.uint8)
    p3=pack_fixed(ids3,bits3);b3=ZC.compress(p3);dids3=unpack_fixed(ZD.decompress(b3),bits3,len(ids3))
    if not (np.array_equal(ids1,dids1) and np.array_equal(ids2,dids2) and np.array_equal(ids3,dids3)):raise RuntimeError('id decode')
    fb,frep,fdec=kframe(fallback)
    seed=R0[TARGET_CH,-P:].astype(np.int32);sb=ZC.compress(seed.tobytes());seeddec=np.frombuffer(ZD.decompress(sb),np.int32).reshape(seed.shape)
    # Replay decoder from serialized codebook/modes/IDs/fallback.
    pi=fi=0;decR=[]
    for ci,c in enumerate(TARGET_CH):
        state=seeddec[ci].astype(np.int64).copy();rr=[]
        for bi,t in enumerate(range(TRAIN,END,L)):
            mi=ci*((END-TRAIN)//L)+bi;base=openloop(state,co)
            if mdec[mi]:
                v=d1[int(dids1[pi])].astype(np.int64)+d2[int(dids2[pi])].astype(np.int64)+d3[int(dids3[pi])].astype(np.int64);rec=base+v;pi+=1
            else:
                rec=np.empty(L,np.int64)
                for q in range(L):
                    vv=float(co[-1])
                    for j in range(P):vv+=float(co[j])*state[-1-j]
                    pred=int(np.rint(vv));rec[q]=pred+STEP*int(fdec[fi]);fi+=1
                    state[:-1]=state[1:];state[-1]=rec[q]
                rr.extend(rec.tolist());continue
            rr.extend(rec.tolist())
            for z in rec:state[:-1]=state[1:];state[-1]=int(z)
        decR.append(rr)
    decR=np.asarray(decR,np.int64);me=float(np.max(np.abs(X[TARGET_CH,TRAIN:END]-decR)))
    if me>eps*(1+1e-10):raise RuntimeError(('final hard',n3,me,eps))
    total=model_bytes+cb+(len(sb)+32)+(len(mb)+20)+(len(b1)+20)+(len(b2)+20)+(len(b3)+20)+fb+64
    return {'n3':n3,'index_bits_nominal_per_block':16+bits3,'index_nominal_bps':(16+bits3)/L,'bytes':int(total),'bps':8*total/decR.size,
            'model_bytes':model_bytes,'codebook_bytes':cb,'seed_bytes':len(sb)+32,'mode_bytes':len(mb)+20,'id1_bytes':len(b1)+20,'id2_bytes':len(b2)+20,'id3_bytes':len(b3)+20,
            'fallback_bytes':fb,'fallback_rep':frep,'covered_fraction':float(np.mean(mode)),'fallback_fraction':float(np.mean(mode==0)),'maxerr':me,
            'median_covered_maxerr':float(np.median(covered_err)) if covered_err else None,'codebook_dtype':dt}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    model_bytes,co,R0=fit_prefix(X,eps);V=training_vectors(X,R0,co);print(json.dumps({'training_vectors':V.shape,'training_residual_std':float(V.std())}),flush=True)
    c1,c2,c3=train_codebooks(V);base=baseline(X,co,R0,eps);szb=szrun(X[TARGET_CH,TRAIN:END],eps)
    rows=[]
    for n3 in N3S:
        z=run_config(X,co,R0,eps,c1,c2,c3,n3,model_bytes);z['baseline_bytes']=base['bytes'];z['gain_vs_step267']=base['bytes']/z['bytes'];z['sz3_bytes']=szb[0];z['gain_vs_sz3']=szb[0]/z['bytes'];rows.append(z);print(json.dumps(z,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes'])
    out={'global_std':std,'eps':eps,'hard_region_c0':C0,'ar_order':P,'training_samples':TRAIN,'target_interval':[TRAIN,END],'target_channels':[int(C0+x) for x in TARGET_CH],
         'block_length':L,'beam':BEAM,'third_stage_sizes':list(N3S),'training_vector_count':len(V),'model_bytes':model_bytes,'baseline':base,
         'sz3':{'bytes':szb[0],'bps':8*szb[0]/(len(TARGET_CH)*(END-TRAIN)),'maxerr':szb[1],'orientation':szb[2]},'rows':rows,'best':rows[0],
         'scope':'Constructive additive vector-cover gate motivated by PR338. A shared AR32 model and three 8-D residual codebooks are learned only from t<1024 of the hard 128-channel block and fully serialized. On 32 held-out hard-zone channels, each future 8-sample block starts from decoder-known AR32 state; an open-loop AR32 trajectory is generated and a 3-stage additive residual codeword is selected by bounded beam search. Three small IDs implicitly choose among millions of 8-D trajectories. A block is accepted only if every reconstructed sample lies inside the unchanged +/-10%-global-std hard box; uncovered blocks fall back to exact step267 AR innovations. Codebook, state seed, mode mask, IDs, fallback innovations, model and framing are all actually serialized/decoded and charged; decoder replays the full target trajectory and hard error is verified. Matched SZ3 and step267 AR32 are rerun on exactly the same held-out array. No AI; hard-zone gate, not whole-array.'}
    print(json.dumps({'baseline':base,'sz3':out['sz3'],'best':rows[0]},indent=2),flush=True);json.dump(out,open('imperial_ar32_additive_block_cover.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
