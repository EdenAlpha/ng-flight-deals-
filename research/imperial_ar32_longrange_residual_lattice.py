import json,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C=6912;BLOCK=128;P=32;TRAIN=1024;NT=8192;A0=4096;MAXOFF=512;STEP=256
CHECK=(1,2,4,8,16,24,32,48,64,96,128,160,192,224,256,320,384,448,512)

@njit(cache=True)
def recur_block(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int64);K=np.zeros((nc,nt),np.int16)
    for t in range(nt):
        for c in range(nc):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            if v>2.0e9:v=2.0e9
            elif v< -2.0e9:v=-2.0e9
            pred=int(np.rint(v));k=int(np.rint((X[c,t]-pred)/step));K[c,t]=k;R[c,t]=pred+step*k
    return R,K

def fft_spatial_corr(Z,maxoff):
    c,t=Z.shape;nfft=1
    while nfft<2*c:nfft*=2
    spec=np.zeros(nfft//2+1,np.complex128)
    for j in range(0,t,256):
        x=np.asarray(Z[:,j:min(t,j+256)],np.float64);F=np.fft.rfft(x,n=nfft,axis=0);spec+=(F*np.conj(F)).sum(axis=1)
    ac=np.fft.irfft(spec,n=nfft)[:maxoff+1].real;den=np.array([(c-d)*t for d in range(maxoff+1)],np.float64)
    return ac/den

def offset_detail(Z,d):
    a=Z[:-d] if d else Z;b=Z[d:] if d else Z;corr=float(np.mean(a*b));sg=float(np.mean((a>=0)==(b>=0)))
    def bin8(x):
        q=np.zeros(x.shape,np.int8);ax=np.abs(x);q+=(ax>0.5);q+=(ax>1.0);q+=(ax>2.0);q+=(ax>4.0);return q+4*(x<0)
    aa=bin8(a[:,::8]).ravel().astype(np.int32);bb=bin8(b[:,::8]).ravel().astype(np.int32);joint=np.bincount(aa*8+bb,minlength=64).reshape(8,8).astype(np.float64);joint/=joint.sum();pa=joint.sum(1);pb=joint.sum(0);mi=0.
    for i in range(8):
        for j in range(8):
            if joint[i,j]>0:mi+=joint[i,j]*np.log2(joint[i,j]/(pa[i]*pb[j]))
    return {'offset':d,'corr':corr,'sign_agreement':sg,'coarse_empirical_mi_bits':float(mi)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;Kall=np.empty((C,NT),np.int16);model_bytes=0;maxerr=0.;blocks=[]
        for bi,c0 in enumerate(range(0,C,BLOCK)):
            X=np.asarray(d[:NT,c0:c0+BLOCK],np.float64).T;co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co);model_bytes+=mb;R,K=recur_block(X,np.asarray(cd,np.float32),P,STEP);me=float(np.max(np.abs(X-R.astype(np.float64))));maxerr=max(maxerr,me)
            if me>128.000001 or me>eps:
                raise RuntimeError(('hard',bi,me,eps))
            Kall[c0:c0+BLOCK]=K
            blocks.append({'block':bi,'c0':c0,'model_bytes':int(mb),'analysis_k_std':float(K[:,A0:].std()),'analysis_zero_fraction':float(np.mean(K[:,A0:]==0))})
            if bi%9==0:print(json.dumps({'block':bi,'c0':c0,'kstd':blocks[-1]['analysis_k_std']}),flush=True)
    X=Kall[:,A0:].astype(np.float64);mu=X.mean(axis=1,keepdims=True);sd=X.std(axis=1,keepdims=True);valid=(sd[:,0]>1e-9);Z=np.zeros_like(X,np.float32);Z[valid]=((X[valid]-mu[valid])/sd[valid]).astype(np.float32)
    corr=fft_spatial_corr(Z,MAXOFF);rank=np.argsort(-np.abs(corr[1:]))[:40]+1;top=[{'offset':int(d),'corr':float(corr[d]),'abs_corr':float(abs(corr[d]))} for d in rank]
    fixed=[offset_detail(Z,int(d)) for d in CHECK];detailed=[];seen=set()
    for d in list(rank[:12])+list(CHECK):
        d=int(d)
        if d not in seen:detailed.append(offset_detail(Z,d));seen.add(d)
    periodic=[{'offset':d,'corr':float(corr[d])} for d in range(BLOCK,MAXOFF+1,BLOCK)]
    out={'global_std':std,'eps':eps,'step':STEP,'ar_order':P,'training_samples':TRAIN,'processed_samples':NT,'analysis_interval':[A0,NT],'channels':C,'block_width':BLOCK,'model_bytes':model_bytes,'maxerr':maxerr,
         'top_offsets_by_abs_corr':top,'fixed_offsets':fixed,'detailed_offsets':detailed,'block_periodic_offsets':periodic,'all_corr_1_to_512':[float(x) for x in corr[1:]],'blocks':blocks,
         'scope':'Long-range post-AR32 spatial-lattice diagnostic. The full 6912-channel cable is split exactly as the persistent codec: each 128-channel block fits/decodes one shared float32 AR32 model using only t<1024, then recursively generates exact 256-step innovations through t<8192 with <=128 reconstruction error. On held-out t=4096..8191 innovations, every channel is standardized over time and non-circular spatial autocorrelation offsets 1..512 are computed by zero-padded FFT. Top/fixed offsets also report sign agreement and coarse empirical MI. Diagnostic only, no compression claim, no AI.'}
    print(json.dumps({'top':top[:20],'fixed':fixed,'periodic':periodic},indent=2),flush=True);json.dump(out,open('imperial_ar32_longrange_residual_lattice.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
