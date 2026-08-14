import collections,json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;TB=1024
REGIONS=(("hard",512),("easy",2304))
STEPS=(96,128,160,224,267)
SMOOTH=0.25
SELECTOR_BYTES=1


def logadd2(x,y):
    if x==-math.inf:return y
    if y==-math.inf:return x
    if y>x:x,y=y,x
    d=y-x
    if d<-60:return x
    return x+math.log2(1.0+2.0**d)


def support(step):
    lo=int(math.floor(-32768.0/step))-2
    hi=int(math.ceil(32767.0/step))+2
    return lo,hi,hi-lo+1


def build_counter(seq):
    glo=collections.Counter();one={};two={};n=0
    for q in seq:
        q=[int(v) for v in q]
        glo.update(q);n+=len(q)
        for i in range(1,len(q)):one.setdefault(q[i-1],collections.Counter())[q[i]]+=1
        for i in range(2,len(q)):two.setdefault((q[i-2],q[i-1]),collections.Counter())[q[i]]+=1
    return glo,one,two,n


def make_prior(seqs,A):
    glo,one,two,n=build_counter(seqs);cache={}
    def smooth(c,k):
        z=sum(c.values());return (c.get(int(k),0)+SMOOTH)/(z+SMOOTH*A)
    def pg(k):return (glo.get(int(k),0)+SMOOTH)/(n+SMOOTH*A)
    def p1(p,k):
        c=one.get(int(p));return pg(k) if c is None else 0.80*smooth(c,k)+0.20*pg(k)
    def p2(p2v,p1v,k):
        key=(int(p2v),int(p1v),int(k));z=cache.get(key)
        if z is not None:return z
        c=two.get((int(p2v),int(p1v)))
        z=p1(p1v,k) if c is None else 0.70*smooth(c,k)+0.20*p1(p1v,k)+0.10*pg(k)
        cache[key]=z;return z
    return p2


