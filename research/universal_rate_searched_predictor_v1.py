#!/usr/bin/env python3
from __future__ import annotations
import json,math,struct,sys
import h5py,numpy as np
import imperial_fair_ar_coarse_mixture_container as cm
import imperial_fair_ar_coarse_prefix_container as fair
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

A=cm.a
STEP=267
CURRENT_BASE=22527
CURRENT_BEST=22463
MAX_SAMPLE_FEATURES=8
MAX_K_FEATURES=5
TOP_PROXY=12

# Generic causal offsets. (dt,dc): dt>0 permits either channel direction; dt=0 only dc<0.
SAMPLE_POOL=[]
for dt in (1,2,3,4,6,8,12,16,24,32):
    SAMPLE_POOL.append((dt,0))
for dt in (1,2,3,4,6,8,12,16):
    for dc in (-8,-4,-2,-1,1,2,4,8): SAMPLE_POOL.append((dt,dc))
for dc in (-1,-2,-4,-8): SAMPLE_POOL.append((0,dc))
SAMPLE_POOL=list(dict.fromkeys(SAMPLE_POOL))
K_POOL=[]
for dt in (1,2,3,4,6,8):
    for dc in (-4,-2,-1,0,1,2,4): K_POOL.append((dt,dc))
for dc in (-1,-2,-4): K_POOL.append((0,dc))
K_POOL=list(dict.fromkeys(K_POOL))


def off_value(Y,c,t,off):
    dt,dc=off;tt=t-dt;cc=c+dc
    if tt<0 or cc<0 or cc>=Y.shape[0]: return 0.0
    if dt==0 and dc>=0: raise RuntimeError('noncausal offset')
    return float(Y[cc,tt])


def feature_matrix(Y,pool):
    nc,nt=Y.shape;cols={}
    for off in pool:
        z=np.zeros((nc,nt),np.float64)
        for t in range(nt):
            for c in range(nc): z[c,t]=off_value(Y,c,t,off)
        cols[off]=z.reshape(-1)
    return cols


def fit_cols(target,cols,offs,skip_t0=False):
    nc,nt=target.shape
    mask=np.ones((nc,nt),bool)
    if skip_t0: mask[:,0]=False
    idx=mask.reshape(-1)
    M=np.column_stack([cols[o][idx] for o in offs]+[np.ones(int(idx.sum()),np.float64)])
    y=target.reshape(-1)[idx]
    co=np.linalg.lstsq(M,y,rcond=1e-7)[0].astype(np.float32)
    return co


def model_rt(co):
    buf,name=fair.encode_model(np.asarray(co,np.float32));cod,pos=fair.decode_model(buf,0,len(co))
    if pos!=len(buf) or not np.array_equal(cod.view(np.uint32),np.asarray(co,np.float32).view(np.uint32)): raise RuntimeError('model replay')
    return buf,name,cod


def offset_rt(offs):
    if len(offs)>255: raise RuntimeError('too many offsets')
    b=bytearray([len(offs)])
    for dt,dc in offs: b.extend(struct.pack('Bb',dt,dc))
    p=1;out=[]
    for _ in range(b[0]):
        dt,dc=struct.unpack('Bb',bytes(b[p:p+2]));p+=2;out.append((int(dt),int(dc)))
    if p!=len(b) or out!=list(offs): raise RuntimeError('offset replay')
    return bytes(b),out


def entropy_bits(K):
    _,cnt=np.unique(K,return_counts=True);p=cnt/cnt.sum();return float(-(p*np.log2(p)).sum()*K.size)


def proxy_rate(target,cols,offs,co,step):
    P=np.zeros(target.size,np.float64)
    for j,o in enumerate(offs): P+=float(co[j])*cols[o]
    P+=float(co[-1]);P=P.reshape(target.shape)
    if step is None: Q=np.rint(target-P).astype(np.int32)
    else: Q=np.rint((target-P)/step).astype(np.int32)
    return entropy_bits(Q)


def sample_pred(R,c,t,co,offs):
    if t==0:return 0
    s=float(co[-1])
    for j,o in enumerate(offs): s+=float(co[j])*off_value(R,c,t,o)
    if not math.isfinite(s):raise RuntimeError('nonfinite sample pred')
    return int(np.rint(s))


def build_sample(X,co,offs):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=sample_pred(R,c,t,co,offs);k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def sample_screen(X,offs,co):
    mb,_,cod=model_rt(co);ob,od=offset_rt(offs);R,K=build_sample(X,cod,od)
    legacy=int(m.encode_k(K)[0]);return fair.COMMON_HEADER+1+len(ob)+len(mb)+legacy,R,K,mb,ob,cod


def search_sample(X):
    cols=feature_matrix(X,SAMPLE_POOL);selected=[(1,0)];history=[]
    co=fit_cols(X,cols,selected,True);best=sample_screen(X,selected,co);best_score=best[0]
    history.append({'stage':1,'offsets':selected,'screen_bytes':best_score})
    while len(selected)<MAX_SAMPLE_FEATURES:
        cand=[]
        for o in SAMPLE_POOL:
            if o in selected:continue
            oo=selected+[o];cc=fit_cols(X,cols,oo,True);pr=proxy_rate(X,cols,oo,cc,STEP)
            cand.append((pr,o,cc))
        cand.sort(key=lambda z:z[0]);winner=None
        for pr,o,cc in cand[:TOP_PROXY]:
            q=sample_screen(X,selected+[o],cc)
            row=(q[0],o,cc,q,pr)
            if winner is None or row[0]<winner[0]:winner=row
        if winner is None or winner[0]>=best_score:break
        best_score,o,co,best,pr=winner;selected.append(o)
        history.append({'stage':len(selected),'added':list(o),'offsets':[list(x) for x in selected],'proxy_entropy_bits':pr,'screen_bytes':best_score})
    return selected,co,best,history


