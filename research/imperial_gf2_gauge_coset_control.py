import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_dyadic_legal_grid_full_array as m

H=128.0; SAFETY=1-1e-5
PHASES=(0.0,64.0)
OBJECTIVES=('contour','l1','bitflip')
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
POPC=np.array([int(i).bit_count() for i in range(65536)],dtype=np.uint8)

def legal_q(X,eps,phase):
    b=eps*SAFETY
    lo=np.ceil((X-b-phase)/H-1e-12).astype(np.int32)
    hi=np.floor((X+b-phase)/H+1e-12).astype(np.int32)
    if np.any(lo>hi): raise RuntimeError('empty legal set')
    return lo,hi

def B_for_parity(X,lo,hi,phase,p):
    p=np.asarray(p,np.int32)
    blo=-np.floor_divide(-(lo-p),2)
    bhi=np.floor_divide(hi-p,2)
    if np.any(blo>bhi): raise RuntimeError('requested parity not legal')
    target=(X-phase-H*p)/(2*H)
    B=np.rint(target).astype(np.int32)
    B=np.minimum(np.maximum(B,blo),bhi)
    q=2*B+p
    if np.any(q<lo)|np.any(q>hi): raise RuntimeError('parity B illegal')
    return B

def zz(a):
    a=np.asarray(a,np.int64)
    return ((a<<1)^(a>>63)).astype(np.uint64)

def ecost(a,b,kind):
    a=np.asarray(a);b=np.asarray(b)
    if kind=='contour': return int(np.count_nonzero(a!=b))
    if kind=='l1': return int(np.abs(a.astype(np.int64)-b.astype(np.int64)).sum())
    x=np.bitwise_xor(zz(a),zz(b))
    if int(x.max(initial=0))>=POPC.size: return int(sum(int(v).bit_count() for v in x.ravel()))
    return int(POPC[x.astype(np.int64)].sum())

def full_proxy(B,kind):
    return ecost(B[:,:-1],B[:,1:],kind)+ecost(B[:-1,:],B[1:,:],kind)

