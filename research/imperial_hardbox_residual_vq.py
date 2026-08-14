import json,sys,math,struct
import h5py,numpy as np,zstandard as zstd
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_decoder_phase_automaton as m

C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
REGIONS=(('hard',512),('easy',2304));GROUPS=(2,4);MS=(4,8,16)
Z=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def train_books(X,P0,g,Mmax,eps):
    ng=C//g;books=np.empty((ng,Mmax,g),np.int32);cover_train=[]
    for q in range(ng):
        sl=slice(q*g,(q+1)*g)
        V=np.rint((X[sl,:TRAIN]-P0[sl,:TRAIN]).T).astype(np.int32)
        # Candidate centers are exact prefix residual vectors. A center covers a
        # vector only when every coordinate is already inside the public box.
        D=np.max(np.abs(V[:,None,:].astype(np.int64)-V[None,:,:].astype(np.int64)),axis=2)<=eps
        uncovered=np.ones(TRAIN,bool);chosen=[]
        for j in range(Mmax):
            if np.any(uncovered):
                score=D[:,uncovered].sum(axis=1);ix=int(np.argmax(score))
            else:ix=0
            chosen.append(ix);uncovered &= ~D[ix]
        books[q]=V[np.asarray(chosen)]
        cover_train.append(float(1-uncovered.mean()))
    return books,float(np.mean(cover_train))

def pack_codebook(B):
    if int(B.min())>=-32768 and int(B.max())<=32767:
        raw=np.asarray(B,dtype='<i2').tobytes();dtype='i16'
    else:
        raw=np.asarray(B,dtype='<i4').tobytes();dtype='i32'
    blob=Z.compress(raw);dec=ZD.decompress(blob)
    if dec!=raw:raise RuntimeError('codebook byte decode')
    return blob,dtype

def encode_tokens(T,M):
    ng,nt=T.shape;nb=max(1,int(math.ceil(math.log2(M+1))));nctx=ng*nb*4;E=h.AE(nctx)
    for t in range(nt):
        for q in range(ng):
            val=int(T[q,t]);pref=0
            for bp in range(nb-1,-1,-1):
                bit=(val>>bp)&1;pos=nb-1-bp;cx=((q*nb+pos)*4+pref);E.put(bit,cx);pref=((pref<<1)|bit)&3
    bb,nbit=E.finish();D=h.AD(bb,nbit,nctx);Td=np.zeros_like(T)
    for t in range(nt):
        for q in range(ng):
            val=0;pref=0
            for bp in range(nb-1,-1,-1):
                pos=nb-1-bp;cx=((q*nb+pos)*4+pref);bit=D.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
            Td[q,t]=val
    if not np.array_equal(Td,T):raise RuntimeError('token decode')
    return bb,nbit,Td

def pack_escapes(E):
    E=np.asarray(E,np.int32)
    if E.size==0:return b'', 'empty', E.copy()
    if int(E.min())<-32768 or int(E.max())>32767:dt='<i4'
    else:dt='<i2'
    variants=[]
    raw=np.asarray(E,dtype=dt).tobytes();variants.append(('raw',Z.compress(raw),raw,dt))
    D=E.copy()
    if E.shape[1]>1:D[:,1:]=E[:,1:]-E[:,:-1]
    raw2=np.asarray(D,dtype=dt).tobytes();variants.append(('within_delta',Z.compress(raw2),raw2,dt))
    flat=E.ravel();ds=np.empty_like(flat);ds[0]=flat[0]
    if len(flat)>1:ds[1:]=np.diff(flat)
    raw3=np.asarray(ds,dtype=dt).tobytes();variants.append(('stream_delta',Z.compress(raw3),raw3,dt))
    name,blob,rawx,dtype=min(variants,key=lambda z:len(z[1]));arr=np.frombuffer(ZD.decompress(blob),dtype=dtype).astype(np.int32)
    if name=='raw':Ed=arr.reshape(E.shape)
    elif name=='within_delta':
        Ed=arr.reshape(E.shape);Ed=np.cumsum(Ed,axis=1,dtype=np.int64).astype(np.int32)
    else:
        Ed=np.cumsum(arr,dtype=np.int64).astype(np.int32).reshape(E.shape)
    if not np.array_equal(Ed,E):raise RuntimeError(('escape decode',name))
    return blob,name,Ed

