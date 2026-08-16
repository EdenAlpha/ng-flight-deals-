import json,sys,math
import h5py,numpy as np
import imperial_ar1_legal_trajectory_address as lt
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(128,144,160,176,192,208,224,232,240,248,256,264,267)
OBJECTIVES=('lowbits','causal_bits','symbol_causal','zero_mag')
EXACT_TOP=18
BEAM=128


def build_step(X,coef,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared')
            k=int(np.rint((float(X[c,t])-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    return R,K


def replay_step(X,coef,K,eps,step):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared');R[c,t]=pred+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',step,me,eps))
    return R,me


def quick_score(K):
    # Independent cheap screen only. It never decides the final winner.
    u=m.zig(K);n=u.size;mx=int(u.max()) if n else 0;nb=max(1,mx.bit_length());bits=0.0
    for b in range(nb):
        B=((u>>b)&1).astype(np.uint8);o=int(B.sum());p=(o+0.5)/(n+1.0)
        hg=-(p*math.log2(p)+(1-p)*math.log2(1-p))*n
        # causal binary Markov screens in time and channel; use the best simple public view
        def cond(axis):
            a=B[:,:-1] if axis==1 else B[:-1,:];z=B[:,1:] if axis==1 else B[1:,:]
            s=0.0
            for pv in (0,1):
                q=(a==pv);nn=int(q.sum())
                if not nn:continue
                oo=int(z[q].sum());pp=(oo+0.5)/(nn+1.0)
                s-=nn*(pp*math.log2(pp)+(1-pp)*math.log2(1-pp))
            return s
        bits+=min(hg,cond(1)+8.0,cond(0)+8.0)
    return float(bits/8.0)


def exact(K,X,coef,eps,step,obj,model_bytes,diag):
    fb,_,Kd,detail=lt.A.hybrid_frame(K)
    if not np.array_equal(Kd,K):raise RuntimeError(('K decode',step,obj))
    _,me=replay_step(X,coef,Kd,eps,step)
    total=fair.COMMON_HEADER+1+model_bytes+int(fb)
    return {'step':step,'objective':obj,'bytes':int(total),'field_bytes':int(fb),'model_bytes':model_bytes,'maxerr':me,'quick_bytes':quick_score(K),'field_detail':detail,**diag}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    co=fair.fit(X,1,'prefix64');model,mname=fair.encode_model(co);coef,pos=fair.decode_model(model,0,2)
    if pos!=len(model):raise RuntimeError('model trailing')
    oldbeam=lt.BEAM;lt.BEAM=BEAM
    screened=[];objects={}
    for step in STEPS:
        R0,K0=build_step(X,coef,step);me=float(np.max(np.abs(X-R0.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('baseline hard',step,me,eps))
        key=(step,'nearest_baseline');objects[key]=K0.copy()
        screened.append({'step':step,'objective':'nearest_baseline','quick_bytes':quick_score(K0),'changed_k':0,'ambiguity_ratio_est':max(0.0,2*eps/step-1.0)})
        C=lt.cost_model(K0);lt.STEP=step
        for obj in OBJECTIVES:
            K,R,mer,diag=lt.optimize(X,coef,K0,eps,obj,C);key=(step,obj);objects[key]=K.copy()
            screened.append({'step':step,'objective':obj,'quick_bytes':quick_score(K),'ambiguity_ratio_est':max(0.0,2*eps/step-1.0),**diag})
        print(json.dumps({'screen_step':step,'ambiguity_ratio_est':max(0.0,2*eps/step-1.0),'best_quick':min(r['quick_bytes'] for r in screened if r['step']==step)},indent=2),flush=True)
    # Exact materialization is reserved for the strongest cheap screens, but force
    # the 267 baseline and at least one candidate from each broad spacing regime.
    screened.sort(key=lambda r:r['quick_bytes']);selected={(r['step'],r['objective']) for r in screened[:EXACT_TOP]}
    selected.add((267,'nearest_baseline'))
    for lo,hi in ((128,175),(176,215),(216,239),(240,255),(256,267)):
        rr=[r for r in screened if lo<=r['step']<=hi]
        if rr:selected.add((rr[0]['step'],rr[0]['objective']))
    exact_rows=[]
    for r in screened:
        key=(r['step'],r['objective'])
        if key not in selected:continue
        row=exact(objects[key],X,coef,eps,r['step'],r['objective'],len(model),{k:v for k,v in r.items() if k not in ('step','objective','quick_bytes')})
        exact_rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='field_detail'},indent=2),flush=True)
    lt.BEAM=oldbeam
    exact_rows.sort(key=lambda r:r['bytes']);best=exact_rows[0];base267=next(r for r in exact_rows if r['step']==267 and r['objective']=='nearest_baseline')
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'steps':list(STEPS),'objectives':list(OBJECTIVES),'beam':BEAM,
         'exact_top_screen':EXACT_TOP,'selected_exact':[list(x) for x in sorted(selected)],'model_bytes':len(model),'model_rep':mname,
         'common_header_bytes':fair.COMMON_HEADER,'sz3':{'bytes':int(szb),'orientation':ori},'baseline267_bytes':base267['bytes'],
         'screened':screened,'exact_rows':exact_rows,'best':best,
         'scope':'Wide GCA legal-set search. AR1/prefix64 is frozen, but public lattice spacings 128..267 deliberately vary reconstruction multiplicity. For each step the nearest stream and four legal-trajectory beam searches are generated. A cheap entropy/causal screen only decides which candidates deserve expensive materialization; it never determines the reported winner. The strongest screened candidates plus forced representatives from every spacing regime are physically encoded with the exact coarse-prefix+mixture address, independently decoded, recursively AR1-replayed and hard-error checked. Only actual exact_rows bytes can win. Step/config identity is covered by the charged one-byte public selector.'}
    json.dump(out,open('imperial_ar1_wide_legal_set_search.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline267':base267['bytes'],'best':best['bytes'],'step':best['step'],'objective':best['objective'],'delta_vs_267':best['bytes']-base267['bytes'],'changed_k':best.get('changed_k',0),'quick_bytes':best['quick_bytes'],'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
