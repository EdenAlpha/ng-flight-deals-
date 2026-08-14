import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m

C=128
NT=30000
TB=1024
N_BLOCKS=54
N_PARTS=3
FULL_PSD_NT=(NT//TB)*TB


def waterfill(eigs,D):
    e=np.maximum(np.asarray(eigs,np.float64).ravel(),0.0)
    if D>=float(e.mean()):
        return float(e.max()),0.0
    lo=0.0;hi=float(e.max())
    for _ in range(100):
        th=(lo+hi)/2.0
        d=float(np.mean(np.minimum(e,th)))
        if d<D: lo=th
        else: hi=th
    th=(lo+hi)/2.0
    mask=e>th
    if not np.any(mask): return th,0.0
    R=float(np.mean(0.5*np.log2(e[mask]/th)))*float(np.mean(mask))
    return th,R


def stats1(x):
    z=np.asarray(x,np.float64).ravel()
    mu=float(z.mean())
    v=float(np.mean((z-mu)**2))
    sd=math.sqrt(max(v,1e-300))
    q=(z-mu)/sd
    return {
        'mean':mu,'std':sd,
        'skew':float(np.mean(q**3)),
        'excess_kurtosis':float(np.mean(q**4)-3.0),
    }


def psd2(X):
    P=None;n=0
    for t0 in range(0,FULL_PSD_NT,TB):
        A=np.asarray(X[:,t0:t0+TB],np.float64)
        A=A-A.mean(axis=1,keepdims=True)
        A=A-A.mean(axis=0,keepdims=True)+A.mean()
        F=np.fft.fft2(A,norm='ortho')
        Q=np.abs(F)**2
        if P is None: P=Q
        else: P+=Q
        n+=1
    return P/float(n),n


def matched_sz3(X,eps):
    total=0
    rows=[]
    for t0 in range(0,NT,TB):
        t1=min(t0+TB,NT)
        b,meta=m.szrun(X[:,t0:t1],eps)
        total+=int(b)
        rows.append({'t0':t0,'nt':t1-t0,'bytes':int(b),'meta':meta})
    return total,rows


def main(path,part):
    part=int(part)
    if not 0<=part<N_PARTS: raise ValueError(part)
    per=(N_BLOCKS+N_PARTS-1)//N_PARTS
    b0=part*per;b1=min(N_BLOCKS,(part+1)*per)
    out_rows=[]
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912): raise RuntimeError(('unexpected shape',d.shape))
        _,gstd=m.stats(d)
        eps=.1*gstd
        for bi in range(b0,b1):
            c0=bi*C
            X=np.asarray(d[:,c0:c0+C],np.float64).T
            mom=stats1(X)
            P,npsd=psd2(X)
            theta,R=waterfill(P,eps*eps)
            sz,sz_tiles=matched_sz3(X,eps)
            n=int(X.size)
            rd_bytes=float(R*n/8.0)
            target=float(sz/2.0)
            row={
                'block_index':bi,'c0':c0,'channels':C,'samples':n,
                'local_std':mom['std'],'eps_over_local_std':eps/mom['std'],
                'skew':mom['skew'],'excess_kurtosis':mom['excess_kurtosis'],
                'psd_tiles':npsd,
                'spectral_flatness':float(np.exp(np.mean(np.log(P+1e-30)))/(np.mean(P)+1e-30)),
                'waterfill_theta':theta,
                'active_spectral_fraction':float(np.mean(P>theta)),
                'gaussian_2d_mse_RD_bps':R,
                'gaussian_model_bytes':rd_bytes,
                'matched_sz3_bytes':int(sz),
                'matched_sz3_bps':float(8*sz/n),
                'two_x_sz3_target_bytes':target,
                'two_x_sz3_target_bps':float(4*sz/n),
                'gaussian_RD_over_2x_target':rd_bytes/target if target>0 else None,
                'gaussian_model_below_2x_target':bool(rd_bytes<target),
                'sz3_tiles':sz_tiles,
            }
            out_rows.append(row)
            print(json.dumps({k:row[k] for k in (
                'block_index','c0','local_std','eps_over_local_std','spectral_flatness',
                'gaussian_2d_mse_RD_bps','matched_sz3_bps','two_x_sz3_target_bps',
                'gaussian_RD_over_2x_target')},indent=2),flush=True)
    sums={
        'samples':int(sum(r['samples'] for r in out_rows)),
        'gaussian_model_bytes':float(sum(r['gaussian_model_bytes'] for r in out_rows)),
        'matched_sz3_bytes':int(sum(r['matched_sz3_bytes'] for r in out_rows)),
        'two_x_sz3_target_bytes':float(sum(r['two_x_sz3_target_bytes'] for r in out_rows)),
        'blocks_below_2x_target':int(sum(r['gaussian_model_below_2x_target'] for r in out_rows)),
    }
    sums['gaussian_model_over_2x_target']=sums['gaussian_model_bytes']/sums['two_x_sz3_target_bytes']
    result={
        'part':part,'block_range':[b0,b1],'global_std':gstd,'eps':eps,
        'tile_shape':[C,TB],'analysis_samples_per_block':C*NT,
        'psd_samples_per_block':C*FULL_PSD_NT,
        'rows':out_rows,'part_summary':sums,
        'scope':(
            'Full-cable model-based information audit, NOT a theorem about the actual non-Gaussian fixed file and NOT a compression claim. '
            'Every fixed 128-channel block uses all 30000 samples for local moments and matched SZ3. Its stationary 2-D Gaussian covariance spectrum is estimated by averaging all 29 complete 128x1024 orthonormal periodograms after the same row/column centering as PR368. '
            'Reverse waterfilling computes the squared-error rate-distortion function of the Gaussian field with that measured spectrum at D=epsilon^2. Under that Gaussian model, a max-error<=epsilon codec must also satisfy MSE<=epsilon^2, so the reported Gaussian R(D) is a model-conditional lower bound. It is not a rigorous bound for the real seismic data. '
            'Matched SZ3 is rerun on the identical full 30000-sample block partition and every SZ3 frame is hard-error checked by the imported canonical helper. No AI.'
        )
    }
    fn=f'imperial_full_cable_gaussian_rd_{part}.json'
    json.dump(result,open(fn,'w'),indent=2)
    print(json.dumps({'part_summary':sums},indent=2),flush=True)

if __name__=='__main__':
    if len(sys.argv)!=3: raise SystemExit('usage: script imperial.h5 PART')
    main(sys.argv[1],sys.argv[2])
