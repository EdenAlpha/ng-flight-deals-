import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

P=32; TRAIN=1024; END=2048; C=128
GROUPS=(8,16,32,64,128)
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
PREFIX_STEP=267

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P); mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64)
    for t in range(TRAIN):
        if t<P: pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P): v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/PREFIX_STEP).astype(np.int64)
        R[:,t]=pred+PREFIX_STEP*k
    me=float(np.max(np.abs(X[:,:TRAIN]-R)))
    if me>eps*(1+1e-10):raise RuntimeError(('prefix hard',me,eps))
    return mb,cd,R

def predict(state,co):
    v=np.full(C,float(co[-1]),np.float64)
    for j in range(P):v+=float(co[j])*state[:,-1-j]
    return np.rint(v).astype(np.int64)

def feasible_construct(lo,hi):
    out=np.empty(len(lo),np.int64); prev=-(1<<60)
    for i,(l,h) in enumerate(zip(lo,hi)):
        y=max(prev,int(l))
        if y>int(h):return False,None
        out[i]=y;prev=y
    return True,out

def max_subset_count(lo,hi):
    n=len(lo); INF=1<<60
    best=[INF]*(n+1);best[0]=-INF;maxk=0
    for i,(l,h) in enumerate(zip(lo,hi)):
        upto=min(i,maxk)
        for k in range(upto,-1,-1):
            if best[k]>=INF:continue
            y=max(best[k],int(l))
            if y<=int(h) and y<best[k+1]:
                best[k+1]=y
                if k+1>maxk:maxk=k+1
    return maxk

def process_region(name,c0,X,eps):
    mb,co,R0=fit_prefix(X,eps)
    out={'region':name,'c0':c0,'model_bytes':mb,'groups':{}}
    for G in GROUPS:
        state=R0[:,-P:].copy()
        full_int=0;full_grid=0;total=0;sub_int=[];sub_grid=[];fallback_groups=0
        changed_rank_pairs=[];plateau=[]
        for t in range(TRAIN,END):
            pred=predict(state,co);Rnew=np.empty(C,np.int64)
            for g0 in range(0,C,G):
                sl=np.arange(g0,g0+G);order=np.argsort(pred[sl],kind='stable');idx=sl[order]
                xx=X[idx,t]
                ilo=np.ceil(xx-eps-1e-12).astype(np.int64);ihi=np.floor(xx+eps+1e-12).astype(np.int64)
                ok,ys=feasible_construct(ilo,ihi);mi=max_subset_count(ilo,ihi);sub_int.append(mi/G)
                qlo=np.ceil((xx-eps)/256.0-1e-12).astype(np.int64);qhi=np.floor((xx+eps)/256.0+1e-12).astype(np.int64)
                gok,qy=feasible_construct(qlo,qhi);mg=max_subset_count(qlo,qhi);sub_grid.append(mg/G)
                total+=1;full_int+=int(ok);full_grid+=int(gok)
                if ok:
                    rr=np.empty(G,np.int64);rr[order]=ys;Rnew[sl]=rr
                    plateau.append(float(np.mean(np.diff(ys)==0)) if G>1 else 1.0)
                else:
                    fallback_groups+=1
                    kk=np.rint((X[sl,t]-pred[sl])/PREFIX_STEP).astype(np.int64);rr=pred[sl]+PREFIX_STEP*kk
                    if float(np.max(np.abs(X[sl,t]-rr)))>eps*(1+1e-10):raise RuntimeError('fallback hard')
                    Rnew[sl]=rr
                sr=np.argsort(np.argsort(X[sl,t],kind='stable'),kind='stable')
                pr=np.argsort(np.argsort(pred[sl],kind='stable'),kind='stable')
                changed_rank_pairs.append(float(np.mean(sr!=pr)))
            state[:,:-1]=state[:,1:];state[:,-1]=Rnew
        out['groups'][str(G)]={'group':G,'group_times':total,'integer_full_order_feasible_fraction':full_int/total,
             'grid256_full_order_feasible_fraction':full_grid/total,'integer_mean_max_consistent_fraction':float(np.mean(sub_int)),
             'integer_median_max_consistent_fraction':float(np.median(sub_int)),'grid256_mean_max_consistent_fraction':float(np.mean(sub_grid)),
             'grid256_median_max_consistent_fraction':float(np.median(sub_grid)),'integer_fallback_fraction':fallback_groups/total,
             'median_plateau_edge_fraction_when_feasible':float(np.median(plateau)) if plateau else 0.0,
             'mean_source_vs_predictor_rank_changed_fraction':float(np.mean(changed_rank_pairs))}
        print(json.dumps({'region':name,**out['groups'][str(G)]},indent=2),flush=True)
    return out

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;rows.append(process_region(name,c0,X,eps))
    aggregate={}
    for G in GROUPS:
        rr=[x['groups'][str(G)] for x in rows]
        aggregate[str(G)]={k:float(np.mean([z[k] for z in rr])) for k in (
            'integer_full_order_feasible_fraction','grid256_full_order_feasible_fraction','integer_mean_max_consistent_fraction',
            'grid256_mean_max_consistent_fraction','integer_fallback_fraction','mean_source_vs_predictor_rank_changed_fraction')}
    out={'global_std':std,'eps':eps,'ar_order':P,'training_samples':TRAIN,'target_interval':[TRAIN,END],'groups':list(GROUPS),'regions':rows,'aggregate':aggregate,
         'scope':'Rank-gauge existence audit. One persistent shared AR32 model per fixed 128-channel hard/easy/medium/far region is fit only on t<1024. For each future time and fixed group, decoder-known AR32 predictions define a sensor ordering. Source samples contribute only exact +/-epsilon intervals. The audit asks whether legal integer reconstructions can be synthesized monotonically in that predicted order (zero permutation/identity field), and separately whether the same is possible when restricted to the globally legal 256 grid. When full ordering is impossible, an exact dynamic program reports the maximum cardinality subset of sensors that can obey the predicted order. For the integer experiment, fully feasible groups actually use the canonical minimal nondecreasing reconstruction and feed it into future AR32 state; infeasible groups fall back to guaranteed-legal step267 reconstruction, so the predictor trajectory is decoder-real for the tested rule. This is a structural existence audit, not yet a compression-byte claim. No AI.'}
    print(json.dumps({'aggregate':aggregate},indent=2),flush=True);json.dump(out,open('imperial_ar32_rank_gauge_synthesis.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