def run_candidate(X,co,Rprefix,books,g,M,eps):
    ng=C//g;tail=NT-TRAIN;T=np.full((ng,tail),M,np.uint8);esc=[];R=np.zeros((C,NT),np.int32);R[:,:TRAIN]=Rprefix
    a=float(co[0]);b=np.asarray(co[1:],np.float32);hits=0
    for tt,t in enumerate(range(TRAIN,NT)):
        pred=np.empty(C,np.int32)
        for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
        for q in range(ng):
            sl=slice(q*g,(q+1)*g);e=X[sl,t]-pred[sl].astype(np.float64);B=books[q,:M]
            ok=np.max(np.abs(B.astype(np.float64)-e[None,:]),axis=1)<=eps
            if np.any(ok):
                j=int(np.flatnonzero(ok)[0]);T[q,tt]=j;R[sl,t]=pred[sl]+B[j];hits+=1
            else:
                k=np.rint(e/STEP).astype(np.int32);rr=pred[sl].astype(np.int64)+STEP*k.astype(np.int64)
                if float(np.max(np.abs(X[sl,t]-rr.astype(np.float64))))>eps*(1+1e-12):raise RuntimeError(('escape hard',q,t))
                R[sl,t]=rr.astype(np.int32);esc.append(k.copy())
    return R,T,np.asarray(esc,np.int32).reshape(-1,g),float(hits/(ng*tail))

def decode_candidate(Kpre,co,books,g,M,T,Esc):
    ng=C//g;R=np.zeros((C,NT),np.int32);R[:,:TRAIN]=h.decode_source(Kpre,co);a=float(co[0]);b=np.asarray(co[1:],np.float32);ep=0
    for tt,t in enumerate(range(TRAIN,NT)):
        pred=np.empty(C,np.int32)
        for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
        for q in range(ng):
            sl=slice(q*g,(q+1)*g);j=int(T[q,tt])
            if j<M:R[sl,t]=pred[sl]+books[q,j]
            elif j==M:
                if ep>=len(Esc):raise RuntimeError('escape eof')
                R[sl,t]=pred[sl]+STEP*Esc[ep];ep+=1
            else:raise RuntimeError(('bad token',j,M))
    if ep!=len(Esc):raise RuntimeError(('escape tail',ep,len(Esc)))
    return R

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X);R0,K0=h.run_ar(X,co);base,_,_,K0d=h.arithmetic(K0);R0d=h.decode_source(K0d,co)
            if not np.array_equal(R0,R0d):raise RuntimeError((region,'baseline decode'))
            old=h.NT;h.NT=TRAIN;prebytes,_,_,Kpre=h.arithmetic(K0[:,:TRAIN]);h.NT=old
            Rpre=h.decode_source(Kpre,co);P0=R0.astype(np.int64)-STEP*K0.astype(np.int64)
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            vv=[]
            for g in GROUPS:
                books16,traincover=train_books(X,P0,g,max(MS),eps)
                for M in MS:
                    books=books16[:,:M].copy();R,T,Esc,hit=run_candidate(X,co,Rpre,books,g,M,eps);me=float(np.max(np.abs(X-R.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,g,M,'hard',me,eps))
                    cb,cdtype=pack_codebook(books);tb,nbit,Td=encode_tokens(T,M);eb,emethod,Ed=pack_escapes(Esc)
                    Rd=decode_candidate(Kpre,co,books,g,M,Td,Ed);dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                    if not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((region,g,M,'decode',dme,eps))
                    total=int(prebytes+len(cb)+len(tb)+len(eb)+80)
                    z={'group':g,'M':M,'bytes':total,'bps':8*total/X.size,'prefix_bytes':int(prebytes),'codebook_bytes':len(cb),'token_bytes':len(tb),'escape_bytes':len(eb),'escape_method':emethod,'codebook_dtype':cdtype,'tail_hit_fraction':hit,'train_cover_fraction_M16':traincover,'escape_fraction':float(len(Esc)/(T.size)),'gain_vs_step267':float(base/total),'gain_vs_sz3':float(sz/total),'ratio_to_2x':float(total/(sz/2)),'maxerr':dme,'token_arithmetic_bits':int(nbit)}
                    vv.append(z);print(json.dumps({'region':region,'candidate':z},indent=2),flush=True)
            best=min(vv,key=lambda z:z['bytes']);row={'region':region,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':vv};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Direct source-coordinate hard-box vector-quantization gate. The first 1024 samples use the exact incumbent Huber AR32 step267 path and are independently arithmetic-decoded. For each contiguous 2/4-channel group, a small transmitted codebook is greedily trained from exact prefix temporal residual vectors: each selected center maximizes newly covered prefix vectors under the ORIGINAL coordinatewise L-infinity radius epsilon. After the prefix, the decoder-real AR32 predictor runs normally. A codeword token is emitted only when every current source residual coordinate is within epsilon of that codeword; otherwise the group emits an exact step267 escape vector. Codebooks are Zstd-compressed and byte-decoded, token IDs use exact adaptive arithmetic with per-group contexts, escape vectors use the cheapest exact Zstd layout, all framing is charged, and the complete recursive source is replayed and hard-error checked. Unlike Hadamard/Haar/KLT, this never rotates the error cube. No AI. Draft/do not merge.'},open('imperial_hardbox_residual_vq.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])