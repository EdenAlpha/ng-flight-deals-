import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_ar32_halfstep_control_channel as h
import imperial_decoder_phase_automaton as m
import imperial_ar32_hadamard_control_code as w

C0=512;C=128;P=32;TRAIN=1024;END=5120;COARSE=256;HALF=128
BETAS=(0.0,0.12,0.30)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def ideal_masks(X,co,R0,beta=.12):
    T=X.shape[1]-TRAIN;state=R0[:,-P:].astype(np.int64).copy();prevj=np.zeros(C,np.int64);M=np.empty((T,C),np.uint8)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);x=X[:,TRAIN+u]
        j0=np.rint((x-pred)/COARSE).astype(np.int64);j1=np.rint((x-pred-HALF)/COARSE).astype(np.int64)
        c0=np.log2(1+np.abs(j0).astype(float))+beta*np.log2(1+np.abs(j0-prevj).astype(float))
        c1=np.log2(1+np.abs(j1).astype(float))+beta*np.log2(1+np.abs(j1-prevj).astype(float))
        b=(c1<c0).astype(np.uint8);M[u]=b
        j=np.where(b!=0,j1,j0);rr=pred+COARSE*j+HALF*b.astype(np.int64)
        state[:,:-1]=state[:,1:];state[:,-1]=rr;prevj=j
    return M

def farthest_codebook(M,K=256):
    M=np.asarray(M,np.uint8);book=[(np.mean(M,axis=0)>=.5).astype(np.uint8)];best=np.sum(M!=book[0],axis=1).astype(np.int16)
    while len(book)<K:
        i=int(np.argmax(best));b=M[i].copy();book.append(b);d=np.sum(M!=b,axis=1).astype(np.int16);best=np.minimum(best,d)
        if int(best.max())==0:
            for q in range(w.BOOK.shape[0]):
                if len(book)>=K:break
                cand=w.BOOK[q]
                if not any(np.array_equal(cand,z) for z in book):book.append(cand.copy())
            break
    B=np.stack(book[:K]);mind=np.full(M.shape[0],C+1,np.int16)
    for b in B:mind=np.minimum(mind,np.sum(M!=b,axis=1).astype(np.int16))
    return B,mind

def codebook_frame(B):
    B=np.asarray(B,np.uint8);packed=np.packbits(B,axis=1,bitorder='little').tobytes();zb=ZC.compress(packed)
    if len(zb)+32<len(packed)+24:kind='zstd';raw=ZD.decompress(zb);n=len(zb)+32
    else:kind='raw';raw=packed;n=len(packed)+24
    bb=np.frombuffer(raw,np.uint8).reshape(B.shape[0],(B.shape[1]+7)//8);back=np.unpackbits(bb,axis=1,bitorder='little')[:,:B.shape[1]].astype(np.uint8)
    if not np.array_equal(back,B):raise RuntimeError('book rt')
    return n,back,kind

def control_run(X,co,R0,BOOK,beta):
    T=X.shape[1]-TRAIN;state=R0[:,-P:].astype(np.int64).copy();prevj=np.zeros(C,np.int64);J=np.empty((C,T),np.int64);R=np.empty((C,T),np.int64);ids=np.empty(T,np.uint8);used=np.zeros(BOOK.shape[0],np.int64);bookf=BOOK.astype(float)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);x=X[:,TRAIN+u];j0=np.rint((x-pred)/COARSE).astype(np.int64);j1=np.rint((x-pred-HALF)/COARSE).astype(np.int64)
        c0=np.log2(1+np.abs(j0).astype(float));c1=np.log2(1+np.abs(j1).astype(float))
        if beta:
            c0+=beta*np.log2(1+np.abs(j0-prevj).astype(float));c1+=beta*np.log2(1+np.abs(j1-prevj).astype(float))
        k=int(np.argmin(bookf@(c1-c0)));b=BOOK[k].astype(np.int64);j=np.where(b!=0,j1,j0);rr=pred+COARSE*j+HALF*b
        J[:,u]=j;R[:,u]=rr;ids[u]=k;used[k]+=1;prevj=j;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return J,R,ids,used

