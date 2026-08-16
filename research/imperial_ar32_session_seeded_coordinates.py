import json,sys,math
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

SEED_HEADER=8
SHEARS=(-96,-64,-48,-32,-24,-16,-12,-8,-6,-4,-3,-2,-1,0,1,2,3,4,6,8,12,16,24,32,48,64,96)
TOPK=12

# One seed selects a complete public invertible coordinate system.
# (shear, reverse_channels, reverse_time, serpentine_time)
def seed_table():
    out=[]
    for s in SHEARS:
        for rc in (0,1):
            for rt in (0,1):
                for snake in (0,1):out.append((int(s),rc,rt,snake))
    return out

SEEDS=seed_table()

def transform(A,seed):
    s,rc,rt,snake=seed;A=np.asarray(A,np.int32);C,T=A.shape;Y=np.empty_like(A)
    for oc in range(C):
        sc=C-1-oc if rc else oc
        rev=bool(rt) ^ (bool(snake) and bool(oc&1))
        j=np.arange(T,dtype=np.int64)
        logical=(-j if rev else j)
        st=np.mod(logical+s*oc,T)
        Y[oc]=A[sc,st]
    return Y

def inverse_transform(Y,seed):
    s,rc,rt,snake=seed;Y=np.asarray(Y,np.int32);C,T=Y.shape;A=np.empty_like(Y)
    for oc in range(C):
        sc=C-1-oc if rc else oc
        rev=bool(rt) ^ (bool(snake) and bool(oc&1))
        j=np.arange(T,dtype=np.int64)
        logical=(-j if rev else j)
        st=np.mod(logical+s*oc,T)
        A[sc,st]=Y[oc]
    return A

def logcomb(n,k):
    n=int(n);k=int(k)
    if k<0 or k>n:return 1e30
    if k==0 or k==n:return 0.0
    return (math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1))/math.log(2.0)

def type_cost(B,fam):
    B=np.asarray(B,np.uint8);C,T=B.shape
    l=np.zeros_like(B);l[1:]=B[:-1]
    u=np.zeros_like(B);u[:,1:]=B[:,:-1]
    if fam=='global':ids=np.zeros(B.size,np.int16);nctx=1
    elif fam=='lu':ids=(l|(u<<1)).ravel();nctx=4
    elif fam=='lud':
        d=np.zeros_like(B);d[1:,1:]=B[:-1,:-1];ids=(l|(u<<1)|(d<<2)).ravel();nctx=8
    elif fam=='luu2':
        u2=np.zeros_like(B);u2[:,2:]=B[:,:-2];ids=(l|(u<<1)|(u2<<2)).ravel();nctx=8
    else:raise ValueError(fam)
    y=B.ravel().astype(np.int64);n=np.bincount(ids,minlength=nctx);k=np.bincount(ids,weights=y,minlength=nctx)
    bits=0.0
    for nn,kk in zip(n,k):bits+=logcomb(int(nn),int(round(kk)))
    # Conservative screening proxy for fully charged n/k state fingerprints and selector.
    bits += 16.0*nctx + 16.0
    return bits

def screen_score(K):
    u=m.zig(np.asarray(K,np.int32));mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());score=0.0
    for bit in range(nb-1,-1,-1):
        B=((u>>bit)&1).astype(np.uint8)
        score += min(type_cost(B,x) for x in ('global','lu','lud','luu2'))
    return score

def exact_seed_frame(K,seed_id):
    seed=SEEDS[int(seed_id)];Y=transform(K,seed);b,rep,Yd,detail=ac.autocomplexity_frame(Y)
    Kd=inverse_transform(Yd,seed)
    if not np.array_equal(Kd,K):raise RuntimeError(('seed inverse',seed_id,seed))
    return int(b)+SEED_HEADER,'session_seeded_'+rep,Kd,{'seed_id':int(seed_id),'seed':list(seed),'seed_header':SEED_HEADER,'inner_bytes':int(b),'planes':detail}

def validate(X,eps,mb,cd,R,K,seed_id):
    fb,rep,Kd,detail=exact_seed_frame(K,seed_id);Rd=np.zeros_like(R)
    for cc in range(g.C):
        for t in range(g.T):Rd[cc,t]=g.ar.predict_hist(Rd,cc,t,cd,g.P,'shared')+base.STEP*int(Kd[cc,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('AR replay seed',seed_id))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard seed',seed_id,me,eps))
    total=mb+fb+base.HEADER
    return {'seed_id':int(seed_id),'seed':list(SEEDS[seed_id]),'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(fb),'inner_address_bytes':int(fb-SEED_HEADER),'seed_header_bytes':SEED_HEADER,'maxerr':me,'rep':rep,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=base.build_ar32(X)
    # Exact current incumbent with no coordinate wrapper.
    ab,arep,AK,ad=ac.autocomplexity_frame(K)
    if not np.array_equal(AK,K):raise RuntimeError('identity auto replay')
    incumbent={'bytes':int(mb+ab+base.HEADER),'bps':8*(mb+ab+base.HEADER)/X.size,'model_bytes':int(mb),'address_bytes':int(ab),'rep':arep,'maxerr':float(np.max(np.abs(X-R.astype(np.float64))))}
    screens=[]
    for sid,seed in enumerate(SEEDS):
        Y=transform(K,seed);sc=screen_score(Y);screens.append((float(sc),sid))
    screens.sort();cand=[];seen=set()
    # Always include identity coordinate seed plus the strongest proxy candidates.
    identity=SEEDS.index((0,0,0,0));ids=[identity]+[sid for _,sid in screens[:TOPK]]
    for sid in ids:
        if sid in seen:continue
        seen.add(sid);z=validate(X,eps,mb,cd,R,K,sid);z['screen_bits']=next(sc for sc,ss in screens if ss==sid);z['gain_vs_current']=incumbent['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];cand.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    cand.sort(key=lambda x:x['bytes']);best=cand[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':base.STEP,'seed_count':len(SEEDS),'topk_exact':TOPK,'seed_header_bytes':SEED_HEADER,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'current_ar32_autocomplexity':incumbent,'screen_top':[{'screen_bits':sc,'seed_id':sid,'seed':list(SEEDS[sid])} for sc,sid in screens[:32]],'candidates':cand,'best':best,'scope':'SESSION-SEEDED GPS coordinate-search gate on the exact incumbent AR32 innovation field. The AR32 model, step267, K values, reconstruction and hard-error contract are frozen. A public seed indexes one of 216 invertible spacetime coordinate systems built from channel reversal, time reversal, optional serpentine time direction and a channel-dependent circular time shear. Encoder search is computation only. A cheap exact-type-class proxy screens every public seed, then the best candidates are physically serialized with the exact AUTO-COMPLEXITY rank stream. The stored seed is charged by an 8-byte wrapper. Decoder reads the seed, decodes the transformed innovation address, deterministically inverts the coordinate map to identical K, and recursively reproduces identical AR32 R. No dataset label, target-trained probability table, ideal entropy or uncharged transform is used. This is a direct field-data implementation of the uploaded NOVA Fast principle: search over shared coordinate configurations, transmit the winning coordinate identifier plus irreducible correction/address.'}
    json.dump(out,open('imperial_ar32_session_seeded_coordinates.json','w'),indent=2)
    print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_seed':best['seed'],'current_bytes':incumbent['bytes'],'sz3_bytes':int(szb),'gain_current':incumbent['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
