import json,math,sys
from collections import Counter,defaultdict
import h5py,numpy as np
import imperial_dyadic_shared_resonator as ar
import imperial_decoder_phase_automaton as m

ORDERS=(0,16,32)
ALPHA=0.1

def entropy_int(a):
    a=np.asarray(a).ravel()
    if not a.size:return 0.0
    _,cnt=np.unique(a,return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())

def joint_entropy(cols):
    A=np.column_stack([np.asarray(x).ravel() for x in cols])
    if not A.size:return 0.0
    _,cnt=np.unique(A,axis=0,return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())

def cond_entropy(y,ctx):
    return max(0.0,joint_entropy(list(ctx)+[y])-joint_entropy(ctx))

def moments(a):
    x=np.asarray(a,np.float64).ravel();mu=float(x.mean());sd=float(x.std())
    if sd==0:return {'mean':mu,'std':0.0,'skew':0.0,'excess_kurtosis':-3.0}
    z=(x-mu)/sd
    return {'mean':mu,'std':sd,'skew':float(np.mean(z**3)),'excess_kurtosis':float(np.mean(z**4)-3.0)}

def corr(a,b):
    x=np.asarray(a,np.float64).ravel();y=np.asarray(b,np.float64).ravel();x-=x.mean();y-=y.mean();den=float(np.sqrt(np.dot(x,x)*np.dot(y,y)))
    return float(np.dot(x,y)/den) if den else 0.0

def spectral_flatness(E):
    E=np.asarray(E,np.float64);F=np.fft.rfft(E-E.mean(axis=1,keepdims=True),axis=1);P=(F.real*F.real+F.imag*F.imag)[:,1:]
    if P.size==0:return 0.0
    tiny=max(float(P.mean())*1e-15,1e-30);gm=np.exp(np.mean(np.log(P+tiny),axis=1));am=np.mean(P+tiny,axis=1)
    return float(np.median(gm/am))

def recursive_shared(X,p):
    if p==0:
        P=np.zeros(X.shape,np.int32);K=np.rint(X/m.STEP).astype(np.int32);R=m.STEP*K
        return P,K,R,np.empty(0,np.float32),0
    co=ar.fit_shared(X,p);mb,cd=ar.model_frame(co);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);P=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=ar.predict_hist(R,c,t,cd,p,'shared');k=int(np.rint((float(X[c,t])-pred)/m.STEP));rr=pred+m.STEP*k
            P[c,t]=pred;K[c,t]=k;R[c,t]=rr
    return P,K,R,cd,mb

def cv_context_xent(K):
    K=np.asarray(K,np.int32);C,T=K.shape;cut=T//2
    root=Counter();c1=defaultdict(Counter);c2=defaultdict(Counter);c3=defaultdict(Counter)
    for c in range(C):
        for t in range(1,cut):
            y=int(K[c,t]);pt=int(K[c,t-1]);left=int(K[c-1,t]) if c else 0;lp=int(K[c-1,t-1]) if c else 0
            root[y]+=1;c1[pt][y]+=1
            if c:c2[(pt,left)][y]+=1;c3[(pt,left,lp)][y]+=1
    V=max(1,len(root));N=sum(root.values());symbols=list(root.keys())
    def basep(y):return (root.get(y,0)+ALPHA)/(N+ALPHA*V)
    def blend(tab,key,y,p0):
        cc=tab.get(key)
        if not cc:return p0
        n=sum(cc.values());lam=n/(n+16.0)
        return lam*((cc.get(y,0)+ALPHA)/(n+ALPHA*V))+(1-lam)*p0
    bits1=bits2=bits3=0.0;n=0
    for c in range(C):
        for t in range(max(cut,1),T):
            y=int(K[c,t]);pt=int(K[c,t-1]);left=int(K[c-1,t]) if c else 0;lp=int(K[c-1,t-1]) if c else 0
            p=basep(y);p1=blend(c1,pt,y,p);p2=blend(c2,(pt,left),y,p1) if c else p1;p3=blend(c3,(pt,left,lp),y,p2) if c else p2
            bits1-=math.log2(max(p1,1e-15));bits2-=math.log2(max(p2,1e-15));bits3-=math.log2(max(p3,1e-15));n+=1
    return {'test_samples':n,'prev_time_xent_bps':bits1/n,'prev_time_left_xent_bps':bits2/n,'prev_time_left_leftprev_xent_bps':bits3/n}

