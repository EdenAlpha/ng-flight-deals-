import json, math, sys
import h5py
import numpy as np

C=128; NT=30000; C0=512; RAD=133
INC=2464819
MATCHED_SZ3=2767977
TARGET=MATCHED_SZ3/2.0


def stats(d):
    s=ss=0.0; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    mean=s/n
    return mean,float(np.sqrt(max(0.0,ss/n-mean*mean)))


def win_sum(a,w):
    cs=np.empty(len(a)+1,np.float64);cs[0]=0.0;np.cumsum(a,out=cs[1:])
    return cs[w:]-cs[:-w]


def objective_and_multiplier(q,p,active,L,rad):
    W=2*rad+1
    Z=win_sum(q,W)
    if np.any(Z[active]<=0):raise RuntimeError('zero legal mass')
    f=np.zeros(L,np.float64);f[active]=p[active]/Z[active]
    pf=np.empty(L+1,np.float64);pf[0]=0.0;np.cumsum(f,out=pf[1:])
    j=np.arange(L+2*rad,dtype=np.int64)
    aa=np.maximum(0,j-2*rad);bb=np.minimum(L,j+1)
    M=np.where(bb>aa,pf[bb]-pf[aa],0.0)
    I=float(-np.sum(p[active]*np.log2(Z[active])))
    # F(q)=-sum_x p(x)log2[(Aq)_x] is convex on the probability simplex.
    # grad_j F=-M_j/ln2 and sum_j q_j M_j=1, so the tangent-plane
    # lower bound minimized over the simplex is F(q)+(1-max_j M_j)/ln2.
    maxM=float(np.max(M))
    lower=float(I+(1.0-maxM)/math.log(2.0))
    return I,M,lower,maxM


def hardbox_rd_from_values(v,rad=RAD,max_iter=1000,tol=1e-12,cert_tol=None):
    v=np.asarray(v,np.int64).reshape(-1)
    lo=int(v.min());hi=int(v.max());L=hi-lo+1
    h=np.bincount((v-lo).astype(np.int64),minlength=L).astype(np.float64)
    p=h/h.sum();active=p>0
    q=np.full(L+2*rad,1.0/(L+2*rad),np.float64)
    prevI=None; converged=False; certified=False
    for it in range(max_iter):
        I,M,lower,maxM=objective_and_multiplier(q,p,active,L,rad)
        gap=I-lower
        if cert_tol is not None and gap<=cert_tol:
            converged=True;certified=True;break
        qn=q*M
        s=float(qn.sum())
        if not np.isfinite(s) or s<=0:raise RuntimeError('bad BA normalization')
        qn/=s
        if prevI is not None and abs(I-prevI)<tol:
            q=qn;converged=True;break
        q=qn;prevI=I
    I,M,lower,maxM=objective_and_multiplier(q,p,active,L,rad)
    nz=int(np.count_nonzero(q>1e-15))
    return {'bps':I,'certified_lower_bps':lower,'certificate_gap_bps':I-lower,'max_compatibility_multiplier':maxM,'iterations':it+1,'converged':converged,'certificate_converged':certified,'source_min':lo,'source_max':hi,'source_support':int(np.count_nonzero(active)),'reproduction_support_gt_1e15':nz}


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    Xi=np.rint(X).astype(np.int64)
    if np.max(np.abs(X-Xi))>1e-6:raise RuntimeError('noninteger source')
    if int(math.floor(eps))!=RAD:raise RuntimeError(('unexpected eps',eps))
    # Global solve gets a tight convex certificate; channel solves remain a secondary diagnostic.
    g=hardbox_rd_from_values(Xi,max_iter=10000,tol=1e-14,cert_tol=1e-8)
    print(json.dumps({'global':g}),flush=True)
    ch=[]
    for c in range(C):
        r=hardbox_rd_from_values(Xi[c],max_iter=1000,tol=2e-11,cert_tol=1e-6);r['channel']=c;ch.append(r)
        if c%16==15:print(json.dumps({'channels_done':c+1,'mean_bps':float(np.mean([z['bps'] for z in ch])),'mean_lower_bps':float(np.mean([z['certified_lower_bps'] for z in ch]))}),flush=True)
    cbps=float(np.mean([z['bps'] for z in ch])); clower=float(np.mean([z['certified_lower_bps'] for z in ch]))
    N=C*NT
    out={
      'scope':'Information-theoretic scalar hard-box rate-distortion diagnostic. It minimizes the convex objective F(q)=-sum_x p(x)log2(sum_{|y-x|<=133}q(y)), equivalent to memoryless zero-outside-hard-box R(D). The reported convex tangent certificate lower-bounds the optimum at every iterate: F(q)+(1-max_j M_j)/ln(2). This is NOT a serialized codec result and NOT a universal finite-file lower bound. Channel-conditioned result additionally gives channel index to both sides for free.',
      'shape':[C,NT],'samples':N,'eps':eps,'integer_radius':RAD,'legal_values_per_sample':2*RAD+1,
      'current_exact_bytes':INC,'current_bps':8*INC/N,'matched_sz3_bytes':MATCHED_SZ3,'two_x_target_bytes':TARGET,'two_x_target_bps':8*TARGET/N,
      'global_memoryless_rd':g,'global_equivalent_bytes':g['bps']*N/8.0,'global_certified_lower_equivalent_bytes':g['certified_lower_bps']*N/8.0,
      'channel_conditioned_memoryless_rd_bps':cbps,'channel_conditioned_certified_lower_bps':clower,'channel_conditioned_equivalent_bytes':cbps*N/8.0,'channel_conditioned_certified_lower_equivalent_bytes':clower*N/8.0,
      'channel_min_bps':float(min(z['bps'] for z in ch)),'channel_max_bps':float(max(z['bps'] for z in ch)),
      'channels':ch
    }
    json.dump(out,open('imperial_hardbox_rate_distortion.json','w'),indent=2)
    keys=['current_bps','two_x_target_bps','global_memoryless_rd','global_equivalent_bytes','global_certified_lower_equivalent_bytes','channel_conditioned_memoryless_rd_bps','channel_conditioned_certified_lower_bps','channel_conditioned_equivalent_bytes','channel_conditioned_certified_lower_equivalent_bytes','channel_min_bps','channel_max_bps']
    print(json.dumps({'summary':{k:out[k] for k in keys}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
