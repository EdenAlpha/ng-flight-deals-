import json, math, sys
import h5py
import numpy as np
import zstandard as zstd
from scipy.spatial import cKDTree

C=128; NT=30000; C0=512; TRAIN=8192; CURRENT_BYTES=2468803; MATCHED_SZ3=2767977

def h0_bits(a):
    a=np.asarray(a).reshape(-1); _,cnt=np.unique(a,return_counts=True); p=cnt/cnt.sum(); return float(-(p*np.log2(p)).sum())
def zbytes(a): return len(zstd.ZstdCompressor(level=19).compress(np.ascontiguousarray(a).tobytes()))
def report(name,r,overhead_bits=0,kind='causal'):
    r=np.rint(r).astype(np.int32).reshape(-1); n=len(r); h=h0_bits(r); z=zbytes(r)
    row={'name':name,'kind':kind,'samples':n,'residual_h0_bps':h,'residual_zstd_bps':8*z/n,'residual_zstd_bytes':z,
         'overhead_bits':int(overhead_bits),'h0_plus_overhead_bps':h+overhead_bits/n,
         'h0_minus_log2_267_bps':max(0.0,h-math.log2(267))}
    print(json.dumps({'result':row}),flush=True); return row

def affine_fit(y,x):
    xm=float(x.mean()); ym=float(y.mean()); xv=x-xm; den=float(np.dot(xv,xv))
    a=float(np.dot(xv,y-ym)/den) if den>1e-9 else 0.0; b=ym-a*xm
    return a,b

def block_recurrence(X,B,causal=True):
    nb=NT//B; Xb=X[:,:nb*B].reshape(C,nb,B).transpose(1,0,2)
    ti=np.linspace(0,B-1,min(8,B),dtype=int); ci=np.arange(0,C,8)
    sig=Xb[:,ci][:,:,ti].reshape(nb,-1).astype(np.float64)
    sm=sig.mean(1,keepdims=True); ss=sig.std(1,keepdims=True); ss[ss<1e-9]=1.0; sig=(sig-sm)/ss
    nrm=np.sum(sig*sig,axis=1); D=nrm[:,None]+nrm[None,:]-2*sig@sig.T
    start=(TRAIN+B-1)//B; residuals=[]; overhead=0; choices=[]
    for j in range(start,nb):
        if causal: cand=np.arange(j)
        else: cand=np.concatenate([np.arange(j),np.arange(j+1,nb)])
        if len(cand)==0: continue
        k=min(8,len(cand)); sel=cand[np.argpartition(D[j,cand],k-1)[:k]]
        y=Xb[j].reshape(-1); best=None
        for q in sel:
            x=Xb[q].reshape(-1); a,b=affine_fit(y,x); rr=y-(a*x+b); mse=float(np.mean(rr*rr))
            if best is None or mse<best[0]: best=(mse,q,a,b,rr)
        _,q,a,b,rr=best; residuals.append(rr); choices.append((j,int(q),a,b))
        overhead += math.ceil(math.log2(max(2,len(cand)))) + 64
    r=np.concatenate(residuals)
    row=report(f"{'causal' if causal else 'noncausal'}_block_recurrence_B{B}",r,math.ceil(overhead), 'causal_reference' if causal else 'noncausal_oracle')
    row.update({'block':B,'blocks_tested':len(choices)})
    return row

