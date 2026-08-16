import json, math, sys
import h5py, numpy as np

sys.path.insert(0, __file__.rsplit('/',1)[0])
import imperial_huber_ar32_coldstart_arithmetic_regions as base

# Fast but real gate. The essential correction is that the encoder searches the
# WHOLE legal reconstruction set in a short block and scores it in transmitted
# probability bits, rather than minimizing raw correction magnitude.
C=8; NT=4096; TRAIN=1024; P=32; L=2; TB=1024
REGIONS=(('hard',512),('easy',2304))
STEPS=(224,256)
VARIANTS=('static_huber','shared_local_das')
NB=8; NCTX=9*9*NB*4
REFIT=64; WIN=512; RIDGE=1e-2; CLIP_CORR_K=4.0


def clip4(x): return int(max(-4,min(4,int(x))))+4
def zig(k): return (int(k)<<1) ^ (int(k)>>63)
def ctx(prev,left,pos,pref): return (((clip4(prev)*9+clip4(left))*NB+pos)*4+pref)

def update_symbol(counts,k,prev,left):
    u=zig(k)
    if u < 0 or u >= (1<<NB): return False
    pref=0
    for bp in range(NB-1,-1,-1):
        bit=(u>>bp)&1; pos=NB-1-bp; cx=ctx(prev,left,pos,pref)
        counts[cx,bit]+=1
        if int(counts[cx,0]+counts[cx,1])>16384: counts[cx]=(counts[cx]+1)//2
        pref=((pref<<1)|bit)&3
    return True

def symbol_prob(counts,k,prev,left):
    u=zig(k)
    if u < 0 or u >= (1<<NB): return 0.0
    p=1.0; pref=0
    for bp in range(NB-1,-1,-1):
        bit=(u>>bp)&1; pos=NB-1-bp; cx=ctx(prev,left,pos,pref)
        c0=int(counts[cx,0]); c1=int(counts[cx,1]); tot=c0+c1
        p *= (c1 if bit else c0)/tot
        pref=((pref<<1)|bit)&3
    return p

def huber_pred(hist,co):
    if len(hist)<P: return 0
    a=float(co[0]); b=np.asarray(co[1:],np.float32)
    return int(np.rint(a + float(np.dot(b, np.asarray(hist[-P:][::-1],np.float32)))))

def dense_prefix(X,co,step):
    R=np.zeros((C,TRAIN),np.int32); K=np.zeros((C,TRAIN),np.int32)
    for c in range(C):
        for t in range(TRAIN):
            p=0 if t<P else huber_pred(R[c,:t],co)
            k=int(np.rint((float(X[c,t])-p)/step)); K[c,t]=k; R[c,t]=p+step*k
    return R,K

def local_features(K,c,u):
    # All features are decoder-known at the time they are used. Same-time
    # spatial features are strictly from already-decoded channels.
    f=[1.0]
    for lag in (1,2,4,8): f.append(float(K[c,u-lag]) if u>=lag else 0.0)
    for dc in (1,2):
        cc=c-dc
        for lag in (0,1,2,4):
            uu=u-lag
            f.append(float(K[cc,uu]) if cc>=0 and uu>=0 else 0.0)
    return np.asarray(f,np.float64)

def refit_betas(R,K,co,t0,step):
    nf=1+4+8; B=np.zeros((C,nf),np.float64)
    lo=max(P+8,t0-WIN); hi=t0
    for c in range(C):
        if hi-lo < 64: continue
        A=[]; y=[]
        for u in range(lo,hi):
            p0=huber_pred(R[c,:u],co)
            A.append(local_features(K,c,u))
            y.append((float(R[c,u])-p0)/step)
        A=np.asarray(A,np.float64); y=np.asarray(y,np.float64)
        G=A.T@A + RIDGE*np.eye(A.shape[1]); rhs=A.T@y
        try: B[c]=np.linalg.solve(G,rhs)
        except np.linalg.LinAlgError: B[c]=np.linalg.lstsq(G,rhs,rcond=None)[0]
    return B

def predictor(R,K,co,B,c,t,step,variant):
    p0=0 if t<P else huber_pred(R[c,:t],co)
    if variant=='static_huber' or t<TRAIN: return p0
    ck=float(B[c]@local_features(K,c,t))
    ck=float(np.clip(ck,-CLIP_CORR_K,CLIP_CORR_K))
    return p0 + int(np.rint(step*ck))

def legal_range(x,p,eps,step):
    lo=int(math.ceil((float(x)-eps-p)/step-1e-12))
    hi=int(math.floor((float(x)+eps-p)/step+1e-12))
    return lo,hi

