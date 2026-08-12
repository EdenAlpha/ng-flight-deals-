import json,os,sys
import numpy as np

# Load the arithmetic experiment without executing its main.  The original
# prototype had three one-line `if ...; ...` statements whose semicolon suites
# accidentally made normal model writes conditional on the error branch.
# Override only those serializer/parser functions; all coding semantics remain
# otherwise identical.
src=open('research/soda_intergap_arithmetic_model.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_arithmetic_model.py','exec'),globals())


def serialize_models(ctx,models):
    # Context IDs and population totals are decoder-visible from run structure.
    # Store only alphabet size, sorted symbol deltas, and all but final count.
    out=bytearray()
    used=sorted(int(x) for x in np.unique(ctx).tolist())
    for c in used:
        m=models[c]
        sy=m['syms']
        f=m['freq']
        vput(out,len(sy))
        prev=-1
        for s0 in sy.tolist():
            s=int(s0)
            d=s if prev<0 else s-prev-1
            if d<0:
                raise RuntimeError(('symbol order',c,s,prev))
            vput(out,d)
            prev=s
        for q0 in f[:-1].tolist():
            q=int(q0)
            if q<=0:
                raise RuntimeError(('bad source freq',c,q))
            vput(out,q)
    return bytes(out)


def parse_models(ctx,b):
    ctx=np.asarray(ctx,np.int32)
    used=sorted(int(x) for x in np.unique(ctx).tolist())
    p=0
    models={}
    for c in used:
        total=int(np.sum(ctx==c))
        m,p=vget(b,p)
        if m<=0:
            raise RuntimeError(('empty model',c,m))
        sy=[]
        prev=-1
        for _ in range(m):
            d,p=vget(b,p)
            s=int(d) if prev<0 else prev+1+int(d)
            sy.append(s)
            prev=s
        f=[]
        ss=0
        for _ in range(m-1):
            q,p=vget(b,p)
            if q<=0:
                raise RuntimeError(('bad freq',c,q))
            f.append(int(q))
            ss+=int(q)
        last=total-ss
        if last<=0:
            raise RuntimeError(('bad final freq',c,last,total,ss))
        f.append(last)
        sy=np.asarray(sy,np.int32)
        f=np.asarray(f,np.int64)
        cum=np.r_[0,np.cumsum(f,dtype=np.int64)]
        if int(cum[-1])!=total:
            raise RuntimeError(('model total',c,int(cum[-1]),total))
        models[c]={'syms':sy,'freq':f,'cum':cum,'total':total}
    if p!=len(b):
        raise RuntimeError(('model trailing bytes',p,len(b)))
    return models


def main_v2(path):
    order=(0,1,2)
    X,gx,gy,dt=load(path)
    std=float(X.astype(np.float64).std())
    eps=.1*std
    step=2*eps
    rawbytes=X.nbytes
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:
        G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32)
    K=delta(G,3)
    cache=prepare_common(K,order)
    common=compress_common(cache[2])

    # Incumbent PR #167 is a real candidate, so this experiment cannot report a
    # win unless the transmitted-model arithmetic stream is actually smaller.
    bb,bparts=encode_kind(K,3,order,cache,common)
    BR=decode_kind(bb)
    if not np.array_equal(BR,K):
        raise RuntimeError('PR167 baseline decode')
    rows=[{'kind':99,'name':'PR167-singleton-relative-rank','main_bytes':len(bb),
           'parts':bparts,'blob':bb,'decoder':'baseline'}]

    for kind in (-1,0,1,2,3,4,5,6,7,8,9):
        name='global' if kind<0 else context_name(kind)
        print('ARITH CONTEXT',kind,name,flush=True)
        b,parts=encode_arith(K,kind,order,cache,common)
        R=decode_arith(b)
        if not np.array_equal(R,K):
            raise RuntimeError(('arith exact K',kind,int(np.sum(R!=K))))
        rows.append({'kind':kind,'name':parts['context_name'],'main_bytes':len(b),
                     'parts':parts,'blob':b,'decoder':'arith'})
        print(json.dumps({'kind':kind,'name':parts['context_name'],
                          'main_bytes':len(b),'model_bytes':parts['gap_model'],
                          'payload_bytes':parts['gap_arithmetic'],
                          'model_plus_payload':parts['gap_model']+parts['gap_arithmetic'],
                          'entropy_bytes':parts['entropy_bytes'],
                          'arithmetic_raw_bytes':parts['arithmetic_raw_bytes'],
                          'model_raw_bytes':parts['model_raw_bytes'],
                          'timing_bytes':parts['timing_bytes']},indent=2),flush=True)

    rows.sort(key=lambda x:x['main_bytes'])
    best=rows[0]
    RK=decode_kind(best['blob']) if best['decoder']=='baseline' else decode_arith(best['blob'])
    bo=best_out(O)
    RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):
        raise RuntimeError('arith outlier decode')
    RG=undelta(RK,3)
    recon=np.empty_like(X)
    for tid,c,l,s in tm:
        recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step)
    me=float(np.max(np.abs(X-recon)))
    szb,sze=sz3_bytes(X,eps)
    container=TOPS+best['main_bytes']+int(bo[0])
    baseline=133226
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,
         'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),
         'best':{k:v for k,v in best.items() if k!='blob'},
         'candidates':[{k:v for k,v in r.items() if k!='blob'} for r in rows],
         'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,
         'container_bytes':container,'ratio':float(rawbytes/container),
         'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),
         'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},
         'gain_vs_direct_sz3':float(szb/container),
         'strongest_verified_p75_baseline_bytes':baseline,
         'gain_vs_strongest_verified_p75_baseline':float(baseline/container),
         'prior_pr167_bytes':63657,'improvement_vs_pr167_bytes':int(63657-container)}
    print(json.dumps({k:out[k] for k in ('container_bytes','ratio','gain_vs_direct_sz3',
          'gain_vs_strongest_verified_p75_baseline','improvement_vs_pr167_bytes',
          'maxerr','valid')},indent=2),flush=True)
    json.dump(out,open('soda_intergap_arithmetic_model.json','w'),indent=2)


main_v2(sys.argv[1])
