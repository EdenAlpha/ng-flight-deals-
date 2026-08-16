import json,sys,math
from collections import Counter
import h5py,numpy as np
import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

# GCA-style encoder search: keep the charged AR1/prefix64 decoder model and step267,
# but exploit every hard-error-legal neighboring innovation trajectory. The search
# objective is encoder-only; only the final K field is transmitted.
A=cm.a
STEP=267
BEAM=64
OBJECTIVES=('lowbits','allbits','symbol','temporal_bits','causal_bits','symbol_causal','zero_mag')


def zz(k):
    k=int(k)
    return 2*k if k>=0 else -2*k-1


def cost_model(K):
    U=m.zig(K);n=U.size;mx=int(U.max());nb=max(1,mx.bit_length())
    bit=np.empty((nb,2),np.float64)
    for b in range(nb):
        o=int(np.sum((U>>b)&1));p=(o+1.0)/(n+2.0)
        bit[b,1]=-math.log2(p);bit[b,0]=-math.log2(1.0-p)
    tt=np.ones((nb,2,2),np.float64);tc=np.ones((nb,2),np.float64)
    cc=np.ones((nb,2,2),np.float64);cn=np.ones((nb,2),np.float64)
    for b in range(nb):
        B=((U>>b)&1).astype(np.uint8)
        for pv in (0,1):
            q=B[:,:-1]==pv
            vals=B[:,1:][q]
            if vals.size:
                tt[b,pv,0]+=int(np.sum(vals==0));tt[b,pv,1]+=int(np.sum(vals==1));tc[b,pv]+=vals.size
            q=B[:-1,:]==pv
            vals=B[1:,:][q]
            if vals.size:
                cc[b,pv,0]+=int(np.sum(vals==0));cc[b,pv,1]+=int(np.sum(vals==1));cn[b,pv]+=vals.size
    tcost=np.empty_like(tt);ccost=np.empty_like(cc)
    for b in range(nb):
        for pv in (0,1):
            z=tt[b,pv].sum();zc=cc[b,pv].sum()
            for x in (0,1):
                tcost[b,pv,x]=-math.log2(tt[b,pv,x]/z)
                ccost[b,pv,x]=-math.log2(cc[b,pv,x]/zc)
    hist=Counter(int(x) for x in K.ravel());den=n+len(hist)+32
    scost={k:-math.log2((v+1.0)/den) for k,v in hist.items()};sunseen=-math.log2(1.0/den)
    return {'nb':nb,'bit':bit,'tcost':tcost,'ccost':ccost,'scost':scost,'sunseen':sunseen}


def local_cost(kind,k,prevk,leftk,C):
    u=zz(k);pu=zz(prevk);lu=zz(leftk)
    def bitsum(lo,hi,tab):
        s=0.0
        for b in range(lo,hi):s+=tab[b,(u>>b)&1]
        return s
    if kind=='lowbits':return bitsum(0,min(3,C['nb']),C['bit'])
    if kind=='allbits':return bitsum(0,C['nb'],C['bit'])
    if kind=='symbol':return C['scost'].get(int(k),C['sunseen'])
    if kind=='zero_mag':return (0.0 if k==0 else 1.0)+0.015*abs(int(k))
    ts=cs=0.0
    for b in range(C['nb']):
        x=(u>>b)&1;ts+=C['tcost'][b,(pu>>b)&1,x];cs+=C['ccost'][b,(lu>>b)&1,x]
    if kind=='temporal_bits':return ts
    if kind=='causal_bits':return 0.55*ts+0.45*cs
    if kind=='symbol_causal':return C['scost'].get(int(k),C['sunseen'])+0.22*ts+0.18*cs
    raise ValueError(kind)


def legal_bounds(x,pred,eps):
    lo=int(math.ceil((float(x)-float(eps)-pred)/STEP-1e-12))
    hi=int(math.floor((float(x)+float(eps)-pred)/STEP+1e-12))
    return lo,hi


