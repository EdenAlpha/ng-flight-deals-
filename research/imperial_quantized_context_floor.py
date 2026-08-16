import json, math, sys
import h5py
import numpy as np

C=128; NT=30000; C0=512; TRAIN=8192; STEP=267
CURRENT_BYTES=2468803; MATCHED_SZ3=2767977
OFF=512; ALPH=1024; LAMBDA=16.0


def pack_context(features):
    if len(features) > 5:
        raise ValueError('at most five 10-bit fields')
    key=np.zeros(features[0].size,dtype=np.uint64)
    for i,f in enumerate(features):
        v=np.asarray(f,dtype=np.int64).reshape(-1)
        if int(v.min()) < -OFF or int(v.max()) >= OFF:
            raise RuntimeError(('context range',int(v.min()),int(v.max())))
        key |= (v+OFF).astype(np.uint64) << np.uint64(10*i)
    return key


def lookup_counts(u,c,q):
    idx=np.searchsorted(u,q)
    out=np.zeros(len(q),dtype=np.int64)
    ok=idx < len(u)
    ii=idx[ok]
    qq=q[ok]
    same=u[ii] == qq
    pos=np.flatnonzero(ok)[same]
    out[pos]=c[ii[same]]
    return out


def fit_rate(train_ctx,train_sym,test_ctx,test_sym,k,lam=LAMBDA):
    ts=np.asarray(train_sym,dtype=np.int64).reshape(-1)
    vs=np.asarray(test_sym,dtype=np.int64).reshape(-1)
    if ts.min() < -OFF or ts.max() >= OFF or vs.min() < -OFF or vs.max() >= OFF:
        raise RuntimeError(('symbol range',int(ts.min()),int(ts.max()),int(vs.min()),int(vs.max())))
    # Global smoothed distribution is the backoff model.
    gc=np.bincount((ts+OFF).astype(np.int64),minlength=ALPH).astype(np.float64)
    gp=(gc+0.5)/(len(ts)+0.5*ALPH)
    if k==0:
        p=gp[(vs+OFF).astype(np.int64)]
        return float(np.mean(-np.log2(p))),1.0,float(np.mean(gc[(vs+OFF).astype(np.int64)]>0))
    cu,cc=np.unique(train_ctx,return_counts=True)
    shift=np.uint64(10*k)
    train_pair=train_ctx | ((ts+OFF).astype(np.uint64) << shift)
    test_pair=test_ctx | ((vs+OFF).astype(np.uint64) << shift)
    pu,pc=np.unique(train_pair,return_counts=True)
    nctx=lookup_counts(cu,cc,test_ctx).astype(np.float64)
    npair=lookup_counts(pu,pc,test_pair).astype(np.float64)
    pglobal=gp[(vs+OFF).astype(np.int64)]
    p=(npair+lam*pglobal)/(nctx+lam)
    bps=float(np.mean(-np.log2(p)))
    return bps,float(np.mean(nctx>0)),float(np.mean(npair>0))


def arrays(q,t0,t1,family,coarse=1):
    # Target is temporal increment Q[c,t]-Q[c,t-1] for interior channels.
    D=np.diff(q,axis=1)
    target=D[1:-1,t0-1:t1-1]
    prev1=D[1:-1,t0-2:t1-2]
    prev2=D[1:-1,t0-3:t1-3]
    left_cur=D[:-2,t0-1:t1-1]
    left_prev=D[:-2,t0-2:t1-2]
    right_prev=D[2:,t0-2:t1-2]
    qprev=q[1:-1,t0-1:t1-1]
    right_cur=D[2:,t0-1:t1-1]
    qfuture=q[1:-1,t0+1:t1+1]
    fs={
      'temporal1':[prev1],
      'temporal2':[prev1,prev2],
      'causal3':[prev1,prev2,left_cur],
      'causal_wave5':[prev1,prev2,left_cur,left_prev,right_prev],
      'causal_level5':[prev1,prev2,left_cur,right_prev,qprev],
      'oracle5':[prev1,prev2,left_cur,right_cur,qfuture],
      'oracle_twosided5':[qprev,qfuture,left_cur,right_cur,right_prev],
    }[family]
    if coarse>1:
        fs=[np.floor_divide(f,coarse) for f in fs]
    return fs,target


