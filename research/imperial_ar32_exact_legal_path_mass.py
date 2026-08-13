import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;END=4096;L=8;FINE=128
CH=np.arange(0,128,16,dtype=np.int64)  # 8 hard channels
ALPHA=.5
ZC=zstd.ZstdCompressor(level=19)

def fit_model_and_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int32)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/FINE).astype(np.int64);R[:,t]=pred+FINE*k;K[:,t]=k
    me=float(np.max(np.abs(X[:,:TRAIN]-R)))
    if me>eps*(1+1e-10):raise RuntimeError(('prefix hard',me,eps))
    return int(mb),cd,R,K

def make_prob(K):
    mn=int(K.min())-4;mx=int(K.max())+4;cnt=np.bincount((K.ravel()-mn).astype(np.int64),minlength=mx-mn+1).astype(np.float64)
    den=float(cnt.sum()+ALPHA*len(cnt));prob=(cnt+ALPHA)/den;logs=np.log2(prob)
    meta=np.rint(cnt).astype('<i4').tobytes();mb=len(ZC.compress(meta))+32
    floor=math.log2(ALPHA/den)
    return mn,mx,logs,floor,mb

def logp(k,mn,mx,logs,floor):
    return float(logs[k-mn]) if mn<=k<=mx else float(floor)

def predict(state,co):
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(state[-1-j])
    return int(np.rint(v))

def enumerate_block(src,state,co,eps,mn,mx,logs,floor):
    bestlog=-1e300;bestR=None;bestK=None;count=0;logmass=-np.inf
    stack=[(0,state.copy(),0.0,[],[])]
    nodes=0;branches=[]
    while stack:
        q,s,lp,ks,rs=stack.pop();nodes+=1
        if q==L:
            count+=1;logmass=float(np.logaddexp2(logmass,lp))
            if lp>bestlog:bestlog=lp;bestR=np.asarray(rs,np.int64);bestK=np.asarray(ks,np.int32)
            continue
        p=predict(s,co);lo=int(math.ceil((float(src[q])-eps-p)/FINE-1e-12));hi=int(math.floor((float(src[q])+eps-p)/FINE+1e-12))
        if lo>hi:continue
        branches.append(hi-lo+1)
        for k in range(lo,hi+1):
            rr=p+FINE*k
            if abs(float(src[q])-rr)>eps*(1+1e-10):continue
            ns=s.copy();ns[:-1]=ns[1:];ns[-1]=rr
            stack.append((q+1,ns,lp+logp(k,mn,mx,logs,floor),ks+[k],rs+[rr]))
    if count==0:raise RuntimeError('no legal fine path')
    return {'count':count,'log2_mass':logmass,'best_log2_prob':bestlog,'bestR':bestR,'bestK':bestK,'nodes':nodes,'mean_branch':float(np.mean(branches)) if branches else 0.0}

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(X,cfg);R,_=sz.decompress(b,np.float32,X.shape);me=float(np.max(np.abs(X-R)))
        if me>eps*(1+5e-6):raise RuntimeError('sz hard')
        z=(int(b.size),me,'T' if tr else 'CT')
        if best is None or z[0]<best[0]:best=z
    return best

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    model_bytes,co,R0,K0=fit_model_and_prefix(X,eps);mn,mx,logs,floor,prob_meta=make_prob(K0)
    rows=[];all_counts=[];all_set=[];all_map=[];all_freedom=[];all_branch=[];all_nodes=[];all_cross=[]
    for c in CH:
        state=R0[c,-P:].copy();rates=[];counts=[]
        for t in range(TRAIN,END,L):
            src=X[c,t:t+L];z=enumerate_block(src,state,co,eps,mn,mx,logs,floor)
            setbps=-z['log2_mass']/L;mapbps=-z['best_log2_prob']/L;free=math.log2(z['count'])/L
            rates.append(setbps);counts.append(z['count']);all_counts.append(z['count']);all_set.append(setbps);all_map.append(mapbps);all_freedom.append(free);all_branch.append(z['mean_branch']);all_nodes.append(z['nodes'])
            # Cross-entropy of the canonical MAP path under the prefix model.
            all_cross.extend([-logp(int(k),mn,mx,logs,floor) for k in z['bestK']])
            for rr in z['bestR']:state[:-1]=state[1:];state[-1]=int(rr)
            if float(np.max(np.abs(src-z['bestR'])))>eps*(1+1e-10):raise RuntimeError('MAP hard')
        rows.append({'channel':int(C0+c),'blocks':len(rates),'mean_set_mass_bps':float(np.mean(rates)),'median_set_mass_bps':float(np.median(rates)),
                     'mean_legal_paths':float(np.mean(counts)),'median_legal_paths':float(np.median(counts)),'p90_legal_paths':float(np.percentile(counts,90))})
        print(json.dumps(rows[-1]),flush=True)
    A=X[CH,TRAIN:END];szb=szrun(A,eps);szbps=8*szb[0]/A.size;target=szbps/2
    q=lambda a,p:float(np.percentile(a,p))
    out={'global_std':std,'eps':eps,'ar_order':P,'fine_step':FINE,'block_length':L,'training_samples':TRAIN,'target_interval':[TRAIN,END],
         'channels':[int(C0+x) for x in CH],'model_bytes':model_bytes,'probability_table_bytes':prob_meta,'probability_support':[mn,mx],
         'matched_sz3':{'bytes':szb[0],'bps':szbps,'two_x_target_bps':target,'maxerr':szb[1],'orientation':szb[2]},
         'aggregate':{'mean_legal_paths':float(np.mean(all_counts)),'median_legal_paths':q(all_counts,50),'p90_legal_paths':q(all_counts,90),'p99_legal_paths':q(all_counts,99),
                      'mean_distortion_freedom_bps_log2M_over_L':float(np.mean(all_freedom)),'median_distortion_freedom_bps':q(all_freedom,50),
                      'mean_exact_set_mass_bps':float(np.mean(all_set)),'median_exact_set_mass_bps':q(all_set,50),'p90_exact_set_mass_bps':q(all_set,90),
                      'mean_MAP_path_bps':float(np.mean(all_map)),'mean_MAP_symbol_cross_entropy_bps':float(np.mean(all_cross)),
                      'mean_branching_factor':float(np.mean(all_branch)),'mean_DFS_nodes_per_block':float(np.mean(all_nodes)),
                      'ratio_mean_set_mass_to_2x_target':float(np.mean(all_set))/target},'rows':rows,
         'scope':'Exact legal-trajectory mass diagnostic, NOT yet a byte codec. Shared AR32 is fitted only from hard-region t<1024 and a decoder-known zero-order fine-innovation probability table is learned from the same prefix. Reconstruction uses step128, so each source sample normally admits multiple exact legal innovations under the unchanged +/-10%-global-std bound. For every held-out 8-sample block on eight hard channels, exhaustive DFS enumerates every recursively legal AR32 innovation path (no beam/pruning), computes its exact count, total prior probability mass, and MAP path. The MAP legal reconstruction is actually fed into the next block so the tested state trajectory is decoder-real. -log2(total legal-path mass)/8 is the ideal set/arithmetic-seed rate under this specific prefix model, not realized bytes; log2(path count)/8 measures pure distortion freedom independent of a codebook. Matched SZ3 on the same held-out array supplies the exact 2x target. No AI.'}
    print(json.dumps(out['aggregate'],indent=2),flush=True);json.dump(out,open('imperial_ar32_exact_legal_path_mass.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