def search_channel(x,coef,eps,kind,C,left):
    # DP state is (previous reconstruction, previous K). For AR1 this is a complete
    # decoder state. Beam pruning is only an encoder search approximation; every
    # surviving trajectory is still exactly legal and decoder-real.
    a=float(coef[0]);b=float(coef[-1]);states={(0,0):0.0};layers=[];max_states=1
    for t in range(x.size):
        cand={}
        for pk,score in states.items():
            rp,prevk=pk
            pred=0 if t==0 else int(np.rint(b+a*float(rp)))
            lo,hi=legal_bounds(x[t],pred,eps)
            if hi<lo:continue
            lk=int(left[t]) if left is not None else 0
            nchoice=hi-lo+1
            for k in range(lo,hi+1):
                r=pred+STEP*k
                if abs(float(x[t])-r)>eps*(1+5e-10):continue
                ns=score+local_cost(kind,k,prevk,lk,C);nk=(int(r),int(k));old=cand.get(nk)
                row=(ns,pk,int(k),nchoice)
                if old is None or ns<old[0]:cand[nk]=row
        if not cand:raise RuntimeError(('no legal state',kind,t))
        if len(cand)>BEAM:
            keep=sorted(cand.items(),key=lambda z:z[1][0])[:BEAM];cand=dict(keep)
        layers.append(cand);states={k:v[0] for k,v in cand.items()};max_states=max(max_states,len(states))
    key=min(states,key=states.get);seq=np.empty(x.size,np.int32);amb=0
    for t in range(x.size-1,-1,-1):
        score,prev,k,nchoice=layers[t][key];seq[t]=k;amb+=int(nchoice>1);key=prev
    return seq,float(min(states.values())),amb,max_states


def replay(X,coef,K,eps):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            pred=fair.ar.predict_hist(R,c,t,coef,1,'shared');R[c,t]=pred+STEP*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard replay',me,eps))
    return R,me


def optimize(X,coef,K0,eps,kind,C):
    K=K0.copy();amb=0;mx=0;scores=[]
    for c in range(K.shape[0]):
        left=K[c-1] if c>0 else None
        q,sc,aa,mm=search_channel(X[c],coef,eps,kind,C,left);K[c]=q;amb+=aa;mx=max(mx,mm);scores.append(sc)
    R,me=replay(X,coef,K,eps)
    return K,R,me,{'objective':kind,'chosen_ambiguous_steps':amb,'max_beam_states':mx,'proxy_score':float(sum(scores)),'changed_k':int(np.sum(K!=K0))}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std
        X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    co=fair.fit(X,1,'prefix64');model,mname=fair.encode_model(co);coef,pos=fair.decode_model(model,0,2)
    if pos!=len(model):raise RuntimeError('model trailing')
    R0,K0=fair.build(X,1,coef);me0=float(np.max(np.abs(X-R0.astype(np.float64))))
    if me0>eps*(1+5e-6):raise RuntimeError(('baseline hard',me0,eps))
    f0,_,D0,d0=A.hybrid_frame(K0)
    if not np.array_equal(D0,K0):raise RuntimeError('baseline K decode')
    base_total=fair.COMMON_HEADER+1+len(model)+int(f0)
    C=cost_model(K0);rows=[{'objective':'nearest_baseline','bytes':base_total,'field_bytes':int(f0),'model_bytes':len(model),'maxerr':me0,'changed_k':0,'field_detail':d0}]
    print(json.dumps({k:v for k,v in rows[0].items() if k!='field_detail'},indent=2),flush=True)
    for kind in OBJECTIVES:
        K,R,me,diag=optimize(X,coef,K0,eps,kind,C)
        fb,_,Kd,detail=A.hybrid_frame(K)
        if not np.array_equal(Kd,K):raise RuntimeError(('K decode',kind))
        Rd,mer=replay(X,coef,Kd,eps)
        if not np.array_equal(Rd,R):raise RuntimeError(('R replay',kind))
        total=fair.COMMON_HEADER+1+len(model)+int(fb)
        row={**diag,'bytes':int(total),'field_bytes':int(fb),'model_bytes':len(model),'maxerr':mer,'field_detail':detail}
        rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='field_detail'},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'step':STEP,'order':1,'fit_scope':'prefix64','beam':BEAM,
         'objectives':list(OBJECTIVES),'model_bytes':len(model),'model_rep':mname,'common_header_bytes':fair.COMMON_HEADER,
         'sz3':{'bytes':int(szb),'orientation':ori},'baseline_bytes':base_total,'rows':rows,'best':best,
         'scope':'GCA-style legal-trajectory search on the strict AR1/prefix64 common container. The decoder model and step267 are frozen. At every sample the encoder enumerates every neighboring integer K whose recursively reconstructed value remains inside the unchanged ±epsilon source interval. Because AR1 is first-order and channel-separable, a beam DP searches legal decoder trajectories per channel under several public encoder-only proxy objectives (low/all bit NLL, symbol NLL, temporal/spatial bit NLL and zero/magnitude). The search objective/path is never transmitted; only the final exact K field is encoded with the same coarse-prefix+mixture address. Every candidate K stream is physically decoded, the AR1 source is recursively replayed, and hard error is verified. The final winner is chosen only by actual materialized bytes.'}
    json.dump(out,open('imperial_ar1_legal_trajectory_address.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base_total,'best':best['bytes'],'objective':best['objective'],'delta':best['bytes']-base_total,'changed_k':best.get('changed_k',0),'sz3':int(szb),'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
