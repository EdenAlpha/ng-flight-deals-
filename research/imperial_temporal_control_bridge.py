import json,sys
import h5py,numpy as np,zstandard as zstd
from numba import njit
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;SAFETY=1-1e-5;PHASES=4;ROUNDS=4
HFACTORS=(2.0,1.0);LAMBDAS=(0.0,0.25,1.0);POLS=(1,-1)
Z=zstd.ZstdCompressor(level=19)

@njit(cache=True)
def choose_chain(lo,hi,xodd,bound,h,phi,hcorr,pol,lam,kcost,D,maxs):
    na=lo.size;pc=np.full(maxs,1e300,np.float64);cc=np.full(maxs,1e300,np.float64);back=np.zeros((na,maxs),np.int8)
    for s in range(hi[0]-lo[0]+1):pc[s]=0.0
    for i in range(na-1):
        nsa=hi[i]-lo[i]+1;nsb=hi[i+1]-lo[i+1]+1
        for s in range(maxs):cc[s]=1e300
        hasodd=i<xodd.size
        for sb in range(nsb):
            qb=lo[i+1]+sb;best=1e300;bi=0
            for sa in range(nsa):
                qa=lo[i]+sa;c=pc[sa]+lam*abs((qb-qa)*h/hcorr)
                if hasodd:
                    # pol=+1 ordinary midpoint; pol=-1 is implicit Nyquist demodulation/remodulation.
                    mid=pol*(phi+0.5*h*(qa+qb))
                    k=int(np.rint((xodd[i]-mid)/hcorr));idx=k+D
                    c+=kcost[idx] if 0<=idx<kcost.size else 1e6
                if c<best:best=c;bi=sa
            cc[sb]=best;back[i+1,sb]=bi
        for s in range(maxs):pc[s]=cc[s]
    ns=hi[-1]-lo[-1]+1;sb=0;best=pc[0]
    for s in range(1,ns):
        if pc[s]<best:best=pc[s];sb=s
    q=np.empty(na,np.int32);q[-1]=lo[-1]+sb
    for i in range(na-1,0,-1):sb=back[i,sb];q[i-1]=lo[i-1]+sb
    return q

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return m,float(np.sqrt(max(0,ss/n-m*m)))

