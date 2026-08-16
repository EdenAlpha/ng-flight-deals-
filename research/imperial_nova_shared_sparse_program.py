import json,sys,math,struct
import h5py,numpy as np,zstandard as zstd
from sklearn.decomposition import MiniBatchDictionaryLearning,SparseCoder
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar
import imperial_persistent_ar32_full_array_jit as inc

C=128; NT=4096; T0=14488; TRAIN=1024; P=32; TARGET_STEP=267
REGIONS=(('hard',512),('easy',2304)); PC=8; PT=64; DIM=PC*PT
ATOMS=256; SPARSITIES=(2,4,8,16,32); QSTEPS=(0.125,0.25,0.5,1.0,2.0)
HEADER=96; ZC=zstd.ZstdCompressor(level=19); ZM=zstd.ZstdCompressor(level=22)

def get_k(path,c0,target=False):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+NT,c0:c0+C],np.float64).T
    step=TARGET_STEP if target else int(math.floor(2*eps));old=m.STEP;m.STEP=step
    try:
        co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=inc.build(X,cd)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('hard',path,c0,step,me,eps))
        return {'X':X,'K':np.asarray(K,np.int32),'std':std,'eps':eps,'step':step,'model_bytes':int(mb),'cd':cd,'maxerr':me}
    finally:m.STEP=old

def patch(K):
    K=np.asarray(K,np.int32);rows=[]
    for c in range(0,C,PC):
        for t in range(0,NT,PT):rows.append(K[c:c+PC,t:t+PT].reshape(-1))
    return np.asarray(rows,np.float32)

def unpatch(A):
    A=np.asarray(A,np.int32);K=np.empty((C,NT),np.int32);i=0
    for c in range(0,C,PC):
        for t in range(0,NT,PT):K[c:c+PC,t:t+PT]=A[i].reshape(PC,PT);i+=1
    return K

def train_dictionary(A,seed):
    mdl=MiniBatchDictionaryLearning(n_components=ATOMS,alpha=1.0,max_iter=60,batch_size=128,
        fit_algorithm='cd',transform_algorithm='omp',transform_n_nonzero_coefs=8,
        random_state=seed,shuffle=True,verbose=False)
    mdl.fit(np.asarray(A,np.float64));D=np.asarray(mdl.components_,np.float32)
    raw=D.astype('<f4').tobytes();blob=ZM.compress(raw);D2=np.frombuffer(raw,dtype='<f4').reshape(D.shape).copy()
    return D2,len(blob),len(raw)

def pack_sparse(Q):
    Q=np.asarray(Q,np.int32);out=bytearray();out+=struct.pack('<I',Q.shape[0])
    for row in Q:
        nz=np.flatnonzero(row)
        if len(nz)>255:raise RuntimeError('too many nz')
        out.append(len(nz))
        for j in nz:
            v=int(row[j])
            if v<-32768 or v>32767:raise RuntimeError(('coef overflow',v))
            out.append(int(j));out+=struct.pack('<h',v)
    return bytes(out)

def unpack_sparse(raw,nrows):
    q=np.zeros((nrows,ATOMS),np.int32);off=0
    got=struct.unpack_from('<I',raw,off)[0];off+=4
    if got!=nrows:raise RuntimeError(('rows',got,nrows))
    for i in range(nrows):
        n=raw[off];off+=1
        for _ in range(n):
            j=raw[off];off+=1;v=struct.unpack_from('<h',raw,off)[0];off+=2;q[i,j]=v
    if off!=len(raw):raise RuntimeError(('latent trailing',off,len(raw)))
    return q

def replay(rec,K):
    old=m.STEP;m.STEP=rec['step']
    try:R=inc.decode(np.asarray(K,np.int32),rec['cd'])
    finally:m.STEP=old
    me=float(np.max(np.abs(rec['X']-R.astype(np.float64))))
    if me>rec['eps']*(1+1e-12):raise RuntimeError(('replay hard',me,rec['eps']))
    return me

def candidate(T,D,dname,s,qstep,rec):
    coder=SparseCoder(dictionary=np.asarray(D,np.float64),transform_algorithm='omp',transform_n_nonzero_coefs=s)
    code=np.asarray(coder.transform(np.asarray(T,np.float64)),np.float64)
    Q=np.rint(code/qstep).astype(np.int32);latent_raw=pack_sparse(Q);latent_blob=ZC.compress(latent_raw)
    Q2=unpack_sparse(zstd.ZstdDecompressor().decompress(latent_blob),len(T))
    if not np.array_equal(Q2,Q):raise RuntimeError('latent replay')
    pred=np.rint((Q2.astype(np.float64)*qstep)@np.asarray(D,np.float64)).astype(np.int32)
    corr=np.asarray(T,np.int32)-pred;KC=unpatch(corr)
    old=m.STEP;m.STEP=TARGET_STEP
    try:cf=m.encode_k(KC)
    finally:m.STEP=old
    Cd=np.asarray(cf[2],np.int32)
    if not np.array_equal(Cd,KC):raise RuntimeError('correction decode')
    K2=unpatch(pred)+Cd
    if not np.array_equal(K2,rec['K']):raise RuntimeError('K reconstruction')
    me=replay(rec,K2)
    total=len(latent_blob)+int(cf[0])+rec['model_bytes']+HEADER
    return {'dictionary':dname,'sparsity':s,'qstep':qstep,'latent_bytes':len(latent_blob),'correction_bytes':int(cf[0]),
        'correction_rep':cf[1],'model_bytes':rec['model_bytes'],'total_shared_bytes':int(total),'bps':8*total/rec['K'].size,
        'latent_nonzeros':int(np.count_nonzero(Q)),'mean_nz_per_patch':float(np.count_nonzero(Q)/len(Q)),
        'correction_zero_fraction':float(np.mean(KC==0)),'correction_std':float(np.std(KC)),'maxerr':me}

