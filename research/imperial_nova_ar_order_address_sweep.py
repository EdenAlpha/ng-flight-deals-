import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

ORDERS=(8,12,16,20,24,28,32,36,40,48,56,64)
STEPS=(264,266,267)
TRAIN=256
HEADER=32
SELECTOR=1


def encode_one(X,eps,p,step):
    co=ar.fit_shared(X[:,:TRAIN],p);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared');k=int(np.rint((float(X[c,t])-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):return None
    pb,rep,Kd,detail=rr.restricted_rank_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('rank replay',p,step))
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=ar.predict_hist(Rd,c,t,coef,p,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('causal replay',p,step))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',p,step,mer))
    total=int(mb)+int(pb)+HEADER+SELECTOR
    return {'order':int(p),'step':int(step),'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'payload_bytes':int(pb),'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);inc=g.ar32_baseline(X,eps);rows=[]
    for p in ORDERS:
        for step in STEPS:
            r=encode_one(X,eps,p,step)
            if r is None:continue
            r['gain_vs_old_ar32']=inc['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];rows.append(r)
            print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'orders':list(ORDERS),'steps':list(STEPS),'train':TRAIN,'old_ar32':inc,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'NOVA shared-coordinate search under the new exact address. Earlier Imperial AR order selection was made for the legacy innovation stream. This gate re-searches a public family of shared temporal AR coordinate systems only after replacing the payload with PR512 exact restricted ranking. For every order/step, coefficients are fitted from the same first 256 samples, float32 serialized/decoded and fully charged; K is physically restricted-ranked, independently decoded, the complete causal reconstruction is replayed, and the unchanged source hard-error bound is verified. A one-byte public configuration selector is charged. No ideal rate or untransmitted model counts.'}
    json.dump(out,open('imperial_nova_ar_order_address_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_order':best['order'],'best_step':best['step'],'best_bytes':best['bytes'],'old_ar32':inc['bytes'],'sz3':int(szb),'gain_vs_old_ar32':inc['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
