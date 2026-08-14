import collections,json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_spatiotemporal_super_oracle as supero

C=8; NT=4096; H=32; TB=1024
STEPS=(64,96,128,160,192,224,256,267)
REGIONS=(("hard",512),("easy",2304))
a.NT=NT
SMOOTH=0.25


def logadd2(x,y):
    if x == -math.inf: return y
    if y == -math.inf: return x
    if y > x: x,y=y,x
    d=y-x
    if d < -60.0: return x
    return x + math.log2(1.0 + 2.0**d)


def train_prior(q, alphabet):
    """Deliberately free target-trained per-channel order-2 backoff prior."""
    glo=collections.Counter(int(v) for v in q)
    one={}; two={}
    for i in range(1,len(q)):
        p=int(q[i-1]); k=int(q[i])
        one.setdefault(p,collections.Counter())[k]+=1
    for i in range(2,len(q)):
        key=(int(q[i-2]),int(q[i-1])); k=int(q[i])
        two.setdefault(key,collections.Counter())[k]+=1
    A=int(alphabet); ng=len(q); cache={}
    def smoothed(counter,k):
        n=sum(counter.values())
        return (counter.get(int(k),0)+SMOOTH)/(n+SMOOTH*A)
    def pg(k):
        return (glo.get(int(k),0)+SMOOTH)/(ng+SMOOTH*A)
    def p1(prev,k):
        c=one.get(int(prev))
        if c is None: return pg(k)
        return 0.80*smoothed(c,k)+0.20*pg(k)
    def p2(p2v,p1v,k):
        key=(int(p2v),int(p1v),int(k)); z=cache.get(key)
        if z is not None:return z
        c=two.get((int(p2v),int(p1v)))
        if c is None:z=p1(p1v,k)
        else:z=0.70*smoothed(c,k)+0.20*p1(p1v,k)+0.10*pg(k)
        cache[key]=z
        return z
    return pg,p1,p2