def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def legal(x,bound,h,phi):
    lo=np.ceil((x-bound-phi)/h-1e-12).astype(np.int32);hi=np.floor((x+bound-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal')
    return lo,hi

def encode_int(a):
    a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0;c=[]
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            c.append((len(Z.compress(np.ascontiguousarray(a).astype(dt).tobytes()))+24,'signed_'+dt.str));break
    zz=((a.astype(np.int64)<<1)^(a.astype(np.int64)>>63)).astype(np.uint64);mz=int(zz.max()) if zz.size else 0
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mz<=np.iinfo(dt).max:
            c.append((len(Z.compress(np.ascontiguousarray(zz).astype(dt).tobytes()))+24,'zigzag_'+dt.str));break
    nz=a!=0;sup=Z.compress(np.packbits(nz.astype(np.uint8),bitorder='little').tobytes());v=a[nz];vmn=int(v.min()) if v.size else 0;vmx=int(v.max()) if v.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if vmn>=np.iinfo(dt).min and vmx<=np.iinfo(dt).max:
            c.append((len(sup)+len(Z.compress(v.astype(dt).tobytes()))+48,'sparse_'+dt.str));break
    return min(c)

def field_reps(q):
    c=[]
    def add(name,a):
        b,r=encode_int(a);c.append((b+16,name+'_'+r))
    add('raw',q);dt=q.copy();dt[:,1:]-=q[:,:-1];add('dt',dt);ds=q.copy();ds[1:]-=q[:-1];add('ds',ds)
    L=q.copy();L[1:,1:]=q[1:,1:]-q[:-1,1:]-q[1:,:-1]+q[:-1,:-1];add('lorenzo',L)
    return min(c),sorted(c)

def k_model(K,D=48):
    k=K.ravel();cnt=np.bincount(np.clip(k,-D,D)+D,minlength=2*D+1).astype(np.float64)+.25;p=cnt/cnt.sum();return -np.log2(p),D

def solve(X,bound,hfactor,phase,lam,pol):
    h=hfactor*bound;hcorr=2*bound;phi=h*phase/PHASES
    at=np.r_[np.arange(0,T,2,dtype=np.int32),T-1];ot=np.arange(1,T-1,2,dtype=np.int32)
    # For pol=-1, the transmitted even samples are unchanged by (-1)^t, so their legal intervals are the same.
    lo,hi=legal(X[:,at],bound,h,phi);maxs=int(np.max(hi-lo+1));Q=np.empty((C,len(at)),np.int32)
    if maxs>8:raise RuntimeError(('states',maxs))
    D=48;kcost=2+np.log2(1+np.abs(np.arange(-D,D+1,dtype=np.float64)));kcost[D]=0;kcost[D-1]=kcost[D+1]=1
    for _ in range(ROUNDS):
        for c in range(C):Q[c]=choose_chain(lo[c],hi[c],X[c,ot],bound,h,phi,hcorr,pol,lam,kcost,D,maxs)
        mid=pol*(phi+0.5*h*(Q[:,:-2]+Q[:,1:-1]));K=np.rint((X[:,ot]-mid)/hcorr).astype(np.int32);kcost,D=k_model(K,D)
    R=np.empty_like(X);R[:,at]=phi+h*Q;R[:,ot]=pol*(phi+0.5*h*(Q[:,:-2]+Q[:,1:-1]))+hcorr*K
    me=float(np.max(np.abs(X-R)));ar,all_ar=field_reps(Q);kr=encode_int(K);tot=ar[0]+kr[0]+96
    return {'h_over_eps':hfactor,'phase':phase,'lambda':lam,'polarity':pol,'bytes':tot,'anchor_bytes':ar[0],'correction_bytes':kr[0],'anchor_rep':ar[1],'correction_rep':kr[1],'mean_anchor_legal_states':float(np.mean(hi-lo+1)),'correction_nonzero_fraction':float(np.mean(K!=0)),'correction_abs1_fraction':float(np.mean(np.abs(K)==1)),'maxerr':me,'all_anchor_reps':all_ar}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY
        specs=[('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392)];rows=[];tiles=[]
        for name,t0,c0 in specs:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);tiles.append({'tile':name,'sz3':sb,'raw':X.size*2})
            for hf in HFACTORS:
                for ph in range(PHASES):
                    for lam in LAMBDAS:
                        for pol in POLS:
                            r=solve(X,bound,hf,ph,lam,pol)
                            if r['maxerr']>eps*(1+5e-6):raise RuntimeError(('hard',name,r['maxerr'],eps))
                            r.update({'tile':name,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r)
        combos=[]
        for hf in HFACTORS:
            for ph in range(PHASES):
                for lam in LAMBDAS:
                    for pol in POLS:
                        rr=[r for r in rows if r['h_over_eps']==hf and r['phase']==ph and r['lambda']==lam and r['polarity']==pol];b=sum(r['bytes'] for r in rr);s=sum(t['sz3'] for t in tiles)
                        combos.append({'h_over_eps':hf,'phase':ph,'lambda':lam,'polarity':pol,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'median_anchor_legal_states':float(np.median([r['mean_anchor_legal_states'] for r in rr])),'anchor_bytes':sum(r['anchor_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr)})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'bound':bound,'combos':combos,'rows':rows,'scope':'Temporal control bridge. Every other time sample is transmitted as a legal lattice state; intervening samples are derived by ordinary or alternating-sign midpoint plus exact 2eps correction. Fine anchor choices are selected by exact per-channel chain DP to minimize learned missing-sample correction cost. One fixed definition across four tiles; all bytes counted and hard error verified.'}
        print(json.dumps({'best':combos[:12]},indent=2),flush=True);json.dump(out,open('imperial_temporal_control_bridge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
