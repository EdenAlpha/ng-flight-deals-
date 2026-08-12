import json,math,sys
import h5py
import numpy as np

NVAL=65536
MINV=-32768
GROUP=256
MAXITER=4000
TOL=1e-12


def histograms(d):
    # Row 0 = global empirical amplitude distribution.
    # Rows 1..27 = decoder-known contiguous 256-channel blocks (6912 = 27*256).
    if d.shape[1] % GROUP: raise RuntimeError(('channel count not divisible',d.shape[1],GROUP))
    ng=d.shape[1]//GROUP
    H=np.zeros((ng+1,NVAL),dtype=np.int64)
    for t0 in range(0,d.shape[0],1024):
        A=np.asarray(d[t0:min(d.shape[0],t0+1024)],dtype=np.int32)
        z=(A-MINV).ravel()
        H[0]+=np.bincount(z,minlength=NVAL)
        for g in range(ng):
            z=(A[:,g*GROUP:(g+1)*GROUP]-MINV).ravel()
            H[g+1]+=np.bincount(z,minlength=NVAL)
    return H


def cover_sum_r(r,W,N):
    # z_x=sum r_a for every maximal legal clique/window a..a+W-1 containing x.
    # r shape G x M, M=N-W+1.
    G,M=r.shape
    cs=np.concatenate([np.zeros((G,1),np.float64),np.cumsum(r,axis=1)],axis=1)
    x=np.arange(N)
    lo=np.maximum(0,x-W+1)
    hi=np.minimum(x,M-1)+1
    return cs[:,hi]-cs[:,lo]


def cover_sum_x(v,W):
    # b_a=sum_{x=a}^{a+W-1} v_x for every length-W maximal clique.
    G,N=v.shape
    cs=np.concatenate([np.zeros((G,1),np.float64),np.cumsum(v,axis=1)],axis=1)
    return cs[:,W:]-cs[:,:-W]


