import json,sys,math
import h5py
import numpy as np
import zstandard as zstd
from numba import njit
from pysz import sz,szConfig,szErrorBoundMode

T=1024;C=128;SAFETY=1-1e-5;ZC=zstd.ZstdCompressor(level=19)
HFACT=(1.0,0.5)
SEEDS=('empirical','laplace05','laplace15','laplace4','spike')
ROUNDS=5

@njit(cache=True)
def viterbi_box(lo,hi,cost,D,maxs):
    n=lo.size
    back=np.zeros((n,maxs),np.int16)
    pc=np.full(maxs,1e300,np.float64);cc=np.full(maxs,1e300,np.float64)
    ps=int(hi[0]-lo[0]+1)
    for i in range(ps):pc[i]=0.0
    for t in range(1,n):
        cs=int(hi[t]-lo[t]+1);pps=int(hi[t-1]-lo[t-1]+1)
        for j in range(maxs):cc[j]=1e300
        for j in range(cs):
            q=int(lo[t]+j);best=1e300;bi=0
            for i in range(pps):
                p=int(lo[t-1]+i);di=q-p+D
                w=cost[di] if 0<=di<cost.size else 1e6
                z=pc[i]+w
                if z<best:best=z;bi=i
            cc[j]=best;back[t,j]=bi
        for j in range(maxs):pc[j]=cc[j]
    ls=int(hi[n-1]-lo[n-1]+1);j=0;best=pc[0]
    for k in range(1,ls):
        if pc[k]<best:best=pc[k];j=k
    out=np.empty(n,np.int32);out[n-1]=lo[n-1]+j
    for t in range(n-1,0,-1):
        j=int(back[t,j]);out[t-1]=lo[t-1]+j
    return out

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    m=s/n;return float(m),float(np.sqrt(max(0,ss/n-m*m)))