def audit_model(X,eps,p):
    P,K,R,coef,model_bytes=recursive_shared(X,p);E=np.rint(X).astype(np.int32)-P
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>128.000001 or me>eps*(1+1e-12):raise RuntimeError(('hard',p,me,eps))
    em=moments(E);km=moments(K)
    t_y=K[:,1:];t_prev=K[:,:-1];s_y=K[1:,:];s_left=K[:-1,:]
    yy=K[1:,1:];pt=K[1:,:-1];left=K[:-1,1:];lp=K[:-1,:-1]
    lags={str(l):corr(E[:,:-l],E[:,l:]) for l in (1,2,4,8,16,32) if l<E.shape[1]}
    allowed_ints=2*int(math.floor(eps))+1
    H_E=entropy_int(E);H_K=entropy_int(K)
    # This is a one-symbol entropy-covering bound only. Correlations can lower process rate further.
    zero_order_cover=max(0.0,H_E-math.log2(allowed_ints))
    gref=max(0.0,math.log2(max(em['std'],1e-30)/eps)+0.5*math.log2(2*math.pi*math.e)-1.0)
    frame=m.encode_k(K);actual_bytes=int(frame[0])+int(model_bytes)+20
    return {
      'order':p,'model_bytes':int(model_bytes),'actual_innovation_codec_bytes':actual_bytes,'actual_innovation_codec_bps':8*actual_bytes/X.size,'innovation_rep':frame[1],
      'maxerr':me,'residual':em,'innovation':km,'residual_entropy_bps':H_E,'innovation_zero_order_entropy_bps':H_K,
      'innovation_time_cond_entropy_bps':cond_entropy(t_y,[t_prev]),'innovation_space_cond_entropy_bps':cond_entropy(s_y,[s_left]),
      'innovation_2d_context_empirical_bps':cond_entropy(yy,[pt,left,lp]),'crossvalidated_context':cv_context_xent(K),
      'residual_lag_corr':lags,'residual_adjacent_channel_corr':corr(E[:-1,:],E[1:,:]),'residual_spectral_flatness_median':spectral_flatness(E),
      'integer_error_ball_cardinality':allowed_ints,'zero_order_entropy_cover_bound_bps':zero_order_cover,
      'gaussian_same_variance_highrate_reference_bps':gref,'k_zero_fraction':float(np.mean(K==0)),'k_abs_le1_fraction':float(np.mean(np.abs(K)<=1))
    }

def main(path):
  with h5py.File(path,'r') as f:
    d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
    for name,t0,c0 in m.SPECS:
      X=np.asarray(d[t0:t0+m.T,c0:c0+m.C],np.float64).T;sb,ori=m.szrun(X,eps);source_H=entropy_int(np.rint(X).astype(np.int32));models=[]
      for p in ORDERS:
        q=audit_model(X,eps,p);q['gain_vs_sz3']=sb/q['actual_innovation_codec_bytes'];models.append(q);print(json.dumps({'tile':name,'order':p,'actual_bps':q['actual_innovation_codec_bps'],'Hk':q['innovation_zero_order_entropy_bps'],'ctx_cv':q['crossvalidated_context'],'resid_std':q['residual']['std'],'flatness':q['residual_spectral_flatness_median']}),flush=True)
      rows.append({'tile':name,'t0':t0,'c0':c0,'samples':int(X.size),'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),'source_zero_order_entropy_bps':source_H,'source_zero_order_cover_bound_bps':max(0.0,source_H-math.log2(2*int(math.floor(eps))+1)),'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'strict_2x_target_bps':4*sb/X.size,'sz3_orientation':ori,'models':models})
    out={'global_std':std,'eps':eps,'step':m.STEP,'orders':list(ORDERS),'rows':rows,'scope':'Information/headroom audit, not an impossibility proof and not a compression claim beyond the explicitly byte-counted innovation frames. For each canonical 128x1024 Imperial regime, shared recursive AR states generate integer decoder predictors and exact 256-step hard-error innovations. The audit reports actual existing frame bytes plus zero-order/conditional innovation entropies, out-of-sample second-half cross-entropy under first-half causal contexts, residual autocorrelation/spectral flatness and distribution shape. H(E)-log2(267) is only a single-symbol entropy-covering bound; it is not a process-rate lower bound because cross-sample dependence can reduce rate. The Gaussian same-variance number is a reference, not a lower bound. Purpose: decide whether a genuine block/syndrome code has enough remaining structure to plausibly approach the 2x-SZ3 target.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_hardzone_information_floor.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
