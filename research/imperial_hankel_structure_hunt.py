import json,math,sys
import h5py,numpy as np

C=128; C0=512; TRAIN=8192; NSEG=8192; CURRENT_BYTES=2468803; MATCHED_SZ3=2767977
L=65; K=C-L+1
RANKS=(1,2,4,8,12,16,24,32,48,64)

def h0_bits(a):
    a=np.asarray(a).reshape(-1); _,cnt=np.unique(a,return_counts=True); p=cnt/cnt.sum(); return float(-(p*np.log2(p)).sum())
def hankel(v):
    return np.lib.stride_tricks.sliding_window_view(v,K)[:L]
def dehankel(H):
    out=np.zeros(C,np.complex128); cnt=np.zeros(C,np.int32)
    for i in range(L):
        out[i:i+K]+=H[i]; cnt[i:i+K]+=1
    return out/cnt

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; total=d.shape[0]*d.shape[1]; s=s2=0.0
        for i in range(0,d.shape[0],4096):
            a=np.asarray(d[i:i+4096,:],np.float64); s+=float(a.sum()); s2+=float(np.square(a).sum())
        mean=s/total; eps=.1*math.sqrt(max(0,s2/total-mean*mean))
        X=np.asarray(d[TRAIN:TRAIN+NSEG,C0:C0+C],np.float64).T
    F=np.fft.rfft(X,axis=1); nf=F.shape[1]
    Fr={r:np.zeros_like(F) for r in RANKS}
    eff99=[]; eff999=[]; eff9999=[]; sv_rat=[]
    for j in range(nf):
        H=hankel(F[:,j]); U,S,Vh=np.linalg.svd(H,full_matrices=False)
        e=np.cumsum(S*S); tot=e[-1] if e[-1]>0 else 1.0
        eff99.append(int(np.searchsorted(e,.99*tot)+1)); eff999.append(int(np.searchsorted(e,.999*tot)+1)); eff9999.append(int(np.searchsorted(e,.9999*tot)+1))
        sv_rat.append(float(S[0]/(S.sum()+1e-30)))
        for r in RANKS:
            Hr=(U[:,:r]*S[:r])@Vh[:r]
            Fr[r][:,j]=dehankel(Hr)
        if j%512==0: print(json.dumps({'frequency_bin':j,'nf':nf,'rank99':eff99[-1],'rank999':eff999[-1]}),flush=True)
    rows=[]
    for r in RANKS:
        R=np.fft.irfft(Fr[r],n=NSEG,axis=1)
        E=X-R; mx=float(np.max(np.abs(E))); rmse=float(np.sqrt(np.mean(E*E))); h=h0_bits(np.rint(E).astype(np.int32))
        row={'rank':r,'maxerr':mx,'rmse':rmse,'within_hard_eps':bool(mx<=eps),'rounded_residual_h0_bps':h,
             'h0_minus_log2_267_bps':max(0.0,h-math.log2(267))}
        rows.append(row); print(json.dumps({'rank_reconstruction':row}),flush=True)
    dist={'rank99_median':float(np.median(eff99)),'rank99_p90':float(np.percentile(eff99,90)),'rank99_max':int(max(eff99)),
          'rank999_median':float(np.median(eff999)),'rank999_p90':float(np.percentile(eff999,90)),'rank999_max':int(max(eff999)),
          'rank9999_median':float(np.median(eff9999)),'rank9999_p90':float(np.percentile(eff9999,90)),'rank9999_max':int(max(eff9999)),
          'leading_sv_share_median':float(np.median(sv_rat))}
    legal=[x for x in rows if x['within_hard_eps']]
    out={'segment':[TRAIN,TRAIN+NSEG],'shape':[C,NSEG],'eps':eps,'hankel_shape':[L,K],'frequency_bins':nf,
         'rank_distribution':dist,'rank_reconstructions':rows,'smallest_tested_hard_legal_rank':legal[0] if legal else None,
         'note':'Time is transformed with a public rFFT. Each spatial frequency slice is Hankelized and truncated by SVD, then anti-diagonal averaged and inverse transformed. This is a full-data oracle diagnostic on the heldout segment: factor transmission cost is not encoded here, so it is not a final codec or lower bound.'}
    json.dump(out,open('imperial_hankel_structure_hunt.json','w'),indent=2)
    print(json.dumps({'summary':{'rank_distribution':dist,'smallest_hard_legal':out['smallest_tested_hard_legal_rank']}},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
