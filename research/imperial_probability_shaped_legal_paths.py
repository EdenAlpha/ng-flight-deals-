import json, math, sys
from collections import defaultdict, Counter
import h5py, numpy as np

QMIN=-256; QMAX=255; ALPHA=.05
BETAS=(2.0,8.0,32.0)
FAC=1.0
REGIONS=(0,2304,4606,6880)
NCH=8
SAFETY=1-1e-5
FULL_SZ3_BPS=3.331839158950617
TARGET_BPS=FULL_SZ3_BPS/2

def stats(d):
    s=ss=0.; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.,ss/n-m*m)))

def nearest_q(x,eps):
    h=FAC*eps
    q=np.rint(np.asarray(x,np.float64)/h).astype(np.int16)
    if int(q.min())<QMIN or int(q.max())>QMAX:
        raise RuntimeError(('q range',int(q.min()),int(q.max())))
    return q

def legal_bounds(x,eps):
    h=FAC*eps; b=eps*SAFETY
    x=np.asarray(x,np.float64)
    lo=np.ceil((x-b)/h).astype(np.int16)
    hi=np.floor((x+b)/h).astype(np.int16)
    if np.any(lo>hi): raise RuntimeError('empty legal set')
    if int(lo.min())<QMIN or int(hi.max())>QMAX:
        raise RuntimeError(('legal q range',int(lo.min()),int(hi.max())))
    return lo,hi,h

def train_model(a,b,lefta=None,leftb=None):
    root=Counter(); c1=defaultdict(Counter); c2=defaultdict(Counter); c3=defaultdict(Counter)
    for q,left in ((a,lefta),(b,leftb)):
        q=np.asarray(q,dtype=np.int16)
        for t in range(1,q.size):
            z=int(q[t]); p=int(q[t-1]); root[z]+=1; c1[p][z]+=1
            if left is not None:
                lc=int(left[t]); lp=int(left[t-1]); c2[(p,lc)][z]+=1; c3[(p,lc,lp)][z]+=1
    root[int(a[0])]+=1; root[int(b[0])]+=1
    return root,c1,c2,c3

def root_probs(root):
    arr=np.full(QMAX-QMIN+1,ALPHA,np.float64)
    for q,n in root.items():
        if QMIN<=q<=QMAX: arr[q-QMIN]+=n
    arr/=arr.sum()
    return arr

def make_prob_fn(model,beta):
    root,c1,c2,c3=model; rp=root_probs(root); cache={}
    def backoff(cnt,key,q,pback):
        cc=cnt.get(key)
        if not cc: return pback
        n=sum(cc.values()); lam=n/(n+beta)
        return lam*(cc.get(q,0)/n)+(1-lam)*pback
    def prob(prev,q,left_now=None,left_prev=None):
        key=(prev,q,left_now,left_prev)
        z=cache.get(key)
        if z is not None: return z
        p=float(rp[q-QMIN])
        p=backoff(c1,prev,q,p)
        if left_now is not None:
            p=backoff(c2,(prev,left_now),q,p)
            p=backoff(c3,(prev,left_now,left_prev),q,p)
        p=max(p,1e-15); cache[key]=p; return p
    return prob

def path_rate_fixed(q,left,prob):
    lp=None if left is None else int(left[0])
    bits=-math.log2(max(prob(int(q[0]),int(q[0]),lp,lp),1e-15))
    for t in range(1,len(q)):
        bits-=math.log2(prob(int(q[t-1]),int(q[t]),None if left is None else int(left[t]),None if left is None else int(left[t-1])))
    return bits

def choose_beta(train_q,val_q,train_left,val_left):
    scores=[]
    model=train_model(train_q,train_q,train_left,train_left)
    for beta in BETAS:
        p=make_prob_fn(model,beta)
        scores.append((path_rate_fixed(val_q,val_left,p),beta))
    scores.sort()
    return scores[0][1],scores

def viterbi_and_mass(lo,hi,left,prob):
    n=len(lo); cur={}; fwd={}; backs=[]
    for q in range(int(lo[0]),int(hi[0])+1):
        lp=None if left is None else int(left[0]); pr=prob(q,q,lp,lp)
        cur[q]=-math.log2(pr); fwd[q]=math.log(pr)
    backs.append({q:None for q in cur})
    for t in range(1,n):
        nc={}; nf={}; back={}
        lc=None if left is None else int(left[t]); lprev=None if left is None else int(left[t-1])
        for q in range(int(lo[t]),int(hi[t])+1):
            best=1e300; bp=None; logs=[]
            for p,cost in cur.items():
                pr=prob(p,q,lc,lprev); z=cost-math.log2(pr)
                if z<best: best=z; bp=p
                logs.append(fwd[p]+math.log(pr))
            nc[q]=best; back[q]=bp
            m=max(logs); nf[q]=m+math.log(sum(math.exp(x-m) for x in logs))
        cur=nc; fwd=nf; backs.append(back)
    qlast=min(cur,key=cur.get); map_bits=cur[qlast]
    logs=list(fwd.values()); m=max(logs); logmass=m+math.log(sum(math.exp(x-m) for x in logs)); mass_bits=-logmass/math.log(2)
    out=np.empty(n,np.int16); out[-1]=qlast
    for t in range(n-1,0,-1): out[t-1]=backs[t][int(out[t])]
    return out,float(map_bits),float(mass_bits)