def szrun(x,eps):
    best=None
    for tr in (False,True):
        a=np.ascontiguousarray((x.T if tr else x).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(a,cfg);r,_=sz.decompress(b,np.float32,a.shape);me=float(np.max(np.abs(a-r)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        if best is None or int(b.size)<best:best=int(b.size)
    return best

def legal(X,bound,h):
    lo=np.ceil((X-bound)/h).astype(np.int32);hi=np.floor((X+bound)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal set')
    q=np.rint(X/h).astype(np.int32);q=np.minimum(np.maximum(q,lo),hi)
    return lo,hi,q

def morton_order(nc,nt):
    c=np.repeat(np.arange(nc,dtype=np.uint32),nt);t=np.tile(np.arange(nt,dtype=np.uint32),nc)
    code=np.zeros(c.size,np.uint32)
    # interleave 7 channel bits and 10 time bits; remaining time bits continue above
    pos=0
    for b in range(10):
        code|=((t>>b)&1)<<(pos);pos+=1
        if b<7:
            code|=((c>>b)&1)<<(pos);pos+=1
    return np.argsort(code,kind='stable').astype(np.int32)

def traversals(nc,nt):
    ids=np.arange(nc*nt,dtype=np.int32).reshape(nc,nt)
    a=[]
    # channel snake: temporal neighborhoods dominate, but channel boundaries remain spatially adjacent
    q=[]
    for c in range(nc):q.extend(ids[c,::1 if c%2==0 else -1].tolist())
    a.append(('channel_snake',np.asarray(q,np.int32)))
    q=[]
    for t in range(nt):q.extend(ids[::1 if t%2==0 else -1,t].tolist())
    a.append(('time_snake',np.asarray(q,np.int32)))
    a.append(('morton',morton_order(nc,nt)))
    return a

def H(a):
    _,cnt=np.unique(a,return_counts=True);p=cnt.astype(np.float64)/cnt.sum();return float(-(p*np.log2(p)).sum()),int(cnt.size)

def initial_cost(seed,D,delta=None):
    x=np.arange(-D,D+1,dtype=np.float64)
    if seed=='empirical' and delta is not None:
        cnt=np.bincount(delta+D,minlength=2*D+1).astype(np.float64)+0.5;p=cnt/cnt.sum();return -np.log2(p)
    if seed.startswith('laplace'):
        lam={'laplace05':.5,'laplace15':1.5,'laplace4':4.0}[seed]
        return lam*np.abs(x)
    if seed=='spike':
        z=5+np.log2(1+np.abs(x));z[x==0]=0;z[np.abs(x)==1]=1.5;return z
    return np.abs(x)

def learned_cost(delta,D):
    cnt=np.bincount(delta+D,minlength=2*D+1).astype(np.float64)+0.25;p=cnt/cnt.sum();return -np.log2(p)

def encode_delta(delta):
    mn=int(delta.min());mx=int(delta.max());cands=[]
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        if mn>=np.iinfo(dt).min and mx<=np.iinfo(dt).max:
            b=ZC.compress(np.ascontiguousarray(delta).astype(dt).tobytes());cands.append((len(b)+12,'signed_'+dt.str))
    zz=(delta.astype(np.int64)<<1)^(delta.astype(np.int64)>>63);mxz=int(zz.max())
    for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
        if mxz<=np.iinfo(dt).max:
            b=ZC.compress(np.ascontiguousarray(zz).astype(dt).tobytes());cands.append((len(b)+12,'zigzag_'+dt.str))
    return min(cands)

def synthesize(lo2,hi2,q02,order,seed):
    lo=lo2.ravel()[order];hi=hi2.ravel()[order];q0=q02.ravel()[order]
    maxs=int(np.max(hi-lo+1));
    if maxs>16:raise RuntimeError(('too many legal states',maxs))
    # enough delta support for every legal transition on this path
    D=int(max(np.max(np.abs(hi[1:]-lo[:-1])),np.max(np.abs(lo[1:]-hi[:-1])),np.max(np.abs(np.diff(q0)))))+4
    d0=np.diff(q0);cost=initial_cost(seed,D,d0)
    best=None
    for r in range(ROUNDS+1):
        q=viterbi_box(lo,hi,cost,D,maxs);d=np.diff(q)
        h,k=H(d);model=8*k+32;ideal=(h*d.size+32+8*model)/8
        zb,rep=encode_delta(d);actual=zb+4
        row={'round':r,'H_delta_bps':h,'alphabet':k,'ideal_bytes_with_model':ideal,'zstd_bytes':actual,'rep':rep,'zero_fraction':float(np.mean(d==0)),'abs1_fraction':float(np.mean(np.abs(d)==1)),'D':D}
        if best is None or row['ideal_bytes_with_model']<best[0]['ideal_bytes_with_model']:best=(row,q.copy())
        cost=learned_cost(d,D)
    return best

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];mu,std=stats(d);pub=.1*std;bound=pub*SAFETY;tpos=[0,14488,28976];cpos=[0,3392,6784]
        paths=traversals(C,T);tiles=[];rows=[]
        for ti,t0 in enumerate(tpos):
            for ci,c0 in enumerate(cpos):
                X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;raw=X.size*2;sb=szrun(X,pub);tid=f't{ti}c{ci}';tiles.append({'id':tid,'raw':raw,'sz3':sb})
                for fac in HFACT:
                    h=fac*bound;lo,hi,q0=legal(X,bound,h)
                    for pname,order in paths:
                        for seed in SEEDS:
                            stat,qpath=synthesize(lo,hi,q0,order,seed)
                            qflat=np.empty(qpath.size,np.int32);qflat[order]=qpath;q=qflat.reshape(C,T);R=q.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
                            if me>pub*(1+5e-6):raise RuntimeError(('hard error',tid,fac,pname,seed,me,pub))
                            rr=dict(stat);rr.update({'tile':tid,'h_over_eps':fac,'path':pname,'seed':seed,'gain_vs_sz3_ideal':sb/stat['ideal_bytes_with_model'],'gain_vs_sz3_zstd':sb/stat['zstd_bytes'],'ratio_raw_ideal':raw/stat['ideal_bytes_with_model'],'ratio_raw_zstd':raw/stat['zstd_bytes'],'maxerr':me,'mean_legal_states':float(np.mean(hi-lo+1))});rows.append(rr)
        # pick one fixed (fac,path,seed) definition across all nine tiles, no per-tile mode cheating
        combos=[]
        for fac in HFACT:
            for pname,_ in paths:
                for seed in SEEDS:
                    rr=[r for r in rows if r['h_over_eps']==fac and r['path']==pname and r['seed']==seed];szb=sum(t['sz3'] for t in tiles);raw=sum(t['raw'] for t in tiles);ib=sum(r['ideal_bytes_with_model'] for r in rr);zb=sum(r['zstd_bytes'] for r in rr)
                    combos.append({'h_over_eps':fac,'path':pname,'seed':seed,'ideal_bytes':ib,'zstd_bytes':zb,'sz3_bytes':szb,'gain_vs_sz3_ideal':szb/ib,'gain_vs_sz3_zstd':szb/zb,'ideal_bps':8*ib/(raw/2),'zstd_bps':8*zb/(raw/2),'median_zero_fraction':float(np.median([r['zero_fraction'] for r in rr])),'median_delta_entropy':float(np.median([r['H_delta_bps'] for r in rr]))})
        combos.sort(key=lambda x:x['ideal_bytes']);out={'std':std,'eps':pub,'tiles':tiles,'fixed_definition_combos':combos,'best_fixed':combos[:10],'rows':rows,'two_x_sz3_target_bps':1.8859028760018859,'scope':'Exact Viterbi search over every legal lattice state along decoder-known 2-D traversals. The source samples are constraints; reconstruction states are selected globally to minimize a learned delta codelength. Ideal counts include a pessimistic static model estimate; Zstd is a separately counted realizable backend screen. No per-tile selector in fixed-definition aggregate.'}
        print(json.dumps({'best':combos[:10]},indent=2),flush=True);json.dump(out,open('imperial_entropy_shaped_codeword.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
