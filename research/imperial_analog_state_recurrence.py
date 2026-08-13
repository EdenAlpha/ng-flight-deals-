import json,sys,math
import h5py,numpy as np
from scipy.spatial import cKDTree
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;STEP=267;PREFIX=4096;DICT_END=3072;END=8192
MS=(8,16,32,64);CH=np.arange(0,128,8,dtype=np.int64)

def ar_prefix(X,eps):
    co=r.fit_shared(X[:,:1024],P);mb,cd=r.model_frame(co);R=np.zeros((C,PREFIX),np.int64);K=np.zeros((C,PREFIX),np.int32)
    for t in range(PREFIX):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/STEP).astype(np.int64);R[:,t]=pred+STEP*k;K[:,t]=k
    if float(np.max(np.abs(X[:,:PREFIX]-R)))>eps*(1+1e-10):raise RuntimeError('prefix hard')
    return int(mb),cd,R,K

def arpred(state,co):
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(state[-1-j])
    return int(np.rint(v))

def feature(state,M):
    z=np.diff(np.asarray(state[-M:],np.float64));sc=float(np.sqrt(np.mean(z*z))+1.0)
    return (z/sc).astype(np.float32),sc

def build_dict(Rc,M):
    F=[];cont=[];scales=[]
    for t in range(M,DICT_END):
        f,s=feature(Rc[t-M:t],M);F.append(f);cont.append((float(Rc[t]-Rc[t-1]))/s);scales.append(s)
    F=np.asarray(F,np.float32);return cKDTree(F,compact_nodes=True,balanced_tree=True),np.asarray(cont,np.float64),np.asarray(scales,np.float64)

def analog_pred(state,M,tree,cont):
    f,s=feature(state,M);dist,idx=tree.query(f,k=1,p=2,workers=1);dy=int(np.rint(s*float(cont[int(idx)])));return int(state[-1])+dy,float(dist),int(idx)

def choose_threshold(Rc,co,M,tree,cont):
    ds=[];loss_a=[];loss_h=[]
    for t in range(DICT_END,PREFIX):
        state=Rc[:t];pa=arpred(state,co);pr,d,_=analog_pred(state,M,tree,cont);target=int(Rc[t])
        ds.append(d);loss_a.append(math.log2(1+abs(int(np.rint((target-pa)/STEP)))));loss_h.append(math.log2(1+abs(int(np.rint((target-pr)/STEP)))))
    ds=np.asarray(ds);la=np.asarray(loss_a);lh=np.asarray(loss_h);qs=np.unique(np.quantile(ds,[0,.05,.1,.2,.35,.5,.65,.8,.9,.95,1.0]))
    best=(float(np.mean(la)), -1.0, 0.0)
    for q in qs:
        use=ds<=q;loss=np.where(use,lh,la);z=(float(np.mean(loss)),float(q),float(np.mean(use)))
        if z[0]<best[0]:best=z
    return {'proxy_bps':best[0],'threshold':best[1],'validation_analog_fraction':best[2],'ar_proxy_bps':float(np.mean(la)),'analog_proxy_bps':float(np.mean(lh))}

def run_channel(Xc,Rprefix,co,M,tree,cont,threshold,eps,mode):
    state=Rprefix.copy().astype(np.int64);ks=[];rr=[];dists=[];analog_used=0
    for t in range(PREFIX,END):
        pa=arpred(state,co);pr,d,_=analog_pred(state,M,tree,cont);dists.append(d)
        if mode=='analog':pred=pr;analog_used+=1
        elif mode=='gate':
            if threshold>=0 and d<=threshold:pred=pr;analog_used+=1
            else:pred=pa
        else:pred=pa
        k=int(np.rint((float(Xc[t])-pred)/STEP));y=pred+STEP*k
        if abs(float(Xc[t])-y)>eps*(1+1e-10):raise RuntimeError(('hard',mode,t,Xc[t],pred,k,y))
        ks.append(k);rr.append(y);state=np.append(state,y) if len(state)<P else np.concatenate([state[-(P-1):],[y]])
    return np.asarray(ks,np.int64),np.asarray(rr,np.int64),{'analog_fraction':analog_used/(END-PREFIX),'median_state_distance':float(np.median(dists)),'p90_state_distance':float(np.percentile(dists,90))}

