import json,sys,math
from collections import defaultdict
import h5py,numpy as np
from scipy.stats import beta
import imperial_decoder_phase_automaton as m

C0=512;C=128;T0=4096;T1=12288
CHANNELS=np.arange(0,C,4,dtype=int) # 32 deterministic hard-region channels
LENS=(1,2,4,8); PAIRS=50_000_000; CHUNK=250_000; SEED=20260813
CTX_PAIRS=8_000_000

def make_pool(X,L,maxn=300000):
    arr=[];ctx=[]
    for ci in range(X.shape[0]):
        x=X[ci]
        for off in range(L):
            n=(len(x)-off)//L
            if n<=1:continue
            b=x[off:off+n*L].reshape(n,L)
            arr.append(b)
            prev=np.empty(n,np.float64);prev[0]=0.0
            starts=off+np.arange(n)*L
            ok=starts>0;prev[ok]=x[starts[ok]-1]
            ctx.append(prev)
    A=np.concatenate(arr,axis=0);P=np.concatenate(ctx)
    if len(A)>maxn:
        rng=np.random.default_rng(SEED+L);ix=rng.choice(len(A),maxn,replace=False);A=A[ix];P=P[ix]
    return np.asarray(A,np.float32),np.asarray(P,np.float32)

def compat_mc(A,diam,npairs,seed):
    rng=np.random.default_rng(seed);n=len(A);hits=0;done=0
    while done<npairs:
        z=min(CHUNK,npairs-done);i=rng.integers(0,n,z);j=rng.integers(0,n,z)
        same=i==j
        while np.any(same):j[same]=rng.integers(0,n,int(same.sum()));same=i==j
        hits+=int(np.count_nonzero(np.max(np.abs(A[i]-A[j]),axis=1)<=diam));done+=z
    # one-sided 95% Clopper-Pearson upper bound; use this to make rate lower bound conservative.
    pu=float(beta.ppf(.95,hits+1,npairs-hits)) if hits<npairs else 1.0
    ph=hits/npairs
    return hits,ph,pu

def entropy_rows(A):
    # empirical Shannon entropy of exact rows after nearest legal step267, diagnostic only.
    Q=np.rint(A/267.0).astype(np.int16)
    key=np.ascontiguousarray(Q).view(np.dtype((np.void,Q.dtype.itemsize*Q.shape[1]))).ravel()
    _,cnt=np.unique(key,return_counts=True);p=cnt.astype(float)/cnt.sum()
    return float(-(p*np.log2(p)).sum())/Q.shape[1],int(len(cnt))

def genie_context_bound(A,P,diam,L):
    # Give encoder/decoder original preceding amplitude quantized at 267 for free.
    # Estimate compatibility independently inside each sufficiently populated context.
    q=np.rint(P/267.0).astype(np.int32);groups=defaultdict(list)
    for i,v in enumerate(q):groups[int(v)].append(i)
    usable=[(k,np.asarray(v,dtype=np.int32)) for k,v in groups.items() if len(v)>=64]
    total=sum(len(v) for _,v in usable)
    if total==0:return None
    budget=CTX_PAIRS;rows=[];weighted=0.0;covered=0
    for gi,(k,ix) in enumerate(usable):
        w=len(ix)/total;npair=max(2000,int(round(budget*w)));rng=np.random.default_rng(SEED+1000+L*131+gi);hits=0;done=0
        while done<npair:
            z=min(100000,npair-done);a=rng.integers(0,len(ix),z);b=rng.integers(0,len(ix),z);same=a==b
            while np.any(same):b[same]=rng.integers(0,len(ix),int(same.sum()));same=a==b
            hits+=int(np.count_nonzero(np.max(np.abs(A[ix[a]]-A[ix[b]]),axis=1)<=diam));done+=z
        pu=float(beta.ppf(.95,hits+1,npair-hits)) if hits<npair else 1.0
        lb=-math.log2(max(pu,1e-300))/L;weighted+=w*lb;covered+=len(ix)
        rows.append({'context':k,'n':len(ix),'weight':w,'pairs':npair,'hits':hits,'p_upper95':pu,'rate_lb_bps':lb})
    return {'free_context':'round(original previous source sample / 267), given to decoder at zero bits','covered_fraction':covered/len(A),'weighted_conditional_collision_rate_lb_bps':weighted,'contexts':len(rows),'largest_contexts':sorted(rows,key=lambda z:z['n'],reverse=True)[:12]}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T1,C0:C0+C],np.float32).T[CHANNELS]
    diam=2*eps
    sz,_=m.szrun(X,eps);szbps=8*sz/X.size;target=szbps/2
    out={'global_std':std,'eps':eps,'diameter_2eps':diam,'hard_region':[C0,C0+C-1],'time_interval':[T0,T1],'channels':[int(C0+x) for x in CHANNELS],'samples':int(X.size),'matched_sz3_bytes':int(sz),'matched_sz3_bps':szbps,'two_x_target_bps':target,'pair_trials_per_length':PAIRS,'rows':[]}
    for L in LENS:
        A,P=make_pool(X,L);hits,ph,pu=compat_mc(A,diam,PAIRS,SEED+L)
        lb=-math.log2(max(pu,1e-300))/L;emp,uniq=entropy_rows(A);ctx=genie_context_bound(A,P,diam,L) if L<=4 else None
        row={'L':L,'pool_blocks':len(A),'compat_hits':hits,'compat_probability':ph,'compat_probability_upper95':pu,'memoryless_vector_collision_rate_lb_bps':lb,'fixed267_empirical_block_entropy_bps':emp,'fixed267_unique_blocks':uniq,'ratio_lb_to_2x_target':lb/target,'free_previous_source_context':ctx}
        out['rows'].append(row);print(json.dumps(row,indent=2),flush=True)
    out['scope']='Hard-zone block-covering information diagnostic, NOT a universal impossibility theorem. A length-L hard-error codeword can represent two source blocks only if their coordinatewise epsilon intervals have a common intersection; equivalently max_i |x_i-x_i_prime| <= 2epsilon. For any memoryless L-sample vector quantizer, same reconstruction codeword implies this compatibility event. Therefore collision probability of the code index is <= measured block compatibility probability, so H2(code index)>=-log2(Pcompat), and Shannon H>=H2. We estimate Pcompat from 50 million independent distinct block pairs and use a one-sided 95% upper confidence bound, yielding a conservative per-sample collision-entropy lower bound. A second deliberately favorable diagnostic gives the exact previous ORIGINAL source amplitude quantized at 267 to the decoder for free and computes a weighted within-context bound. This does not bound arbitrary stateful/contextual whole-file codes, nor prove an information-theoretic rate-distortion limit; it identifies whether short vector-covering codebooks have plausible 2x headroom. The fixed267 block entropy is a plug-in diagnostic, not a lower bound.'
    print(json.dumps({'sz3_bps':szbps,'two_x_target_bps':target,'rows':[{k:v for k,v in r.items() if k!='free_previous_source_context'} for r in out['rows']]},indent=2),flush=True);json.dump(out,open('imperial_hardzone_block_covering_rate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