def block_paths(X,R,K,co,B,counts,c,t0,step,eps,variant):
    # Enumerate the COMPLETE legal 2-sample path set. Since 2*eps is only
    # slightly larger than the tested steps, branching is tiny (normally 1-2).
    left0=int(K[c-1,t0]) if c else 0
    prev0=int(K[c,t0-1])
    p0=predictor(R,K,co,B,c,t0,step,variant)
    lo0,hi0=legal_range(X[c,t0],p0,eps,step)
    paths=[]
    for k0 in range(lo0,hi0+1):
        pr0=symbol_prob(counts,k0,prev0,left0)
        if pr0<=0: continue
        r0=p0+step*k0
        # temporary candidate state for sample 2
        R[c,t0]=r0; K[c,t0]=k0
        t1=t0+1; left1=int(K[c-1,t1]) if c else 0
        p1=predictor(R,K,co,B,c,t1,step,variant)
        lo1,hi1=legal_range(X[c,t1],p1,eps,step)
        for k1 in range(lo1,hi1+1):
            pr1=symbol_prob(counts,k1,k0,left1)
            if pr1<=0: continue
            r1=p1+step*k1
            paths.append((pr0*pr1,k0,k1,r0,r1))
        R[c,t0]=0; K[c,t0]=0
    return paths

def run_variant(X,co,eps,step,variant):
    Rp,Kp=dense_prefix(X,co,step)
    # Real prefix payload, decoded before any shared local model is inferred.
    pbytes,prep,Kpd=base.m.encode_k(Kp)
    if not np.array_equal(Kpd,Kp): raise RuntimeError(('prefix',variant,step))
    R=np.zeros((C,NT),np.int32); K=np.zeros((C,NT),np.int32)
    R[:,:TRAIN]=Rp; K[:,:TRAIN]=Kpd
    counts=np.ones((NCTX,2),np.int32)
    for t in range(TRAIN):
        for c in range(C):
            prev=int(K[c,t-1]) if t else 0; left=int(K[c-1,t]) if c else 0
            update_symbol(counts,int(K[c,t]),prev,left)
    B=np.zeros((C,13),np.float64)
    mass_bits=0.0; map_bits=0.0; nearest_bits=0.0
    nblocks=0; multi=0; empty=0; mass_values=[]; map_values=[]
    for t0 in range(TRAIN,NT,L):
        if variant=='shared_local_das' and ((t0-TRAIN)%REFIT==0):
            B=refit_betas(R,K,co,t0,step)
        for c in range(C):
            paths=block_paths(X,R,K,co,B,counts,c,t0,step,eps,variant)
            nblocks+=1
            if not paths:
                # Exact legal fallback. It is included in the actual K stream;
                # the ideal-set metric marks this block as an escape instead of
                # pretending the proposal assigned it probability.
                empty+=1
                for j in range(L):
                    t=t0+j; p=predictor(R,K,co,B,c,t,step,variant)
                    k=int(np.rint((float(X[c,t])-p)/step)); K[c,t]=k; R[c,t]=p+step*k
                    prev=int(K[c,t-1]) if t else 0; left=int(K[c-1,t]) if c else 0
                    update_symbol(counts,k,prev,left)
                continue
            if len(paths)>1: multi+=1
            mass=sum(q[0] for q in paths); best=max(paths,key=lambda q:q[0])
            mass=max(mass,1e-300); bp=max(best[0],1e-300)
            mass_bits += -math.log2(mass); map_bits += -math.log2(bp)
            mass_values.append(mass); map_values.append(bp)
            # Concrete decoder trajectory: the most probable legal path. The
            # exact constrained-address mass is reported separately; actual K
            # bytes below are fully constructive one-path bytes.
            _,k0,k1,r0,r1=best
            K[c,t0]=k0; R[c,t0]=r0; K[c,t0+1]=k1; R[c,t0+1]=r1
            for j in range(L):
                t=t0+j; prev=int(K[c,t-1]) if t else 0; left=int(K[c-1,t]) if c else 0
                pr=symbol_prob(counts,int(K[c,t]),prev,left)
                nearest_bits += -math.log2(max(pr,1e-300))
                update_symbol(counts,int(K[c,t]),prev,left)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-12): raise RuntimeError(('hard',variant,step,me,eps))
    # Independent decoder replay: it receives only K + shared base model, then
    # recomputes every local DAS coefficient from its own prior reconstruction.
    Rd=np.zeros_like(R); Kd=K.copy(); Rd[:,:TRAIN]=Rp
    Bd=np.zeros((C,13),np.float64)
    for t0 in range(TRAIN,NT,L):
        if variant=='shared_local_das' and ((t0-TRAIN)%REFIT==0):
            Bd=refit_betas(Rd,Kd,co,t0,step)
        for c in range(C):
            for j in range(L):
                t=t0+j; p=predictor(Rd,Kd,co,Bd,c,t,step,variant); Rd[c,t]=p+step*int(Kd[c,t])
    if not np.array_equal(Rd,R): raise RuntimeError(('replay',variant,step,int(np.count_nonzero(Rd!=R))))
    dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
    # Actual exact path bytes through the audited incumbent arithmetic backend.
    oldc,oldn=base.C,base.NT; base.C,base.NT=C,NT
    try: abytes,abits,anb,Kad=base.arithmetic(K)
    finally: base.C,base.NT=oldc,oldn
    if not np.array_equal(Kad,K): raise RuntimeError(('K arithmetic',variant,step))
    held=C*(NT-TRAIN); total=X.size
    ideal_payload_bits=mass_bits + empty*L*NB
    ideal_total_bytes=int(base.MODEL_BYTES)+int(pbytes)+math.ceil(ideal_payload_bits/8)+64
    return {
      'variant':variant,'step':step,'prefix_bytes':int(pbytes),'prefix_rep':prep,
      'actual_map_path_bytes':int(abytes),'actual_map_path_bps':8*abytes/total,
      'ideal_constrained_address_bytes':int(ideal_total_bytes),'ideal_constrained_address_bps':8*ideal_total_bytes/total,
      'heldout_set_mass_bps':mass_bits/held,'heldout_map_nll_bps':map_bits/held,
      'set_gain_vs_map_nll':(map_bits/mass_bits if mass_bits>0 else None),
      'empty_proposal_blocks':empty,'blocks':nblocks,'proposal_coverage':1-empty/nblocks,
      'multi_legal_path_fraction':multi/nblocks,
      'mean_legal_mass':float(np.mean(mass_values)) if mass_values else 0.0,
      'median_legal_mass':float(np.median(mass_values)) if mass_values else 0.0,
      'mean_map_path_probability':float(np.mean(map_values)) if map_values else 0.0,
      'k_zero_fraction':float(np.mean(K[:,TRAIN:]==0)),'k_std':float(np.std(K[:,TRAIN:].astype(np.float64))),
      'maxerr':dme,'local_model_bytes':0,
      'audit':'K exact arithmetic-decoded; source independently replayed; shared-local coefficients recomputed only from prior decoded R/K.'
    }

