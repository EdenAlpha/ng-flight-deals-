import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_sparse_causal_annihilator as m

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
NC=128;TRAIN=4096;STEP=256;ALPHA=.5
KLO=-512;KHI=511;A=KHI-KLO+2 # final symbol is escape

@njit(cache=True)
def recur(X,coeff,intercept):
    nc,nt=X.shape;o=coeff.size
    R=np.empty((nc,nt),np.int64);K=np.zeros((nc,nt),np.int64)
    for c in range(nc):
        for t in range(o):R[c,t]=int(np.rint(X[c,t]/STEP))*STEP
    for t in range(o,nt):
        for c in range(nc):
            p=intercept
            for j in range(o):p+=coeff[j]*R[c,t-1-j]
            if p>200000.:p=200000.
            elif p< -200000.:p=-200000.
            pi=int(np.rint(p));k=int(np.rint((X[c,t]-pi)/STEP));K[c,t]=k;R[c,t]=pi+STEP*k
    return R,K

def bucket(x,bits):
    a=np.abs(np.asarray(x,np.int64));z=np.zeros(a.shape,np.int16);nz=a>0
    z[nz]=np.floor(np.log2(a[nz].astype(np.float64))).astype(np.int16)+1
    return np.minimum(z,(1<<bits)-1).astype(np.int32)

def entropy_symbols(k):
    _,n=np.unique(np.asarray(k).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def symbol_index(k):
    k=np.asarray(k,np.int64);q=k-KLO;esc=(k<KLO)|(k>KHI);q=np.clip(q,0,KHI-KLO).astype(np.int32);q[esc]=A-1;return q

def conditional_target_entropy(ctx,kidx):
    ctx=np.asarray(ctx,np.int64).ravel();k=np.asarray(kidx,np.int64).ravel();nc=int(ctx.max())+1
    pair=ctx*A+k;cnt=np.bincount(pair,minlength=nc*A).reshape(nc,A).astype(np.float64);n=cnt.sum(axis=1);tot=n.sum();h=0.
    for c in range(nc):
        if n[c]<=0:continue
        p=cnt[c][cnt[c]>0]/n[c];h+=(n[c]/tot)*float(-(p*np.log2(p)).sum())
    return h,nc

def crossentropy_train_test(ctx,kidx,split=TRAIN,beta=64.0):
    # Flatten only t-major-compatible slices: contexts are [c,t]. Training and test are disjoint in time.
    trc=ctx[:,:split].ravel().astype(np.int64);trk=kidx[:,:split].ravel().astype(np.int64)
    tec=ctx[:,split:].ravel().astype(np.int64);tek=kidx[:,split:].ravel().astype(np.int64)
    nc=int(max(ctx.max(),0))+1
    pc=np.bincount(trk,minlength=A).astype(np.float64)+ALPHA;pc/=pc.sum()
    pair=trc*A+trk;cnt=np.bincount(pair,minlength=nc*A).reshape(nc,A).astype(np.float64);n=cnt.sum(axis=1)
    # Dirichlet backoff to global training symbol law; decoder can rebuild all of this from transmitted/training prefix.
    probs=(cnt+beta*pc[None,:])/(n[:,None]+beta)
    p=probs[tec,tek]
    return float((-np.log2(np.maximum(p,1e-300))).mean())

def build_contexts(R,K,P):
    nc,nt=R.shape
    prev=np.zeros_like(R);prev[:,1:]=R[:,:-1]
    prev2=np.zeros_like(R);prev2[:,2:]=R[:,:-2]
    slope=bucket(prev-prev2,3) # 0..7
    sp=np.zeros_like(R);sp[1:,1:]=R[1:,:-1]-R[:-1,:-1]
    spatial=bucket(sp,3)
    amp=bucket(P,3)
    pk=np.zeros_like(K);pk[:,1:]=K[:,:-1]
    pkm=np.minimum(np.abs(pk),3).astype(np.int32);pks=(pk>0).astype(np.int32)-(pk<0).astype(np.int32);pks+=1
    return {
      'amp8':amp,
      'slope8':slope,
      'spatial8':spatial,
      'motion64':slope*8+spatial,
      'amp_motion512':(amp*8+slope)*8+spatial,
      'motion_prevkmag256':(slope*8+spatial)*4+pkm,
      'amp_prevsign24':amp*3+pks,
      'amp_motion_prevsign1536':((amp*8+slope)*8+spatial)*3+pks,
    }

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        old=m.TRAIN_END;m.TRAIN_END=TRAIN
        for name,c0 in REGIONS:
            X=np.asarray(d[:,c0:c0+NC],np.float64).T
            off,beta=m.fit_ar16(X);coeff=np.asarray(beta[1:],np.float64);inter=float(beta[0]);R,K=recur(X,coeff,inter);P=R-STEP*K
            me=float(np.max(np.abs(X-R)))
            if me>128.000001:raise RuntimeError((name,'hard',me))
            ki=symbol_index(K);baseH=entropy_symbols(K[:,TRAIN:]);contexts=build_contexts(R,K,P)
            modes=[]
            for cn,ctx in contexts.items():
                h,nctx=conditional_target_entropy(ctx[:,TRAIN:],ki[:,TRAIN:])
                xents=[]
                for b in (16.,64.,256.,1024.):xents.append((crossentropy_train_test(ctx,ki,TRAIN,b),b))
                xents.sort();modes.append({'context':cn,'nctx':nctx,'target_cond_entropy_bps':h,'optimistic_gain_bps':baseH-h,'best_crossentropy_bps':xents[0][0],'best_beta':xents[0][1],'crossentropy_gain_bps':baseH-xents[0][0],'all_betas':[{'beta':b,'xent':x} for x,b in xents]})
            modes.sort(key=lambda z:z['best_crossentropy_bps'])
            row={'region':name,'c0':c0,'samples':int(X.size),'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),'maxerr':me,'test_zero_order_entropy_bps':baseH,'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'k_std':float(K[:,TRAIN:].std()),'modes':modes};rows.append(row)
            print(json.dumps({'region':name,'baseH':baseH,'best':modes[:4]},indent=2),flush=True)
        m.TRAIN_END=old
    out={'global_std':gstd,'eps':eps,'step':STEP,'training_prefix':TRAIN,'regions':[x[0] for x in REGIONS],'rows':rows,'scope':'Decoder-known variance-state information audit on persistent AR16 innovations. One AR16 law per 128-channel region is fit only on t<4096. The decoder can know predictor magnitude, past temporal slope, previous-time spatial gradient and previous innovation state before decoding the current innovation, so these contexts require no target regime map. Fixed power-of-two bins avoid trained thresholds. For t>=4096 the report gives both target conditional entropy (optimistic structural diagnostic) and a genuinely out-of-sample cross-entropy using only prefix counts with Dirichlet backoff to the prefix global symbol law; beta menu is a screen and would need one charged selector if integrated. No compression claim until a real coder is built.'}
    json.dump(out,open('imperial_decoder_known_variance_state.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
