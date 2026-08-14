import numpy as np


def _ar_key(c):
    return (int(c.get('ar_order',32)),int(c.get('train_samples',1024)),int(c.get('huber_iterations',6)))

def _prepare_ar(g,X,eps,cand,source_integer):
    X=np.asarray(X);p,train,it=_ar_key(cand);train=min(train,X.shape[1]);mode,step=g.ar_step(eps,bool(source_integer));co=g.fit_huber_ar(X,p,train,step,it);R,K=g.ar_quantize(X,co,p,step,mode==1);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
    if me>float(eps):raise RuntimeError(('AR hard bound',me,float(eps)))
    return {'X':X,'p':p,'train':train,'mode':mode,'step':step,'co':co,'K':K,'maxerr':me,'zero_fraction':float(np.mean(K==0))}

def _ar_blob(g,prep,W):
    bb,nbit=g.encode_zsm(prep['K'],int(W));co=np.asarray(prep['co'],dtype='<f4');cob=co.tobytes();hdr=g.struct.pack(g.AR_HDR,g.AR_MAGIC,1,int(prep['mode']),int(prep['p']),int(prep['K'].shape[0]),int(prep['K'].shape[1]),int(prep['train']),int(W),float(prep['step']),int(nbit),len(bb));blob=hdr+cob+bb
    meta={'maxerr':prep['maxerr'],'zero_fraction':prep['zero_fraction'],'step':prep['step']}
    return blob,meta

def screen_candidates(g,X,eps,cfg,source_integer=False):
    X=np.asarray(X);ns=min(int(cfg['selector']['screen_samples']),X.shape[1]);P=X[:,:ns]
    if ns<=32:raise ValueError('screen prefix too short')
    rows=[];cache={}
    for cand in sorted(cfg['candidates'],key=lambda c:int(c['id'])):
        try:
            if cand['engine']=='ar32_zsm':
                key=_ar_key(cand)
                if key not in cache:cache[key]=_prepare_ar(g,P,eps,cand,source_integer)
                bb,meta=_ar_blob(g,cache[key],int(cand['zsm_window']))
            elif cand['engine']=='spectral_topn':bb,meta=g.encode_spectral_topn(P,eps,int(cand['time_block']),float(cand['fraction']))
            else:raise ValueError(cand['engine'])
            rows.append({'id':int(cand['id']),'engine':cand['engine'],'bytes':len(bb),'samples':int(P.size),'bps':8.*len(bb)/P.size,'valid':True,'meta':meta})
        except Exception as e:rows.append({'id':int(cand['id']),'engine':cand['engine'],'bytes':None,'samples':int(P.size),'bps':float('inf'),'valid':False,'error':repr(e)})
    valid=[r for r in rows if r['valid']]
    if not valid:raise RuntimeError(('no valid candidate',rows))
    return min(valid,key=lambda r:(r['bps'],r['id'])),rows

def encode_portfolio(g,X,eps,cfg,source_integer=False):
    best,screen=screen_candidates(g,X,eps,cfg,source_integer);cand={int(c['id']):c for c in cfg['candidates']}[int(best['id'])]
    if cand['engine']=='ar32_zsm':body,meta=_ar_blob(g,_prepare_ar(g,X,eps,cand,source_integer),int(cand['zsm_window']))
    elif cand['engine']=='spectral_topn':body,meta=g.encode_spectral_topn(X,eps,int(cand['time_block']),float(cand['fraction']))
    else:raise ValueError(cand['engine'])
    blob=bytes([int(best['id'])])+body;R=g.decode_portfolio(blob);me=float(np.max(np.abs(np.asarray(X,np.float64)-np.asarray(R,np.float64))))
    if me>float(eps):raise RuntimeError(('portfolio hard bound',me,float(eps)))
    return blob,{'selected_id':int(best['id']),'selected_engine':cand['engine'],'screen':screen,'maxerr':me,'engine_meta':meta}

def equivalence(g,cfg,seed=97531):
    rng=np.random.default_rng(seed);cases=[]
    # Small enough to keep the reference test inexpensive, large enough to exercise all candidates.
    for name,X,isint in [
        ('float',rng.normal(size=(12,768)).astype(np.float32),False),
        ('integer',rng.integers(-2000,2001,size=(12,768),dtype=np.int16),True),
    ]:
        eps=.1*float(X.astype(np.float64).std())
        a,ma=g.encode_portfolio(X,eps,cfg,isint);b,mb=encode_portfolio(g,X,eps,cfg,isint)
        if a!=b:raise AssertionError((name,'portfolio bytes differ',len(a),len(b),ma['selected_id'],mb['selected_id']))
        if ma['screen']!=mb['screen']:raise AssertionError((name,'screen rows differ',ma['screen'],mb['screen']))
        cases.append({'name':name,'bytes':len(a),'selected_id':ma['selected_id'],'engine':ma['selected_engine']})
    return cases
