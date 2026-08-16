import json, math, sys
import h5py
import numpy as np
import zstandard as zstd
from scipy.fft import dctn, idctn

C=128; NT=30000; C0=512; TRAIN=8192; EPS_INT=133; STEP=267
CURRENT_BYTES=2468803; MATCHED_SZ3=2767977


def h0_bits(a):
    a=np.asarray(a).reshape(-1)
    _,cnt=np.unique(a,return_counts=True)
    p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def zbytes(a):
    a=np.ascontiguousarray(a)
    return len(zstd.ZstdCompressor(level=19).compress(a.tobytes()))


def report_resid(name,r,model_bytes=0,kind='causal'):
    r=np.rint(r).astype(np.int32,copy=False).reshape(-1)
    hb=h0_bits(r); zb=zbytes(r); n=len(r)
    row={'name':name,'kind':kind,'samples':int(n),'residual_h0_bps':hb,
         'residual_zstd_bps':8.0*zb/n,'residual_zstd_bytes':int(zb),
         'model_bytes':int(model_bytes),
         'h0_minus_log2_267_bps':max(0.0,hb-math.log2(267))}
    print(json.dumps({'residual':row}),flush=True)
    return row


def fit_var(X,lag):
    rows=[]
    for j in range(1,lag+1): rows.append(X[:,lag-j:TRAIN-j].T)
    F=np.concatenate(rows,axis=1)
    Y=X[:,lag:TRAIN].T
    mu=F.mean(0); sc=F.std(0); sc[sc<1e-9]=1.0
    ym=Y.mean(0); ys=Y.std(0); ys[ys<1e-9]=1.0
    A=np.column_stack([np.ones(len(F)),(F-mu)/sc])
    B,*_=np.linalg.lstsq(A,(Y-ym)/ys,rcond=None)
    return {'B':B,'mu':mu,'sc':sc,'ym':ym,'ys':ys}


def apply_var(X,lag,m):
    rows=[]
    for j in range(1,lag+1): rows.append(X[:,TRAIN-j:NT-j].T)
    F=np.concatenate(rows,axis=1)
    P=m['ym']+m['ys']*(np.column_stack([np.ones(len(F)),(F-m['mu'])/m['sc']])@m['B'])
    Y=X[:,TRAIN:NT].T
    return Y-np.rint(P)


def latent_prev_predictors(X,ranks):
    Xt=X[:,:TRAIN]
    mu=Xt.mean(1,keepdims=True)
    Zc=Xt-mu
    cov=(Zc@Zc.T)/TRAIN
    w,U=np.linalg.eigh(cov); U=U[:,np.argsort(w)[::-1]]
    out=[]
    for r in ranks:
        Ur=U[:,:r]
        Zin=(Ur.T@(X[:,:TRAIN-1]-mu)).T
        Y=X[:,1:TRAIN].T
        zm=Zin.mean(0); zs=Zin.std(0); zs[zs<1e-9]=1.0
        ym=Y.mean(0); ys=Y.std(0); ys[ys<1e-9]=1.0
        A=np.column_stack([np.ones(len(Zin)),(Zin-zm)/zs])
        B,*_=np.linalg.lstsq(A,(Y-ym)/ys,rcond=None)
        Ztest=(Ur.T@(X[:,TRAIN-1:NT-1]-mu)).T
        P=ym+ys*(np.column_stack([np.ones(len(Ztest)),(Ztest-zm)/zs])@B)
        res=X[:,TRAIN:NT].T-np.rint(P)
        model_floats=Ur.size+B.size+zm.size+zs.size+ym.size+ys.size+mu.size
        row=report_resid(f'heldout_latent_prev_rank{r}',res,4*model_floats,'causal_source_state')
        row['rank']=r
        out.append(row)
    return out