def main(paths):
    fs=[h5py.File(p,'r') for p in paths]
    try:
        ds=[f['Acoustic'] for f in fs]
        if any(tuple(d.shape)!=(30000,6912) for d in ds): raise RuntimeError('shape drift')
        stds=[stats(d)[1] for d in ds]; eps=[.1*s for s in stds]; rows=[]
        for c0 in REGIONS:
            c1=min(c0+NCH,6912); X=[np.asarray(d[:,c0:c1],np.float64) for d in ds]; Q=[nearest_q(x,e) for x,e in zip(X,eps)]
            decoded_target=[]; reg_map=reg_mass=reg_near=0.; nsamp=0
            for j in range(c1-c0):
                left0=None if j==0 else Q[0][:,j-1]; left1=None if j==0 else Q[1][:,j-1]; leftt=None if j==0 else decoded_target[j-1]
                beta,bs=choose_beta(Q[0][:,j],Q[1][:,j],left0,left1)
                model=train_model(Q[0][:,j],Q[1][:,j],left0,left1); prob=make_prob_fn(model,beta)
                lo,hi,h=legal_bounds(X[2][:,j],eps[2]); qmap,map_bits,mass_bits=viterbi_and_mass(lo,hi,leftt,prob)
                R=qmap.astype(np.float64)*h; me=float(np.max(np.abs(X[2][:,j]-R)))
                if me>eps[2]*(1+5e-6): raise RuntimeError(('hard error',c0,j,me,eps[2]))
                near_bits=path_rate_fixed(Q[2][:,j],leftt,prob); decoded_target.append(qmap)
                reg_map+=map_bits; reg_mass+=mass_bits; reg_near+=near_bits; nsamp+=len(qmap)
                rows.append({'region_c0':c0,'channel':c0+j,'beta':beta,'validation_beta_scores':bs,'nearest_model_bps':near_bits/len(qmap),'map_legal_path_bps':map_bits/len(qmap),'legal_path_mass_bps':mass_bits/len(qmap),'map_gain_vs_nearest_model':near_bits/map_bits,'mass_gain_vs_nearest_model':near_bits/mass_bits,'map_gain_vs_fullfile_sz3_bps':FULL_SZ3_BPS/(map_bits/len(qmap)),'mass_gain_vs_fullfile_sz3_bps':FULL_SZ3_BPS/(mass_bits/len(qmap)),'mean_legal_states':float(np.mean(hi-lo+1)),'max_legal_states':int(np.max(hi-lo+1)),'maxerr':me})
            rows.append({'region_c0':c0,'aggregate':True,'samples':nsamp,'nearest_model_bps':reg_near/nsamp,'map_legal_path_bps':reg_map/nsamp,'legal_path_mass_bps':reg_mass/nsamp,'map_gain_vs_fullfile_sz3_bps':FULL_SZ3_BPS/(reg_map/nsamp),'mass_gain_vs_fullfile_sz3_bps':FULL_SZ3_BPS/(reg_mass/nsamp),'strict_2x_target_bps':TARGET_BPS})
        agg=[r for r in rows if r.get('aggregate')]; totaln=sum(r['samples'] for r in agg)
        out={'shape':[30000,6912],'stds':stds,'eps':eps,'lattice_h_over_eps':FAC,'regions':list(REGIONS),'channels_per_region':NCH,'betas':list(BETAS),'verified_fullfile_sz3_bps':FULL_SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,'aggregate':{'samples':totaln,'nearest_model_bps':sum(r['nearest_model_bps']*r['samples'] for r in agg)/totaln,'map_legal_path_bps':sum(r['map_legal_path_bps']*r['samples'] for r in agg)/totaln,'legal_path_mass_bps':sum(r['legal_path_mass_bps']*r['samples'] for r in agg)/totaln},'rows':rows,'scope':'Decoder-honest probability-shaped reconstruction audit. r0/r1 are the only model source; beta is selected by r0->r1 validation and final counts use r0+r1. Target samples are interval constraints on a fine h=epsilon lattice. Exact Viterbi chooses the minimum arithmetic-codelength legal path using causal same-channel state plus already-decoded left-channel side information. A forward partition sum separately reports -log2 total probability mass of every legal path, which is an enumerative/set-code existence rate rather than yet a byte container. No target-trained probabilities.'}
        a=out['aggregate']; a['map_gain_vs_fullfile_sz3']=FULL_SZ3_BPS/a['map_legal_path_bps']; a['mass_gain_vs_fullfile_sz3']=FULL_SZ3_BPS/a['legal_path_mass_bps']; a['map_ratio_to_2x_target']=a['map_legal_path_bps']/TARGET_BPS; a['mass_ratio_to_2x_target']=a['legal_path_mass_bps']/TARGET_BPS
        print(json.dumps({'aggregate':a,'region_aggregates':agg},indent=2),flush=True); json.dump(out,open('imperial_probability_shaped_legal_paths.json','w'),indent=2)
    finally:
        for f in fs:f.close()
if __name__=='__main__': main(sys.argv[1:])
