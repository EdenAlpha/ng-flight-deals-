import json, sys
import numpy as np, h5py
from numba import njit
import imperial_sparse_causal_annihilator as m
import imperial_sparse_causal_annihilator_jit as j

C0=512; NC=128; FIT_END=3072; VAL_END=4096; TARGET_PHASE_STEP=64.0
PASSES=2; NCOEF=16

@njit(cache=True)
def run_states(X,dtv,dcv,coeff,intercept,maxdt):
    nc,nt=X.shape
    R=np.empty((nc,nt),np.int64); K=np.zeros((nc,nt),np.int64)
    for c in range(nc):
        for t in range(maxdt): R[c,t]=int(np.rint(X[c,t]/m.STEP))*m.STEP
    for t in range(maxdt,nt):
        for c in range(nc):
            p=intercept
            for z in range(coeff.size):
                cc=c+dcv[z]
                if cc<0 or cc>=nc: continue
                p += coeff[z]*R[cc,t-dtv[z]]
            if p>200000.0: p=200000.0
            elif p< -200000.0: p=-200000.0
            pi=int(np.rint(p)); k=int(np.rint((X[c,t]-pi)/m.STEP))
            K[c,t]=k; R[c,t]=pi+m.STEP*k
    return R,K

def val_score(X,offs,beta):
    dtv=np.asarray([x[0] for x in offs],np.int64); dcv=np.asarray([x[1] for x in offs],np.int64)
    coeff=np.asarray(beta[1:],np.float64); maxdt=int(max(dtv))
    R,K=run_states(np.ascontiguousarray(X[:,:VAL_END],np.float64),dtv,dcv,coeff,float(beta[0]),maxdt)
    me=float(np.max(np.abs(X[:,:VAL_END]-R)))
    if me>128.000001: raise RuntimeError(('val hard error',me))
    b,rep=m.encode_array(K[:,FIT_END:VAL_END])
    # Secondary deterministic tie break: fewer absolute innovation quanta.
    l1=int(np.abs(K[:,FIT_END:VAL_END]).sum())
    return int(b),l1,rep

