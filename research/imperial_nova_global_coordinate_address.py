import json,sys,math
import h5py,numpy as np,zstandard as zstd
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar
import imperial_persistent_ar32_full_array_jit as inc

C=32
T0=14488
NT=4096
TRAIN=1024
P=32
SAFETY=1.0-1e-10
REGIONS=(('hard',512),('easy',2304))
SHEARS=(0,1,-1,2,-2,4,-4,8,-8,16,-16,32,-32)
COST_MODES=(0,1,2)
LATTICE_RATIOS=(1.0,0.75,0.5)
HEADER_BYTES=40
MATERIALIZE=32
ZF=zstd.ZstdCompressor(level=1)

def bitrev_perm(n):
    b=(n-1).bit_length()
    return np.asarray([int(f'{i:0{b}b}'[::-1],2) for i in range(n)],np.int64)

def channel_perms(n):
    p=[('natural',np.arange(n,dtype=np.int64)),
       ('reverse',np.arange(n-1,-1,-1,dtype=np.int64))]
    if n&(n-1)==0:
        p.append(('bitrev',bitrev_perm(n)))
        p.append(('gray',np.asarray([i^(i>>1) for i in range(n)],np.int64)))
    return p

def make_diag_order(nc,nt,perm,shear,snake):
    out=np.empty(nc*nt,np.int64);k=0
    for u in range(nt):
        pp=perm[::-1] if (snake and (u&1)) else perm
        for cc in pp:
            c=int(cc);t=(u-shear*c)%nt
            out[k]=c*nt+t;k+=1
    if np.unique(out).size!=out.size:raise RuntimeError(('order not bijective',shear,snake))
    return out

def make_channel_order(nc,nt,perm,snake):
    out=np.empty(nc*nt,np.int64);k=0
    for j,cc in enumerate(perm):
        tt=range(nt-1,-1,-1) if (snake and (j&1)) else range(nt)
        c=int(cc)
        for t in tt:
            out[k]=c*nt+t;k+=1
    return out

def configs(nc,nt):
    rows=[]
    for pname,p in channel_perms(nc):
        for s in SHEARS:
            for snake in (False,True):
                rows.append((f'diag_{pname}_s{s}_snake{int(snake)}',make_diag_order(nc,nt,p,s,snake)))
        for snake in (False,True):
            rows.append((f'channel_{pname}_snake{int(snake)}',make_channel_order(nc,nt,p,snake)))
    return rows

def legal_bounds(X,eps,h):
    b=eps*SAFETY
    lo=np.ceil((X-b)/h).astype(np.int32);hi=np.floor((X+b)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal interval')
    w=hi-lo+1
    return lo,hi,int(w.max()),float(w.mean()),float(np.mean(w>1))

@njit(cache=True)
def _edge_cost(a,b,c,mode):
    d1=c-b;d2=c-2*b+a
    if mode==0:return math.log2(1.0+abs(d2))+0.125*math.log2(1.0+abs(d1))
    if mode==1:return math.log2(1.0+abs(d2))+0.5*math.log2(1.0+abs(d1))
    return math.log2(1.0+abs(d1))

@njit(cache=True)
def viterbi(lo_flat,hi_flat,order,mode,maxs):
    n=order.size
    vals=np.zeros((n,maxs),np.int32);cnt=np.zeros(n,np.int8)
    for i in range(n):
        z=order[i];a=lo_flat[z];b=hi_flat[z];k=b-a+1
        if k>maxs:return np.empty(0,np.int32),1e300
        cnt[i]=k
        for j in range(k):vals[i,j]=a+j
    if n==1:return np.asarray([vals[0,0]],np.int32),0.0
    inf=1e300;dp=np.full((maxs,maxs),inf,np.float64)
    for a in range(cnt[0]):
        for b in range(cnt[1]):
            dp[a,b]=math.log2(1.0+abs(vals[1,b]-vals[0,a]))
    back=np.full((n,maxs,maxs),-1,np.int8)
    for i in range(2,n):
        nd=np.full((maxs,maxs),inf,np.float64)
        for b in range(cnt[i-1]):
            for c in range(cnt[i]):
                best=inf;ba=-1
                for a in range(cnt[i-2]):
                    z=dp[a,b]+_edge_cost(vals[i-2,a],vals[i-1,b],vals[i,c],mode)
                    if z<best:best=z;ba=a
                nd[b,c]=best;back[i,b,c]=ba
        dp=nd
    best=inf;ba=-1;bb=-1
    for a in range(cnt[n-2]):
        for b in range(cnt[n-1]):
            if dp[a,b]<best:best=dp[a,b];ba=a;bb=b
    q=np.empty(n,np.int32);q[n-2]=vals[n-2,ba];q[n-1]=vals[n-1,bb]
    aidx=ba;bidx=bb
    for i in range(n-1,1,-1):
        p=int(back[i,aidx,bidx]);q[i-2]=vals[i-2,p];bidx=aidx;aidx=p
    return q,best

def proxy_bytes(q):
    q=np.asarray(q,np.int32)
    d1=q.copy();d1[1:]=q[1:]-q[:-1]
    d2=d1.copy();d2[1:]=d1[1:]-d1[:-1]
    best=1<<60
    for a in (q,d1,d2):
        mn=int(a.min());mx=int(a.max())
        dt=np.dtype('<i2') if mn>=-32768 and mx<=32767 else np.dtype('<i4')
        best=min(best,len(ZF.compress(a.astype(dt).tobytes())))
    return int(best)

def optimize(lo,hi,order,mode):
    lf=np.ascontiguousarray(lo.ravel(),np.int32);hf=np.ascontiguousarray(hi.ravel(),np.int32)
    maxs=int(np.max(hf-lf+1))
    q,score=viterbi(lf,hf,np.ascontiguousarray(order,np.int64),mode,maxs)
    if q.size!=order.size:raise RuntimeError(('viterbi failed',maxs))
    return q,float(score)

def materialize(q,order,h,X,eps):
    fr=m.encode_k(np.asarray(q,np.int32).reshape(1,-1));qd=np.asarray(fr[2],np.int32).ravel()
    if not np.array_equal(qd,q):raise RuntimeError('address stream decode')
    flat=np.empty(X.size,np.int32);flat[order]=qd;Q=flat.reshape(X.shape);R=Q.astype(np.float64)*h
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+2e-10):raise RuntimeError(('address hard error',me,eps))
    return {'bytes':int(fr[0])+HEADER_BYTES,'payload_bytes':int(fr[0]),'rep':fr[1],
            'maxerr':me,'q_zero_fraction':float(np.mean(q==0)),'q_std':float(q.std())}

