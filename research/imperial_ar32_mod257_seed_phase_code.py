import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar

C0=512;C=128;P=32;TRAIN=1024;END=1536;B=64;MOD=257
CH=np.arange(0,128,16,dtype=np.int64)
SIZES=(64,256,1024);BETA=.12
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()
MASK=np.uint64(0xffffffffffffffff)

def splitmix64(x):
    x=(x+np.uint64(0x9E3779B97F4A7C15))&MASK
    z=x.copy();z=((z^(z>>np.uint64(30)))*np.uint64(0xBF58476D1CE4E5B9))&MASK
    z=((z^(z>>np.uint64(27)))*np.uint64(0x94D049BB133111EB))&MASK
    return z^(z>>np.uint64(31))

def residues(n,block_index):
    s=np.arange(n,dtype=np.uint64)[:,None];t=np.arange(B,dtype=np.uint64)[None,:]
    x=s ^ (np.uint64(block_index+1)*np.uint64(0xD1B54A32D192ED03)) ^ ((t+np.uint64(1))*np.uint64(0x94D049BB133111EB))
    return (splitmix64(x)%np.uint64(MOD)).astype(np.int16)

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

def pred_many(S,co):return np.rint(S@co[:P][::-1].astype(np.float64)+float(co[-1])).astype(np.int64)
def pred_one(s,co):return int(np.rint(float(np.dot(s.astype(np.float64),co[:P][::-1].astype(np.float64)))+float(co[-1])))

def pack_ids(ids,n):
    ids=np.asarray(ids,np.uint16);bits=max(1,int(math.ceil(math.log2(n))));b=((ids[:,None]>>np.arange(bits,dtype=np.uint16))&1).astype(np.uint8).reshape(-1);raw=np.packbits(b,bitorder='little').tobytes();zb=ZC.compress(raw)
    use=zb if len(zb)<len(raw) else raw;kind='zstd' if len(zb)<len(raw) else 'raw';rr=ZD.decompress(use) if kind=='zstd' else use;bb=np.unpackbits(np.frombuffer(rr,np.uint8),bitorder='little')[:ids.size*bits].reshape(ids.size,bits);back=np.sum(bb.astype(np.uint16)<<np.arange(bits,dtype=np.uint16),axis=1).astype(np.uint16)
    if not np.array_equal(back,ids):raise RuntimeError('id rt')
    return len(use)+24,back,bits,kind

def kframe(K):
    fr=m.encode_k(np.asarray(K,np.int32));return int(fr[0])+20,fr[1],np.asarray(fr[2],np.int32)

def baseline_channel(x,state,co,eps):
    out=[];R=[];s=state.copy()
    for xx in x:
        p=pred_one(s,co);q=int(np.rint((float(xx)-p)/267.0));rr=p+267*q
        if abs(float(xx)-rr)>eps*(1+1e-10):raise RuntimeError('base hard')
        out.append(q);R.append(rr);s[:-1]=s[1:];s[-1]=rr
    return np.asarray(out,np.int32),np.asarray(R,np.int64)

def run_channel(x,state0,co,eps,n,channel_tag):
    state=state0.copy();prevq=0;ids=[];Q=[];R=[];block_stats=[]
    for bi,t0 in enumerate(range(0,len(x),B)):
        src=np.asarray(x[t0:t0+B],np.float64);nb=len(src)
        if nb!=B:raise RuntimeError('target must divide block')
        RS=residues(n,channel_tag*1000+bi)[:,:nb].astype(np.int64);S=np.repeat(state[None,:],n,axis=0);pq=np.full(n,prevq,np.int64);cost=np.zeros(n,np.float64);QS=np.empty((n,nb),np.int32)
        for t in range(nb):
            p=pred_many(S,co);d=src[t]-p.astype(np.float64)-RS[:,t].astype(np.float64);q=np.rint(d/MOD).astype(np.int64);rr=p+RS[:,t]+MOD*q;err=np.abs(src[t]-rr.astype(np.float64))
            if float(err.max())>128.000001:raise RuntimeError(('mod257 guarantee failed',float(err.max())))
            cost+=np.log2(1+np.abs(q).astype(np.float64))+BETA*np.log2(1+np.abs(q-pq).astype(np.float64));QS[:,t]=q.astype(np.int32);pq=q;S[:,:-1]=S[:,1:];S[:,-1]=rr
        k=int(np.argmin(cost));ids.append(k);qq=QS[k].astype(np.int32);rrs=[];rseq=RS[k]
        for t,q in enumerate(qq):
            p=pred_one(state,co);rr=p+int(rseq[t])+MOD*int(q)
            if abs(float(src[t])-rr)>eps*(1+1e-10):raise RuntimeError(('chosen hard',t0+t))
            rrs.append(rr);state[:-1]=state[1:];state[-1]=rr
        prevq=int(qq[-1]);Q.extend(qq.tolist());R.extend(rrs);block_stats.append({'best_surrogate':float(cost[k]),'seed':k,'q_zero_fraction':float(np.mean(qq==0)),'q_std':float(qq.std())})
    return np.asarray(Q,np.int32),np.asarray(R,np.int64),np.asarray(ids,np.uint16),block_stats

