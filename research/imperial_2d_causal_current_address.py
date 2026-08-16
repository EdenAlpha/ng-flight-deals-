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
 't1_l':('t1','l1'),
 't1_l_d':('t1','l1','d1'),
 't2_l':('t1','t2','l1'),
 't2_l_d':('t1','t2','l1','d1'),
 't2_l2_d':('t1','t2','l1','l2','d1'),
 'causal6':('t1','t2','l1','l2','d1','d2'),
}
TRAINS=(64,256,1024)
EXACT_TOP=10


def val(X,c,t,f):
    if f=='t1':return X[c,t-1] if t>0 else 0.0
    if f=='t2':return X[c,t-2] if t>1 else 0.0
    if f=='l1':return X[c-1,t] if c>0 else 0.0
    if f=='l2':return X[c-2,t] if c>1 else 0.0
    if f=='d1':return X[c-1,t-1] if c>0 and t>0 else 0.0
    if f=='d2':return X[c-1,t-2] if c>0 and t>1 else 0.0
    raise ValueError(f)

def fit(X,features,train):
    nt=min(train,X.shape[1]);rows=[];yy=[]
    for c in range(X.shape[0]):
        for t in range(nt):
            rows.append([val(X,c,t,f) for f in features]+[1.0]);yy.append(float(X[c,t]))
    M=np.asarray(rows,np.float64);Y=np.asarray(yy,np.float64)
    return np.linalg.lstsq(M,Y,rcond=1e-8)[0].astype(np.float32)

def pred(R,c,t,co,features):
    s=float(co[-1])
    for j,f in enumerate(features):s+=float(co[j])*float(val(R,c,t,f))
    if not math.isfinite(s):raise RuntimeError('nonfinite')
    return int(np.rint(s))

def build(X,co,features):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=pred(R,c,t,co,features);k=int(np.rint((float(X[c,t])-p)/STEP));R[c,t]=p+STEP*k;K[c,t]=k
    return R,K

def model_rt(co):
    buf,name=fair.encode_model(co);cod,pos=fair.decode_model(buf,0,len(co))
    if pos!=len(buf) or not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)):raise RuntimeError('model replay')
    return buf,name,cod

def replay(X,co,features,K,eps):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=pred(R,c,t,co,features)+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return R,me

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);screen=[];cache={}
    # exact incumbent is kept as a forced candidate
    baseco=np.asarray(fair.fit(X,1,'prefix64'),np.float32);basebuf,basename,basecod=model_rt(baseco);baseR,baseK=build(X,basecod,CONFIGS['t1'])
    cache[('t1',64)]=(basecod,baseK,baseR,basebuf,basename)
    for name,features in CONFIGS.items():
        for tr in TRAINS:
            if name=='t1' and tr==64:co=baseco
            else:co=fit(X,features,tr)
            buf,mname,cod=model_rt(co);R,K=build(X,cod,features);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('screen hard',name,tr,me,eps))
            legacy=int(m.encode_k(K)[0]);row={'model':name,'train':tr,'features':list(features),'model_bytes':len(buf),'model_rep':mname,'legacy_bytes':legacy,'screen_total':fair.COMMON_HEADER+1+len(buf)+legacy,'maxerr':me,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0))}
            screen.append(row);cache[(name,tr)]=(cod,K,R,buf,mname);print(json.dumps({'screen':row}),flush=True)
    screen.sort(key=lambda r:r['screen_total']);selected={(r['model'],r['train']) for r in screen[:EXACT_TOP]};selected.add(('t1',64))
    rows=[]
    for r in screen:
        key=(r['model'],r['train'])
        if key not in selected:continue
        name,tr=key;features=CONFIGS[name];cod,K,R,buf,mname=cache[key];field,_,Kd,detail=A.hybrid_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',name,tr))
        Rd,me=replay(X,cod,features,Kd,eps)
        if not np.array_equal(Rd,R):raise RuntimeError(('R replay',name,tr))
        total=fair.COMMON_HEADER+1+len(buf)+int(field);q={**r,'bytes':int(total),'field_bytes':int(field),'maxerr':me,'coefficients':cod.tolist(),'field_detail':detail};rows.append(q);print(json.dumps({k:v for k,v in q.items() if k not in ('field_detail','coefficients')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];base=next(r for r in rows if r['model']=='t1' and r['train']==64)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'configs':{k:list(v) for k,v in CONFIGS.items()},'trains':list(TRAINS),'exact_top':EXACT_TOP,
         'screen':screen,'selected_exact':[list(x) for x in sorted(selected)],'rows':rows,'baseline':base,'best':best,'sz3':{'bytes':int(szb),'orientation':ori},
         'scope':'Current-address retest of tiny learned 2-D causal predictors. Candidate float32 models use temporal reconstructed history plus already reconstructed previous-channel and diagonal states in a decoder-valid channel-major order. Coefficients are fitted from declared source prefixes and fully serialized/decoded; step267 guarantees the unchanged hard error after nearest innovation correction. A cheap legacy-codec screen only allocates exact current-address evaluations. Exact finalists materialize/decode the full coarse-prefix+mixture K stream and causally replay the source with identical 32-byte header + one-byte public model selector accounting.'}
    json.dump(out,open('imperial_2d_causal_current_address.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base['bytes'],'best':best['bytes'],'delta':best['bytes']-base['bytes'],'model':best['model'],'train':best['train'],'model_bytes':best['model_bytes'],'field_bytes':best['field_bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
