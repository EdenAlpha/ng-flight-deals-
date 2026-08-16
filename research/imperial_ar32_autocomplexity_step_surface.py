import json,sys
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(128,144,160,176,192,208,224,232,240,248,256,260,264,267)
SELECTOR_BYTES=2

def run_step(X,eps,cd,mb,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=g.ar.predict_hist(R,c,t,cd,g.P,'shared');k=int(np.rint((float(X[c,t])-p)/step));R[c,t]=p+step*k;K[c,t]=k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard source',step,me,eps))
    ab,rep,Kd,detail=ac.autocomplexity_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('K frame',step))
    Rd=np.zeros_like(R)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('AR replay',step))
    total=int(mb)+int(ab)+base.HEADER+SELECTOR_BYTES
    return {'step':int(step),'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(ab),'selector_bytes':SELECTOR_BYTES,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'rep':rep,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=g.ar.fit_shared(X[:,:g.TRAIN],g.P);mb,cd=g.ar.model_frame(co)
    # Frozen fixed-step incumbent without a selector byte.
    _,_,R267,K267=base.build_ar32(X);ab267,_,Kd267,_=ac.autocomplexity_frame(K267)
    if not np.array_equal(Kd267,K267):raise RuntimeError('incumbent K replay')
    incumbent=int(mb)+int(ab267)+base.HEADER
    rows=[]
    for step in STEPS:
        z=run_step(X,eps,cd,mb,step);z['gain_vs_fixed267']=incumbent/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'steps':list(STEPS),'selector_bytes':SELECTOR_BYTES,'fixed267_autocomplexity_bytes':incumbent,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'rows':rows,'best':best,'scope':'Re-optimization of the frozen shared AR32 reconstruction lattice after changing the innovation address language. The AR32 model is fit exactly as before and fully charged. For every public integer step <=267, the encoder recursively forms the nearest legal reconstruction R=pred+step*K; because step/2 <= epsilon, source max error is guaranteed and verified. The identical K is encoded/decoded with the exact AUTO-COMPLEXITY rank stream and used to reproduce identical R. A 2-byte lattice-step selector is charged to every swept candidate; the fixed step267 incumbent remains the 23,092-byte reference without selector overhead. This tests whether the old step was coupled to the old ZSM/bitplane address and should move under the new restricted-address objective. No oracle rate or uncharged parameter is used.'}
    json.dump(out,open('imperial_ar32_autocomplexity_step_surface.json','w'),indent=2)
    print(json.dumps({'summary':{'best_step':best['step'],'best_bytes':best['bytes'],'fixed267_bytes':incumbent,'sz3_bytes':int(szb),'gain_fixed':incumbent/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
