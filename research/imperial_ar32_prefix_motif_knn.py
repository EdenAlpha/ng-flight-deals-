import json,sys
import h5py,numpy as np
from numba import njit
import imperial_huber_ar32_coldstart_arithmetic_regions as base

SPECS=(("hard",512),("easy",2304))
C=128;NT=2048;TRAIN=1024;P=32;STEP=267;L=6;DSTRIDE=8;TB=1024
NEIGHBORS=(1,3);STRENGTHS=(0.5,1.0);SELECTOR_BYTES=1
base.NT=NT

@njit(cache=True)
def clip4(x):
    if x < -4.0:return -4.0
    if x > 4.0:return 4.0
    return x

@njit(cache=True)
def ar_predict(R,c,t,co):
    if t<P:return 0
    v=float(co[0])
    for j in range(P):v += float(co[j+1])*float(R[c,t-1-j])
    return int(np.rint(v))

@njit(cache=True)
def motif_pred(K,c,t,nneigh):
    bestd0=1<<60;bestd1=1<<60;bestd2=1<<60
    bestk0=0;bestk1=0;bestk2=0
    for idx in range(L,TRAIN,DSTRIDE):
        dist=0
        for j in range(L):
            z=int(K[c,t-L+j])-int(K[c,idx-L+j])
            if z<0:z=-z
            dist += z
        target=int(K[c,idx])
        if dist<bestd0:
            bestd2,bestk2=bestd1,bestk1;bestd1,bestk1=bestd0,bestk0;bestd0,bestk0=dist,target
        elif dist<bestd1:
            bestd2,bestk2=bestd1,bestk1;bestd1,bestk1=dist,target
        elif dist<bestd2:
            bestd2,bestk2=dist,target
    if nneigh==1:return float(bestk0)
    return (float(bestk0)+float(bestk1)+float(bestk2))/3.0

@njit(cache=True)
def encode_candidate(X,co,Rprefix,Kprefix,nneigh,strength):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32)
    R[:,:TRAIN]=Rprefix[:,:TRAIN];K[:,:TRAIN]=Kprefix[:,:TRAIN]
    for c in range(C):
        for t in range(TRAIN,NT):
            pa=ar_predict(R,c,t,co);pk=motif_pred(K,c,t,nneigh)
            p=int(np.rint(float(pa)+float(strength)*STEP*clip4(pk)))
            k=int(np.rint((float(X[c,t])-float(p))/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K

@njit(cache=True)
def decode_candidate(K,co,nneigh,strength,Rprefix):
    # The prefix itself is reconstructed outside this kernel by the audited incumbent
    # float32-dot decoder, then the deterministic motif predictor takes over.
    R=np.zeros((C,NT),np.int32);R[:,:TRAIN]=Rprefix[:,:TRAIN]
    for c in range(C):
        for t in range(TRAIN,NT):
            pa=ar_predict(R,c,t,co);pk=motif_pred(K,c,t,nneigh)
            p=int(np.rint(float(pa)+float(strength)*STEP*clip4(pk)));R[c,t]=p+STEP*int(K[c,t])
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=base.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=base.fits(X);Rb,Kb=base.run_ar(X,co)
            baseline,_,_,Kbd=base.arithmetic(Kb);Rbd=base.decode_source(Kbd,co)
            if not np.array_equal(Rbd,Rb):raise RuntimeError((region,'baseline replay'))
            bme=float(np.max(np.abs(X-Rb.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))
            candidates=[]
            for nneigh in NEIGHBORS:
                for strength in STRENGTHS:
                    R,K=encode_candidate(X,np.asarray(co,np.float32),Rb,Kb,int(nneigh),float(strength))
                    me=float(np.max(np.abs(X-R.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,nneigh,strength,'encoder hard',me,eps))
                    n,bits,nb,Kd=base.arithmetic(K);n+=SELECTOR_BYTES
                    audited_prefix=base.decode_source(Kd[:,:TRAIN],co)
                    if not np.array_equal(audited_prefix,R[:,:TRAIN]):raise RuntimeError((region,nneigh,strength,'audited prefix mismatch'))
                    Rd=decode_candidate(Kd,np.asarray(co,np.float32),int(nneigh),float(strength),audited_prefix)
                    if not np.array_equal(Rd,R):raise RuntimeError((region,nneigh,strength,'decoder replay'))
                    dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                    if dme>eps*(1+1e-12):raise RuntimeError((region,nneigh,strength,'decoder hard',dme,eps))
                    q={'neighbors':int(nneigh),'strength':float(strength),'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':baseline/n,'zero_fraction':float(np.mean(K==0)),'k_std':float(K.astype(np.float64).std()),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':dme};candidates.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=base.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(baseline),'baseline_bps':8*baseline/X.size,'baseline_zero_fraction':float(np.mean(Kb==0)),'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'history_length':L,'dictionary_stride':DSTRIDE,'scope':'Decoder-real nonlinear temporal motif gate. The unchanged audited Huber AR32 step267 decoder reconstructs the first 1024 samples exactly. That decoded K prefix becomes a free per-channel dictionary of six-symbol innovation histories. For each later sample the decoder finds the nearest prefix history by L1 distance and uses the following prefix K (or mean of three nearest followers) only as a bounded +/-4K correction to a deterministic tail AR predictor. No dictionary/model is transmitted. Neighbors 1/3 and strengths 0.5/1.0 are screened with one selector byte charged. Exact arithmetic K decode, audited prefix replay, complete tail replay and unchanged max error are mandatory. Hard/easy 128x2048. No AI. Draft/do not merge.'},open('imperial_ar32_prefix_motif_knn.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
