import json,sys
import h5py,numpy as np
import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=cm.a
STEP=267
GROUPS=(32,16,8,4,2,1)
TRAINS=(64,128,256)
EXACT_TOP=10


def fit_groups(X,gs,train):
    co=[]
    for c0 in range(0,X.shape[0],gs):co.append(fair.ar.fit_shared(X[c0:c0+gs,:train],1))
    return np.asarray(co,np.float32)

def build(X,co,gs):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        q=co[c//gs];a=float(q[0]);b=float(q[1])
        for t in range(X.shape[1]):
            pred=0 if t==0 else int(np.rint(b+a*float(R[c,t-1])))
            k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    return R,K

def model_roundtrip(co):
    flat=np.asarray(co,np.float32).reshape(-1);buf,name=fair.encode_model(flat);cod,pos=fair.decode_model(buf,0,flat.size)
    if pos!=len(buf) or not np.array_equal(cod.view(np.uint32),flat.view(np.uint32)):raise RuntimeError('model replay')
    return buf,name,cod.reshape(co.shape)

def replay(X,co,gs,K,eps):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        q=co[c//gs];a=float(q[0]);b=float(q[1])
        for t in range(K.shape[1]):
            pred=0 if t==0 else int(np.rint(b+a*float(R[c,t-1])))
            R[c,t]=pred+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',gs,me,eps))
    return R,me

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);screen=[];cache={}
    for gs in GROUPS:
        for tr in TRAINS:
            co=fit_groups(X,gs,tr);model,mname,cod=model_roundtrip(co);R,K=build(X,cod,gs);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+5e-6):raise RuntimeError(('screen hard',gs,tr,me,eps))
            legacy=int(m.encode_k(K)[0]);row={'group_size':gs,'train':tr,'model_bytes':len(model),'model_rep':mname,'legacy_bytes':legacy,'screen_total':fair.COMMON_HEADER+1+len(model)+legacy,'maxerr':me}
            screen.append(row);cache[(gs,tr)]=(cod,K,R);print(json.dumps({'screen':row}),flush=True)
    screen.sort(key=lambda r:r['screen_total']);selected={(r['group_size'],r['train']) for r in screen[:EXACT_TOP]};selected.add((32,64))
    rows=[]
    for r in screen:
        key=(r['group_size'],r['train'])
        if key not in selected:continue
        gs,tr=key;cod,K,R=cache[key];model,mname,_=model_roundtrip(cod);field,_,Kd,detail=A.hybrid_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',gs,tr))
        Rd,me=replay(X,cod,gs,Kd,eps)
        if not np.array_equal(Rd,R):raise RuntimeError(('R replay',gs,tr))
        total=fair.COMMON_HEADER+1+len(model)+int(field)
        q={**r,'bytes':int(total),'field_bytes':int(field),'maxerr':me,'field_detail':detail};rows.append(q);print(json.dumps({k:v for k,v in q.items() if k!='field_detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0];base=next(r for r in rows if r['group_size']==32 and r['train']==64)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'group_sizes':list(GROUPS),'train_prefixes':list(TRAINS),'exact_top':EXACT_TOP,
         'screen':screen,'selected_exact':[list(x) for x in sorted(selected)],'rows':rows,'best':best,'baseline':base,'sz3':{'bytes':int(szb),'orientation':ori},
         'scope':'Retest of grouped AR1 coordinate systems under the current strict coarse-prefix+mixture address. Earlier grouped-model experiments used weaker residual/rank languages. Each candidate partitions the 32 hard channels into fixed contiguous groups, fits one AR1+intercept from the declared prefix per group, serializes/decodes every float32 model coefficient, and reconstructs with step267. A cheap legacy-codec screen only allocates exact-address compute; it cannot win. Exact finalists materialize/decode the complete current address, causally replay reconstruction and satisfy unchanged hard error. Common 32-byte header and one-byte public configuration selector are charged.'}
    json.dump(out,open('imperial_grouped_ar1_coarse_mixture.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base['bytes'],'best':best['bytes'],'delta':best['bytes']-base['bytes'],'group_size':best['group_size'],'train':best['train'],'model':best['model_bytes'],'field':best['field_bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
