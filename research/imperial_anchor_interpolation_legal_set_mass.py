import collections,json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;TB=1024;EPS_ANCHOR_STEP=267
REGIONS=(("hard",512),("easy",2304))
SPACINGS=(16,32,64)
STEPS=(96,128,160,224,267)
SMOOTH=0.25;SELECTOR_BYTES=2


def logadd2(x,y):
    if x==-math.inf:return y
    if y==-math.inf:return x
    if y>x:x,y=y,x
    d=y-x
    if d<-60:return x
    return x+math.log2(1.0+2.0**d)


def arithmetic_bytes(K):
    oldc,oldnt=a.C,a.NT;a.C=K.shape[0];a.NT=K.shape[1]
    try:n,_,_,D=a.arithmetic(K)
    finally:a.C=oldc;a.NT=oldnt
    if not np.array_equal(D,K):raise RuntimeError('arithmetic decode mismatch')
    return int(n)


def anchors_for_spacing(X,spacing):
    idx=list(range(0,NT,spacing))
    if idx[-1]!=NT-1:idx.append(NT-1)
    idx=np.asarray(idx,np.int32)
    Q=np.rint(X[:,idx]/EPS_ANCHOR_STEP).astype(np.int32)
    R=Q.astype(np.float64)*EPS_ANCHOR_STEP
    return idx,Q,R


def interpolation(idx,R):
    P=np.empty((C,NT),np.float64)
    for j in range(len(idx)-1):
        l=int(idx[j]);r=int(idx[j+1]);den=float(r-l)
        w=np.arange(r-l+1,dtype=np.float64)/den
        P[:,l:r+1]=R[:,j,None]*(1.0-w[None,:])+R[:,j+1,None]*w[None,:]
    return P


def make_prior(Kprefix,step):
    # Shared order-2 prior trained only from paid/decoded prefix residuals.
    glo=collections.Counter();one={};two={};n=0
    for c in range(C):
        seq=[int(v) for v in Kprefix[c]]
        glo.update(seq);n+=len(seq)
        for i in range(1,len(seq)):one.setdefault(seq[i-1],collections.Counter())[seq[i]]+=1
        for i in range(2,len(seq)):two.setdefault((seq[i-2],seq[i-1]),collections.Counter())[seq[i]]+=1
    # Public conservative support from int16 source span plus interpolated anchors.
    A=2*int(math.ceil(70000.0/step))+9
    cache={}
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