def shifted_channel_reference(X):
    residuals=[]; overhead=0; params=[]
    residuals.append(X[0,TRAIN:]-X[0,TRAIN-1:NT-1])
    for c in range(1,C):
        refs=[c-k for k in (1,2,4,8,16) if c-k>=0]
        y=X[c,:TRAIN]
        best=None
        for r in refs:
            xr=X[r]
            scores=[]
            for lag in range(-128,129,8):
                t0=max(0,-lag); t1=min(TRAIN,TRAIN-lag)
                yy=y[t0:t1]; xx=xr[t0+lag:t1+lag]; a,b=affine_fit(yy,xx); mse=float(np.mean((yy-(a*xx+b))**2)); scores.append((mse,lag,a,b))
            lag0=min(scores)[1]
            for lag in range(max(-128,lag0-8),min(128,lag0+8)+1):
                t0=max(0,-lag); t1=min(TRAIN,TRAIN-lag)
                yy=y[t0:t1]; xx=xr[t0+lag:t1+lag]; a,b=affine_fit(yy,xx); mse=float(np.mean((yy-(a*xx+b))**2))
                if best is None or mse<best[0]: best=(mse,r,lag,a,b)
        _,r,lag,a,b=best
        t0=max(TRAIN,TRAIN-lag); t1=min(NT,NT-lag)
        yy=X[c,t0:t1]; xx=X[r,t0+lag:t1+lag]; residuals.append(yy-(a*xx+b))
        params.append((c,r,lag,a,b)); overhead += 8+16+32+32
    rr=np.concatenate(residuals)
    row=report('heldout_shifted_previous_channel_reference',rr,overhead,'causal_channel_reference')
    row['channels_modelled']=len(params); row['median_abs_lag']=float(np.median([abs(x[2]) for x in params]))
    return row

def knn_features(X,cs,ts,oracle=False):
    cols=[X[cs,ts-1],X[cs,ts-2],X[cs,ts-4],X[cs-1,ts-1],X[cs+1,ts-1],X[cs-2,ts-1],X[cs+2,ts-1],X[cs-1,ts]]
    if oracle: cols += [X[cs+1,ts],X[cs,ts+1]]
    return np.column_stack(cols)

def knn_hunt(X,oracle=False):
    rng=np.random.default_rng(260817+(1 if oracle else 0)); ntr=120000; nte=120000
    ctr=rng.integers(2,C-2,size=ntr); ttr=rng.integers(4,TRAIN-1,size=ntr)
    cte=rng.integers(2,C-2,size=nte); tlo=TRAIN; thi=NT-1 if oracle else NT; tte=rng.integers(tlo,thi,size=nte)
    F=knn_features(X,ctr,ttr,oracle); y=X[ctr,ttr]
    Ft=knn_features(X,cte,tte,oracle); yt=X[cte,tte]
    mu=F.mean(0); sc=F.std(0); sc[sc<1e-9]=1.0; F=(F-mu)/sc; Ft=(Ft-mu)/sc
    tree=cKDTree(F)
    rows=[]
    for k in (1,4,16):
        _,ix=tree.query(Ft,k=k,workers=-1)
        pred=y[ix] if k==1 else np.mean(y[ix],axis=1)
        row=report(f"heldout_{'oracle_' if oracle else ''}knn{k}",yt-pred,0,'noncausal_oracle_sample' if oracle else 'causal_warmup_dictionary_sample')
        row.update({'k':k,'train_points':ntr,'test_points':nte,'features':F.shape[1]}); rows.append(row)
    return rows

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; X=np.asarray(d[:,C0:C0+C],np.float64).T
    if np.max(np.abs(X-np.rint(X)))>1e-6: raise RuntimeError('noninteger source')
    n=X.size; meta={'shape':[C,NT],'samples':n,'current_bps':8*CURRENT_BYTES/n,'target_2x_bps':8*(MATCHED_SZ3/2)/n}
    rows=[]
    for B in (32,64,128,256,512): rows.append(block_recurrence(X,B,True))
    for B in (64,128,256): rows.append(block_recurrence(X,B,False))
    rows.append(shifted_channel_reference(X))
    rows+=knn_hunt(X,False); rows+=knn_hunt(X,True)
    best=min(rows,key=lambda z:z['residual_h0_bps'])
    out={'meta':meta,'results':rows,'summary':{'best':best,'note':'Block recurrence includes reference-index plus two-float affine overhead in a rough H0 rate, but is not a final entropy container. kNN is evaluated on held-out random samples; the warmup dictionary is source-side diagnostic. Noncausal variants are explicitly oracle-only.'}}
    json.dump(out,open('imperial_longrange_nonlinear_hunt.json','w'),indent=2)
    print(json.dumps({'summary':out['summary']},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
