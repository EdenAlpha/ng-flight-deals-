import collections,json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;P=32;TB=1024
REGIONS=(("hard",512),("easy",2304))
COARSE_STEPS=(384,768,1024)
FINE_STEPS=(96,160,224,267)
SMOOTH=0.25;SELECTOR_BYTES=2


def logadd2(x,y):
    if x==-math.inf:return y
    if y==-math.inf:return x
    if y>x:x,y=y,x
    d=y-x
    return x if d<-60 else x+math.log2(1.0+2.0**d)


def arithmetic_bytes(K):
    oldc,oldnt=a.C,a.NT;a.C=K.shape[0];a.NT=K.shape[1]
    try:n,_,_,D=a.arithmetic(K)
    finally:a.C=oldc;a.NT=oldnt
    if not np.array_equal(D,K):raise RuntimeError('arithmetic decode mismatch')
    return int(n)


def coarse_path(X,co,S):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32)
    aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for t in range(NT):
        if t<P:pred=np.zeros(C,np.int32)
        else:pred=np.rint(aa+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
        k=np.rint((X[:,t]-pred.astype(np.float64))/S).astype(np.int32)
        K[:,t]=k;R[:,t]=(pred.astype(np.int64)+S*k.astype(np.int64)).astype(np.int32)
    return R,K


def decode_coarse(K,co,S):
    R=np.zeros(K.shape,np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for t in range(NT):
        if t<P:pred=np.zeros(C,np.int32)
        else:pred=np.rint(aa+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
        R[:,t]=(pred.astype(np.int64)+S*K[:,t].astype(np.int64)).astype(np.int32)
    return R


def make_prior(Kp,step):
    glo=collections.Counter();one={};two={};n=0
    for c in range(C):
        seq=[int(v) for v in Kp[c]];glo.update(seq);n+=len(seq)
        for i in range(1,len(seq)):one.setdefault(seq[i-1],collections.Counter())[seq[i]]+=1
        for i in range(2,len(seq)):two.setdefault((seq[i-2],seq[i-1]),collections.Counter())[seq[i]]+=1
    A=2*int(math.ceil(90000.0/step))+9;cache={}
    def sm(c,k):
        z=sum(c.values());return (c.get(int(k),0)+SMOOTH)/(z+SMOOTH*A)
    def pg(k):return (glo.get(int(k),0)+SMOOTH)/(n+SMOOTH*A)
    def p1(p,k):
        c=one.get(int(p));return pg(k) if c is None else .8*sm(c,k)+.2*pg(k)
    def p2(p2v,p1v,k):
        key=(int(p2v),int(p1v),int(k));z=cache.get(key)
        if z is not None:return z
        c=two.get((int(p2v),int(p1v)))
        z=p1(p1v,k) if c is None else .7*sm(c,k)+.2*p1(p1v,k)+.1*pg(k)
        cache[key]=z;return z
    return p2


def tail_mass(x,p,eps,step,kprefix,p2):
    lo=np.ceil((x-eps-p)/step-1e-12).astype(np.int32);hi=np.floor((x+eps-p)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError(('empty legal set',step))
    near=np.rint((x-p)/step).astype(np.int32)
    if np.any(near<lo)|np.any(near>hi):raise RuntimeError(('nearest illegal',step))
    aa=int(kprefix[-2]);bb=int(kprefix[-1]);nlog=0.0
    for k in near:
        lp=math.log2(max(p2(aa,bb,int(k)),1e-300));nlog-=lp;aa,bb=bb,int(k)
    states={(int(kprefix[-2]),int(kprefix[-1])):(0.0,0.0)}
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
    return nlog,float(-lv),float(-lm),float(np.mean(mult)),float(np.mean(mult>1)),int(mult.max())


def candidate(X,co,eps,S,step):
    Cpath,Kc=coarse_path(X,co,S);cb=arithmetic_bytes(Kc);Cd=decode_coarse(Kc,co,S)
    if not np.array_equal(Cd,Cpath):raise RuntimeError((S,step,'coarse replay'))
    Kp=np.rint((X[:,:TRAIN]-Cpath[:,:TRAIN].astype(np.float64))/step).astype(np.int32)
    Rp=Cpath[:,:TRAIN].astype(np.float64)+step*Kp.astype(np.float64);pme=float(np.max(np.abs(X[:,:TRAIN]-Rp)))
    if pme>eps*(1+1e-12):raise RuntimeError((S,step,'prefix hard',pme,eps))
    pb=arithmetic_bytes(Kp)
    # arithmetic() charges the same fixed AR-model allowance in both streams; only the coarse stream needs it.
    side_bytes=cb+max(0,pb-a.MODEL_BYTES)+SELECTOR_BYTES
    prior=make_prior(Kp,step);nb=mb=sb=0.0;means=[];multis=[];mx=1
    for c in range(C):
        n,m,s,mean,multi,mmax=tail_mass(X[c,TRAIN:],Cpath[c,TRAIN:].astype(np.float64),eps,step,Kp[c],prior)
        nb+=n;mb+=m;sb+=s;means.append(mean);multis.append(multi);mx=max(mx,mmax)
    return {'coarse_step':int(S),'fine_step':int(step),'coarse_bytes':int(cb),'prefix_bytes_raw':int(pb),'charged_side_bytes':int(side_bytes),
            'coarse_bps':8*cb/X.size,'charged_prefix_extra_bps':8*(side_bytes-cb)/X.size,
            'nearest_total_bps':(8*side_bytes+nb)/X.size,'map_total_bps':(8*side_bytes+mb)/X.size,'legal_set_mass_total_bps':(8*side_bytes+sb)/X.size,
            'set_gain_vs_nearest_total':(8*side_bytes+nb)/(8*side_bytes+sb),'mean_legal_states':float(np.mean(means)),
            'multi_fraction':float(np.mean(multis)),'max_legal_states':int(mx),'prefix_maxerr':pme,
            'coarse_rmse_over_eps':float(np.sqrt(np.mean((X-Cpath.astype(np.float64))**2))/eps)}


def region(name,c0,d,eps):
    X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=a.fits(X)
    sz=0
    for t0 in range(0,NT,TB):n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
    target=(8.0*sz/X.size)/2.0;rows=[]
    for S in COARSE_STEPS:
        for step in FINE_STEPS:
            q=candidate(X,co,eps,S,step);q['mass_ratio_to_2x_target']=q['legal_set_mass_total_bps']/target;q['map_ratio_to_2x_target']=q['map_total_bps']/target
            rows.append(q);print(json.dumps({'region':name,'candidate':q},indent=2),flush=True)
    best=min(rows,key=lambda r:r['legal_set_mass_total_bps']);bestmap=min(rows,key=lambda r:r['map_total_bps'])
    return {'region':name,'c0':c0,'samples':int(X.size),'eps':float(eps),'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'local_2x_target_bps':target,'best_mass':best,'best_map':bestmap,'candidates':rows}


def main(path):
    a.C=C;a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[region(n,c,d,eps) for n,c in REGIONS]
    for r in rows:print(json.dumps({'summary':r},indent=2),flush=True)
    json.dump({'rows':rows,'scope':'Paid dense-side-information legal-set existence gate. A self-contained Huber AR32 coarse trajectory is generated and recursively decoded using only its own coarse reconstruction state, at coarse innovation steps 384/768/1024; its exact K stream and the shared AR model are arithmetic-coded and fully charged. This coarse trajectory is fixed side information and never depends on the fine reconstruction. The first 1024 fine residuals around that decoded coarse path are nearest-quantized at steps 96/160/224/267, transmitted/decoded and charged (without double-charging the already-paid AR model), and only that paid prefix trains a shared order-2 fine-residual prior. Exact forward DP then sums the probability mass of every legal fine residual sequence over the remaining 3072 samples; exact MAP and nearest rates are also reported. This differs from PR425 because no one-repair-symbol tail is transmitted: the coarse layer is used only to define a decoder-known proposal for legal-set/binning coding. Matched SZ3 runs on full hard/easy 128x4096. No AI. Draft/do not merge.'},open('imperial_coarse_ar_sideinfo_legal_set_mass.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