def init_factors(nc,nt,k):
    if k==0:return np.zeros(nc,np.uint8),np.zeros(nt,np.uint8)
    if k==1:return (np.arange(nc)&1).astype(np.uint8),np.zeros(nt,np.uint8)
    if k==2:return np.zeros(nc,np.uint8),(np.arange(nt)&1).astype(np.uint8)
    if k==3:return (np.arange(nc)&1).astype(np.uint8),(np.arange(nt)&1).astype(np.uint8)
    if k==4:return ((np.arange(nc)//2)&1).astype(np.uint8),((np.arange(nt)//4)&1).astype(np.uint8)
    rng=np.random.default_rng(20260812+k)
    return rng.integers(0,2,nc,dtype=np.uint8),rng.integers(0,2,nt,dtype=np.uint8)

def optimize(B0,B1,kind,init_id,maxpass=8):
    nc,nt=B0.shape;r,s=init_factors(nc,nt,init_id)
    p=np.bitwise_xor(r[:,None],s[None,:]);B=np.where(p,B1,B0).astype(np.int32)
    flips=0
    for _ in range(maxpass):
        changed=0
        for c in range(nc):
            old=B[c].copy();pn=np.bitwise_xor(np.uint8(1-r[c]),s);new=np.where(pn,B1[c],B0[c]).astype(np.int32)
            oc=ecost(old[:-1],old[1:],kind);ncost=ecost(new[:-1],new[1:],kind)
            if c: oc+=ecost(B[c-1],old,kind);ncost+=ecost(B[c-1],new,kind)
            if c+1<B.shape[0]: oc+=ecost(old,B[c+1],kind);ncost+=ecost(new,B[c+1],kind)
            if ncost<oc:
                r[c]^=1;B[c]=new;changed+=1;flips+=1
        for t in range(nt):
            old=B[:,t].copy();pn=np.bitwise_xor(r,np.uint8(1-s[t]));new=np.where(pn,B1[:,t],B0[:,t]).astype(np.int32)
            oc=ecost(old[:-1],old[1:],kind);ncost=ecost(new[:-1],new[1:],kind)
            if t: oc+=ecost(B[:,t-1],old,kind);ncost+=ecost(B[:,t-1],new,kind)
            if t+1<B.shape[1]: oc+=ecost(old,B[:,t+1],kind);ncost+=ecost(new,B[:,t+1],kind)
            if ncost<oc:
                s[t]^=1;B[:,t]=new;changed+=1;flips+=1
        if not changed:break
    return r,s,B,full_proxy(B,kind),flips

def encode_B(B):
    c=m.signed_reps(B)+m.xor_reps(B)+[m.bitplane_rep(B,False),m.bitplane_rep(B,True),m.byteshuffle_rep(B)]
    return min(c,key=lambda x:x[0])

def pack_factor(a):
    raw=np.packbits(np.asarray(a,np.uint8),bitorder='little').tobytes();bb=Z.compress(raw)
    rr=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:len(a)].astype(np.uint8)
    if not np.array_equal(rr,a):raise RuntimeError('factor roundtrip')
    return bb,rr

def materialize(X,eps,phase,r,s,B):
    rb,rd=pack_factor(r);sb,sd=pack_factor(s)
    best=encode_B(B);Bd=best[2].astype(np.int32)
    p=np.bitwise_xor(rd[:,None],sd[None,:]).astype(np.int32);q=2*Bd+p
    R=phase+H*q.astype(np.float64);me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
    total=int(best[0])+len(rb)+len(sb)+72
    return {'bytes':total,'bps':8*total/X.size,'B_bytes':int(best[0]),'B_rep':best[1],'r_bytes':len(rb),'s_bytes':len(sb),'factor_bytes':len(rb)+len(sb),'factor_bps':8*(len(rb)+len(sb))/X.size,'maxerr':me,'p_one_fraction':float(np.mean(p)),'B_edge_fraction':float((np.count_nonzero(B[:,:-1]!=B[:,1:])+np.count_nonzero(B[:-1,:]!=B[1:,:]))/(B[:,:-1].size+B[:-1,:].size))}

def evaluate(X,eps,phase):
    lo,hi=legal_q(X,eps,phase)
    B0=B_for_parity(X,lo,hi,phase,np.zeros(X.shape,np.int32))
    B1=B_for_parity(X,lo,hi,phase,np.ones(X.shape,np.int32))
    # Existence audit: with interval width > 2H, both parities should be legal everywhere.
    if float(np.min(hi-lo+1))<2:raise RuntimeError('parity freedom assumption failed')
    rows=[]
    z=np.zeros(X.shape[0],np.uint8);zt=np.zeros(X.shape[1],np.uint8)
    base=materialize(X,eps,phase,z,zt,B0);base.update({'kind':'constant_p0','objective':'none','proxy':None,'flips':0});rows.append(base)
    for obj in OBJECTIVES:
        cand=[]
        for init in range(8):
            r,s,B,proxy,flips=optimize(B0,B1,obj,init)
            rr=materialize(X,eps,phase,r,s,B);rr.update({'kind':'gf2_gauge','objective':obj,'init':init,'proxy':proxy,'flips':flips})
            cand.append(rr)
        rows.append(min(cand,key=lambda x:x['bytes']))
    return rows,{'mean_legal_states':float(np.mean(hi-lo+1)),'min_legal_states':int(np.min(hi-lo+1)),'both_parities_legal_fraction':1.0}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+m.TB,c0:c0+m.CB],np.float64).T;sb,ori=m.szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'sz3_orientation':ori,'local_std':float(X.std())})
            for ph in PHASES:
                rr,audit=evaluate(X,eps,ph)
                for r in rr:
                    r.update({'tile':name,'t0':t0,'c0':c0,'phase':ph,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],**audit});rows.append(r)
                    print(json.dumps(r),flush=True)
        combos=[]
        keys=[('constant_p0','none')]+[('gf2_gauge',x) for x in OBJECTIVES]
        for ph in PHASES:
            for kind,obj in keys:
                rr=[r for r in rows if r['phase']==ph and r['kind']==kind and r['objective']==obj]
                b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=m.CB*m.TB*len(rr)
                combos.append({'phase':ph,'kind':kind,'objective':obj,'bytes':b,'sz3_bytes':s,'bps':8*b/n,'gain_vs_sz3':s/b,'mean_factor_bps':float(np.mean([r['factor_bps'] for r in rr])),'median_B_edge_fraction':float(np.median([r['B_edge_fraction'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['bytes'])
        out={'global_std':std,'eps':eps,'fine_step':H,'patch_shape':[m.CB,m.TB],'phases':list(PHASES),'objectives':list(OBJECTIVES),'specs':[list(x) for x in SPECS],'combos':combos,'rows':rows,'scope':'GF(2) low-rate gauge/coset control screen. On the 128-spaced reconstruction lattice the unchanged +/-10%-global-std interval contains at least two consecutive states everywhere, so either parity is legal for every sample. Rather than transmitting a full parity plane, the plane is constrained to p(c,t)=r(c) XOR s(t), giving an exponentially large 2^(C+T-1) legal control codebook for only C+T factor bits. Coordinate descent selects r/s to minimize coarse-byte contour, L1-delta, or zigzag bit-transition proxy. The factors and exact coarse B field are actually Zstd serialized/byte-decoded, q=2B+p reconstructed, and final hard error verified. The B field uses the exact decoder-real PR287/288 representation menu; matched SZ3 is rerun on identical 128x1024 hard/easy/medium/far tiles. No AI; patch screen only.'}
        print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_gf2_gauge_coset_control.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
