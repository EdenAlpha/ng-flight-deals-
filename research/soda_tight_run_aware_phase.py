import json,os,struct,sys
import numpy as np

# Reuse PR #189's exact refined timing/Rice codec and PR #186 phase container.
src=open('research/soda_tight_refined_context_phase.py').read().rsplit('\nmain(sys.argv[1],float(sys.argv[2]))',1)[0]
exec(compile(src,'soda_tight_refined_context_phase.py','exec'),globals())


def phase_metrics(x,step,k):
    phi=step*(k/NPH);q=np.rint((x.astype(np.float64,copy=False)-phi)/step).astype(np.int32)
    d=np.empty_like(q);d[0]=q[0];d[1:]=q[1:]-q[:-1];m=d!=0
    events=int(m.sum());runs=int(m[0])+(int(np.count_nonzero(m[1:] & ~m[:-1])) if m.size>1 else 0);big=int(np.count_nonzero(np.abs(d)>1));mag=int(np.abs(d.astype(np.int64)).sum())
    return q,(runs,events,big,mag,k)


def choose_phase(x,step,mode):
    best=None
    for k in range(NPH):
        q,m=phase_metrics(x,step,k);runs,events,big,mag,kk=m
        if mode=='run_first':score=(runs,events,big,mag,kk)
        elif mode=='run4':score=(4*runs+events,big,mag,runs,events,kk)
        else:raise ValueError(mode)
        if best is None or score<best[0]:best=(score,k,q,m)
    return int(best[1]),best[2],best[3]


def quantize_independent(X,tm,outids,shape,step,mode):
    G=np.zeros(shape,np.int32);P=np.zeros(shape[:-1],np.uint8);runs=events=big=0
    for tid,c,l,s in tm:
        k,q,m=choose_phase(X[tid],step,mode);P[c,l,s]=k;G[c,l,s]=q;runs+=m[0];events+=m[1];big+=m[2]
    O=np.empty((len(outids),X.shape[1]),np.int32);OP=np.zeros(len(outids),np.uint8);oruns=oevents=0
    for j,tid in enumerate(outids.tolist()):
        k,q,m=choose_phase(X[tid],step,mode);OP[j]=k;O[j]=q;oruns+=m[0];oevents+=m[1]
    return G,P,O,OP,{'mode':mode,'main_runs':runs,'main_events':events,'main_big':big,'out_runs':oruns,'out_events':oevents}


def quantize_site_shared(X,tm,outids,shape,step):
    # One decoder-visible phase index per occupied physical receiver site, shared
    # by every component present at that site. The full repeated phase plane is
    # still serialized by the standard exact phase-map codec, so no hidden map.
    groups={}
    for tid,c,l,s in tm:groups.setdefault((l,s),[]).append((tid,c))
    G=np.zeros(shape,np.int32);P=np.zeros(shape[:-1],np.uint8);runs=events=big=0
    for (l,s),members in groups.items():
        cand=[]
        for k in range(NPH):
            rs=ev=bg=mg=0;qs=[]
            for tid,c in members:
                q,m=phase_metrics(X[tid],step,k);qs.append((c,q,m));rs+=m[0];ev+=m[1];bg+=m[2];mg+=m[3]
            score=(4*rs+ev,bg,mg,rs,ev,k);cand.append((score,k,qs))
        score,k,qs=min(cand,key=lambda z:z[0])
        for c,q,m in qs:P[c,l,s]=k;G[c,l,s]=q;runs+=m[0];events+=m[1];big+=m[2]
    # Outliers have no reliable 3C site grouping; keep the same independent run-weighted rule.
    O=np.empty((len(outids),X.shape[1]),np.int32);OP=np.zeros(len(outids),np.uint8);oruns=oevents=0
    for j,tid in enumerate(outids.tolist()):
        k,q,m=choose_phase(X[tid],step,'run4');OP[j]=k;O[j]=q;oruns+=m[0];oevents+=m[1]
    return G,P,O,OP,{'mode':'site_shared_run4','sites':len(groups),'main_runs':runs,'main_events':events,'main_big':big,'out_runs':oruns,'out_events':oevents}


def eval_variant(X,tm,outids,shape,internal_eps,variant):
    step=2*internal_eps
    if variant in ('run_first','run4'):G,P,O,OP,sdiag=quantize_independent(X,tm,outids,shape,step,variant)
    elif variant=='site_shared_run4':G,P,O,OP,sdiag=quantize_site_shared(X,tm,outids,shape,step)
    else:raise ValueError(variant)
    K=delta(G,3);mb,parts=prepare_refined_main(K);RK=decode_refined_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError((variant,'main exact K'))
    bo=best_out(O);RO=decode_out_exact(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError((variant,'out exact'))
    top,pacct=encode_phase_top(internal_eps,P,OP,mb,bo);ee,DP,DOP,DRK,DRO=decode_phase_top_refined(top,G.shape[:-1],O.shape)
    if not np.array_equal(DP,P) or not np.array_equal(DOP,OP) or not np.array_equal(DRK,K) or not np.array_equal(DRO,O):raise RuntimeError((variant,'top exact decode'))
    RG=undelta(DRK,3);Y=reconstruct(X.shape,tm,outids,RG,DRO,DP,DOP,2*ee)
    return {'variant':variant,'container_bytes':len(top),'main_bytes':len(mb),'outlier_bytes':int(bo[0]),'K_nonzero_fraction':float(np.mean(K!=0)),'main_parts':parts,'phase_accounting':pacct,'selection_diag':sdiag,'recon':Y}


def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy)
    # Exact old frontiers on the same data for audit.
    oldphase=old_phase_bytes(X,tm,outids,G0.shape,internal_eps);refold=eval_phase(X,tm,outids,G0.shape,internal_eps)
    variants=[]
    for v in ('run_first','run4','site_shared_run4'):
        r=eval_variant(X,tm,outids,G0.shape,internal_eps,v);Y=r.pop('recon');r['maxerr']=float(np.max(np.abs(X-Y)));r['valid']=bool(r['maxerr']<=public_eps*(1+3e-6))
        if not r['valid']:raise RuntimeError((v,'hard error',r['maxerr'],public_eps));variants.append(r)
    variants.sort(key=lambda r:r['container_bytes']);best=variants[0];szb,sze=sz3_bytes(X,public_eps);target=szb/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'old_phase_bytes':int(oldphase),'pr189_refined_phase_bytes':int(refold['container_bytes']),'variants':variants,'best':best,'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'two_x_target_bytes':target,'gain_vs_direct_sz3':float(szb/best['container_bytes']),'clears_2x':bool(best['container_bytes']<=target)}
    print(json.dumps({'old_phase':oldphase,'pr189_refined_phase':refold['container_bytes'],'best_variant':best['variant'],'best_bytes':best['container_bytes'],'gain_sz3':out['gain_vs_direct_sz3'],'target':target,'clears_2x':out['clears_2x'],'variants':[{k:r[k] for k in ('variant','container_bytes','K_nonzero_fraction','maxerr')} for r in variants]},indent=2),flush=True);json.dump(out,open('soda_tight_run_aware_phase.json','w'),indent=2)

main(sys.argv[1])
