import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

ORDERS=tuple(range(1,17))
TRAINS=(64,96,128,192,256,384,512)
STEP=267
HEADER=32
SELECTOR=1


def one(X,eps,p,train):
    co=ar.fit_shared(X[:,:train],p);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared')
            k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):return None
    pb,rep,Kd,detail=rr.restricted_rank_frame(K);pb=int(pb)
    if not np.array_equal(Kd,K):raise RuntimeError(('rank replay',p,train))
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=ar.predict_hist(Rd,c,t,coef,p,'shared')+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('causal replay',p,train))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',p,train,mer))
    total=int(mb)+pb+HEADER+SELECTOR
    return {'order':p,'train':train,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'payload_bytes':pb,'maxerr':mer,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0)),'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);old=g.ar32_baseline(X,eps);rows=[]
    for train in TRAINS:
        for p in ORDERS:
            if train<=p+2:continue
            r=one(X,eps,p,train)
            if r is None:continue
            r['gain_vs_old_ar32']=old['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];rows.append(r)
            print(json.dumps({k:v for k,v in r.items() if k!='detail'},flush=True),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'orders':list(ORDERS),'trains':list(TRAINS),'old_ar32':old,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Fine NOVA coordinate-system search around the AR8 restricted-address breakthrough. The source object, step267, hard-error contract, exact PR512 address and accounting remain fixed. Only public shared AR order 1..16 and prefix training length are searched. Every candidate fits only from its declared prefix, serializes/decodes and fully charges the AR model, physically restricted-ranks and independently decodes the complete K field, causally replays the identical reconstruction, and verifies the original source hard error. One byte selects the public (order,training-length) configuration. No ideal rate or uncharged model selection.'}
    json.dump(out,open('imperial_nova_fine_ar_neighborhood.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_train':best['train'],'best_bytes':best['bytes'],'current_ar8_256_floor':23448,'old_ar32':old['bytes'],'sz3':int(szb),'delta_vs_23448':best['bytes']-23448,'gain_vs_old_ar32':old['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
