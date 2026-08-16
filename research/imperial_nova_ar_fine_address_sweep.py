import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

ORDERS=tuple(range(1,13))
TRAINS=(64,96,128,160,192,256,384,512,768,1024)
STEP=267
HEADER=32
SELECTOR=1


def encode_one(X,eps,p,train):
    co=ar.fit_shared(X[:,:train],p);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared')
            k=int(np.rint((float(X[c,t])-pred)/STEP))
            R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):return None
    pb,rep,Kd,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('rank replay',p,train))
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            Rd[c,t]=ar.predict_hist(Rd,c,t,coef,p,'shared')+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('causal replay',p,train))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',p,train,mer))
    total=int(mb)+int(pb)+HEADER+SELECTOR
    return {'order':int(p),'train':int(train),'step':STEP,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'payload_bytes':int(pb),'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);inc=g.ar32_baseline(X,eps);rows=[]
    floor=23448
    for p in ORDERS:
        for train in TRAINS:
            if train<=p+2:continue
            r=encode_one(X,eps,p,train)
            if r is None:continue
            r['gain_vs_old_ar32']=inc['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];r['delta_vs_ar8_256_floor']=r['bytes']-floor
            rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'orders':list(ORDERS),'trains':list(TRAINS),'step':STEP,'ar8_train256_floor':floor,'old_ar32':inc,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Fine NOVA coordinate-system search after PR564 established AR8/train256/step267 + exact restricted ranking as the 23,448-byte hard-Imperial floor. This gate searches shared temporal AR orders 1..12 and multiple public training-prefix lengths at the maximal hard-error-valid step267. Every source-derived model is float32 serialized/decoded and fully charged; every K field is physically restricted-ranked and independently decoded; the complete causal reconstruction is replayed and the unchanged source-domain hard bound is verified. One byte is charged for selecting a configuration from this public family. Reported bytes are real materialized stream bytes, not entropy estimates.'}
    json.dump(out,open('imperial_nova_ar_fine_address_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_train':best['train'],'best_bytes':best['bytes'],'ar8_train256_floor':floor,'delta_vs_floor':best['bytes']-floor,'old_ar32':inc['bytes'],'sz3':int(szb),'gain_vs_old_ar32':inc['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