def encode(K):
    b,rep,dec=m.encode_k(np.asarray(K,np.int64));dd=np.asarray(dec,np.int64).reshape(np.asarray(K).shape)
    if not np.array_equal(dd,K):raise RuntimeError('k frame')
    return int(b)+32,rep

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    model_bytes,co,R0,K0=ar_prefix(X,eps);rows=[]
    # AR32 conditional-on-prefix incumbent on identical 16 held-out hard channels.
    AK=[]
    for c in CH:
        k,rr,st=run_channel(X[c],R0[c],co,8,*build_dict(R0[c],8)[:2],-1,eps,'ar');AK.append(k)
    AK=np.stack(AK);ab,arep=encode(AK)
    for M in MS:
        Kanalog=[];Kgate=[];stats=[];val=[]
        for c in CH:
            tree,cont,_=build_dict(R0[c],M);v=choose_threshold(R0[c],co,M,tree,cont);val.append(v)
            ka,ra,sa=run_channel(X[c],R0[c],co,M,tree,cont,v['threshold'],eps,'analog')
            kg,rg,sg=run_channel(X[c],R0[c],co,M,tree,cont,v['threshold'],eps,'gate')
            if float(np.max(np.abs(X[c,PREFIX:END]-ra)))>eps*(1+1e-10) or float(np.max(np.abs(X[c,PREFIX:END]-rg)))>eps*(1+1e-10):raise RuntimeError('final hard')
            Kanalog.append(ka);Kgate.append(kg);stats.append({'analog':sa,'gate':sg})
        Kanalog=np.stack(Kanalog);Kgate=np.stack(Kgate);ba,repa=encode(Kanalog);bg,repg=encode(Kgate)
        row={'M':M,'analog_bytes':ba,'analog_bps':8*ba/Kanalog.size,'analog_gain_vs_ar32':ab/ba,'analog_rep':repa,
             'gated_bytes':bg,'gated_bps':8*bg/Kgate.size,'gated_gain_vs_ar32':ab/bg,'gated_rep':repg,'ar32_bytes':ab,'ar32_bps':8*ab/AK.size,
             'median_validation_threshold':float(np.median([v['threshold'] for v in val])),'median_validation_analog_fraction':float(np.median([v['validation_analog_fraction'] for v in val])),
             'median_target_gate_analog_fraction':float(np.median([z['gate']['analog_fraction'] for z in stats])),'median_target_state_distance':float(np.median([z['analog']['median_state_distance'] for z in stats]))}
        rows.append(row);print(json.dumps(row,indent=2),flush=True)
    rows.sort(key=lambda z:z['gated_bytes'])
    out={'global_std':std,'eps':eps,'hard_region_c0':C0,'channels':[int(C0+c) for c in CH],'prefix_samples':PREFIX,'dictionary_end':DICT_END,'target_interval':[PREFIX,END],
         'ar_order':P,'step':STEP,'ar_model_bytes':model_bytes,'ar32_conditional_prefix':{'bytes':ab,'bps':8*ab/AK.size,'rep':arep},'rows':rows,'best_gated':rows[0],
         'scope':'Nonlinear analog-state recurrence gate, conditional on the already-decoded 4096-sample prefix and therefore not a whole-file/SZ3 claim. For each hard-zone channel, the decoder deterministically builds a cKDTree from prefix states only. A state is the recent M-sample reconstructed increment shape normalized by its own RMS; each historical state stores only the normalized next increment, also derived from decoded prefix. At target time, the nearest historical state predicts the next increment after rescaling to the current decoder-known state amplitude. No learned model or dictionary payload is transmitted. A deterministic AR32-vs-analog gate threshold is itself selected from decoded prefix validation (3072..4095), so no target selector bits are sent. Target innovations use the unchanged legal step267 and are actually encoded/decoded with the incumbent innovation frame; final hard error is checked. This tests nonlinear recurrence beyond AR32 and exact phrase reuse. No AI.'}
    print(json.dumps({'ar32':out['ar32_conditional_prefix'],'best':rows[0]},indent=2),flush=True);json.dump(out,open('imperial_analog_state_recurrence.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
