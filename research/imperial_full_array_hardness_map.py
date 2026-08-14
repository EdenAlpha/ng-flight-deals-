import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128; NT=30000; NCB=54

def robust_sigma(v):
    # Deterministic sampled MAD; enough for a structural diagnostic without
    # allocating/sorting all 3.84M values twice per block.
    q=np.asarray(v).ravel()[::64].astype(np.float64)
    med=float(np.median(q)); return 1.4826*float(np.median(np.abs(q-med)))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        rows=[]
        for cb in range(NCB):
            c0=cb*C; X=np.asarray(d[:,c0:c0+C],np.float64).T
            local_std=float(np.std(X)); dt=np.diff(X,axis=1); dt_std=float(np.std(dt))
            ch_std=np.std(X,axis=1); ch_dt_std=np.std(dt,axis=1)
            # Cheap coherence proxies: same-time adjacent-channel correlation
            # and lag-1 temporal correlation, each averaged after centering.
            Z=X-X.mean(axis=1,keepdims=True)
            den=np.sqrt(np.sum(Z[:-1]*Z[:-1],axis=1)*np.sum(Z[1:]*Z[1:],axis=1))
            adj=np.sum(Z[:-1]*Z[1:],axis=1)/np.maximum(den,1e-30)
            den_t=np.sqrt(np.sum(Z[:,:-1]**2,axis=1)*np.sum(Z[:,1:]**2,axis=1))
            lag=np.sum(Z[:,:-1]*Z[:,1:],axis=1)/np.maximum(den_t,1e-30)
            row={'cb':cb,'c0':c0,'samples':int(X.size),'global_std':float(gstd),'eps':float(eps),
                 'local_std':local_std,'eps_over_local_std':float(eps/max(local_std,1e-30)),
                 'local_std_over_eps':float(local_std/eps),'dt_std':dt_std,'eps_over_dt_std':float(eps/max(dt_std,1e-30)),
                 'robust_sigma':robust_sigma(X),'robust_dt_sigma':robust_sigma(dt),
                 'channel_std_median':float(np.median(ch_std)),'channel_std_min':float(ch_std.min()),'channel_std_max':float(ch_std.max()),
                 'channel_dt_std_median':float(np.median(ch_dt_std)),
                 'adjacent_corr_mean':float(np.mean(adj)),'adjacent_corr_median':float(np.median(adj)),
                 'lag1_corr_mean':float(np.mean(lag)),'lag1_corr_median':float(np.median(lag))}
            rows.append(row);print(json.dumps(row),flush=True)
        vals=np.array([r['local_std_over_eps'] for r in rows]);dv=np.array([r['dt_std']/eps for r in rows])
        out={'blocks':NCB,'global_std':float(gstd),'eps':float(eps),'rows':rows,
             'summary':{'local_std_over_eps_min':float(vals.min()),'median':float(np.median(vals)),'mean':float(vals.mean()),'max':float(vals.max()),
                        'dt_std_over_eps_min':float(dv.min()),'dt_median':float(np.median(dv)),'dt_mean':float(dv.mean()),'dt_max':float(dv.max())},
             'scope':'Full-array structural hardness map. No codec changes. Measures each 128-channel cable block local amplitude scale, first-difference scale, robust scale and simple spatial/temporal coherence relative to the unchanged global epsilon. Intended to join against the already-audited PR444 per-block activity/K-rate results to quantify what predicts Imperial compressibility. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_full_array_hardness_map.json','w'),indent=2)
        print(json.dumps(out['summary'],indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