def reconstruct(J,ids,co,R0,BOOK):
    T=J.shape[1];state=R0[:,-P:].astype(np.int64).copy();R=np.empty((C,T),np.int64)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);b=BOOK[int(ids[u])].astype(np.int64);rr=pred+COARSE*J[:,u]+HALF*b;R[:,u]=rr;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0,J0=h.fit_prefix(X);G,GR=w.greedy_all(X,co,R0);gbytes,Gd,greps=w.encode_j_frames(G);baseline=mb+gbytes
    IM=ideal_masks(X,co,R0,.12);BOOK,hd=farthest_codebook(IM,256);cb,BOOKd,cbkind=codebook_frame(BOOK);sz=0
    for t0 in range(TRAIN,END,1024):
        sb,_=m.szrun(X[:,t0:min(t0+1024,END)],eps);sz+=sb
    rows=[]
    for beta in BETAS:
        J,R,ids,used=control_run(X,co,R0,BOOKd,beta);jb,Jd,reps=w.encode_j_frames(J);ib,idd,ikind=w.encode_ids(ids);Rd=reconstruct(Jd,idd,co,R0,BOOKd);me=float(np.max(np.abs(X[:,TRAIN:END]-Rd)))
        if me>eps*(1+1e-10) or not np.array_equal(Rd,R):raise RuntimeError(('final',beta,me))
        total=mb+cb+jb+ib+1;rows.append({'beta':beta,'bytes':total,'bps':8*total/J.size,'model_bytes':mb,'codebook_bytes':cb,'codebook_bps':8*cb/J.size,'codebook_rep':cbkind,'id_bytes':ib,'id_bps':8*ib/J.size,'id_rep':ikind,'innovation_bytes':jb,'innovation_bps':8*jb/J.size,'gain_vs_baseline':baseline/total,'gain_vs_sz3':sz/total,'sz3_bytes':sz,'distinct_ids':int(np.count_nonzero(used)),'top_id_fraction':float(used.max()/used.sum()),'mean_parity_one_fraction':float(np.mean(BOOKd[ids])),'j_zero_fraction':float(np.mean(J==0)),'j_std':float(J.std()),'maxerr':me,'reps':reps})
    rows.sort(key=lambda z:z['bytes'])
    out={'global_std':std,'eps':eps,'ar_order':P,'target_interval':[TRAIN,END],'channels':[C0,C0+C-1],'ideal_mask_mean_nearest_hamming':float(np.mean(hd)),'ideal_mask_median_nearest_hamming':float(np.median(hd)),'ideal_mask_max_nearest_hamming':int(np.max(hd)),'baseline':{'bytes':baseline,'bps':8*baseline/G.size,'model_bytes':mb,'innovation_bytes':gbytes,'gain_vs_sz3':sz/baseline,'sz3_bytes':sz},'best':rows[0],'rows':rows,'scope':'Adaptive vector-codebook distortion-control screen. One shared persistent AR32 model is trained only from t<1024 on the hardest 128-channel Imperial block. The encoder first derives the per-time 128-bit half-step mask that would locally minimize a fixed log-magnitude/delta coarse-innovation cost, then builds a deterministic 256-entry farthest-point Hamming cover of those masks. Unlike a hidden learned model, the entire 256x128-bit dictionary is actually packbits/Zstd serialized, decoded and charged (~4 KB raw), and every target time transmits one uint8 dictionary ID. Thus one small symbol selects 128 coordinated legal 128-unit reconstruction shifts. Coarse innovations use the existing self-decoding frame menu; dictionary/IDs/model/framing/mode bytes are charged; the exact AR trajectory is regenerated and the unchanged public 10%-global-std hard error verified. Matched SZ3 is rerun identically. Target-adaptive but fully self-contained; no AI; hard-region gate, not whole-array.'}
    print(json.dumps({'coverage':[out['ideal_mask_mean_nearest_hamming'],out['ideal_mask_median_nearest_hamming'],out['ideal_mask_max_nearest_hamming']],'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_adaptive_mask_codebook.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