def legal_sets(x,p,eps,step):
    lo=np.ceil((x-eps-p)/step-1e-12).astype(np.int32)
    hi=np.floor((x+eps-p)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError(('empty legal interval',step,int(np.sum(lo>hi))))
    return lo,hi


def channel_mass(x,p,eps,step):
    lo,hi=legal_sets(x,p,eps,step)
    nearest=np.rint((x-p)/step).astype(np.int32)
    if np.any(nearest<lo) or np.any(nearest>hi):raise RuntimeError(('nearest not legal',step))
    amin=int(lo.min());amax=int(hi.max());A=amax-amin+1
    pg,p1,p2=train_prior(nearest,A)
    ln=math.log2(pg(int(nearest[0])))
    if len(nearest)>1:ln+=math.log2(p1(int(nearest[0]),int(nearest[1])))
    for t in range(2,len(nearest)):
        ln+=math.log2(p2(int(nearest[t-2]),int(nearest[t-1]),int(nearest[t])))

    states={}
    for k in range(int(lo[0]),int(hi[0])+1):
        z=math.log2(pg(k));states[int(k)]=(z,z)
    if len(nearest)>1:
        nxt={}
        for pk,(lm,lv) in states.items():
            for k in range(int(lo[1]),int(hi[1])+1):
                z=math.log2(p1(pk,k));key=(pk,int(k));candm=lm+z;candv=lv+z
                if key in nxt:
                    om,ov=nxt[key];nxt[key]=(logadd2(om,candm),max(ov,candv))
                else:nxt[key]=(candm,candv)
        states=nxt
    for t in range(2,len(nearest)):
        nxt={}
        for (k2,k1),(lm,lv) in states.items():
            for k in range(int(lo[t]),int(hi[t])+1):
                z=math.log2(p2(k2,k1,k));key=(k1,int(k));candm=lm+z;candv=lv+z
                if key in nxt:
                    om,ov=nxt[key];nxt[key]=(logadd2(om,candm),max(ov,candv))
                else:nxt[key]=(candm,candv)
        states=nxt
    lm=-math.inf;lv=-math.inf
    for m,v in states.values():lm=logadd2(lm,m);lv=max(lv,v)
    mult=(hi.astype(np.int64)-lo.astype(np.int64)+1)
    return {'nearest_bits':float(-ln),'map_bits':float(-lv),'mass_bits':float(-lm),
            'mean_legal_states':float(np.mean(mult)),'multi_fraction':float(np.mean(mult>1)),
            'max_legal_states':int(mult.max()),'alphabet':int(A)}


def region(region,c0,d,eps):
    X=np.asarray(d[:NT,c0:c0+C],np.float64).T
    Xfull=np.asarray(d[:NT,c0:c0+128],np.float64).T
    Pfull,_,_,_,_,_=supero.oracle_k(Xfull);P=Pfull[:C]
    rows=[]
    for step in STEPS:
        nb=mb=sb=0.0;means=[];multis=[];mx=0;alph=[]
        for c in range(C):
            z=channel_mass(X[c,H:NT-H],P[c,H:NT-H],eps,step)
            nb+=z['nearest_bits'];mb+=z['map_bits'];sb+=z['mass_bits'];means.append(z['mean_legal_states']);multis.append(z['multi_fraction']);mx=max(mx,z['max_legal_states']);alph.append(z['alphabet'])
        denom=float(X.size)
        rr={'step':step,'nearest_model_bps':nb/denom,'map_model_bps':mb/denom,'legal_set_mass_bps':sb/denom,
            'set_gain_vs_nearest_model':float(nb/sb),'map_gain_vs_nearest_model':float(nb/mb),
            'mean_legal_states':float(np.mean(means)),'multi_fraction':float(np.mean(multis)),'max_legal_states':int(mx),'mean_alphabet':float(np.mean(alph))}
        rows.append(rr);print(json.dumps({'region':region,'candidate':rr},indent=2),flush=True)

    _,K,R,_,_,_=supero.oracle_k(Xfull);K=K[:C];R=R[:C]
    ob,_,_,Kd=a.arithmetic(K)
    if not np.array_equal(Kd,K):raise RuntimeError((region,'oracle K decode'))
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+1e-12):raise RuntimeError((region,'oracle hard',me,eps))
    sz=0
    for t0 in range(0,NT,TB):
        n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
    target_bps=(8*sz/X.size)/2.0
    for r in rows:r['ratio_to_local_2x_target']=float(r['legal_set_mass_bps']/target_bps)
    best=min(rows,key=lambda r:r['legal_set_mass_bps'])
    return {'region':region,'c0':c0,'channels':C,'samples':int(X.size),'eps':float(eps),'sz3_bps':8*sz/X.size,'local_2x_target_bps':target_bps,
            'super_oracle_step267_bps':8*ob/X.size,'super_oracle_maxerr':me,'best':best,'candidates':rows}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        rows=[region(name,c0,d,eps) for name,c0 in REGIONS]
    for r in rows:print(json.dumps({'summary':r},indent=2),flush=True)
    json.dump({'rows':rows,'scope':'Extremely generous legal-set probability-mass ceiling. The predictor is the impossible PR469 true-past/true-future/all-other-sensors target-fitted predictor and is supplied free. For each dense reconstruction lattice step, a per-channel order-2 categorical backoff prior is trained on the COMPLETE target nearest-K sequence and supplied free. Exact forward dynamic programming sums the probability of EVERY K sequence whose reconstruction lies in every unchanged +/-epsilon interval. This is an existence-rate ceiling, not a constructive byte codec. If even this target-trained free-model/free-predictor set mass stays above local 2x SZ3 on hard Imperial, ordinary dense-lattice legal-set coding cannot supply the missing factor. No AI. Draft/do not merge.'},open('imperial_super_oracle_legal_set_mass.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
