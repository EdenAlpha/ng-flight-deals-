import json,math,sys,itertools
import h5py,numpy as np
sys.path.append('research')
import imperial_dyadic_legal_grid_full_array as m

STEP=256;CB=128;TB=1024;SAFETY=1-1e-5
PHASES=(0,64)
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))


def legal_byte_states(X,eps,phase):
    b=eps*SAFETY
    lo=np.ceil((X-b-phase)/STEP-1e-12).astype(np.int16)
    hi=np.floor((X+b-phase)/STEP+1e-12).astype(np.int16)
    if np.any(lo>hi):raise RuntimeError('empty legal byte state')
    width=hi.astype(np.int32)-lo.astype(np.int32)
    if int(width.max())>1:raise RuntimeError(('more than two coarse byte states',int(width.max())))
    return lo.astype(np.int32),hi.astype(np.int32)


def encode_B(B):
    B=np.asarray(B,np.int32)
    c=m.signed_reps(B)+m.xor_reps(B)+[m.bitplane_rep(B,False),m.bitplane_rep(B,True),m.byteshuffle_rep(B)]
    best=min(c,key=lambda x:x[0])
    if not np.array_equal(best[2],B):raise RuntimeError('B decoder mismatch')
    return best[0]+9,best[1]


def edge_fraction(B):
    a=B[:,1:]!=B[:,:-1];b=B[1:]!=B[:-1]
    return float((a.sum()+b.sum())/(a.size+b.size))


def components(mask):
    H,W=mask.shape;seen=np.zeros_like(mask,bool);out=[]
    for r,c in np.argwhere(mask):
        r=int(r);c=int(c)
        if seen[r,c]:continue
        st=[(r,c)];seen[r,c]=1;comp=[]
        while st:
            x,y=st.pop();comp.append((x,y))
            for xx,yy in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if 0<=xx<H and 0<=yy<W and mask[xx,yy] and not seen[xx,yy]:
                    seen[xx,yy]=1;st.append((xx,yy))
        out.append(comp)
    return out


def solve_component_exact(B,lo,hi,comp):
    # Connected ambiguous components are tiny because ambiguity occupies only ~4-5%
    # of sites. Exhaust every legal binary assignment and choose the exact minimum
    # number of unequal 4-neighbour byte labels, including fixed neighbours.
    idx={p:i for i,p in enumerate(comp)};n=len(comp)
    opts=[(int(lo[p]),int(hi[p])) for p in comp]
    internal=[];boundary=[];H,W=B.shape
    for i,(r,c) in enumerate(comp):
        for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if not (0<=rr<H and 0<=cc<W):continue
            j=idx.get((rr,cc))
            if j is None:
                boundary.append((i,int(B[rr,cc])))
            elif i<j:
                internal.append((i,j))
    if n>22:
        # This should be extraordinarily rare below the 2-D site-percolation
        # threshold. Deterministic exact branch-and-bound with a conservative cap.
        raise RuntimeError(('unexpected large ambiguous component',n))
    best_cost=10**18;best_bits=0
    for bits in range(1<<n):
        vals=[opts[i][(bits>>i)&1] for i in range(n)]
        cost=0
        for i,j in internal:cost+=(vals[i]!=vals[j])
        for i,v in boundary:cost+=(vals[i]!=v)
        if cost<best_cost:
            best_cost=cost;best_bits=bits
    for i,p in enumerate(comp):B[p]=opts[i][(best_bits>>i)&1]
    return best_cost


def optimize(X,eps,phase):
    lo,hi=legal_byte_states(X,eps,phase);amb=lo!=hi
    nearest=np.rint((X-phase)/STEP).astype(np.int32);nearest=np.minimum(np.maximum(nearest,lo),hi)
    B=nearest.copy();comps=components(amb);sizes=[len(x) for x in comps]
    for comp in comps:solve_component_exact(B,lo,hi,comp)
    R=phase+STEP*B.astype(np.float64);me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',phase,me,eps))
    nb,nrep=encode_B(nearest);ob,orep=encode_B(B)
    return {'nearest_bytes':nb,'nearest_rep':nrep,'optimized_bytes':ob,'optimized_rep':orep,
            'gain_optimized_vs_nearest':nb/ob,'maxerr':me,'ambiguous_fraction':float(np.mean(amb)),
            'ambiguous_sites':int(amb.sum()),'components':len(comps),'max_component_size':max(sizes) if sizes else 0,
            'mean_component_size':float(np.mean(sizes)) if sizes else 0.0,
            'nearest_edge_fraction':edge_fraction(nearest),'optimized_edge_fraction':edge_fraction(B)}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+TB,c0:c0+CB],np.float64).T;sb,ori=m.szrun(X,eps)
            for phase in PHASES:
                r=optimize(X,eps,phase);r.update({'tile':name,'phase':phase,'sz3_bytes':sb,'sz3_orientation':ori,
                    'gain_optimized_vs_sz3':sb/r['optimized_bytes'],'gain_nearest_vs_sz3':sb/r['nearest_bytes'],
                    'optimized_bps':8*r['optimized_bytes']/X.size,'sz3_bps':8*sb/X.size})
                rows.append(r);print(json.dumps(r),flush=True)
        combos=[]
        for phase in PHASES:
            rr=[r for r in rows if r['phase']==phase];ob=sum(r['optimized_bytes'] for r in rr);nb=sum(r['nearest_bytes'] for r in rr);sb=sum(r['sz3_bytes'] for r in rr);n=CB*TB*len(rr)
            combos.append({'phase':phase,'optimized_bytes':ob,'nearest_bytes':nb,'sz3_bytes':sb,
                'optimized_bps':8*ob/n,'nearest_bps':8*nb/n,'sz3_bps':8*sb/n,
                'gain_optimized_vs_sz3':sb/ob,'gain_nearest_vs_sz3':sb/nb,'gain_optimized_vs_nearest':nb/ob,
                'median_ambiguous_fraction':float(np.median([r['ambiguous_fraction'] for r in rr])),
                'max_component_size':max(r['max_component_size'] for r in rr),'min_tile_gain':min(r['gain_optimized_vs_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['optimized_bytes'])
        out={'global_std':std,'eps':eps,'step':STEP,'phases':list(PHASES),'patch_shape':[CB,TB],'rows':rows,'combos':combos,
             'scope':'Scalable exact overlap-component synthesis on a legal 256-spaced byte grid. Because epsilon exceeds 128 but is below 256, each sample has one or at most two legal coarse-byte reconstruction values. The ambiguous ~few-percent sites form disconnected 4-neighbour components. Each component is exhaustively solved for the exact minimum number of unequal horizontal/vertical coarse-byte edges including fixed neighbours; components are independent, so the global contour optimum is exact without a full-tile MILP. The optimized byte field is then actually serialized with the PR287 decoder-real representation menu, byte-decoded and hard-error verified. Phase 0 and 64 are tested on four 128x1024 regimes with matched SZ3. No AI; patch screen only.'}
        print(json.dumps({'combos':combos},indent=2),flush=True);json.dump(out,open('imperial_exact_byte_overlap_components.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