def evaluate(q,family,coarse=1):
    tf,ts=arrays(q,3,TRAIN,family,coarse)
    vf,vs=arrays(q,TRAIN,NT-1,family,coarse)
    tc=pack_context(tf); vc=pack_context(vf)
    bps,cov,pair=fit_rate(tc,ts,vc,vs,len(tf))
    row={
      'family':family,'coarse':coarse,'heldout_bps':bps,
      'context_coverage':cov,'pair_coverage':pair,
      'equivalent_full_bytes':bps*(C*NT)/8.0,
      'train_symbols':int(ts.size),'test_symbols':int(vs.size),
      'lambda':LAMBDA,
    }
    print(json.dumps(row),flush=True)
    return row


def main(path):
    with h5py.File(path,'r') as hf:
        X=np.asarray(hf['Acoustic'][:,C0:C0+C],np.int32).T
    q=np.rint(X.astype(np.float64)/STEP).astype(np.int32)
    recon=q.astype(np.int64)*STEP
    maxerr=float(np.max(np.abs(X.astype(np.int64)-recon)))
    if maxerr>133.0: raise RuntimeError(('hard error',maxerr))
    target_bps=8*(MATCHED_SZ3/2)/(C*NT)
    current_bps=8*CURRENT_BYTES/(C*NT)

    # Global held-out increment rate.
    _,train_sym=arrays(q,3,TRAIN,'temporal1',1)
    _,test_sym=arrays(q,TRAIN,NT-1,'temporal1',1)
    gbps,_,gpair=fit_rate(None,train_sym,None,test_sym,0)
    rows=[{'family':'global_increment','coarse':1,'heldout_bps':gbps,'context_coverage':1.0,'pair_coverage':gpair,'equivalent_full_bytes':gbps*(C*NT)/8.0,'train_symbols':int(train_sym.size),'test_symbols':int(test_sym.size),'lambda':None}]
    print(json.dumps(rows[-1]),flush=True)

    specs=[
      ('temporal1',1),('temporal2',1),('causal3',1),
      ('causal_wave5',1),('causal_wave5',2),('causal_wave5',4),
      ('causal_level5',1),('causal_level5',2),('causal_level5',4),
      ('oracle5',1),('oracle5',2),('oracle5',4),
      ('oracle_twosided5',1),('oracle_twosided5',2),('oracle_twosided5',4),
    ]
    for fam,coarse in specs:
        rows.append(evaluate(q,fam,coarse))

    causal=[r for r in rows if not r['family'].startswith('oracle')]
    oracle=[r for r in rows if r['family'].startswith('oracle')]
    best_causal=min(causal,key=lambda r:r['heldout_bps'])
    best_oracle=min(oracle,key=lambda r:r['heldout_bps'])
    out={
      'shape':[C,NT],'samples':C*NT,'step':STEP,'maxerr':maxerr,
      'current_bytes':CURRENT_BYTES,'current_bps':current_bps,
      'matched_sz3_bytes':MATCHED_SZ3,'target_2x_bytes':MATCHED_SZ3/2,
      'target_2x_bps':target_bps,'rows':rows,
      'best_causal':best_causal,'best_oracle':best_oracle,
      'oracle_advantage_bps':best_causal['heldout_bps']-best_oracle['heldout_bps'],
      'gap_best_oracle_to_2x_target_bps':best_oracle['heldout_bps']-target_bps,
      'interpretation':'Held-out cross entropy of the exact legal step-267 scalar reconstruction increments. Context tables are fitted only on t<8192 and evaluated on later samples with global interpolation/backoff. Equivalent bytes are diagnostic cross-entropy projections, not serialized codec sizes. Oracle families deliberately use noncausal right-current/future information and cannot be used as codecs; their purpose is to expose hidden local structure. Exact/coarse context coverage is reported so sparse memorization cannot masquerade as a low rate.'
    }
    json.dump(out,open('imperial_quantized_context_floor.json','w'),indent=2)
    print(json.dumps({'summary':{'current_bps':current_bps,'target_2x_bps':target_bps,'best_causal':best_causal,'best_oracle':best_oracle,'oracle_advantage_bps':out['oracle_advantage_bps'],'gap_oracle_to_target_bps':out['gap_best_oracle_to_2x_target_bps']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
