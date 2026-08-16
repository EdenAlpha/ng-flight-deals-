import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m

T0=14488
C0=512
C=128
T=1024
TRAIN=256
P=8
STEP=267
WIDTHS=(8,16,24,32,40,48,64,128)
GLOBAL_HEADER=32
SELECTOR=1


def build(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,P,'shared')
            k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard encode',me,eps))
    return int(mb),coef,R,K,me


def replay(X,eps,coef,K,Rref):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=ar.predict_hist(R,c,t,coef,P,'shared')+STEP*int(K[c,t])
    if not np.array_equal(R,Rref):raise RuntimeError('causal replay')
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return me


def encode_partition(K,width,kind):
    total=0;Kd=np.empty_like(K);parts=[]
    for c0 in range(0,K.shape[0],width):
        B=np.ascontiguousarray(K[c0:min(c0+width,K.shape[0])],np.int32)
        if kind=='restricted':
            n,rep,D,detail=rr.restricted_rank_frame(B);n=int(n)
        else:
            fr=m.encode_k(B);n=int(fr[0]);rep=fr[1];D=np.asarray(fr[2],np.int32);detail=None
        if not np.array_equal(D,B):raise RuntimeError(('partition decode',kind,width,c0))
        Kd[c0:c0+B.shape[0]]=D;total+=n
        parts.append({'c0':c0,'channels':B.shape[0],'bytes':n,'rep':rep,'detail':detail})
    return total,Kd,parts


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,coef,R,K,me=build(X,eps)
    lf=m.encode_k(K);legacy_whole=int(mb)+int(lf[0])+GLOBAL_HEADER
    if not np.array_equal(np.asarray(lf[2],np.int32),K):raise RuntimeError('legacy whole decode')
    rows=[]
    for width in WIDTHS:
        for kind in ('legacy','restricted'):
            pb,Kd,parts=encode_partition(K,width,kind);mer=replay(X,eps,coef,Kd,R)
            total=mb+pb+GLOBAL_HEADER+SELECTOR
            r={'address_width':width,'kind':kind,'bytes':total,'bps':8*total/X.size,'model_bytes':mb,'payload_bytes':pb,'global_header_bytes':GLOBAL_HEADER,'selector_bytes':SELECTOR,'n_address_frames':len(parts),'maxerr':mer,'gain_vs_legacy_whole':legacy_whole/total,'gain_vs_sz3':szb/total,'delta_vs_legacy_whole':total-legacy_whole,'parts':parts}
            rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='parts'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[C,T],'t0':T0,'c0':C0,'global_std':std,'eps':eps,'order':P,'step':STEP,'train':TRAIN,'widths':list(WIDTHS),'shared_model_bytes':mb,'legacy_whole':{'bytes':legacy_whole,'payload_bytes':int(lf[0]),'rep':lf[1],'maxerr':me},'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Decoder-real separation of generator scale from address scale. One single shared AR8 model is fit across the entire fixed hard 128x1024 tile and charged once. The resulting exact K field and reconstruction are held fixed. Only the address universe is partitioned into fixed contiguous channel widths. Each partition is physically encoded independently either by the legacy K codec or exact PR512 restricted ranking, byte-decoded, concatenated back into the identical full K field, and the one shared AR8 model causally replays the identical source-bounded reconstruction. Every frame is already included in its codec bytes, plus one public width/kind selector byte and one global header. No per-part oracle routing and no model refitting across partitions.'}
    json.dump(out,open('imperial_hard_shared_ar8_address_partition.json','w'),indent=2)
    print(json.dumps({'summary':{'best_width':best['address_width'],'best_kind':best['kind'],'best_bytes':best['bytes'],'legacy_whole':legacy_whole,'sz3':int(szb),'delta_vs_legacy':best['bytes']-legacy_whole,'gain_vs_legacy':legacy_whole/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