def interval_mass(x,p,eps,step,p2):
    if len(x)==0:return 0.0,0.0,0.0,1.0,0.0,1
    lo=np.ceil((x-eps-p)/step-1e-12).astype(np.int32)
    hi=np.floor((x+eps-p)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError(('empty legal interval',step,int(np.sum(lo>hi))))
    near=np.rint((x-p)/step).astype(np.int32)
    if np.any(near<lo)|np.any(near>hi):raise RuntimeError(('nearest illegal',step))
    # Every anchor-bounded interval is an independent shared-codebook unit.
    nearest=0.0;aa=0;bb=0
    for k in near:
        lp=math.log2(max(p2(aa,bb,int(k)),1e-300));nearest-=lp;aa,bb=bb,int(k)
    states={(0,0):(0.0,0.0)}
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
    for mm,vv in states.values():lm=logadd2(lm,mm);lv=max(lv,vv)
    mult=hi.astype(np.int64)-lo.astype(np.int64)+1
    return nearest,float(-lv),float(-lm),float(np.mean(mult)),float(np.mean(mult>1)),int(mult.max())


def candidate(X,eps,spacing,step):
    idx,Qa,Ra=anchors_for_spacing(X,spacing)
    ame=float(np.max(np.abs(X[:,idx]-Ra)))
    if ame>eps*(1+1e-12):raise RuntimeError((spacing,step,'anchor hard',ame,eps))
    abytes=arithmetic_bytes(Qa)
    P=interpolation(idx,Ra)
    Kp=np.rint((X[:,:TRAIN]-P[:,:TRAIN])/step).astype(np.int32)
    # Anchor positions are already paid separately; force their residual symbol to zero.
    for t in idx[idx<TRAIN]:Kp[:,int(t)]=0
    Rp=P[:,:TRAIN]+step*Kp.astype(np.float64)
    for t in idx[idx<TRAIN]:Rp[:,int(t)]=P[:,int(t)]
    pme=float(np.max(np.abs(X[:,:TRAIN]-Rp)))
    if pme>eps*(1+1e-12):raise RuntimeError((spacing,step,'prefix hard',pme,eps))
    pbytes=arithmetic_bytes(Kp)
    prior=make_prior(Kp,step)
    nb=mb=sb=0.0;means=[];multis=[];mx=1;tailn=0
    for c in range(C):
        for j in range(len(idx)-1):
            l=int(idx[j]);r=int(idx[j+1])
            st=max(TRAIN,l+1);en=r
            if en<=st:continue
            n,m,s,mean,multi,mmax=interval_mass(X[c,st:en],P[c,st:en],eps,step,prior)
            nb+=n;mb+=m;sb+=s;tailn+=en-st;means.append(mean);multis.append(multi);mx=max(mx,mmax)
    # Tail excludes paid anchors; all other post-prefix samples are represented by set coding.
    total_bits=8*(abytes+pbytes+SELECTOR_BYTES)+sb
    map_bits=8*(abytes+pbytes+SELECTOR_BYTES)+mb
    near_bits=8*(abytes+pbytes+SELECTOR_BYTES)+nb
    return {'spacing':int(spacing),'step':int(step),'anchor_count':int(len(idx)),'anchor_bytes':int(abytes),'prefix_bytes':int(pbytes),
            'anchor_bps':8*abytes/X.size,'prefix_bps':8*pbytes/X.size,'tail_samples':int(tailn),
            'nearest_total_bps':near_bits/X.size,'map_total_bps':map_bits/X.size,'legal_set_mass_total_bps':total_bits/X.size,
            'set_gain_vs_nearest_total':near_bits/total_bits,'mean_legal_states':float(np.mean(means)) if means else 1.0,
            'multi_fraction':float(np.mean(multis)) if multis else 0.0,'max_legal_states':int(mx),'anchor_maxerr':ame,'prefix_maxerr':pme}


def region(name,c0,d,eps):
    X=np.asarray(d[:NT,c0:c0+C],np.float64).T
    sz=0
    for t0 in range(0,NT,TB):n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
    target=(8.0*sz/X.size)/2.0;rows=[]
    for spacing in SPACINGS:
        for step in STEPS:
            q=candidate(X,eps,spacing,step);q['mass_ratio_to_2x_target']=q['legal_set_mass_total_bps']/target;q['map_ratio_to_2x_target']=q['map_total_bps']/target
            rows.append(q);print(json.dumps({'region':name,'candidate':q},indent=2),flush=True)
    best=min(rows,key=lambda r:r['legal_set_mass_total_bps']);bestmap=min(rows,key=lambda r:r['map_total_bps'])
    return {'region':name,'c0':c0,'samples':int(X.size),'eps':float(eps),'sz3_bytes':int(sz),'sz3_bps':8.0*sz/X.size,'local_2x_target_bps':target,'best_mass':best,'best_map':bestmap,'candidates':rows}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        rows=[region(name,c0,d,eps) for name,c0 in REGIONS]
    for r in rows:print(json.dumps({'summary':r},indent=2),flush=True)
    json.dump({'rows':rows,'scope':'Paid-anchor legal-set existence gate. Sparse source anchors every 16/32/64 samples (plus final sample) are nearest-quantized on the legal step267 source lattice, actually arithmetic-coded/decoded and fully charged. Decoder-known linear interpolation between those paid reconstructed anchors supplies noncausal interior predictions. The first 1024 residual samples are then nearest-quantized on residual steps 96/128/160/224/267, actually transmitted/decoded and charged, and only this paid prefix trains a shared order-2 residual prior. For post-prefix interiors, exact forward DP sums the probability mass of EVERY residual-lattice sequence inside each unchanged +/-epsilon interval, resetting the shared random-codebook unit at each anchor interval; exact MAP and nearest model rates are also reported. Anchors are not double-charged in the tail. This is still an existence-rate ceiling, not yet a byte container, but unlike PR473 all future information comes from paid decoder-known anchors and the proposal is trained only from paid prefix data. Matched SZ3 runs on full 128x4096 hard/easy regions. No AI. Draft/do not merge.'},open('imperial_anchor_interpolation_legal_set_mass.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
