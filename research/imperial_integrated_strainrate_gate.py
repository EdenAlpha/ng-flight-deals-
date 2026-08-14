import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=4096
TRAIN=1024
P=32
TB=1024
REGIONS=(('hard',512),('easy',2304))
RATIOS=(0.5,0.75,1.0)


def source_from_latent(R):
    X=np.empty_like(R,dtype=np.float64)
    X[:,0]=R[:,0]
    X[:,1:]=R[:,1:]-R[:,:-1]
    return X


def exact_backend_bytes(K):
    # No AR model is required for the cumulative/error-feedback stream.
    total=16
    reps={}
    for t0 in range(0,NT,TB):
        A=K[:,t0:min(t0+TB,NT)]
        n,rep,D=a.m.encode_k(A)
        if not np.array_equal(A,D):
            raise RuntimeError(('backend decode',t0))
        total+=int(n)
        reps[rep]=reps.get(rep,0)+1
    return total,reps


def integrated_round(X,h):
    # Encoder-side first-order error feedback: quantize cumulative strain-like
    # state, but transmit only its integer increments. Decoder needs no source
    # state: Xhat = h * D.  The cumulative rounding phase chooses among legal
    # per-sample reconstruction levels in a history-dependent way.
    S=np.cumsum(X,axis=1,dtype=np.float64)
    Q=np.rint(S/h).astype(np.int64)
    D=np.empty_like(Q)
    D[:,0]=Q[:,0]
    D[:,1:]=Q[:,1:]-Q[:,:-1]
    if np.max(np.abs(D))>=2**31:
        raise RuntimeError('integrated delta overflow')
    D=D.astype(np.int32)
    Xr=h*D.astype(np.float64)
    return D,Xr


def design_latent(S):
    n=C*(TRAIN-P)
    A=np.empty((n,P+1),np.float64)
    y=np.empty(n,np.float64)
    j=0
    for c in range(C):
        x=S[c,:TRAIN]
        for t in range(P,TRAIN):
            A[j,0]=1.0
            A[j,1:]=x[t-P:t][::-1]
            y[j]=x[t]
            j+=1
    return A,y


def fit_latent_huber(S,h):
    A,y=design_latent(S)
    co=np.linalg.lstsq(A,y,rcond=None)[0]
    # Robust threshold follows the latent quantizer scale, not the source's
    # incumbent 267-unit step.
    for _ in range(6):
        r=y-A@co
        w=np.minimum(1.0,float(h)/np.maximum(np.abs(r),1e-12))
        sw=np.sqrt(w)
        co=np.linalg.lstsq(A*sw[:,None],y*sw,rcond=None)[0]
    return np.asarray(co,np.float32)


def run_latent_ar(S,co,h):
    R=np.zeros(S.shape,np.float64)
    K=np.zeros(S.shape,np.int32)
    aa=float(co[0])
    b=np.asarray(co[1:],np.float64)
    for c in range(C):
        for t in range(NT):
            p=0.0 if t<P else aa+float(np.dot(b,R[c,t-P:t][::-1]))
            k=int(np.rint((float(S[c,t])-p)/h))
            if abs(k)>=2**31:
                raise RuntimeError(('latent K overflow',c,t,k))
            K[c,t]=k
            R[c,t]=p+h*k
    return R,K


def decode_latent_ar(K,co,h):
    R=np.zeros(K.shape,np.float64)
    aa=float(co[0])
    b=np.asarray(co[1:],np.float64)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            p=0.0 if t<P else aa+float(np.dot(b,R[c,t-P:t][::-1]))
            R[c,t]=p+h*int(K[c,t])
    return R


def arithmetic_no_model(K):
    # Reuse the incumbent exact arithmetic engine, but remove its fixed AR
    # model charge because the error-feedback lattice has no transmitted model.
    n,nbit,nb,Kd=a.arithmetic(K)
    return int(n-a.MODEL_BYTES+8),int(nbit),int(nb),Kd


