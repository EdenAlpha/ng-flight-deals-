import json,sys,math
from collections import Counter
import h5py,numpy as np,zstandard as zstd
import imperial_ar32_halfstep_control_channel as h
import imperial_decoder_phase_automaton as m

C0=512;C=128;P=32;TRAIN=1024;END=5120;COARSE=256;HALF=128
MODES=(('logmag',0.0),('logmag_delta',0.12),('logmag_delta3',0.30))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def hadamard(n):
    H=np.ones((1,1),np.int8)
    while H.shape[0]<n:
        H=np.block([[H,H],[H,-H]])
    if H.shape!=(n,n):raise RuntimeError('bad hadamard')
    return H

H=hadamard(C)
BOOK=np.vstack([(H<0).astype(np.uint8),(H>=0).astype(np.uint8)])
if BOOK.shape!=(256,C):raise RuntimeError(BOOK.shape)

def encode_j_frames(J):
    J=np.asarray(J,np.int64);parts=[];total=0;reps=Counter()
    for t0 in range(0,J.shape[1],1024):
        fr=m.encode_k(J[:,t0:min(t0+1024,J.shape[1])])
        total+=int(fr[0])+20;reps[fr[1]]+=1;parts.append(fr[2].astype(np.int64))
    D=np.concatenate(parts,axis=1)
    if not np.array_equal(D,J):raise RuntimeError('J frame roundtrip')
    return total,D,dict(reps)

def encode_ids(ids):
    a=np.asarray(ids,np.uint8);raw=a.tobytes();zb=ZC.compress(raw)
    if len(zb)+24 < len(raw)+16:
        kind='zstd';back=np.frombuffer(ZD.decompress(zb),np.uint8,count=a.size).copy();n=len(zb)+24
    else:
        kind='raw';back=np.frombuffer(raw,np.uint8,count=a.size).copy();n=len(raw)+16
    if not np.array_equal(back,a):raise RuntimeError('id roundtrip')
    return n,back,kind

def greedy_all(X,co,R0):
    T=X.shape[1]-TRAIN;state=R0[:,-P:].astype(np.int64).copy();J=np.empty((C,T),np.int64);R=np.empty((C,T),np.int64)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);j=np.rint((X[:,TRAIN+u]-pred)/COARSE).astype(np.int64);rr=pred+COARSE*j
        if float(np.max(np.abs(X[:,TRAIN+u]-rr)))>128.000001:raise RuntimeError(('greedy hard',u))
        J[:,u]=j;R[:,u]=rr;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return J,R

def control_run(X,co,R0,beta):
    T=X.shape[1]-TRAIN;state=R0[:,-P:].astype(np.int64).copy();prevj=np.zeros(C,np.int64)
    J=np.empty((C,T),np.int64);R=np.empty((C,T),np.int64);ids=np.empty(T,np.uint8);used=np.zeros(256,np.int64);bookf=BOOK.astype(np.float64)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);x=X[:,TRAIN+u]
        j0=np.rint((x-pred)/COARSE).astype(np.int64);j1=np.rint((x-pred-HALF)/COARSE).astype(np.int64)
        r0=pred+COARSE*j0;r1=pred+HALF+COARSE*j1
        if float(np.max(np.abs(x-r0)))>128.000001 or float(np.max(np.abs(x-r1)))>128.000001:raise RuntimeError(('phase hard',u))
        c0=np.log2(1.0+np.abs(j0).astype(np.float64));c1=np.log2(1.0+np.abs(j1).astype(np.float64))
        if beta:
            c0+=beta*np.log2(1.0+np.abs(j0-prevj).astype(np.float64));c1+=beta*np.log2(1.0+np.abs(j1-prevj).astype(np.float64))
        k=int(np.argmin(bookf@(c1-c0)));b=BOOK[k].astype(np.int64);j=np.where(b!=0,j1,j0);rr=np.where(b!=0,r1,r0)
        J[:,u]=j;R[:,u]=rr;ids[u]=k;used[k]+=1;prevj=j;state[:,:-1]=state[:,1:];state[:,-1]=rr
    return J,R,ids,used

