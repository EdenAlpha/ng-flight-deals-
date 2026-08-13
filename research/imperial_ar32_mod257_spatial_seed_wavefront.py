import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar

C0=512;C=128;P=32;TRAIN=1024;END=4096;MOD=257
SIZES=(64,256);MODES=(('mag',0.0,0.0),('mag_ts',0.12,0.12),('mag_ts2',0.28,0.20))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor();MASK=np.uint64(0xffffffffffffffff)

def splitmix64(x):
    x=(x+np.uint64(0x9E3779B97F4A7C15))&MASK;z=x.copy();z=((z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9))&MASK;z=((z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB))&MASK;return z^(z>>np.uint64(31))

def residue_matrix(n,t):
    s=np.arange(n,dtype=np.uint64)[:,None];c=np.arange(C,dtype=np.uint64)[None,:]
    x=s ^ (np.uint64(t+1)*np.uint64(0xD1B54A32D192ED03)) ^ ((c+np.uint64(1))*np.uint64(0x94D049BB133111EB));return (splitmix64(x)%np.uint64(MOD)).astype(np.int16)

def fit_prefix(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int32)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/267.0).astype(np.int64);rr=pred+267*k
        if float(np.max(np.abs(X[:,t]-rr)))>eps*(1+1e-10):raise RuntimeError(('prefix hard',t))
        R[:,t]=rr;K[:,t]=k
    return int(mb),np.asarray(cd,np.float32),R,K

def predict(S,co):return np.rint(S@co[:P][::-1].astype(np.float64)+float(co[-1])).astype(np.int64)
def kframes(K):
    total=0;parts=[];reps={}
    for t0 in range(0,K.shape[1],1024):
        fr=m.encode_k(np.asarray(K[:,t0:t0+1024],np.int32));total+=int(fr[0])+20;parts.append(np.asarray(fr[2],np.int32));reps[fr[1]]=reps.get(fr[1],0)+1
    D=np.concatenate(parts,axis=1)
    if not np.array_equal(D,K):raise RuntimeError('K frame rt')
    return total,D,reps

def pack_ids(ids,n):
    ids=np.asarray(ids,np.uint16);bits=int(math.ceil(math.log2(n)));raw=np.packbits(((ids[:,None]>>np.arange(bits,dtype=np.uint16))&1).astype(np.uint8).reshape(-1),bitorder='little').tobytes();zb=ZC.compress(raw)
    use,kind=(zb,'zstd') if len(zb)<len(raw) else (raw,'raw');rr=ZD.decompress(use) if kind=='zstd' else use;b=np.unpackbits(np.frombuffer(rr,np.uint8),bitorder='little')[:ids.size*bits].reshape(ids.size,bits);back=np.sum(b.astype(np.uint16)<<np.arange(bits,dtype=np.uint16),axis=1).astype(np.uint16)
    if not np.array_equal(back,ids):raise RuntimeError('id rt')
    return len(use)+24,back,bits,kind

def baseline(X,R0,co,eps):
    state=R0[:,-P:].copy();Q=np.empty((C,END-TRAIN),np.int32);R=np.empty((C,END-TRAIN),np.int64)
    for u,t in enumerate(range(TRAIN,END)):
        p=predict(state,co);q=np.rint((X[:,t]-p)/267.0).astype(np.int64);rr=p+267*q
        if float(np.max(np.abs(X[:,t]-rr)))>eps*(1+1e-10):raise RuntimeError(('base hard',t))
        Q[:,u]=q.astype(np.int32);R[:,u]=rr;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return Q,R

