import json,sys,math
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NSEEDS=1024
TOPK=24
OPS=48


def basis_rows(seed,nb):
    rows=[1<<i for i in range(nb)];x=(int(seed)+1)*0x9E3779B9 & 0xffffffff
    for _ in range(OPS):
        x^=(x<<13)&0xffffffff;x^=x>>17;x^=(x<<5)&0xffffffff;x&=0xffffffff
        aa=x%nb;bb=(x//nb)%nb
        if aa==bb:bb=(bb+1)%nb
        if (x>>29)&1:rows[aa],rows[bb]=rows[bb],rows[aa]
        else:rows[aa]^=rows[bb]
    return rows


def inverse_rows(rows,nb):
    aug=[int(rows[i])|((1<<i)<<nb) for i in range(nb)]
    for col in range(nb):
        p=next((r for r in range(col,nb) if (aug[r]>>col)&1),None)
        if p is None:raise RuntimeError('singular')
        aug[col],aug[p]=aug[p],aug[col]
        for r in range(nb):
            if r!=col and ((aug[r]>>col)&1):aug[r]^=aug[col]
    mask=(1<<nb)-1
    for i,z in enumerate(aug):
        if (z&mask)!=(1<<i):raise RuntimeError('inverse failure')
    return [(z>>nb)&mask for z in aug]


def parity_mask(U,mask):
    z=np.asarray(U,np.uint64)&np.uint64(mask);p=np.zeros(U.shape,np.uint64)
    while mask:
        p^=z&1;z>>=1;mask>>=1
    return p


def apply_rows(U,rows):
    U=np.asarray(U,np.uint64);Y=np.zeros_like(U)
    for i,mask in enumerate(rows):Y|=parity_mask(U,int(mask))<<i
    return Y


def surrogate(Y,nb,lf):
    flat=np.asarray(Y,np.uint64).ravel();s=0.0;ln2=math.log(2.0)
    for bit in range(nb-1,-1,-1):
        pref=(flat>>(bit+1)).astype(np.int64);b=((flat>>bit)&1).astype(np.int64);ng=1<<(nb-bit-1) if bit<nb-1 else 1
        n=np.bincount(pref,minlength=ng).astype(np.int64);k=np.bincount(pref,weights=b,minlength=ng).astype(np.int64)
        nz=n>0;nn=n[nz];kk=k[nz]
        s+=float(np.sum(lf[nn]-lf[kk]-lf[nn-kk]))/ln2
        s+=8.0*float(np.sum(np.where(kk<128,1,np.where(kk<16384,2,3))))
    return s


def exact_candidate(D,seed,nb):
    U=m.zig(np.asarray(D,np.int32));rows=basis_rows(seed,nb);inv=inverse_rows(rows,nb);Y=apply_rows(U,rows)
    if not np.array_equal(apply_rows(Y,inv),U):raise RuntimeError(('inverse',seed))
    T=m.unzig(Y).astype(np.int32);rb,rep,Td,detail=rr.restricted_rank_frame(T);Ud=apply_rows(m.zig(Td),inv);Dd=m.unzig(Ud).astype(np.int32)
    if not np.array_equal(Dd,D):raise RuntimeError(('replay',seed))
    return int(rb)+6,Dd,{'seed':int(seed),'rank_bytes':int(rb),'selector_bytes':6,'rank_rep':rep,'rows':rows,'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size);Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy());Q2,D2,_,changes=a.shape_search(Q2,lo,hi,D2,dts,dcs,co,intercept,g.SCALE,logc,a.NBITS,a.PASSES)
    U=m.zig(D2);mx=int(U.max()) if U.size else 0;nb=max(1,mx.bit_length());lf=np.zeros(X.size+1,np.float64);lf[1:]=np.cumsum(np.log(np.arange(1,X.size+1,dtype=np.float64)))
    scored=[(surrogate(U,nb,lf),-1)]
    for seed in range(NSEEDS):scored.append((surrogate(apply_rows(U,basis_rows(seed,nb)),nb,lf),seed))
    scored.sort();outrows=[]
    for sur,seed in scored[:TOPK]:
        if seed==-1:
            rb,rep,Dd,detail=rr.restricted_rank_frame(D2);b=int(rb);meta={'seed':-1,'rank_bytes':b,'selector_bytes':0,'rank_rep':rep,'detail':detail}
        else:b,Dd,meta=exact_candidate(D2,seed,nb)
        r=c.validate(X,eps,h,Q2,Dd,dts,dcs,co,intercept,b,'gl9_'+str(seed),meta);r.update({'seed':int(seed),'surrogate_bits':float(sur),'gain_vs_sz3':szb/r['bytes'],'gain_vs_ar32':arb['bytes']/r['bytes']});outrows.append(r)
        print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    outrows.sort(key=lambda r:r['bytes']);best=outrows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'nbits':nb,'nseeds':NSEEDS,'ops':OPS,'topk_exact':TOPK,'search_changes':int(changes),'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'best':best,'top':outrows,'surrogate_top':[{'seed':int(seed),'bits':float(bits)} for bits,seed in scored[:40]],'scope':'Full public GL(n,2) NOVA coordinate-system search over the exact PR518 address-shaped defect. Each public seed starts from identity and applies deterministic invertible row swaps/xors, yielding an arbitrary-ish invertible GF(2) basis rather than only a triangular Gray-like family. Encoder searches 1024 public bases using a prefix-enumerative surrogate, physically materializes the top 24 through PR512 exact restricted ranking, and pays a selector/framing charge for nonidentity bases. Decoder regenerates the basis from the seed, byte-decodes transformed coordinates, applies the exact inverse GF(2) matrix, recovers the identical signed defect field, regenerates exact Q through the charged learned generator and verifies unchanged hard source error. Only physical bytes count.'}
    json.dump(out,open('imperial_full_gl9_coordinate_search.json','w'),indent=2)
    print(json.dumps({'summary':{'seed':best['seed'],'bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