def reconstruct(J,ids,co,R0):
    T=J.shape[1];state=R0[:,-P:].astype(np.int64).copy();R=np.empty((C,T),np.int64)
    for u in range(T):
        v=np.full(C,float(co[-1]),np.float64)
        for q in range(P):v+=float(co[q])*state[:,-1-q]
        pred=np.rint(v).astype(np.int64);b=BOOK[int(ids[u])].astype(np.int64);rr=pred+COARSE*J[:,u]+HALF*b;R[:,u]=rr
        state[:,:-1]=state[:,1:];state[:,-1]=rr
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R0,J0=h.fit_prefix(X);G,GR=greedy_all(X,co,R0);gbytes,Gd,greps=encode_j_frames(G);gd=reconstruct(Gd,np.zeros(G.shape[1],np.uint8),co,R0)
    gme=float(np.max(np.abs(X[:,TRAIN:END]-gd)))
    if gme>128.000001:raise RuntimeError(('greedy decode hard',gme))
    baseline=mb+gbytes;sz=0
    for t0 in range(TRAIN,END,1024):
        sb,_=m.szrun(X[:,t0:min(t0+1024,END)],eps);sz+=sb
    rows=[]
    for name,beta in MODES:
        J,R,ids,used=control_run(X,co,R0,beta);jb,Jd,reps=encode_j_frames(J);ib,idd,ikind=encode_ids(ids);Rd=reconstruct(Jd,idd,co,R0);me=float(np.max(np.abs(X[:,TRAIN:END]-Rd)))
        if me>eps*(1+1e-10):raise RuntimeError(('hard final',name,me,eps))
        if not np.array_equal(Rd,R):raise RuntimeError(('state rt',name))
        total=mb+jb+ib+1
        row={'mode':name,'beta':beta,'bytes':total,'bps':8*total/J.size,'model_bytes':mb,'innovation_bytes':jb,'innovation_bps':8*jb/J.size,'id_bytes':ib,'id_bps':8*ib/J.size,'id_rep':ikind,'distinct_ids':int(np.count_nonzero(used)),'top_id_fraction':float(used.max()/used.sum()),'mean_parity_one_fraction':float(np.mean(BOOK[ids])),'j_zero_fraction':float(np.mean(J==0)),'j_std':float(J.std()),'baseline_bytes':baseline,'baseline_bps':8*baseline/G.size,'gain_vs_baseline':baseline/total,'sz3_bytes':sz,'gain_vs_sz3':sz/total,'maxerr':me,'reps':reps}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['bytes'])
    out={'global_std':std,'eps':eps,'ar_order':P,'training_samples':TRAIN,'target_interval':[TRAIN,END],'channels':[C0,C0+C-1],'control_code':'256 decoder-known 128-bit masks = Walsh-Hadamard rows plus complements; one uint8 ID controls all 128 half-step parity decisions at a time sample','baseline':{'bytes':baseline,'bps':8*baseline/G.size,'model_bytes':mb,'innovation_bytes':gbytes,'reps':greps,'sz3_bytes':sz,'gain_vs_sz3':sz/baseline,'maxerr':gme},'best':rows[0],'rows':rows,'scope':'Dense coded-distortion fast gate on the hardest 128-channel Imperial block. Persistent shared AR32 is fitted only from t<1024. Baseline transmits nearest 256-step innovations. New codec uses the always-legal 128 half-step as a dense control bit, but does not transmit one bit per sample: at each target time one 8-bit ID selects one of 256 fixed 128-bit Walsh-Hadamard/complement masks, jointly controlling every channel. For each candidate mask the encoder scores the induced coarse innovations under fixed log-magnitude/delta surrogates, chooses one mask, and advances the actual AR decoder state. Coarse innovations use the existing self-decoding frame menu; IDs are raw/Zstd serialized and decoded; model/ID/mode/framing bytes are charged; the exact trajectory is regenerated and the unchanged public 10%-global-std hard error is verified. Matched SZ3 is rerun on identical 128x1024 target frames. This is a vector/trellis-coded distortion-control experiment, no AI, not a whole-array claim.'}
    print(json.dumps({'baseline':out['baseline'],'best':out['best']},indent=2),flush=True);json.dump(out,open('imperial_ar32_hadamard_control_code.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