def k_predict(K,c,t,co,offs):
    s=float(co[-1])
    for j,o in enumerate(offs):s+=float(co[j])*off_value(K,c,t,o)
    if not math.isfinite(s):raise RuntimeError('nonfinite K pred')
    return int(np.rint(s))


def make_innovation(K,co,offs):
    J=np.zeros(K.shape,np.int32)
    # Predictor sees exact prior K, so encoder/decoder state is identical.
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):J[c,t]=int(K[c,t])-k_predict(K,c,t,co,offs)
    return J


def restore_k(J,co,offs):
    K=np.zeros(J.shape,np.int32)
    for t in range(J.shape[1]):
        for c in range(J.shape[0]):K[c,t]=k_predict(K,c,t,co,offs)+int(J[c,t])
    return K


def k_screen(K,offs,co):
    mb,_,cod=model_rt(co);ob,od=offset_rt(offs);J=make_innovation(K,cod,od);legacy=int(m.encode_k(J)[0])
    Kd=restore_k(J,cod,od)
    if not np.array_equal(Kd,K):raise RuntimeError('K innovation replay')
    return fair.COMMON_HEADER+1+len(ob)+len(mb)+legacy,J,mb,ob,cod


def search_k(K):
    cols=feature_matrix(K.astype(np.float64),K_POOL);selected=[];history=[]
    # Baseline is no second-stage predictor.
    base_legacy=int(m.encode_k(K)[0]);best_score=fair.COMMON_HEADER+1+base_legacy;best=(best_score,K,b'',b'',np.array([0],np.float32))
    while len(selected)<MAX_K_FEATURES:
        cand=[]
        for o in K_POOL:
            if o in selected:continue
            oo=selected+[o];cc=fit_cols(K.astype(np.float64),cols,oo,False);pr=proxy_rate(K.astype(np.float64),cols,oo,cc,None)
            cand.append((pr,o,cc))
        cand.sort(key=lambda z:z[0]);winner=None
        for pr,o,cc in cand[:TOP_PROXY]:
            q=k_screen(K,selected+[o],cc);row=(q[0],o,cc,q,pr)
            if winner is None or row[0]<winner[0]:winner=row
        if winner is None or winner[0]>=best_score:break
        best_score,o,co,best,pr=winner;selected.append(o)
        history.append({'stage':len(selected),'added':list(o),'offsets':[list(x) for x in selected],'proxy_entropy_bits':pr,'screen_bytes':best_score})
    return selected,best,history


def exact_field(J):
    field,_,Jd,detail=A.hybrid_frame(J)
    if not np.array_equal(Jd,J):raise RuntimeError('field replay')
    return int(field),Jd,detail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps)
    # Exact incumbent baseline, same address.
    bco=np.asarray(fair.fit(X,1,'prefix64'),np.float32);bmb,_,bcod=model_rt(bco);bR,bK=build_sample(X,bcod,[(1,0)])
    # The generic offset boundary differs from legacy AR1 only at t=0, where both are zero; verify exact K identity.
    refR,refK=fair.build(X,1,bcod)
    if not np.array_equal(bK,refK) or not np.array_equal(bR,refR):raise RuntimeError('incumbent mismatch')
    bf,_,_=exact_field(bK);baseline=fair.COMMON_HEADER+1+len(bmb)+bf
    if baseline!=CURRENT_BASE:raise RuntimeError(('baseline drift',baseline,CURRENT_BASE))

    offs,co,sbest,shist=search_sample(X);screen,R,K,smb,sob,scod=sbest
    koff,kbest,khist=search_k(K);kscreen,J,kmb,kob,kcod=kbest
    # If no K predictor was selected, keep K directly and charge no second-stage model metadata.
    if not koff:J=K;kmb=b'';kob=b'';kcod=np.array([0],np.float32)
    field,Jd,detail=exact_field(J)
    if koff:Kd=restore_k(Jd,kcod,koff)
    else:Kd=Jd
    if not np.array_equal(Kd,K):raise RuntimeError('final K replay')
    Rd=np.zeros(K.shape,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):Rd[c,t]=sample_pred(Rd,c,t,scod,offs)+STEP*int(Kd[c,t])
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
    total=fair.COMMON_HEADER+1+len(sob)+len(smb)+len(kob)+len(kmb)+field
    out={'kind':'universal-rate-searched-predictor-v1','shape':list(X.shape),'eps':eps,'step':STEP,
         'principle':'SZ3-style prediction -> error-bounded quantization -> entropy coding, but the causal stencil is discovered by rate and the quantized residual may itself be causally predicted losslessly.',
         'sample_offsets':[list(x) for x in offs],'sample_coefficients':scod.tolist(),'sample_search':shist,
         'k_offsets':[list(x) for x in koff],'k_coefficients':kcod.tolist() if koff else [],'k_search':khist,
         'bytes':int(total),'field_bytes':field,'sample_model_bytes':len(smb),'sample_offset_bytes':len(sob),'k_model_bytes':len(kmb),'k_offset_bytes':len(kob),
         'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'innovation_zero_fraction':float(np.mean(J==0)),
         'baseline_bytes':baseline,'current_best_bytes':CURRENT_BEST,'sz3_bytes':int(szb),'sz3_orientation':ori,
         'gain_vs_sz3':float(szb/total),'gain_vs_current_best':float(CURRENT_BEST/total),'field_detail':detail}
    json.dump(out,open('universal_rate_searched_predictor_v1.json','w'),indent=2)
    print('FINAL',json.dumps({k:v for k,v in out.items() if k not in ('field_detail','sample_search','k_search','sample_coefficients','k_coefficients')},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
