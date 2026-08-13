import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r
import imperial_persistent_ar32_full_array_jit as a

C=6912;CB=128;NCB=54;TRAIN=1024;END=2048;P=32;STEP=267
m.STEP=STEP;a.m.m.STEP=STEP
FIXED=(1,2,4,8,16,32,64,128,256,512,1024,1728,2304,3456)


def build_k(d):
    K=np.empty((C,END-TRAIN),np.int32);model_bytes=0;maxerr=0.0
    for cb in range(NCB):
        c0=cb*CB;X=np.asarray(d[:END,c0:c0+CB],np.float64).T
        co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);model_bytes+=int(mb)
        R,Q=a.build(X,cd);me=float(np.max(np.abs(X-R.astype(np.float64))));maxerr=max(maxerr,me)
        K[c0:c0+CB]=Q[:,TRAIN:]
    return K,model_bytes,maxerr


def binary_mi_from_counts(n00,n01,n10,n11):
    n=n00+n01+n10+n11
    if n<=0:return 0.0
    cells=np.array([[n00,n01],[n10,n11]],np.float64)/n
    px=cells.sum(axis=1);py=cells.sum(axis=0);mi=0.0
    for i in range(2):
        for j in range(2):
            p=cells[i,j]
            if p>0 and px[i]>0 and py[j]>0:mi+=p*math.log2(p/(px[i]*py[j]))
    return float(mi)


def all_spatial_binary_mi(B):
    B=np.asarray(B,np.uint8);nc,nt=B.shape
    nfft=1
    while nfft<2*nc-1:nfft*=2
    # Sum exact 1-1 coincidences over time for every non-circular spatial lag.
    F=np.fft.rfft(B.astype(np.float32),n=nfft,axis=0)
    ac=np.fft.irfft(np.conj(F)*F,n=nfft,axis=0)[:nc]
    n11=np.rint(ac.sum(axis=1)).astype(np.int64)
    rs=B.sum(axis=1,dtype=np.int64);pref=np.r_[0,np.cumsum(rs,dtype=np.int64)];tot=int(pref[-1])
    mi=np.zeros(nc,np.float64)
    for lag in range(1,nc):
        left=int(pref[nc-lag]);right=tot-int(pref[lag]);both=int(n11[lag]);N=(nc-lag)*nt
        n10=left-both;n01=right-both;n00=N-both-n10-n01
        mi[lag]=binary_mi_from_counts(n00,n01,n10,both)
    return mi


def feature_arrays(K):
    z=np.asarray(K,np.int64);zz=np.where(z>=0,2*z,-2*z-1).astype(np.uint64)
    return {
        'zero':(z==0),
        'positive':(z>0),
        'abs_ge2':(np.abs(z)>=2),
        'zz_bit0':((zz>>0)&1).astype(bool),
        'zz_bit1':((zz>>1)&1).astype(bool),
        'zz_bit2':((zz>>2)&1).astype(bool),
        'zz_bit3':((zz>>3)&1).astype(bool),
    }


def top_lags(mi,minlag,n=20):
    idx=np.arange(len(mi));mask=idx>=minlag;ii=idx[mask];vals=mi[mask]
    if len(ii)==0:return []
    k=min(n,len(ii));sel=np.argpartition(vals,-k)[-k:];sel=sel[np.argsort(vals[sel])[::-1]]
    return [{'lag':int(ii[j]),'mi_bps':float(vals[j])} for j in sel]


def gf2_rank_time_vectors(B,max_times=1024):
    # Exact rank of the observed full-cable binary state vectors over GF(2).
    B=np.asarray(B,bool)[:,:max_times];basis={};rank=0
    for t in range(B.shape[1]):
        bits=np.packbits(B[:,t],bitorder='little').tobytes();v=int.from_bytes(bits,'little')
        while v:
            p=v.bit_length()-1
            w=basis.get(p)
            if w is None:
                basis[p]=v;rank+=1;break
            v^=w
    return rank


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;K,model_bytes,maxerr=build_k(d)
    if maxerr>eps*(1+1e-12):raise RuntimeError(('hard',maxerr,eps))
    feats=feature_arrays(K);rows=[]
    for name,B in feats.items():
        mi=all_spatial_binary_mi(B)
        fixed=[{'lag':lag,'mi_bps':float(mi[lag])} for lag in FIXED if lag<len(mi)]
        row={'feature':name,'one_fraction':float(np.mean(B)),'gf2_rank_time_vectors':gf2_rank_time_vectors(B),
             'times_for_rank':min(1024,B.shape[1]),'fixed_lags':fixed,
             'top_lags_ge2':top_lags(mi,2,20),'top_lags_ge16':top_lags(mi,16,20),
             'top_lags_ge64':top_lags(mi,64,20),'top_lags_ge256':top_lags(mi,256,20)}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    # Consensus score: rank every lag by summed normalized MI across features.
    mis=[]
    for name,B in feats.items():mis.append(all_spatial_binary_mi(B))
    A=np.stack(mis);scale=np.maximum(np.percentile(A[:,1:],99,axis=1),1e-12)[:,None]
    score=np.sum(A/scale,axis=0);score[:2]=-np.inf
    top=np.argsort(score)[-40:][::-1]
    consensus=[{'lag':int(x),'score':float(score[x]),'feature_mi':{name:float(A[i,x]) for i,name in enumerate(feats)}} for x in top]
    out={'global_std':std,'eps':eps,'analysis_shape':[C,END-TRAIN],'train_samples':TRAIN,'heldout_samples':END-TRAIN,
         'ar_order':P,'step':STEP,'model_bytes':model_bytes,'maxerr':maxerr,'features':rows,'consensus_nonlocal_lags':consensus,
         'scope':('Global hidden-dependency diagnostic, not a compression claim. All 6912 channels are represented by the current 54x128 persistent shared AR32 models fitted only on t<1024; exact held-out step267 innovations from t=1024..2047 are assembled in physical cable order. For seven nonlinear binary features (zero/sign/magnitude and low zigzag bitplanes), zero-padded FFT autocorrelation gives exact 1-1 pair counts at every one of the 6911 nonzero spatial channel lags, from which binary mutual information is computed with exact overlap marginals. The audit therefore searches every possible cable separation rather than guessed offsets such as 64/128/256. It also reports exact GF(2) rank of the 1024 observed full-cable feature-state vectors. Physical nearest-neighbor structure is expected; the decision signal is any sharp nonlocal/periodic lag peak shared across features. No AI.')}
    json.dump(out,open('imperial_global_lag_dependency_spectroscope.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