def solve_batch(P,W):
    G,N=P.shape;M=N-W+1
    # Uniform over maximal legal cliques. Any nonmaximal reproduction support is dominated by
    # a maximal clique because enlarging its allowed source set cannot increase I(X;Y).
    r=np.full((G,M),1.0/M,np.float64)
    prev=np.full(G,np.inf);history=[]
    for it in range(MAXITER):
        z=cover_sum_r(r,W,N)
        # p-positive symbols must remain covered.
        if np.any((P>0)&(z<=0)):raise RuntimeError(('uncovered source',it))
        v=np.divide(P,z,out=np.zeros_like(P),where=z>0)
        b=cover_sum_x(v,W)
        r*=b
        rs=r.sum(axis=1,keepdims=True)
        if np.any(rs<=0):raise RuntimeError(('dead reproduction marginal',it))
        r/=rs
        z2=cover_sum_r(r,W,N)
        rate=-np.sum(P*np.log2(np.maximum(z2,1e-300)),axis=1)
        delta=np.max(np.abs(rate-prev))
        if it<10 or it%25==0:
            # KKT residual only on reproduction symbols carrying meaningful mass.
            active=r>1e-14
            kres=np.max(np.abs(np.where(active,b-1.0,0.0)),axis=1)
            history.append({'iter':it,'rates_bps':rate.tolist(),'max_rate_change':float(delta),'max_active_kkt_residual':float(np.max(kres))})
            print(json.dumps({'iter':it,'global_bps':float(rate[0]),'groups_mean_bps':float(rate[1:].mean()),'groups_minmax':[float(rate[1:].min()),float(rate[1:].max())],'max_change':float(delta)}),flush=True)
        if it>20 and delta<TOL:
            prev=rate
            break
        prev=rate
    # Recompute final diagnostics exactly with final r.
    z=cover_sum_r(r,W,N)
    rate=-np.sum(P*np.log2(np.maximum(z,1e-300)),axis=1)
    v=np.divide(P,z,out=np.zeros_like(P),where=z>0)
    b=cover_sum_x(v,W)
    active=r>1e-12
    kkt=[]
    for g in range(G):
        aa=active[g]
        kkt.append(float(np.max(np.abs(b[g,aa]-1.0))) if np.any(aa) else None)
    eff=[]
    for g in range(G):
        rr=r[g];eff.append(float(2**(-np.sum(rr[rr>0]*np.log2(rr[rr>0])))))
    return rate,r,{'iterations':it+1,'kkt_residual_active_1e12':kkt,'effective_reproduction_symbols':eff,'history_tail':history[-20:]}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912) or str(d.dtype)!='int16':raise RuntimeError(('identity drift',d.shape,d.dtype))
        # Exact global std, same definition as PR204/206.
        s=ss=0.0;n=0
        for t0 in range(0,d.shape[0],2048):
            x=np.asarray(d[t0:min(d.shape[0],t0+2048)],dtype=np.float64)
            s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
        mu=s/n;std=float(np.sqrt(max(0.0,ss/n-mu*mu)));eps=.1*std
        H=histograms(d)
    if H[0].sum()!=30000*6912:raise RuntimeError(('hist total',int(H[0].sum())))
    if not np.array_equal(H[0],H[1:].sum(axis=0)):raise RuntimeError('group histogram sum mismatch')
    P=H.astype(np.float64)/H.sum(axis=1,keepdims=True)
    # Integer source amplitudes x may share one real reconstruction y iff max(x)-min(x)<=2eps.
    # Hence the largest feasible contiguous source clique has span floor(2eps), i.e. W=span+1 values.
    span=int(math.floor(2*eps));W=span+1
    if not (span<=2*eps<span+1):raise RuntimeError('span arithmetic')
    rates,r,diag=solve_batch(P,W)
    global_rate=float(rates[0]);group_rates=rates[1:]
    weighted_group=float(np.mean(group_rates)) # all 27 blocks have equal sample count
    sz3_bps=8*86361271/(30000*6912)
    target=sz3_bps/2
    # Also state the constructive interpretation. Standard memoryless rate-distortion coding can
    # asymptotically approach I(X;Y) with every emitted pair inside the hard allowed relation.
    out={
      'shape':[30000,6912],'dtype':'int16','samples':30000*6912,
      'global_mean':mu,'global_std':std,'public_eps':eps,
      'integer_amplitude_alphabet':NVAL,'max_legal_source_span_integer':span,'maximal_clique_width_values':W,
      'maximal_reproduction_cliques':NVAL-W+1,
      'global_hard_distortion_rate_bps':global_rate,
      'group256_decoder_known_hard_distortion_rate_bps':weighted_group,
      'group256_rates_bps':group_rates.tolist(),
      'group256_min_bps':float(group_rates.min()),'group256_median_bps':float(np.median(group_rates)),'group256_max_bps':float(group_rates.max()),
      'verified_pr204_sz3_bps':sz3_bps,'two_x_sz3_target_bps':target,
      'global_margin_to_2x_target_bps':global_rate-target,
      'group256_margin_to_2x_target_bps':weighted_group-target,
      'theoretical_gain_vs_sz3_global':sz3_bps/global_rate if global_rate>0 else float('inf'),
      'theoretical_gain_vs_sz3_group256':sz3_bps/weighted_group if weighted_group>0 else float('inf'),
      'solver':diag,
      'interpretation':'Single-letter empirical-memoryless hard-distortion rate-distortion audit. Reproduction symbols are maximal interval cliques of integer amplitudes that share at least one real reconstruction within +/-eps. The multiplicative Blahut-Arimoto fixed point minimizes I(X;Y) over all stochastic amplitude codebooks obeying the hard relation. group256 additionally conditions on decoder-known contiguous 256-channel block. This is an asymptotic model-based rate result, not a compressor byte claim and not a lower bound for the measured dependent space-time source.'
    }
    print(json.dumps(out,indent=2),flush=True)
    json.dump(out,open('imperial_harderror_rate_distortion.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