def main(p0,p1,pt):
    train_by_region={}
    train_meta=[]
    for name,c0 in REGIONS:
        parts=[]
        for p in (p0,p1):
            r=get_k(p,c0,False);parts.append(patch(r['K']));train_meta.append({'file':p,'region':name,'std':r['std'],'eps':r['eps'],'step':r['step'],'k_std':float(np.std(r['K']))})
        train_by_region[name]=np.concatenate(parts,axis=0)
    models={};model_meta={}
    for i,(name,_) in enumerate(REGIONS):
        D,cb,raw=train_dictionary(train_by_region[name],2026+i);models[name]=D;model_meta[name]={'compressed_bytes':cb,'raw_float32_bytes':raw,'atoms':ATOMS,'dimension':DIM}
        print('trained',name,model_meta[name],flush=True)
    installed_model_bytes=sum(x['compressed_bytes'] for x in model_meta.values())
    rows=[]
    for region,c0 in REGIONS:
        rec=get_k(pt,c0,True);T=patch(rec['K']);old=m.STEP;m.STEP=TARGET_STEP
        try:basefr=m.encode_k(rec['K'])
        finally:m.STEP=old
        if not np.array_equal(np.asarray(basefr[2],np.int32),rec['K']):raise RuntimeError('base K')
        incumbent=int(basefr[0])+rec['model_bytes']+HEADER;szb,ori=m.szrun(rec['X'],rec['eps']);cand=[]
        for dname,D in models.items():
            for s in SPARSITIES:
                for qs in QSTEPS:cand.append(candidate(T,D,dname,s,qs,rec))
        cand.sort(key=lambda z:z['total_shared_bytes']);best=cand[0]
        selected_model_bytes=model_meta[best['dictionary']]['compressed_bytes'];best['selected_model_standalone_bytes']=best['total_shared_bytes']+selected_model_bytes
        best['installed_two_dictionary_total_bytes']=best['total_shared_bytes']+installed_model_bytes
        best['gain_vs_incumbent_shared']=incumbent/best['total_shared_bytes'];best['gain_vs_incumbent_selected_model_charged']=incumbent/best['selected_model_standalone_bytes'];best['gain_vs_sz3_shared']=int(szb)/best['total_shared_bytes']
        row={'region':region,'c0':c0,'samples':int(rec['K'].size),'global_std':rec['std'],'eps':rec['eps'],'step':rec['step'],
            'patch':[PC,PT],'patches':len(T),'incumbent':{'bytes':incumbent,'innovation_bytes':int(basefr[0]),'rep':basefr[1],'bps':8*incumbent/rec['K'].size},
            'sz3':{'bytes':int(szb),'bps':8*int(szb)/rec['K'].size,'orientation':ori},'best':best,'top':cand[:10]}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'training_records':[p0,p1],'target_record':pt,'train_meta':train_meta,'model_meta':model_meta,'installed_model_bytes':installed_model_bytes,
        'patch':[PC,PT],'atoms':ATOMS,'sparsities':list(SPARSITIES),'qsteps':list(QSTEPS),'rows':rows,
        'scope':'Decoder-real NOVA/shared-model sparse-program gate. Two chronologically prior Imperial records only train two frozen 256-atom dictionaries over 8x64=512-sample dimensionless AR innovation patches (one model family per precommitted prior-region regime; target may select either and selector is covered by fixed framing). Target data never trains atoms. Encoder uses OMP to search sparse latent programs and quantizes coefficients; decoder receives an actual compressed sparse latent stream, regenerates a 512-sample innovation patch from the frozen model, then applies an actual self-decoding exact correction stream so final K is bit-identical to incumbent AR32 K. AR32 source replay and hard error are independently verified. total_shared_bytes treats frozen atom models as installed/shared codec infrastructure; selected-model and installed-two-model standalone totals explicitly charge compressed float32 model bytes. No ideal entropy, oracle, target-trained model, or unmaterialized latent counts as compression.'}
    json.dump(out,open('imperial_nova_shared_sparse_program.json','w'),indent=2)
if __name__=='__main__':main(*sys.argv[1:4])
