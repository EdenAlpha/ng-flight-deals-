import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

GROUPS=(32,16,8,4,2,1)
ORDERS=(4,6,8,10,12)
TRAIN=256
STEP=267
HEADER=32
SELECTOR=1


def fit_groups(X,p,gs):
    models=[];cost=0
    for c0 in range(0,X.shape[0],gs):
        c1=min(X.shape[0],c0+gs)
        co=ar.fit_shared(X[c0:c1,:TRAIN],p);mb,cd=ar.model_frame(co)
        models.append((c0,c1,cd,int(mb)));cost+=int(mb)
    return models,cost

def coef_for(models,c):
    for c0,c1,cd,mb in models:
        if c0<=c<c1:return cd
    raise RuntimeError(c)

def encode_one(X,eps,p,gs):
    models,model_bytes=fit_groups(X,p,gs)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        cd=coef_for(models,c)
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,p,'shared')
            k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):return None
    pb,rep,Kd,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('rank replay',p,gs))
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        cd=coef_for(models,c)
        for t in range(X.shape[1]):
            Rd[c,t]=ar.predict_hist(Rd,c,t,cd,p,'shared')+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('causal replay',p,gs))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',p,gs,mer))
    total=model_bytes+int(pb)+HEADER+SELECTOR
    return {'group_size':int(gs),'num_models':len(models),'order':int(p),'train':TRAIN,'step':STEP,'bytes':total,'bps':8*total/X.size,'model_bytes':model_bytes,'payload_bytes':int(pb),'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);floor=23448;rows=[]
    for gs in GROUPS:
        for p in ORDERS:
            r=encode_one(X,eps,p,gs)
            if r is None:continue
            r['gain_vs_old_ar32']=old['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];r['delta_vs_ar8_shared_floor']=r['bytes']-floor
            rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'group_sizes':list(GROUPS),'orders':list(ORDERS),'train':TRAIN,'step':STEP,'ar8_shared_floor':floor,'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'NOVA coordinate-family search after PR564 showed shared AR8 + exact restricted ranking beats the old AR32 codec. Earlier per-sensor/grouped AR models were judged under a different residual representation and much larger model orders. This gate re-tests contiguous channel-group AR laws under the exact restricted-address objective. Each group model is fitted only from the same first 256 samples of its channels, float32 serialized/decoded and fully charged. The complete K field is physically restricted-ranked, independently decoded, the grouped causal reconstruction is replayed, and the unchanged source hard-error contract is verified. A one-byte public configuration selector is charged. No uncharged per-channel routing, oracle metadata or ideal rates.'}
    json.dump(out,open('imperial_nova_grouped_ar_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_group_size':best['group_size'],'best_order':best['order'],'best_bytes':best['bytes'],'shared_ar8_floor':floor,'delta_vs_floor':best['bytes']-floor,'old_ar32':old['bytes'],'sz3':int(szb),'gain_vs_old_ar32':old['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