def run(X,R0,co,eps,n,wt,ws):
    state=R0[:,-P:].copy();prevq=np.zeros(C,np.int64);Q=np.empty((C,END-TRAIN),np.int32);R=np.empty((C,END-TRAIN),np.int64);ids=np.empty(END-TRAIN,np.uint16)
    for u,t in enumerate(range(TRAIN,END)):
        p=predict(state,co);RM=residue_matrix(n,t).astype(np.int64);d=X[:,t].astype(np.float64)-p.astype(np.float64);qq=np.rint((d[None,:]-RM.astype(np.float64))/MOD).astype(np.int64);rr=p[None,:]+RM+MOD*qq
        if float(np.max(np.abs(X[:,t][None,:]-rr)))>128.000001:raise RuntimeError(('mod guarantee',t))
        cost=np.sum(np.log2(1+np.abs(qq).astype(np.float64)),axis=1)
        if wt:cost+=wt*np.sum(np.log2(1+np.abs(qq-prevq[None,:]).astype(np.float64)),axis=1)
        if ws:cost+=ws*np.sum(np.log2(1+np.abs(qq[:,1:]-qq[:,:-1]).astype(np.float64)),axis=1)
        k=int(np.argmin(cost));q=qq[k];r=rr[k];ids[u]=k;Q[:,u]=q.astype(np.int32);R[:,u]=r;prevq=q;state[:,:-1]=state[:,1:];state[:,-1]=r
    return Q,R,ids

def decode(Q,ids,R0,co,n):
    state=R0[:,-P:].copy();R=np.empty_like(Q,dtype=np.int64)
    for u,t in enumerate(range(TRAIN,END)):
        p=predict(state,co);rm=residue_matrix(n,t)[int(ids[u])].astype(np.int64);rr=p+rm+MOD*Q[:,u].astype(np.int64);R[:,u]=rr;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0,K0=fit_prefix(X,eps);target=X[:,TRAIN:END];BQ,BR=baseline(X,R0,co,eps);bb,BD,breps=kframes(BQ);base=mb+bb+32
    sz=0
    for t0 in range(0,target.shape[1],1024):sb,_=m.szrun(target[:,t0:t0+1024],eps);sz+=sb
    rows=[]
    for n in SIZES:
        for name,wt,ws in MODES:
            Q,R,ids=run(X,R0,co,eps,n,wt,ws);qb,QD,reps=kframes(Q);ib,idd,bits,irep=pack_ids(ids,n);RD=decode(QD,idd,R0,co,n);me=float(np.max(np.abs(target-RD.astype(np.float64))))
            if me>eps*(1+1e-10) or not np.array_equal(RD,R):raise RuntimeError(('final',n,name,me))
            total=mb+qb+ib+40;row={'seed_codebook_size':n,'mode':name,'temporal_weight':wt,'spatial_weight':ws,'bytes':total,'bps':8*total/target.size,'model_bytes':mb,'quotient_bytes':qb,'quotient_bps':8*qb/target.size,'quotient_reps':reps,'seed_bytes':ib,'seed_bps':8*ib/target.size,'seed_bits_per_time':bits,'seed_rep':irep,'distinct_seed_ids':int(np.unique(ids).size),'top_seed_fraction':float(np.bincount(ids.astype(np.int64),minlength=n).max()/len(ids)),'q_zero_fraction':float(np.mean(Q==0)),'q_std':float(Q.std()),'gain_vs_step267_ar32':base/total,'gain_vs_sz3':sz/total,'sz3_bytes':sz,'maxerr':me,'baseline_bytes':base,'baseline_bps':8*base/target.size};rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'ar_order':P,'baseline_step':267,'modulus':MOD,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0,C0+C-1],'baseline':{'bytes':base,'bps':8*base/target.size,'innovation_bytes':bb,'reps':breps,'sz3_bytes':sz,'gain_vs_sz3':sz/base},'best':rows[0],'rows':rows,'scope':'Spatial-wavefront procedural mod257 codec gate. One shared AR32 model is trained only from t<1024. At each held-out time, one tiny seed ID selects a decoder-known 128-residue vector modulo257 across the entire hard 128-channel block. Every residue is always legal because nearest r+257q is within 128 < epsilon. The encoder evaluates 64/256 candidate wavefront seeds at the CURRENT recursive AR state, chooses the spatial quotient vector minimizing a fixed magnitude plus optional temporal/spatial quotient surrogate, updates all 128 decoder states, and proceeds. Thus 6-8 transmitted bits control 128 dense 257-way distortion choices (0.047-0.063 raw bps). Seed IDs are actually bitpacked/decoded; quotient fields use the incumbent exact 128x1024 self-decoding innovation frames; model/framing are charged; decoder regenerates all residue wavefronts and hard-error verifies. Ordinary step267 AR32 and matched SZ3 are rerun on the identical 128x3072 target. No AI, directional gate, not whole-array.'};print(json.dumps({'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_mod257_spatial_seed_wavefront.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
