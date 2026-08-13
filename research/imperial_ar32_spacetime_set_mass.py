import json,sys,math
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

C0=512;C=128;P=32;TRAIN=1024;START=1024;END=1536;L=8;FINE=128
PAIRS=((0,1),(32,33),(64,65),(96,97))
WG=(0.0,0.25,0.5,0.75,1.0)

def fit_prefix(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);mb,cd=r.model_frame(co)
    R=np.zeros((C,TRAIN),np.int64);K=np.zeros((C,TRAIN),np.int32)
    for t in range(TRAIN):
        if t<P:pred=np.zeros(C,np.int64)
        else:
            v=np.full(C,float(cd[-1]),np.float64)
            for j in range(P):v+=float(cd[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        k=np.rint((X[:,t]-pred)/FINE).astype(np.int64);R[:,t]=pred+FINE*k;K[:,t]=k
    if float(np.max(np.abs(X[:,:TRAIN]-R)))>eps*(1+1e-10):raise RuntimeError('prefix hard')
    return int(mb),cd,R,K

def r_from_mean_abs(a):
    x=float(np.mean(np.abs(np.asarray(a,np.float64))))
    if x<=1e-12:return 1e-9
    return float(x/(math.sqrt(1.0+x*x)+1.0))

def lap_logp(d,rho):
    rho=min(max(float(rho),1e-12),1-1e-12)
    return math.log2((1-rho)/(1+rho))+abs(int(d))*math.log2(rho)

def mix_logp(d_t,d_s,rho_t,rho_s,w):
    if w<=0:return lap_logp(d_t,rho_t)
    if w>=1:return lap_logp(d_s,rho_s)
    a=math.log2(1-w)+lap_logp(d_t,rho_t);bb=math.log2(w)+lap_logp(d_s,rho_s)
    return float(np.logaddexp2(a,bb))

def train_prob(K):
    dt=K[:,1:].astype(np.int64)-K[:,:-1].astype(np.int64)
    ds=K[1:,:].astype(np.int64)-K[:-1,:].astype(np.int64)
    rt=r_from_mean_abs(dt);rs=r_from_mean_abs(ds)
    # Pick mixture weight only from the prefix, using all adjacent pairs/times.
    ce=[]
    for w in WG:
        s=0.0;n=0
        for c in range(1,C):
            for t in range(1,TRAIN):
                s-=mix_logp(int(K[c,t]-K[c,t-1]),int(K[c,t]-K[c-1,t]),rt,rs,w);n+=1
        ce.append((s/n,w))
    ce.sort();return rt,rs,float(ce[0][1]),ce

def pred(state,co):
    v=float(co[-1])
    for j in range(P):v+=float(co[j])*float(state[-1-j])
    return int(np.rint(v))

def legal(src,p,eps):
    lo=int(math.ceil((float(src)-eps-p)/FINE-1e-12));hi=int(math.floor((float(src)+eps-p)/FINE+1e-12))
    out=[]
    for k in range(lo,hi+1):
        rr=p+FINE*k
        if abs(float(src)-rr)<=eps*(1+1e-10):out.append((k,rr))
    if not out:raise RuntimeError(('no legal',src,p,lo,hi))
    return out

def enumerate_pair(src0,src1,s0,s1,prevk0,prevk1,co,eps,rt,rs,w):
    # exact DFS over both sensors; ~4^8 leaves in practice
    stack=[(0,s0.copy(),s1.copy(),int(prevk0),int(prevk1),0.0,0.0,[],[])]
    logmass_mix=-np.inf;logmass_ind=-np.inf;best=-1e300;bestR0=bestR1=None;bestK0=bestK1=None;leaves=0;nodes=0
    while stack:
        q,a,b,pk0,pk1,lpm,lpi,rr0,rr1=stack.pop();nodes+=1
        if q==L:
            leaves+=1;logmass_mix=float(np.logaddexp2(logmass_mix,lpm));logmass_ind=float(np.logaddexp2(logmass_ind,lpi))
            if lpm>best:best=lpm;bestR0=np.asarray(rr0,np.int64);bestR1=np.asarray(rr1,np.int64);bestK0=pk0 if False else None
            continue
        p0=pred(a,co);p1=pred(b,co);A=legal(src0[q],p0,eps);B=legal(src1[q],p1,eps)
        for k0,y0 in A:
            l0=lap_logp(k0-pk0,rt)
            na=a.copy();na[:-1]=na[1:];na[-1]=y0
            for k1,y1 in B:
                l1m=mix_logp(k1-pk1,k1-k0,rt,rs,w);l1i=lap_logp(k1-pk1,rt)
                nb=b.copy();nb[:-1]=nb[1:];nb[-1]=y1
                stack.append((q+1,na,nb,k0,k1,lpm+l0+l1m,lpi+l0+l1i,rr0+[y0],rr1+[y1]))
    if leaves==0:raise RuntimeError('pair tree died')
    # Re-run one MAP traceback cheaply with a second DFS retaining path; blocks are small.
    best=-1e300;bp=None
    stack=[(0,s0.copy(),s1.copy(),int(prevk0),int(prevk1),0.0,[],[],[],[])]
    while stack:
        q,a,b,pk0,pk1,lp,R0,R1,K0,K1=stack.pop()
        if q==L:
            if lp>best:best=lp;bp=(np.asarray(R0,np.int64),np.asarray(R1,np.int64),np.asarray(K0,np.int32),np.asarray(K1,np.int32))
            continue
        p0=pred(a,co);p1=pred(b,co)
        for k0,y0 in legal(src0[q],p0,eps):
            l0=lap_logp(k0-pk0,rt);na=a.copy();na[:-1]=na[1:];na[-1]=y0
            for k1,y1 in legal(src1[q],p1,eps):
                nb=b.copy();nb[:-1]=nb[1:];nb[-1]=y1
                stack.append((q+1,na,nb,k0,k1,lp+l0+mix_logp(k1-pk1,k1-k0,rt,rs,w),R0+[y0],R1+[y1],K0+[k0],K1+[k1]))
    return {'leaves':leaves,'nodes':nodes,'mix_bps':-logmass_mix/(2*L),'ind_bps':-logmass_ind/(2*L),'map_bps':-best/(2*L),'path':bp}

def szrun(A,eps):
    best=None
    for tr in (False,True):
        X=np.ascontiguousarray((A.T if tr else A).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        bb,_=sz.compress(X,cfg);RR,_=sz.decompress(bb,np.float32,X.shape);me=float(np.max(np.abs(X-RR)))
        if me>eps*(1+5e-6):raise RuntimeError('sz hard')
        z=(int(bb.size),me,'T' if tr else 'CT')
        if best is None or z[0]<best[0]:best=z
    return best

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:END,C0:C0+C],np.float64).T
    mb,co,R,K=fit_prefix(X,eps);rt,rs,w,ce=train_prob(K)
    rows=[];mix=[];ind=[];mp=[];freedom=[];nodes=[]
    selected=[]
    for c0,c1 in PAIRS:
        s0=R[c0,-P:].copy();s1=R[c1,-P:].copy();pk0=int(K[c0,-1]);pk1=int(K[c1,-1]);r0=[];r1=[]
        for t in range(START,END,L):
            z=enumerate_pair(X[c0,t:t+L],X[c1,t:t+L],s0,s1,pk0,pk1,co,eps,rt,rs,w)
            A,B,K0,K1=z['path'];
            if max(float(np.max(np.abs(X[c0,t:t+L]-A))),float(np.max(np.abs(X[c1,t:t+L]-B))))>eps*(1+1e-10):raise RuntimeError('pair MAP hard')
            for y in A:s0[:-1]=s0[1:];s0[-1]=int(y)
            for y in B:s1[:-1]=s1[1:];s1[-1]=int(y)
            pk0=int(K0[-1]);pk1=int(K1[-1]);r0.extend(A.tolist());r1.extend(B.tolist())
            mix.append(z['mix_bps']);ind.append(z['ind_bps']);mp.append(z['map_bps']);freedom.append(math.log2(z['leaves'])/(2*L));nodes.append(z['nodes'])
        rows.append({'pair':[int(C0+c0),int(C0+c1)],'mean_mixed_set_bps':float(np.mean(mix[-((END-START)//L):])),'mean_independent_set_bps':float(np.mean(ind[-((END-START)//L):])),'mean_legal_freedom_bps':float(np.mean(freedom[-((END-START)//L):]))})
        selected.extend([c0,c1]);print(json.dumps(rows[-1]),flush=True)
    A=X[np.asarray(selected),START:END];szb=szrun(A,eps);szbps=8*szb[0]/A.size;target=szbps/2
    out={'global_std':std,'eps':eps,'ar_order':P,'fine_step':FINE,'block_length':L,'pairs':[[int(C0+a),int(C0+b)] for a,b in PAIRS],
         'probability_model':{'temporal_rho':rt,'spatial_rho':rs,'selected_spatial_mixture_weight':w,'prefix_cross_entropy_grid':[[float(a),float(bb)] for a,bb in ce]},'ar_model_bytes':mb,
         'matched_sz3':{'bytes':szb[0],'bps':szbps,'two_x_target_bps':target,'maxerr':szb[1],'orientation':szb[2]},
         'aggregate':{'mean_independent_set_bps':float(np.mean(ind)),'mean_mixed_spacetime_set_bps':float(np.mean(mix)),'spatial_gain_bps':float(np.mean(ind)-np.mean(mix)),
                      'mean_MAP_bps':float(np.mean(mp)),'mean_legal_freedom_bps':float(np.mean(freedom)),'mean_DFS_nodes':float(np.mean(nodes)),
                      'ratio_mixed_set_to_2x_target':float(np.mean(mix))/target},'rows':rows,
         'scope':'Exact two-channel x eight-time legal-set mass audit, not a byte codec. Shared AR32 and step128 legal reconstruction prefix are decoder-known from t<1024. Four fixed adjacent hard-zone channel pairs are jointly enumerated for t=1024..1535. The first channel uses a normalized two-sided geometric/Laplace law on its innovation change; the second channel uses a prefix-selected normalized mixture of its temporal innovation change and its already-decoded left-neighbor innovation difference. All probability parameters and the mixture weight are fit only from the prefix. Exhaustive DFS sums probability over every recursively legal 16-sample spacetime trajectory and also reports an independent-temporal model on the identical legal tree. The MAP mixed path is fed into subsequent blocks, keeping the reconstruction state decoder-real. Matched SZ3 on the same eight channels supplies the 2x target. No AI.'}
    print(json.dumps(out['aggregate'],indent=2),flush=True);json.dump(out,open('imperial_ar32_spacetime_set_mass.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
