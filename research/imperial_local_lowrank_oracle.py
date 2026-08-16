import json, math, sys
import h5py
import numpy as np

C=128; NT=30000; C0=512; CURRENT_BYTES=2468803; MATCHED_SZ3=2767977
CONFIGS=((32,256),(64,512),(128,1024))
FRACTIONS=(0.125,0.25,0.5,0.75,0.875,0.9375,0.96875,0.984375)
SAMPLES_PER_CONFIG=24


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; total=d.shape[0]*d.shape[1]; s=s2=0.0
        for i in range(0,d.shape[0],4096):
            a=np.asarray(d[i:i+4096,:],np.float64); s+=float(a.sum()); s2+=float(np.square(a).sum())
        mu=s/total; eps=.1*math.sqrt(max(0.0,s2/total-mu*mu)); X=np.asarray(d[:,C0:C0+C],np.float64).T
    if np.max(np.abs(X-np.rint(X)))>1e-6: raise RuntimeError('noninteger')
    results=[]
    for G,B in CONFIGS:
        starts=[]
        all_pairs=[(c,t) for c in range(0,C-G+1,G) for t in range(0,NT-B+1,B)]
        idx=np.linspace(0,len(all_pairs)-1,min(SAMPLES_PER_CONFIG,len(all_pairs)),dtype=int)
        pairs=[all_pairs[i] for i in idx]
        rows={f:{'ranks':[],'rmse':[],'maxerr':[],'energy':[]} for f in FRACTIONS}
        for c0,t0 in pairs:
            A=X[c0:c0+G,t0:t0+B]
            mean=A.mean(axis=1,keepdims=True); Z=A-mean
            U,sv,Vt=np.linalg.svd(Z,full_matrices=False)
            e=sv*sv; et=float(e.sum()) if e.size else 1.0; R=min(G,B)
            for f in FRACTIONS:
                r=max(1,min(R-1,int(round(f*R))))
                rec=mean+(U[:,:r]*sv[:r])@Vt[:r]
                err=A-rec
                rows[f]['ranks'].append(r)
                rows[f]['rmse'].append(float(np.sqrt(np.mean(err*err))))
                rows[f]['maxerr'].append(float(np.max(np.abs(err))))
                rows[f]['energy'].append(float(e[:r].sum()/et))
        summary=[]
        for f in FRACTIONS:
            z=rows[f]
            row={'rank_fraction':f,'rank':int(np.median(z['ranks'])),'median_rmse':float(np.median(z['rmse'])),
                 'p95_rmse':float(np.percentile(z['rmse'],95)),'median_maxerr':float(np.median(z['maxerr'])),
                 'p95_maxerr':float(np.percentile(z['maxerr'],95)),'worst_maxerr':float(np.max(z['maxerr'])),
                 'median_energy_fraction':float(np.median(z['energy'])),'fraction_patches_within_hard_eps':float(np.mean(np.asarray(z['maxerr'])<=eps))}
            summary.append(row); print(json.dumps({'config':[G,B],'rank':row}),flush=True)
        # Extremely optimistic coefficient count: basis + temporal coefficients as float32, no residual.
        first_all=next((r for r in summary if r['fraction_patches_within_hard_eps']>=0.95),None)
        optimistic=None
        if first_all:
            r=first_all['rank']; coeff_floats=r*(G+B)+G
            optimistic={'rank':r,'float32_bytes_per_patch':4*coeff_floats,'bytes_per_source_sample':4*coeff_floats/(G*B)}
        results.append({'channels':G,'time':B,'patches_sampled':len(pairs),'rows':summary,'optimistic_parameterization':optimistic})
    out={'meta':{'shape':[C,NT],'samples':C*NT,'eps':eps,'current_bps':8*CURRENT_BYTES/(C*NT),'target_2x_bps':8*(MATCHED_SZ3/2)/(C*NT)},
         'configs':results,
         'note':'Full SVD is computed independently on sampled local source patches, so this is a deliberately noncausal encoder-side oracle and not a codec. It tests whether local matrices are intrinsically low rank under the hard max-error scale. The optimistic parameter count ignores residual coding and metadata; it is included only to reject false low-rank optimism when the basis itself would already be expensive.'}
    json.dump(out,open('imperial_local_lowrank_oracle.json','w'),indent=2)
if __name__=='__main__': main(sys.argv[1])
