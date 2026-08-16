import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

T0=14488
C0=512
C=128
T=1024
TRAIN=256
STEP=267
WIDTHS=(16,32,64,128)
ORDERS=(4,8,12,16,24,32)
HEADER=32
CONFIG_SELECTOR=1


def encode_group(X,eps,p,restricted):
    co=ar.fit_shared(X[:,:TRAIN],p);mb,coef=ar.model_frame(co)
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,coef,p,'shared');k=int(np.rint((float(X[c,t])-pred)/STEP));R[c,t]=pred+STEP*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('encode hard',p,X.shape,me))
    if restricted:
        pb,rep,Kd,detail=rr.restricted_rank_frame(K);pb=int(pb)
    else:
        fr=m.encode_k(K);pb=int(fr[0]);rep=fr[1];Kd=np.asarray(fr[2],np.int32);detail=None
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=ar.predict_hist(Rd,c,t,coef,p,'shared')+STEP*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('replay',p,X.shape,restricted))
    mer=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if mer>eps*(1+5e-6):raise RuntimeError(('replay hard',mer))
    return {'bytes':int(mb)+pb+HEADER,'model_bytes':int(mb),'payload_bytes':pb,'rep':rep,'maxerr':mer,'detail':detail,'k_std':float(K.std()),'k_zero_fraction':float(np.mean(K==0))}


def config(X,eps,width,p,restricted):
    total=CONFIG_SELECTOR;groups=[]
    for c0 in range(0,C,width):
        Y=X[c0:min(c0+width,C)]
        r=encode_group(Y,eps,p,restricted);r['c0']=c0;r['channels']=Y.shape[0];groups.append(r);total+=r['bytes']
    return {'width':width,'order':p,'restricted':restricted,'bytes':total,'groups':groups,'model_bytes':sum(x['model_bytes'] for x in groups),'payload_bytes':sum(x['payload_bytes'] for x in groups),'headers_bytes':HEADER*len(groups),'selector_bytes':CONFIG_SELECTOR,'maxerr':max(x['maxerr'] for x in groups)}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=m.szrun(X,eps);rows=[]
    # Reproduce the one-block legacy AR32 floor without selector, exactly matching the transfer audit contract.
    floor=encode_group(X,eps,32,False);legacy_floor=floor['bytes']
    for width in WIDTHS:
        for p in ORDERS:
            for restricted in (False,True):
                r=config(X,eps,width,p,restricted);r['gain_vs_legacy_floor']=legacy_floor/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];rows.append(r)
                print(json.dumps({k:v for k,v in r.items() if k!='groups'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[C,T],'t0':T0,'c0':C0,'global_std':std,'eps':eps,'step':STEP,'widths':list(WIDTHS),'orders':list(ORDERS),'legacy_ar32_floor':{'bytes':legacy_floor,'model_bytes':floor['model_bytes'],'payload_bytes':floor['payload_bytes'],'maxerr':floor['maxerr']},'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Decoder-real NOVA coordinate-partition search on the fixed hard 128x1024 Imperial tile. The transfer audit showed one 128-channel restricted universe loses even though the 32-channel hard gate wins. This experiment searches only a public grid of contiguous channel partition widths and shared AR orders. Every subgroup independently fits its model from the same first 256 times, serializes/decodes and fully charges that model, physically encodes K either with the legacy stream or exact PR512 restricted ranking, independently decodes K, causally replays its reconstruction, and verifies the unchanged source hard-error bound. Every subgroup header is charged and one byte is charged for selecting the public (width,order,representation) configuration. No per-group oracle selector, no dataset-name routing, and no ideal rates.'}
    json.dump(out,open('imperial_hard_partition_coordinate_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_width':best['width'],'best_order':best['order'],'best_restricted':best['restricted'],'best_bytes':best['bytes'],'legacy_ar32_floor':legacy_floor,'sz3':int(szb),'delta_vs_legacy':best['bytes']-legacy_floor,'gain_vs_legacy':legacy_floor/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
