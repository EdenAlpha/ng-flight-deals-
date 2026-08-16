import json,sys,math
import h5py,numpy as np
import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=cm.a
STEP=267
CONFIGS={
 't1':('t1',),
 'wave_lap1':('t1','t2','lap1'),
 'wave_lap12':('t1','t2','lap1','lap2'),
 'wave_lr1':('t1','t2','left1','right1'),
 'wave_lr12':('t1','t2','left1','right1','left2','right2'),
 'wave_lap_adv':('t1','t2','lap1','leftcur'),
 'wave_lr_adv':('t1','t2','left1','right1','leftcur'),
 'wave_full':('t1','t2','left1','right1','left2','right2','leftcur'),
}
TRAINS=(64,128,256,512,1024)
EXACT_TOP=12


def raw(X,c,t,f):
    nc=X.shape[0]
    t1=float(X[c,t-1]) if t>0 else 0.0
    t2=float(X[c,t-2]) if t>1 else 0.0
    l1=float(X[c-1,t-1]) if c>0 and t>0 else t1
    r1=float(X[c+1,t-1]) if c+1<nc and t>0 else t1
    l2=float(X[c-1,t-2]) if c>0 and t>1 else t2
    r2=float(X[c+1,t-2]) if c+1<nc and t>1 else t2
    if f=='t1':return t1
    if f=='t2':return t2
    if f=='left1':return l1
    if f=='right1':return r1
    if f=='left2':return l2
    if f=='right2':return r2
    if f=='lap1':return l1-2.0*t1+r1
    if f=='lap2':return l2-2.0*t2+r2
    if f=='leftcur':return float(X[c-1,t]) if c>0 else t1
    raise ValueError(f)


def fit(X,features,train):
    nt=min(train,X.shape[1]);rows=[];yy=[]
    # t=0 is a public zero-predictor cold start. Fit only decoder-active times.
    for t in range(1,nt):
        for c in range(X.shape[0]):
            rows.append([raw(X,c,t,f) for f in features]+[1.0]);yy.append(float(X[c,t]))
    M=np.asarray(rows,np.float64);Y=np.asarray(yy,np.float64)
    return np.linalg.lstsq(M,Y,rcond=1e-8)[0].astype(np.float32)


def pred(R,c,t,co,features):
    if t==0:return 0
    s=float(co[-1])
    for j,f in enumerate(features):s+=float(co[j])*raw(R,c,t,f)
    if not math.isfinite(s):raise RuntimeError('nonfinite predictor')
    return int(np.rint(s))


def build(X,co,features):
    # Time-major is the decoder contract: at time t all channels from t-1/t-2 are
    # known, and c-1,t is also known. c+1,t is never used.
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=pred(R,c,t,co,features);k=int(np.rint((float(X[c,t])-p)/STEP));R[c,t]=p+STEP*k;K[c,t]=k
    return R,K


def model_rt(co):
    buf,name=fair.encode_model(np.asarray(co,np.float32));cod,pos=fair.decode_model(buf,0,len(co))
    if pos!=len(buf) or not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('model replay')
    return buf,name,cod


def replay(X,co,features,K,eps):
    R=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):R[c,t]=pred(R,c,t,co,features)+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return R,me


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);screen=[];cache={}
    baseco=np.asarray(fair.fit(X,1,'prefix64'),np.float32);basebuf,basename,basecod=model_rt(baseco)
    baseR,baseK=build(X,basecod,CONFIGS['t1']);refR,refK=fair.build(X,1,basecod)
    if not np.array_equal(baseK,refK) or not np.array_equal(baseR,refR):raise RuntimeError('baseline contract mismatch')
    cache[('t1',64)]=(basecod,baseK,baseR,basebuf,basename)
    for name,features in CONFIGS.items():
        for tr in TRAINS:
            if name=='t1' and tr==64:co=baseco
            else:co=fit(X,features,tr)
            buf,mname,cod=model_rt(co);R,K=build(X,cod,features);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('screen hard',name,tr,me,eps))
            legacy=int(m.encode_k(K)[0])
            row={'model':name,'train':tr,'features':list(features),'model_bytes':len(buf),'model_rep':mname,
                 'legacy_bytes':legacy,'screen_total':fair.COMMON_HEADER+1+len(buf)+legacy,'maxerr':me,
                 'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0))}
            screen.append(row);cache[(name,tr)]=(cod,K,R,buf,mname);print(json.dumps({'screen':row}),flush=True)
    screen.sort(key=lambda r:r['screen_total']);selected={(r['model'],r['train']) for r in screen[:EXACT_TOP]};selected.add(('t1',64))
    rows=[]
    for r in screen:
        key=(r['model'],r['train'])
        if key not in selected:continue
        name,tr=key;features=CONFIGS[name];cod,K,R,buf,mname=cache[key]
        field,_,Kd,detail=A.hybrid_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',name,tr))
        Rd,me=replay(X,cod,features,Kd,eps)
        if not np.array_equal(Rd,R):raise RuntimeError(('R replay',name,tr))
        total=fair.COMMON_HEADER+1+len(buf)+int(field)
        q={**r,'bytes':int(total),'field_bytes':int(field),'coefficients':cod.tolist(),'maxerr':me,'field_detail':detail}
        rows.append(q);print(json.dumps({k:v for k,v in q.items() if k not in ('field_detail','coefficients')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];base=next(r for r in rows if r['model']=='t1' and r['train']==64)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,
         'decoder_order':'time_major_then_channel','configs':{k:list(v) for k,v in CONFIGS.items()},'trains':list(TRAINS),'exact_top':EXACT_TOP,
         'screen':screen,'selected_exact':[list(x) for x in sorted(selected)],'rows':rows,'baseline':base,'best':best,
         'sz3':{'bytes':int(szb),'orientation':ori},
         'scope':'Physics-shaped coordinate-system retest under the exact current coarse-prefix+mixture address. The decoder reconstructs in time-major order, making both spatial neighbors from t-1/t-2 available before time t and the current-time left channel available causally. Tiny float32 models combine temporal state with symmetric spatial Laplacians or left/right wave stencils; no current-time right neighbor is used. t=0 is the same public zero cold start as the incumbent. Models are fitted from declared source prefixes and fully serialized/decoded. Step267 nearest correction preserves the unchanged hard error. A legacy-codec screen only allocates exact current-address compute; exact finalists K-decode, time-major replay, and are ranked solely by physical bytes with the identical 32-byte header and one-byte public model selector.'}
    json.dump(out,open('imperial_wave_stencil_current_address.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base['bytes'],'best':best['bytes'],'delta':best['bytes']-base['bytes'],
          'model':best['model'],'train':best['train'],'model_bytes':best['model_bytes'],'field_bytes':best['field_bytes'],
          'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
