import json,sys
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as contour
import imperial_resonant_learned_law_address as g

STEPS=(224,232,240,248,252,256,260,264,266,267,268,269,270)
P=32
HEADER=32
SELECTOR=1


def build_ar(X,eps,step,cd):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,P,'shared')
            k=int(np.rint((float(X[c,t])-pred)/step))
            R[c,t]=pred+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):return None,None,me
    return R,K,me


def replay(X,eps,step,cd,K,Rref):
    R=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            R[c,t]=ar.predict_hist(R,c,t,cd,P,'shared')+step*int(K[c,t])
    if not np.array_equal(R,Rref):raise RuntimeError(('AR replay mismatch',step))
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',step,me,eps))
    return me


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    co=ar.fit_shared(X[:,:g.TRAIN],P);mb,cd=ar.model_frame(co)
    incumbent=g.ar32_baseline(X,eps)
    rows=[];invalid=[]
    for sid,step in enumerate(STEPS):
        R,K,me=build_ar(X,eps,int(step),cd)
        if R is None:
            invalid.append({'step':int(step),'maxerr':me});continue
        reps=[]
        fr=m.encode_k(np.ascontiguousarray(K,np.int32));reps.append(('legacy_'+fr[1],int(fr[0]),np.asarray(fr[2],np.int32),None))
        rb,rn,RK,rd=rr.restricted_rank_frame(K);reps.append((rn,int(rb),np.asarray(RK,np.int32),rd))
        cb,cn,CK,cdetail=contour.bitplane_contour_frame(K);reps.append((cn,int(cb),np.asarray(CK,np.int32),cdetail))
        for rep,payload,Kd,detail in reps:
            mer=replay(X,eps,int(step),cd,Kd,R)
            total=int(mb)+int(payload)+HEADER+SELECTOR
            row={'step':int(step),'step_selector':int(sid),'rep':rep,'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'payload_bytes':int(payload),'header_bytes':HEADER,'selector_bytes':SELECTOR,'maxerr':mer,'k_zero_fraction':float(np.mean(K==0)),'k_abs1_fraction':float(np.mean(np.abs(K)==1)),'k_std':float(K.std()),'gain_vs_sz3':szb/total,'gain_vs_incumbent_ar32':incumbent['bytes']/total}
            if detail is not None:row['detail']=detail
            rows.append(row)
            print(json.dumps({k:v for k,v in row.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'steps':list(STEPS),'selector_contract':'One byte is charged for choosing one public step from the fixed table. The AR32 coefficient model is fitted and serialized exactly as the incumbent comparator.','sz3':{'bytes':int(szb),'orientation':ori},'incumbent_ar32':incumbent,'rows':rows,'invalid_steps':invalid,'best':best,'scope':'Direct architecture-fusion gate. Unlike the learned-law GCA branches, this keeps the incumbent shared temporal AR32 generator and asks whether the uploaded Complexity Weapon/NOVA address machinery improves only the transmitted innovation object. For each public reconstruction step, the causal AR32 reconstruction is generated and hard-error validated. The exact K field is then physically encoded by the incumbent representation, PR512 exact restricted ranking, and the contour representation. Every candidate byte-decodes K, causally regenerates the identical AR32 reconstruction, and rechecks the source hard bound. The shared AR32 float32 coefficient stream is charged exactly as before; a one-byte public-table step selector is additionally charged. No ideal entropy, oracle choice or unmaterialized legal-set rate counts.'}
    json.dump(out,open('imperial_ar32_restricted_address_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_step':best['step'],'best_rep':best['rep'],'best_bytes':best['bytes'],'incumbent_ar32':incumbent['bytes'],'sz3':int(szb),'gain_vs_ar32':incumbent['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes'],'delta_bytes_vs_ar32':best['bytes']-incumbent['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
