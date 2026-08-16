import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m

P=32
TRAIN=256
STEP=267
C=128
T=1024
HEADER=32
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))


def encode_tile(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,P,'shared');k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard encode',me,eps))
    legacy=m.encode_k(K);lk=int(legacy[0]);LK=np.asarray(legacy[2],np.int32)
    rb,rn,RK,detail=rr.restricted_rank_frame(K);rb=int(rb)
    for name,Kd in [('legacy',LK),('restricted',RK)]:
        Rd=np.zeros_like(R)
        for c in range(X.shape[0]):
            for t in range(X.shape[1]):Rd[c,t]=ar.predict_hist(Rd,c,t,coef,P,'shared')+STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R):raise RuntimeError(('replay',name))
        mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if mer>eps*(1+5e-6):raise RuntimeError(('hard replay',name,mer))
    return {'model_bytes':int(mb),'maxerr':me,'legacy':{'bytes':int(mb)+lk+HEADER,'payload_bytes':lk,'rep':legacy[1]},'restricted':{'bytes':int(mb)+rb+HEADER,'payload_bytes':rb,'rep':rn,'detail':detail},'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T
            szb,ori=m.szrun(X,eps);r=encode_tile(X,eps);l=r['legacy'];q=r['restricted']
            row={'tile':name,'t0':t0,'c0':c0,'shape':[C,T],'local_std':float(X.std()),'sz3_bytes':int(szb),'sz3_orientation':ori,'model_bytes':r['model_bytes'],'maxerr':r['maxerr'],'legacy_bytes':l['bytes'],'legacy_payload':l['payload_bytes'],'legacy_rep':l['rep'],'restricted_bytes':q['bytes'],'restricted_payload':q['payload_bytes'],'restricted_rep':q['rep'],'restricted_detail':q['detail'],'gain_restricted_vs_legacy':l['bytes']/q['bytes'],'gain_restricted_vs_sz3':szb/q['bytes'],'gain_legacy_vs_sz3':szb/l['bytes'],'delta_bytes':q['bytes']-l['bytes'],'k_zero_fraction':r['k_zero_fraction'],'k_std':r['k_std']}
            rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='restricted_detail'},indent=2),flush=True)
    ls=sum(r['legacy_bytes'] for r in rows);rs=sum(r['restricted_bytes'] for r in rows);ss=sum(r['sz3_bytes'] for r in rows);n=C*T*len(rows)
    out={'global_std':std,'eps':eps,'order':P,'step':STEP,'train':TRAIN,'rows':rows,'aggregate':{'samples':n,'legacy_bytes':ls,'restricted_bytes':rs,'sz3_bytes':ss,'restricted_gain_vs_legacy':ls/rs,'restricted_gain_vs_sz3':ss/rs,'legacy_gain_vs_sz3':ss/ls,'delta_bytes':rs-ls,'restricted_bps':8*rs/n},'scope':'Transfer/generalization audit for the PR552 mechanism. On four precommitted 128x1024 Imperial regimes, each tile independently fits the same shared AR32+intercept from its first 256 samples, serializes/decodes and charges the float32 model, then generates identical step267 innovations. The ONLY codec change is legacy K representation versus PR512 exact restricted ranking. Both streams are byte-decoded and causally regenerate the identical reconstruction; unchanged source hard error is verified. Matched SZ3 is rerun on each identical tile. No tile-name routing beyond the precommitted audit panel and no proxy rate counts.'}
    json.dump(out,open('imperial_ar32_restricted_address_generalization.json','w'),indent=2)
    print(json.dumps({'summary':out['aggregate']},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