def decode_channel(Q,ids,state0,co,n,channel_tag):
    state=state0.copy();R=np.empty(len(Q),np.int64);p=0
    for bi,sid in enumerate(ids):
        rs=residues(n,channel_tag*1000+bi)[int(sid)]
        for t in range(B):
            pr=pred_one(state,co);rr=pr+int(rs[t])+MOD*int(Q[p]);R[p]=rr;state[:-1]=state[1:];state[-1]=rr;p+=1
    if p!=len(Q):raise RuntimeError((p,len(Q)))
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0,K0=fit_prefix(X,eps);target=X[CH,TRAIN:END];baseQ=[];baseR=[]
    for c in CH:
        q,r=baseline_channel(X[c,TRAIN:END],R0[c,-P:],co,eps);baseQ.append(q);baseR.append(r)
    baseQ=np.stack(baseQ);baseR=np.stack(baseR);bb,brep,BQ=kframe(baseQ);base_total=mb+bb+32
    if not np.array_equal(BQ,baseQ):raise RuntimeError('base Q rt')
    sb,_=m.szrun(target,eps);rows=[]
    for n in SIZES:
        QQ=[];RR=[];IDS=[];bst=[]
        for ci,c in enumerate(CH):
            q,r,ids,st=run_channel(X[c,TRAIN:END],R0[c,-P:],co,eps,n,ci);QQ.append(q);RR.append(r);IDS.append(ids);bst.extend(st)
        QQ=np.stack(QQ);RR=np.stack(RR);IDS=np.stack(IDS);qb,qrep,QD=kframe(QQ);ib,idd,bits,irep=pack_ids(IDS.ravel(),n);idd=idd.reshape(IDS.shape);RD=np.stack([decode_channel(QD[i],idd[i],R0[c,-P:],co,n,i) for i,c in enumerate(CH)])
        if not np.array_equal(RD,RR):raise RuntimeError(('decoder mismatch',n))
        me=float(np.max(np.abs(target-RD.astype(np.float64))))
        if me>eps*(1+1e-10):raise RuntimeError(('final hard',n,me,eps))
        total=mb+qb+ib+40;row={'seed_codebook_size':n,'seed_bits_per_block':bits,'bytes':total,'bps':8*total/target.size,'model_bytes':mb,'quotient_bytes':qb,'quotient_bps':8*qb/target.size,'quotient_rep':qrep,'seed_bytes':ib,'seed_bps':8*ib/target.size,'seed_rep':irep,'gain_vs_step267_ar32':base_total/total,'sz3_bytes':int(sb),'gain_vs_sz3':sb/total,'maxerr':me,'mean_seed_id':float(IDS.mean()),'distinct_seed_ids':int(np.unique(IDS).size),'q_zero_fraction':float(np.mean(QQ==0)),'q_std':float(QQ.std()),'baseline_bytes':base_total,'baseline_bps':8*base_total/target.size,'baseline_rep':brep};rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'ar_order':P,'baseline_step':267,'modulus':MOD,'block_length':B,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[int(C0+x) for x in CH],'baseline':{'bytes':base_total,'bps':8*base_total/target.size,'rep':brep,'sz3_bytes':int(sb),'gain_vs_sz3':sb/base_total},'best':rows[0],'rows':rows,'scope':'Procedural mod-257 residue-phase codec gate. Because the public epsilon is 133.6978 and source/predictor values are integer, for every residue r in 0..256 the nearest value r+257q is at most 128 away; therefore every generated residue is guaranteed legal at every sample. One shared AR32 model is trained only from t<1024. Held-out samples are split into 64-step channel blocks. For each block, N=64/256/1024 deterministic SplitMix seeds generate dense 257-way residue sequences; all candidates are replayed through the actual recursive AR32 state and scored by a fixed quotient magnitude/delta surrogate. The winning seed is transmitted in ceil(log2 N) packed bits; only the coarse quotient q is encoded through the existing exact innovation backend. Seed IDs, quotient frames, model and framing are fully charged; decoder regenerates residues from block index+seed, recursively reconstructs the exact trajectory and verifies the unchanged hard bound. Matched SZ3 and ordinary step267 AR32 are rerun on the identical eight-channel held-out target. This is a decoder-real directional gate, no AI, not whole-array.'}
    print(json.dumps({'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_mod257_seed_phase_code.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
