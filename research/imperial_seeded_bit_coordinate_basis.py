import json,sys,math,struct
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NSEEDS=256
TOPK=16


def masks_for(seed,nb):
    # Public deterministic unit upper-triangular GF(2) basis: y_i=x_i xor parity(mask_i & x_{>i}).
    x=(int(seed)+1)*0x9E3779B9 & 0xffffffff;m=[]
    for i in range(nb):
        x ^= (x<<13)&0xffffffff;x ^= x>>17;x ^= (x<<5)&0xffffffff;x &= 0xffffffff
        higher=((1<<nb)-1)^((1<<(i+1))-1)
        m.append(int(x)&higher)
    return m


def parity_u(U,mask):
    z=np.asarray(U,np.uint64)&np.uint64(mask);p=np.zeros(U.shape,np.uint64)
    while mask:
        p^=z&1;z>>=1;mask>>=1
    return p


def forward(U,seed,nb):
    U=np.asarray(U,np.uint64);Y=np.zeros_like(U);ms=masks_for(seed,nb)
    for i in range(nb):
        b=(U>>i)&1
        if ms[i]:b^=parity_u(U,ms[i])
        Y|=b.astype(np.uint64)<<i
    return Y


def inverse(Y,seed,nb):
    Y=np.asarray(Y,np.uint64);X=np.zeros_like(Y);ms=masks_for(seed,nb)
    for i in range(nb-1,-1,-1):
        b=(Y>>i)&1
        if ms[i]:b^=parity_u(X,ms[i])
        X|=b.astype(np.uint64)<<i
    return X


def surrogate(Y,nb):
    # Prefix-restricted enumerative ideal + exact one-byte-ish count penalty.
    flat=np.asarray(Y,np.uint64).ravel();bits=0.0
    for bit in range(nb-1,-1,-1):
        pref=flat>>(bit+1);B=((flat>>bit)&1).astype(np.uint8)
        order=np.argsort(pref,kind='stable');p=pref[order];b=B[order]
        cuts=np.flatnonzero(p[1:]!=p[:-1])+1 if p.size>1 else np.zeros(0,np.int64)
        starts=np.r_[0,cuts];ends=np.r_[cuts,p.size]
        for aa,zz in zip(starts,ends):
            n=int(zz-aa);k=int(b[int(aa):int(zz)].sum())
            bits += math.log2(math.comb(n,k)) if 0<k<n else 0.0
            bits += 8.0*(1 if k<128 else 2 if k<16384 else 3)
    return bits


def exact_candidate(D,seed,nb):
    U=m.zig(np.asarray(D,np.int32));Y=forward(U,seed,nb)
    if not np.array_equal(inverse(Y,seed,nb),U):raise RuntimeError(('basis inverse',seed))
    T=m.unzig(Y).astype(np.int32)
    rb,rep,Td,detail=rr.restricted_rank_frame(T)
    Yd=m.zig(Td);Ud=inverse(Yd,seed,nb);Dd=m.unzig(Ud).astype(np.int32)
    if not np.array_equal(Dd,D):raise RuntimeError(('basis replay',seed))
    # 4 bytes framing + 2-byte public basis id in addition to exact rank stream.
    return int(rb)+6,Dd,{'seed':int(seed),'rank_rep':rep,'rank_bytes':int(rb),'selector_bytes':6,'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size);Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy())
    Q2,D2,_,changes=a.shape_search(Q2,lo,hi,D2,dts,dcs,co,intercept,g.SCALE,logc,a.NBITS,a.PASSES)
    U=m.zig(D2);mx=int(U.max()) if U.size else 0;nb=max(1,mx.bit_length())
    scored=[]
    # seed -1 is identity; public seeded family is 0..255.
    scored.append((surrogate(U,nb),-1))
    for seed in range(NSEEDS):scored.append((surrogate(forward(U,seed,nb),nb),seed))
    scored.sort();cands=[]
    for sur,seed in scored[:TOPK]:
        if seed==-1:
            rb,rep,Dd,detail=rr.restricted_rank_frame(D2);b=int(rb);meta={'seed':-1,'rank_rep':rep,'rank_bytes':b,'selector_bytes':0,'detail':detail}
        else:b,Dd,meta=exact_candidate(D2,seed,nb)
        r=c.validate(X,eps,h,Q2,Dd,dts,dcs,co,intercept,b,'basis_'+str(seed),meta)
        r['surrogate_bits']=float(sur);r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];r['seed']=int(seed);cands.append(r)
        print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    cands.sort(key=lambda r:r['bytes']);best=cands[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'nbits':nb,'nseeds':NSEEDS,'topk_exact':TOPK,'search_changes':int(changes),'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'best':best,'top':cands,'surrogate_top':[{'seed':int(s),'bits':float(v)} for v,s in scored[:32]],'scope':'Public seeded coordinate-basis search over the exact PR518 address-shaped defect. Each candidate seed deterministically generates an invertible unit upper-triangular GF(2) transform over the zigzag defect word. Encoder search over 256 public bases is free computation; a winning non-identity basis pays an explicit selector/framing charge. A cheap prefix-enumerative surrogate selects only the top 16 candidates for physical exact PR512 restricted-rank encoding. The decoder reads the basis selector, reconstructs the public transform, byte-decodes the transformed restricted-rank stream, applies the exact inverse GF(2) basis, recovers the identical signed defect raster, regenerates the exact Q field through the charged learned generator, and passes the unchanged hard source error. Only final materialized bytes are compression claims.'}
    json.dump(out,open('imperial_seeded_bit_coordinate_basis.json','w'),indent=2)
    print(json.dumps({'summary':{'best_seed':best['seed'],'best_bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
