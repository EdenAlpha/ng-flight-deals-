import json,sys
import h5py,numpy as np
import imperial_defect_contour_address as c
import imperial_defect_restricted_rank_address as r
import imperial_defect_autocomplexity_rank as a
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEP=267
HEADER=32


def build_ar32(X):
    co=g.ar.fit_shared(X[:,:g.TRAIN],g.P);mb,cd=g.ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for cc in range(g.C):
        for t in range(g.T):
            pred=g.ar.predict_hist(R,cc,t,cd,g.P,'shared');k=int(np.rint((float(X[cc,t])-pred)/STEP));R[cc,t]=pred+STEP*k;K[cc,t]=k
    return int(mb),cd,R,K


def validate_address(X,eps,mb,cd,R,K,kind,frame_fn):
    fb,rep,Kd,detail=frame_fn(K)
    Kd=np.asarray(Kd,np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError(('K frame mismatch',kind))
    Rd=np.zeros_like(R)
    for cc in range(g.C):
        for t in range(g.T):Rd[cc,t]=g.ar.predict_hist(Rd,cc,t,cd,g.P,'shared')+STEP*int(Kd[cc,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('AR replay',kind))
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',kind,me,eps))
    total=mb+int(fb)+HEADER
    return {'kind':kind,'rep':rep,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'innovation_bytes':int(fb),'maxerr':me,'detail':detail}


def dense_frame(K):
    fr=m.encode_k(K);return int(fr[0]),fr[1],np.asarray(fr[2],np.int32),None


def contour_frame(K):
    b,rep,Kd,d=c.bitplane_contour_frame(K);return b,rep,Kd,d


def rank_frame(K):
    b,rep,Kd,d=r.restricted_rank_frame(K);return b,rep,Kd,d


def auto_frame(K):
    b,rep,Kd,d=a.autocomplexity_frame(K);return b,rep,Kd,d


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);mb,cd,R,K=build_ar32(X);rows=[]
    for kind,fn in [('incumbent',dense_frame),('contour',contour_frame),('restricted_rank',rank_frame),('autocomplexity_rank',auto_frame)]:
        z=validate_address(X,eps,mb,cd,R,K,kind,fn);z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0];inc=next(x for x in rows if x['kind']=='incumbent')
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'step':STEP,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'incumbent':inc,'rows':rows,'best':best,'scope':'Direct carrier/address separation test. The incumbent shared AR32 predictor, prefix fit, decoded float32 model coefficients, step267 reconstruction trajectory and hard-error contract are unchanged. The exact same AR32 innovation K field is serialized four ways: incumbent encode_k/Zstd menu, contour bitplane address, exact static constrained rank, and exact AUTO-COMPLEXITY causal type-class rank. Every candidate frame is independently decoded to identical K, then the charged decoded AR32 model recursively regenerates identical R and source hard error is checked. Model bytes and framing are charged exactly as in the incumbent. This asks whether the original restrict/address ideas improve the strongest existing Imperial carrier instead of handicapping them behind the weaker learned-law carrier.'}
    json.dump(out,open('imperial_ar32_autocomplexity_address.json','w'),indent=2)
    print(json.dumps({'summary':{'best_kind':best['kind'],'best_bytes':best['bytes'],'incumbent_bytes':inc['bytes'],'sz3_bytes':int(szb),'gain_vs_incumbent':inc['bytes']/best['bytes'],'gain_vs_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