def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        _,gstd=a.m.stats(d)
        eps=.1*gstd
        rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T

            # Exact incumbent control on identical samples.
            _,hu=a.fits(X)
            Rb,Kb=a.run_ar(X,hu)
            base_bytes,base_bits,base_nb,Kbd=a.arithmetic(Kb)
            Rbd=a.decode_source(Kbd,hu)
            base_me=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if base_me>eps*(1+1e-12):
                raise RuntimeError((region,'baseline hard',base_me,eps))

            sz=0
            for t0 in range(0,NT,TB):
                b,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps)
                sz+=int(b)

            S=np.cumsum(X,axis=1,dtype=np.float64)
            cands=[]
            for ratio in RATIOS:
                h=float(eps*ratio)

                # A) cumulative rounding / first-order error-feedback quantizer.
                D,Xr=integrated_round(X,h)
                me=float(np.max(np.abs(X-Xr)))
                nb,nbits,sbits,Dd=arithmetic_no_model(D)
                Xd=h*Dd.astype(np.float64)
                dme=float(np.max(np.abs(X-Xd)))
                if dme>eps*(1+1e-12):
                    raise RuntimeError((region,'integrated round decode hard',ratio,dme,eps))
                zb,zrep=exact_backend_bytes(D)
                best_bytes=min(nb,zb)
                cands.append({
                    'mode':'integrated_round',
                    'h_over_eps':ratio,
                    'h':h,
                    'bytes':int(best_bytes),
                    'bps':8*best_bytes/X.size,
                    'arithmetic_bytes':int(nb),
                    'backend_bytes':int(zb),
                    'backend_reps':zrep,
                    'arithmetic_bits':nbits,
                    'symbol_bits':sbits,
                    'maxerr':dme,
                    'zero_fraction':float(np.mean(D==0)),
                    'std_symbol':float(D.std()),
                    'gain_vs_incumbent':base_bytes/best_bytes,
                    'gain_vs_sz3':sz/best_bytes,
                })

                # B) restore a strain-like latent and fit a decoder-real AR32
                # there.  Since |S-R| <= h/2 samplewise, differencing R gives
                # strain-rate error <= h <= epsilon for ratios <= 1.
                co=fit_latent_huber(S,h)
                R,K=run_latent_ar(S,co,h)
                Xra=source_from_latent(R)
                ame=float(np.max(np.abs(X-Xra)))
                if ame>eps*(1+1e-12):
                    raise RuntimeError((region,'integrated AR hard',ratio,ame,eps))
                ab,abits,asbits,Kd=a.arithmetic(K)
                Rd=decode_latent_ar(Kd,co,h)
                Xad=source_from_latent(Rd)
                adme=float(np.max(np.abs(X-Xad)))
                if adme>eps*(1+1e-12):
                    raise RuntimeError((region,'integrated AR decode hard',ratio,adme,eps))
                cands.append({
                    'mode':'integrated_ar32',
                    'h_over_eps':ratio,
                    'h':h,
                    'bytes':int(ab),
                    'bps':8*ab/X.size,
                    'arithmetic_bits':int(abits),
                    'symbol_bits':int(asbits),
                    'maxerr':adme,
                    'latent_maxerr':float(np.max(np.abs(S-Rd))),
                    'zero_fraction':float(np.mean(K==0)),
                    'std_symbol':float(K.std()),
                    'gain_vs_incumbent':base_bytes/ab,
                    'gain_vs_sz3':sz/ab,
                    'coefficients':[float(x) for x in co],
                })

            best=min(cands,key=lambda q:q['bytes'])
            row={
                'region':region,'c0':c0,'samples':int(X.size),
                'eps':eps,
                'incumbent':{'bytes':int(base_bytes),'bps':8*base_bytes/X.size,'maxerr':base_me,'zero_fraction':float(np.mean(Kb==0))},
                'sz3':{'bytes':int(sz),'bps':8*sz/X.size},
                'best_integrated':best,
                'candidates':cands,
            }
            rows.append(row)
            print(json.dumps(row,indent=2),flush=True)

        out={
            'global_std':gstd,'eps':eps,'nt':NT,'channels':C,'train':TRAIN,
            'rows':rows,
            'scope':'Hard-error-safe integration gate motivated by the official Imperial Valley data contract identifying Acoustic as strain-rate. Variant integrated_round cumulatively sums the source, rounds the latent state on h<=epsilon lattices, then transmits only exact integer state increments; this is a deterministic first-order error-feedback quantizer whose decoded strain-rate is h*D. Variant integrated_ar32 fits a prefix-only shared robust AR32 directly to cumulative strain-like state, quantizes its exact innovation with h<=epsilon, arithmetic-decodes K, reconstructs latent state and differences it back to strain-rate. The h<=epsilon condition gives a conservative source hard-error guarantee because adjacent latent errors are each <=h/2. All candidates are byte-decoded and independently hard-error checked. Incumbent Huber AR32 step267 arithmetic and matched SZ3 are rerun on identical hard/easy 128x4096 regions. No AI. Draft/do not merge.'
        }
        json.dump(out,open('imperial_integrated_strainrate_gate.json','w'),indent=2)

if __name__=='__main__':
    main(sys.argv[1])