def incumbent(X,eps):
    old=m.STEP;m.STEP=267
    try:
        co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=inc.build(X,cd)
        fr=m.encode_k(K);Kd=np.asarray(fr[2],np.int32);Rd=inc.decode(Kd,cd)
        if not np.array_equal(Rd,R):raise RuntimeError('incumbent replay mismatch')
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('incumbent hard error',me,eps))
        return {'bytes':int(fr[0])+int(mb)+32,'innovation_bytes':int(fr[0]),'model_bytes':int(mb),
                'rep':fr[1],'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())}
    finally:m.STEP=old

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        _,std=m.stats(d);eps=.1*std;cfgs=configs(C,NT);rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[T0:T0+NT,c0:c0+C],np.float64).T
            sb,ori=m.szrun(X,eps);base=incumbent(X,eps);screens=[];lstats=[]
            for lid,ratio in enumerate(LATTICE_RATIOS):
                h=eps*ratio;lo,hi,maxs,mean_states,multi=legal_bounds(X,eps,h)
                lstats.append({'lattice_id':lid,'ratio':ratio,'h':h,'max_states':maxs,
                               'mean_states':mean_states,'multi_state_fraction':multi})
                for cid,(name,order) in enumerate(cfgs):
                    for mode in COST_MODES:
                        q,score=optimize(lo,hi,order,mode)
                        screens.append({'lattice_id':lid,'ratio':ratio,'h':h,'config_id':cid,
                            'config':name,'cost_mode':mode,'surrogate':score,'proxy_bytes':proxy_bytes(q)})
            screens.sort(key=lambda z:(z['proxy_bytes'],z['surrogate'],z['lattice_id'],z['config_id'],z['cost_mode']))
            finals=[]
            for s in screens[:MATERIALIZE]:
                lid=s['lattice_id'];h=s['h'];lo,hi,_,_,_=legal_bounds(X,eps,h)
                name,order=cfgs[s['config_id']];q,score=optimize(lo,hi,order,s['cost_mode'])
                r=materialize(q,order,h,X,eps);r.update(s);r['surrogate']=score;finals.append(r)
            finals.sort(key=lambda z:(z['bytes'],z['proxy_bytes']))
            best=finals[0]
            h=eps;nearest=np.rint(X/h).astype(np.int32);nfr=m.encode_k(nearest.reshape(1,-1))
            if not np.array_equal(np.asarray(nfr[2],np.int32),nearest):raise RuntimeError('nearest stream')
            nme=float(np.max(np.abs(X-nearest.astype(np.float64)*h)))
            near={'bytes':int(nfr[0])+HEADER_BYTES,'payload_bytes':int(nfr[0]),'rep':nfr[1],'maxerr':nme}
            for z in (best,near,base):
                z['bps']=8*z['bytes']/X.size;z['gain_vs_sz3']=sb/z['bytes']
            best['gain_vs_incumbent']=base['bytes']/best['bytes'];best['gain_vs_nearest_address']=near['bytes']/best['bytes']
            row={'region':region,'c0':c0,'shape':[C,NT],'samples':int(X.size),'global_std':std,'eps':eps,
                 'coordinate_configs':len(cfgs),'cost_modes':len(COST_MODES),'lattice_stats':lstats,
                 'screened_candidates':len(screens),'materialized_candidates':len(finals),'best':best,
                 'top_materialized':finals[:8],'nearest_address':near,'incumbent_ar32_step267':base,
                 'sz3':{'bytes':int(sb),'bps':8*sb/X.size,'orientation':ori}}
            rows.append(row)
            print(json.dumps({'region':region,'sz3_bytes':int(sb),'incumbent':base,'nearest_address':near,
                'best_global_address':best,'lattice_stats':lstats},indent=2),flush=True)
        out={'global_std':std,'eps':eps,'shape':[C,NT],'t0':T0,'regions':[x[0] for x in REGIONS],
             'coordinate_family':'NOVA/Complexity-Weapon faithful gate. Decoder-known global Hamiltonian coordinates are parameterized by channel permutation, spacetime shear and snake direction. For each coordinate and one of three fixed first/second-difference objectives, exact Viterbi chooses the complete epsilon-legal lattice reconstruction jointly across the entire object. Three lattice densities are searched. All candidates are screened with a fixed fast lossless proxy; the top 32 are materialized through the existing self-decoding representation menu. Only actual materialized bytes count. Decoder recovers the integer address, regenerates the chosen global coordinate from its tiny selector, maps every value back to physical channel/time, reconstructs floating samples, and verifies the unchanged hard error. Selector/lattice/framing bytes are charged. No ideal entropy mass, no oracle side information, no target-trained model. Incumbent AR32 step267 and matched SZ3 are rerun on identical arrays.',
             'rows':rows}
        json.dump(out,open('imperial_nova_global_coordinate_address.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