def tune(X,offs,beta):
    beta=np.asarray(beta,np.float64).copy()
    old=m.TRAIN_END; m.TRAIN_END=FIT_END
    A,_=m.design_matrix(X,offs); m.TRAIN_END=old
    scales=A.std(axis=0)+1e-9
    contribution=np.abs(beta[1:])*scales
    order=np.argsort(-contribution)[:min(NCOEF,len(offs))]
    history=[]
    best=val_score(X,offs,beta); history.append({'stage':'initial','bytes':best[0],'l1':best[1],'rep':best[2]})

    def accept(cand,tag):
        nonlocal beta,best
        s=val_score(X,offs,cand)
        if (s[0],s[1]) < (best[0],best[1]):
            beta=cand; best=s; history.append({'stage':tag,'bytes':s[0],'l1':s[1],'rep':s[2]}); return True
        return False

    # Global dynamics scale and byte-phase intercept are cheap high-leverage degrees of freedom.
    for fac in (0.90,0.95,0.975,1.025,1.05,1.10):
        c=beta.copy(); c[1:]*=fac; accept(c,'global_scale_'+str(fac))
    for delta in (-128.,-64.,-32.,-16.,16.,32.,64.,128.):
        c=beta.copy(); c[0]+=delta; accept(c,'intercept_'+str(int(delta)))

    for ps in range(PASSES):
        changed=0
        for jj in order:
            idx=int(jj)+1
            unit=TARGET_PHASE_STEP/float(scales[jj])
            local_best=(best[0],best[1]); chosen=None; chosen_score=None
            for mul in (-2.0,-1.0,-0.5,0.5,1.0,2.0):
                c=beta.copy(); c[idx]+=mul*unit
                s=val_score(X,offs,c)
                if (s[0],s[1]) < local_best:
                    local_best=(s[0],s[1]); chosen=c; chosen_score=s
            if chosen is not None:
                beta=chosen; best=chosen_score; changed+=1
                history.append({'stage':f'pass{ps}_coef{jj}','bytes':best[0],'l1':best[1],'rep':best[2],'coef_index':int(jj),'phase_unit':unit})
        # Revisit intercept after coefficient phase changes.
        for delta in (-64.,-32.,-16.,16.,32.,64.):
            c=beta.copy(); c[0]+=delta
            if accept(c,f'pass{ps}_intercept_{int(delta)}'): changed+=1
        if changed==0: break
    return beta,best,history,[int(x) for x in order],scales

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic']; _,gstd=m.stats(d); eps=.1*gstd
        X=np.asarray(d[:,C0:C0+NC],np.float64).T
    old=m.TRAIN_END
    m.TRAIN_END=FIT_END
    offs_fit,beta_fit=m.fit_omp(X,m.OMP_TAPS)
    m.TRAIN_END=old
    tuned_beta,val_best,history,order,scales=tune(X,offs_fit,beta_fit)

    # Decoder-real full-minute tests. A separate 4096-sample OMP reproduces the PR310/312 model family.
    m.TRAIN_END=VAL_END
    offs_4096,beta_4096=m.fit_omp(X,m.OMP_TAPS)
    ar_off,ar_beta=m.fit_ar16(X)
    m.TRAIN_END=old
    fit3072=j.encode_model_jit(X,offs_fit,beta_fit,eps,'omp_fit3072')
    tuned=j.encode_model_jit(X,offs_fit,tuned_beta,eps,'codelength_shaped')
    fit4096=j.encode_model_jit(X,offs_4096,beta_4096,eps,'omp_fit4096')
    ar=j.encode_model_jit(X,ar_off,ar_beta,eps,'ar16_fit4096')
    szb,_=m.matched_sz3(X,eps)
    rows={'ar16':ar,'omp4096':fit4096,'omp3072':fit3072,'codelength':tuned}
    out={'global_std':gstd,'eps':eps,'region_c0':C0,'shape':[NC,m.NT],'fit_end':FIT_END,'validation':[FIT_END,VAL_END],
         'phase_target_per_coordinate_sigma':TARGET_PHASE_STEP,'passes':PASSES,'optimized_coefficients':NCOEF,
         'validation_initial':history[0],'validation_final':{'bytes':val_best[0],'l1':val_best[1],'rep':val_best[2]},
         'validation_byte_gain':history[0]['bytes']/val_best[0],'search_history':history,'optimized_order':order,
         'feature_scales':[float(x) for x in scales], 'sz3_bytes':int(szb),'sz3_bps':8*szb/X.size,'rows':rows,
         'full_minute':{k:{'bytes':v['bytes'],'bps':v['bps'],'gain_vs_sz3':szb/v['bytes'],'maxerr':v['maxerr']} for k,v in rows.items()},
         'scope':'Hard-region codelength-shaped causal-law experiment. Tap support and initial coefficients use only t<3072. The next 1024 samples are a model-selection validation interval: deterministic coordinate search changes global dynamics scale, predictor intercept and the 16 highest-contribution coefficients to minimize the ACTUAL self-decoding compressed bytes of 256-step validation innovations (L1 only breaks byte ties), not MSE. Feature-scaled coefficient steps are chosen to move the predictor by roughly 64 units per one-sigma feature. The tuned law is then frozen and recursively applied to the entire 30000-sample region; all model/seed/innovation bytes are counted and final error <=128 is checked. OMP fit on 3072, the original 4096-style OMP, AR16 and matched SZ3 are rerun. No AI; hard-zone gate only.'}
    print(json.dumps({'validation_gain':out['validation_byte_gain'],'full_minute':out['full_minute'],'history_tail':history[-10:]},indent=2),flush=True)
    json.dump(out,open('imperial_codelength_shaped_annihilator.json','w'),indent=2)

if __name__=='__main__': main(sys.argv[1])