def main(path):
    base.C=C; base.NT=NT; base.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,gstd=base.m.stats(d); eps=.1*gstd; rows=[]
        print(json.dumps({'global_std':gstd,'eps':eps,'shape':list(d.shape)},indent=2),flush=True)
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            _,co=base.fits(X)
            # Matched small-shape SZ3 is only a gate reference; the main
            # comparison here is actual path bits vs exact constrained-set mass.
            sz=0
            for t0 in range(0,NT,TB):
                n,_=base.m.szrun(X[:,t0:min(t0+TB,NT)],eps); sz+=int(n)
            for variant in VARIANTS:
                for step in STEPS:
                    r=run_variant(X,co,eps,step,variant)
                    r.update({'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
                              'gain_actual_vs_sz3':sz/r['actual_map_path_bytes'],
                              'gain_ideal_set_vs_sz3':sz/r['ideal_constrained_address_bytes']})
                    rows.append(r); print(json.dumps(r,indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'rows':rows,
         'scope':'Corrected GCA fast gate. Unlike the earlier Imperial port, this does not equate GCA with residual ZSM. A Huber AR source state is augmented by a zero-bit local DAS correction whose coefficients are independently recomputed from previously decoded R/K. For each 2-sample block the encoder enumerates the COMPLETE legal reconstruction path set under the unchanged +/-epsilon source constraint. Every legal path is scored under the same decoder-known adaptive bit probability law; exact total legal-set probability mass and MAP path probability are measured. The concrete trajectory uses the MAP legal path and is fully arithmetic-coded/decoded and independently replayed; the ideal constrained-address column charges -log2(total legal mass), plus real prefix/model/framing and explicit escape cost. Thus actual_map_path is constructive, while ideal_constrained_address is a clearly labeled address-existence diagnostic, not yet a byte container. No source-derived local coefficients or hardcoded answers.'}
    json.dump(out,open('imperial_gca_corrected_constrained_address_fastgate.json','w'),indent=2)

if __name__=='__main__': main(sys.argv[1])