def legal_sets(x,eps,step):
    lo=np.ceil((x-eps)/step-1e-12).astype(np.int32)
    hi=np.floor((x+eps)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError(('empty legal interval',step,int(np.sum(lo>hi))))
    return lo,hi


def tail_mass(x,eps,step,qprefix,p2):
    lo,hi=legal_sets(x,eps,step)
    near=np.rint(x/step).astype(np.int32)
    if np.any(near<lo)|np.any(near>hi):raise RuntimeError(('nearest illegal',step))
    p2v=int(qprefix[-2]);p1v=int(qprefix[-1])
    nearest_log=0.0
    aa=p2v;bb=p1v
    for k in near:
        pr=max(p2(aa,bb,int(k)),1e-300);nearest_log+=math.log2(pr);aa,bb=bb,int(k)
    states={(p2v,p1v):(0.0,0.0)}
    mult=hi.astype(np.int64)-lo.astype(np.int64)+1
    for t in range(len(x)):
        nxt={}
        for (k2,k1),(lm,lv) in states.items():
            for k in range(int(lo[t]),int(hi[t])+1):
                lp=math.log2(max(p2(k2,k1,k),1e-300));key=(k1,int(k));cm=lm+lp;cv=lv+lp
                if key in nxt:
                    om,ov=nxt[key];nxt[key]=(logadd2(om,cm),max(ov,cv))
                else:nxt[key]=(cm,cv)
        states=nxt
    lm=-math.inf;lv=-math.inf
    for m,v in states.values():lm=logadd2(lm,m);lv=max(lv,v)
    return {'nearest_bits':float(-nearest_log),'map_bits':float(-lv),'mass_bits':float(-lm),
            'mean_legal_states':float(np.mean(mult)),'multi_fraction':float(np.mean(mult>1)),'max_legal_states':int(mult.max())}


def prefix_bytes(Q):
    oldc,oldnt=a.C,a.NT;a.C=C;a.NT=TRAIN
    try:
        n,_,_,D=a.arithmetic(Q)
    finally:
        a.C=oldc;a.NT=oldnt
    if not np.array_equal(D,Q):raise RuntimeError('prefix decode')
    return int(n)


def region(name,c0,d,eps):
    X=np.asarray(d[:NT,c0:c0+C],np.float64).T
    sz=0
    for t0 in range(0,NT,TB):
        n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
    target_bps=(8.0*sz/X.size)/2.0
    rows=[]
    for step in STEPS:
        Qp=np.rint(X[:,:TRAIN]/step).astype(np.int32)
        Rp=Qp.astype(np.float64)*step
        pme=float(np.max(np.abs(X[:,:TRAIN]-Rp)))
        if pme>eps*(1+1e-12):raise RuntimeError((name,step,'prefix hard',pme,eps))
        pb=prefix_bytes(Qp)
        _,_,A=support(step)
        models={
            'shared':make_prior([Qp[c] for c in range(C)],A),
        }
        # Per-channel priors are derived independently from each decoded prefix.
        per=[make_prior([Qp[c]],A) for c in range(C)]
        for mode in ('shared','per_channel'):
            nb=mb=sb=0.0;means=[];multis=[];mx=0
            for c in range(C):
                prior=models['shared'] if mode=='shared' else per[c]
                z=tail_mass(X[c,TRAIN:],eps,step,Qp[c],prior)
                nb+=z['nearest_bits'];mb+=z['map_bits'];sb+=z['mass_bits'];means.append(z['mean_legal_states']);multis.append(z['multi_fraction']);mx=max(mx,z['max_legal_states'])
            selbits=8*SELECTOR_BYTES
            rr={'step':int(step),'model':mode,'prefix_bytes':pb,'prefix_bps':8.0*pb/X.size,
                'nearest_total_bps':(8*pb+nb+selbits)/X.size,
                'map_total_bps':(8*pb+mb+selbits)/X.size,
                'legal_set_mass_total_bps':(8*pb+sb+selbits)/X.size,
                'mass_ratio_to_2x_target':((8*pb+sb+selbits)/X.size)/target_bps,
                'map_ratio_to_2x_target':((8*pb+mb+selbits)/X.size)/target_bps,
                'set_gain_vs_nearest_total':(8*pb+nb+selbits)/(8*pb+sb+selbits),
                'mean_legal_states':float(np.mean(means)),'multi_fraction':float(np.mean(multis)),'max_legal_states':int(mx),'prefix_maxerr':pme}
            rows.append(rr);print(json.dumps({'region':name,'candidate':rr},indent=2),flush=True)
    best=min(rows,key=lambda r:r['legal_set_mass_total_bps'])
    bestmap=min(rows,key=lambda r:r['map_total_bps'])
    return {'region':name,'c0':c0,'channels':C,'samples':int(X.size),'eps':float(eps),'sz3_bytes':sz,'sz3_bps':8.0*sz/X.size,'local_2x_target_bps':target_bps,'best_mass':best,'best_map':bestmap,'candidates':rows}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        rows=[region(name,c0,d,eps) for name,c0 in REGIONS]
    for r in rows:print(json.dumps({'summary':r},indent=2),flush=True)
    json.dump({'rows':rows,'scope':'Deployable-side legal-set existence gate with NO source oracle predictor and NO target-trained probability model. A legal fixed source lattice with step in {96,128,160,224,267} is used. The first 1024 samples of every 128-channel region are nearest-quantized, actually transmitted and exactly decoded with the existing cold-start arithmetic backend, and their byte cost is charged. Only that decoded prefix is then used to derive either a shared or per-channel order-2 categorical backoff prior. For the remaining 3072 samples, exact forward dynamic programming sums the probability mass of every source-lattice trajectory inside the unchanged +/-epsilon intervals; exact Viterbi/MAP and nearest-path model rates are also reported. One selector byte is charged. The tail mass is an existence-rate ceiling rather than a byte container, but unlike PR473 its proposal model is decoder-derivable from paid prefix data and its reconstruction uses no free future/all-sensor predictor. Matched SZ3 is rerun on the full 128x4096 region. No AI. Draft/do not merge.'},open('imperial_prefix_trained_source_legal_set_mass.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
