import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;BASE_STEP=267;HALF_STEP2=536;MODEL_BYTES=177;TB=1024


def fit_shared_ar(X):
    rows=[];ys=[]
    for c in range(X.shape[0]):
        x=np.asarray(X[c,:TRAIN],np.float64)
        for t in range(P,TRAIN):
            rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
    return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)


def run_integer267(X,coef):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            k=int(np.rint((float(X[c,t])-p)/BASE_STEP));K[c,t]=k;R[c,t]=p+BASE_STEP*k
    return R,K


def run_half268(X,coef,tie):
    # Work in doubled units exactly. Every reconstruction is an odd integer in doubled
    # units, i.e. a half-integer in source units. Source samples are even in doubled
    # units. With lattice spacing 536 (=268 source units), nearest odd-grid distance
    # is at most 267 doubled units = 133.5 source units.
    X2=(2*np.asarray(X,np.int64));R2=np.zeros(X.shape,np.int64);K=np.zeros(X.shape,np.int32)
    a=np.float32(coef[0]);b=np.asarray(coef[1:],np.float32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            if t<P: pred=np.float32(0.0)
            else: pred=a+np.dot(b,(R2[c,t-P:t][::-1].astype(np.float32)*np.float32(0.5)))
            # Nearest half-integer to the decoder-known real predictor. At exact integer
            # ties, choose +0.5 or -0.5 deterministically; both remain decoder-known.
            fp=float(np.floor(float(pred)))
            if tie=='plus':p2=2*int(fp)+1
            elif tie=='minus':
                q=float(pred)
                if q==fp:p2=2*int(fp)-1
                else:p2=2*int(fp)+1
            else:raise ValueError(tie)
            d2=int(X2[c,t])-p2
            # d2 is odd, so d2/536 can never be an exact half-integer tie.
            k=int(np.rint(d2/HALF_STEP2));K[c,t]=k;R2[c,t]=p2+HALF_STEP2*k
    return R2,K


def encode_all(K):
    total=MODEL_BYTES;reps={};frames=[]
    for t0 in range(0,K.shape[1],TB):
        A=K[:,t0:min(t0+TB,K.shape[1])];n,rep,D=m.encode_k(A)
        if not np.array_equal(A,D):raise RuntimeError(('K decode',t0,rep))
        total+=n;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'nt':A.shape[1],'bytes':n,'rep':rep})
    return total,reps,frames


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        if not (133.5<=eps<134.0):raise RuntimeError(('unexpected epsilon for half-grid proof',eps))
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X)
            R,K=run_integer267(X,coef);baseerr=float(np.max(np.abs(X-R.astype(np.float64))));baseb,basereps,baseframes=encode_all(K)
            if baseerr>eps*(1+1e-12):raise RuntimeError((name,'baseline hard',baseerr,eps))
            cand=[]
            for tie in ('plus','minus'):
                R2,K2=run_half268(X,coef,tie);err2=np.max(np.abs((2*np.asarray(X,np.int64))-R2));me=float(err2)/2.0
                if me>eps*(1+1e-12):raise RuntimeError((name,tie,'half hard',me,eps,int(err2)))
                if np.any((R2&1)==0):raise RuntimeError((name,tie,'non half-grid'))
                b,reps,frames=encode_all(K2)
                cand.append({'tie':tie,'bytes':b,'bps':8*b/X.size,'gain_vs_integer267':baseb/b,'maxerr':me,'maxerr_doubled_units':int(err2),'reps':reps,'frames':frames,'k_std':float(K2.std()),'k_zero_fraction':float(np.mean(K2==0))})
            cand.sort(key=lambda x:x['bytes']);best=cand[0]
            sz=0
            for t0 in range(0,NT,TB):q,_=m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=q
            row={'region':name,'c0':c0,'samples':int(X.size),'eps':eps,
                 'integer267':{'bytes':baseb,'bps':8*baseb/X.size,'gain_vs_sz3':sz/baseb,'maxerr':baseerr,'reps':basereps},
                 'half268_candidates':cand,'best_half268':best,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best_gain_vs_sz3':sz/best['bytes']}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'ar_order':P,'integer_step':BASE_STEP,'half_grid_step':268,'rows':rows,
         'scope':'Exact geometry correction to the current AR32 lattice. The canonical source samples are integers but the benchmark/error contract does not require integer reconstructions (matched SZ3 already reconstructs float32 values). With epsilon ~=133.6978, an integer-centered uniform lattice can use at most step267, but a half-integer-centered lattice can legally use step268: in doubled units source samples are even, reconstruction states are forced odd, the lattice spacing is 536, and nearest-grid error is therefore an odd integer at most 267 doubled units =133.5 < epsilon. This branch keeps the same prefix-fitted shared float32 AR32 law, makes its decoder-known prediction phase the nearest half-integer, transmits exact step268 innovations through the existing self-decoding backend, charges the same model/framing bytes, byte-decodes exact K, and verifies the source-domain hard bound. Two deterministic tie conventions at exact integer predictions are tested. Full 128x8192 regions include the training prefix in transmitted K bytes; matched SZ3 uses identical samples/epsilon. No AI. Draft/do not merge.'}
    json.dump(out,open('imperial_ar32_halfgrid_step268.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