def fit_wide_wave(X,margin):
    offs1=np.arange(-margin,margin+1,dtype=np.int64)
    m2=max(2,margin//2); offs2=np.arange(-m2,m2+1,dtype=np.int64)
    leftn=min(8,margin); left=np.arange(1,leftn+1,dtype=np.int64)
    rng=np.random.default_rng(20260817+margin)
    N=100000
    cs=rng.integers(margin,C-margin,size=N)
    ts=rng.integers(2,TRAIN,size=N)
    cols=[X[cs+o,ts-1] for o in offs1]
    cols += [X[cs+o,ts-2] for o in offs2]
    cols += [X[cs-o,ts] for o in left]
    F=np.column_stack(cols)
    y=X[cs,ts]
    mu=F.mean(0); sc=F.std(0); sc[sc<1e-9]=1.0
    ym=float(y.mean()); ys=max(float(y.std()),1.0)
    A=np.column_stack([np.ones(N),(F-mu)/sc])
    b,*_=np.linalg.lstsq(A,(y-ym)/ys,rcond=None)
    t0=TRAIN; t1=NT
    pred=np.full((C-2*margin,t1-t0),ym+ys*b[0],np.float64)
    q=1
    for o in offs1:
        pred += ys*b[q]*(X[margin+o:C-margin+o,t0-1:t1-1]-mu[q-1])/sc[q-1]; q+=1
    for o in offs2:
        pred += ys*b[q]*(X[margin+o:C-margin+o,t0-2:t1-2]-mu[q-1])/sc[q-1]; q+=1
    for o in left:
        pred += ys*b[q]*(X[margin-o:C-margin-o,t0:t1]-mu[q-1])/sc[q-1]; q+=1
    ytest=X[margin:C-margin,t0:t1]
    r=ytest-np.rint(pred)
    row=report_resid(f'heldout_wide_wave_margin{margin}',r,4*(len(b)+2*len(mu)+2),'causal_source_state')
    row.update({'margin':margin,'features':int(F.shape[1])})
    return row


def pca_oracle(X,eps):
    mu=X.mean(1,keepdims=True); A=X-mu
    cov=(A@A.T)/NT
    w,U=np.linalg.eigh(cov); order=np.argsort(w)[::-1]; w=w[order]; U=U[:,order]
    coeff=U.T@A
    total=float(np.sum(w)); rec=np.repeat(mu,NT,axis=1).astype(np.float64)
    selected={1,2,4,8,16,32,48,64,80,96,112,120,124,126,127}
    rows=[]
    for i in range(127):
        rec += np.outer(U[:,i],coeff[i])
        r=i+1
        if r in selected:
            err=X-rec
            row={'rank':r,'energy_fraction':float(np.sum(w[:r])/total),
                 'rmse':float(np.sqrt(np.mean(err*err))),
                 'maxerr':float(np.max(np.abs(err))),
                 'within_hard_eps':bool(np.max(np.abs(err))<=eps)}
            rows.append(row); print(json.dumps({'pca_oracle':row}),flush=True)
    return rows


def dct_oracle(X,eps):
    F=dctn(X,type=2,norm='ortho')
    flat=np.abs(F).reshape(-1)
    order=np.argsort(flat)[::-1]
    G=np.zeros_like(F)
    gf=G.reshape(-1); ff=F.reshape(-1)
    fracs=[0.0005,0.001,0.002,0.005,0.01,0.02,0.05,0.1,0.2,0.4,0.6,0.8]
    rows=[]; prev=0; n=X.size
    for frac in fracs:
        k=max(1,int(round(frac*n)))
        idx=order[prev:k]; gf[idx]=ff[idx]; prev=k
        R=idctn(G,type=2,norm='ortho')
        E=X-R
        row={'fraction':frac,'coefficients':k,'coeff_fraction':k/n,
             'rmse':float(np.sqrt(np.mean(E*E))),'maxerr':float(np.max(np.abs(E))),
             'within_hard_eps':bool(np.max(np.abs(E))<=eps),
             'rounded_residual_h0_bps':h0_bits(np.rint(E).astype(np.int32))}
        rows.append(row); print(json.dumps({'dct_oracle':row}),flush=True)
    return rows


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; total=d.shape[0]*d.shape[1]; s=s2=0.0
        for i in range(0,d.shape[0],4096):
            a=np.asarray(d[i:i+4096,:],np.float64); s+=float(a.sum()); s2+=float(np.square(a).sum())
        mean=s/total; eps=.1*math.sqrt(max(0.0,s2/total-mean*mean))
        X=np.asarray(d[:,C0:C0+C],np.float64).T
    if np.max(np.abs(X-np.rint(X)))>1e-6: raise RuntimeError('noninteger source')
    n=X.size; target_bps=8*(MATCHED_SZ3/2)/n; current_bps=8*CURRENT_BYTES/n
    meta={'shape':[C,NT],'samples':n,'eps':eps,'current_bps':current_bps,'target_2x_bps':target_bps,
          'current_bytes':CURRENT_BYTES,'matched_sz3_bytes':MATCHED_SZ3}
    print(json.dumps({'meta':meta}),flush=True)
    residuals=[]
    for lag in (1,2):
        m=fit_var(X,lag); r=apply_var(X,lag,m)
        floats=m['B'].size+m['mu'].size+m['sc'].size+m['ym'].size+m['ys'].size
        residuals.append(report_resid(f'heldout_global_VAR{lag}',r,4*floats,'causal_source_state'))
    residuals += latent_prev_predictors(X,(4,8,16,32,64))
    for margin in (8,16,32): residuals.append(fit_wide_wave(X,margin))
    pca=pca_oracle(X,eps)
    dct=dct_oracle(X,eps)
    best=min(residuals,key=lambda z:z['residual_h0_bps'])
    out={'meta':meta,'heldout_global_predictors':residuals,'full_file_pca_oracle':pca,'full_file_dct_oracle':dct,
         'summary':{'best_heldout_global_predictor':best,'target_2x_bps':target_bps,
                    'note':'Heldout residual entropies are structural diagnostics, not finite-file lower bounds. PCA/DCT use the full file and are explicitly noncausal oracle decompositions; they reveal global concentration but do not include a complete coefficient/address cost.'}}
    json.dump(out,open('imperial_global_structure_hunt.json','w'),indent=2)
    print(json.dumps({'summary':out['summary']},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
