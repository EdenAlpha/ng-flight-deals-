#!/usr/bin/env python3
from __future__ import annotations
import json,math,sys
import h5py,numpy as np
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEP=267
STRIDES=(8,16,32,64)
TOP_EXACT=2
HEADER=24

def val(R,done,c,t):
    if c<0 or c>=R.shape[0] or t<0 or t>=R.shape[1] or not done[c,t]:return None
    return int(R[c,t])

def anchor_pred(R,done,c,t,stride,pid):
    a=val(R,done,c,t-stride);b=val(R,done,c-1,t);d=val(R,done,c-1,t-stride)
    if pid==0:return 0
    if pid==1:return 0 if a is None else a
    if pid==2:return 0 if b is None else b
    if pid==3:
        if a is not None and b is not None and d is not None:return a+b-d
        if a is not None:return a
        return 0 if b is None else b
    if pid==4:
        z=[x for x in (a,b) if x is not None];return int(round(sum(z)/len(z))) if z else 0
    raise ValueError(pid)

def mid_pred(R,done,c,t,h,pid):
    l=val(R,done,c,t-h);r=val(R,done,c,t+h);ll=val(R,done,c,t-3*h);rr=val(R,done,c,t+3*h);s=val(R,done,c-1,t)
    sl=val(R,done,c-1,t-h);sr=val(R,done,c-1,t+h)
    if l is not None and r is not None:temp=int(round((l+r)/2.0))
    elif l is not None:temp=l
    elif r is not None:temp=r
    else:temp=0
    if pid==0:return temp
    if pid==1:
        if l is not None and r is not None and ll is not None and rr is not None:return int(round((9.0*(l+r)-(ll+rr))/16.0))
        return temp
    if pid==2:return temp if s is None else s
    if pid==3:return temp if s is None else int(round((temp+s)/2.0))
    if pid==4:
        if s is not None and sl is not None and sr is not None:return temp + s-int(round((sl+sr)/2.0))
        return temp
    if pid==5:
        if l is not None and r is not None and ll is not None and rr is not None:
            return l if abs(l-ll)<=abs(rr-r) else r
        return temp
    if pid==6:
        z=[temp]
        if s is not None:z.append(s)
        if l is not None:z.append(l)
        return int(np.median(np.asarray(z,np.int64)))
    if pid==7:
        if l is not None and r is not None:
            dl=0 if ll is None else l-ll;dr=0 if rr is None else rr-r
            return int(round((l+r+0.5*(dl-dr))/2.0))
        return temp
    raise ValueError(pid)

NANCH=5;NMID=8

def code_positions(X,R,done,positions,h,pid,anchor=False,stride=None,commit=False):
    K=[];updates=[]
    for t in positions:
        for c in range(X.shape[0]):
            p=anchor_pred(R,done,c,t,stride,pid) if anchor else mid_pred(R,done,c,t,h,pid)
            k=int(np.rint((float(X[c,t])-float(p))/STEP));rec=p+STEP*k;K.append(k);updates.append((c,t,rec))
            if commit:R[c,t]=rec;done[c,t]=True
    return np.asarray(K,np.int32),updates

def fast_bytes(K):return int(m.encode_k(np.asarray(K,np.int32).reshape(1,-1))[0])

def build(X,stride):
    R=np.zeros(X.shape,np.int32);done=np.zeros(X.shape,bool);seq=[];cfg=[];history=[]
    anchors=list(range(0,X.shape[1],stride));best=None
    for pid in range(NANCH):
        K,_=code_positions(X,R.copy(),done.copy(),anchors,0,pid,anchor=True,stride=stride,commit=True);b=fast_bytes(K)
        if best is None or b<best[0]:best=(b,pid,K)
    _,pid,_=best;K,_=code_positions(X,R,done,anchors,0,pid,anchor=True,stride=stride,commit=True);seq.extend(K.tolist());cfg.append(pid);history.append({'kind':'anchor','h':stride,'pid':pid,'bytes':fast_bytes(K),'n':len(K)})
    h=stride//2
    while h>=1:
        gap=2*h;positions=[t for t in range(h,X.shape[1],gap)];best=None
        for q in range(NMID):
            Rc=R.copy();dc=done.copy();K,_=code_positions(X,Rc,dc,positions,h,q,commit=True);b=fast_bytes(K)
            if best is None or b<best[0]:best=(b,q)
        _,q=best;K,_=code_positions(X,R,done,positions,h,q,commit=True);seq.extend(K.tolist());cfg.append(q);history.append({'kind':'mid','h':h,'pid':q,'bytes':fast_bytes(K),'n':len(K)});h//=2
    if not np.all(done):raise RuntimeError(('undecoded',stride,int(np.sum(~done))))
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    return np.asarray(seq,np.int32),R,cfg,history,me

def replay(shape,stride,cfg,Kseq):
    R=np.zeros(shape,np.int32);done=np.zeros(shape,bool);p=0
    anchors=list(range(0,shape[1],stride));pid=cfg[0]
    for t in anchors:
        for c in range(shape[0]):
            pr=anchor_pred(R,done,c,t,stride,pid);R[c,t]=pr+STEP*int(Kseq[p]);done[c,t]=True;p+=1
    h=stride//2;ci=1
    while h>=1:
        q=cfg[ci];ci+=1;gap=2*h
        for t in range(h,shape[1],gap):
            for c in range(shape[0]):
                pr=mid_pred(R,done,c,t,h,q);R[c,t]=pr+STEP*int(Kseq[p]);done[c,t]=True;p+=1
        h//=2
    if p!=len(Kseq) or not np.all(done):raise RuntimeError(('replay length',p,len(Kseq),int(np.sum(~done))))
    return R

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);screens=[];cache={}
    for stride in STRIDES:
        K,R,cfg,hist,me=build(X,stride)
        if me>eps*(1+5e-6):raise RuntimeError(('hard screen',stride,me,eps))
        rb=replay(X.shape,stride,cfg,K)
        if not np.array_equal(rb,R):raise RuntimeError(('screen replay',stride))
        fb=fast_bytes(K)+HEADER+len(cfg);row={'stride':stride,'fast_bytes':fb,'gain_vs_sz3_fast':float(szb/fb),'config':cfg,'history':hist,'zero_fraction':float(np.mean(K==0)),'maxerr':me};screens.append(row);cache[stride]=(K,R,cfg);print('SCREEN',json.dumps(row),flush=True)
    order=sorted(STRIDES,key=lambda s:next(q['fast_bytes'] for q in screens if q['stride']==s));exact=[]
    for stride in order[:TOP_EXACT]:
        K,R,cfg=cache[stride];field,Kd,detail=v7.super_frame(K.reshape(1,-1));Kd=Kd.reshape(-1)
        Rd=replay(X.shape,stride,cfg,Kd)
        if not np.array_equal(Rd,R):raise RuntimeError(('exact replay',stride))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        total=int(field)+HEADER+len(cfg);row={'stride':stride,'bytes':total,'field_bytes':int(field),'gain_vs_sz3':float(szb/total),'config':cfg,'maxerr':me};exact.append(row);print('EXACT',json.dumps(row),flush=True)
    best=min(exact,key=lambda q:q['bytes'])
    out={'kind':'universal-multiscale-interpolation-v15','shape':list(X.shape),'eps':eps,'step':STEP,'sz3_bytes':int(szb),'sz3_orientation':ori,'best':best,'exact':exact,'screens':screens,
         'principle':'Change only the causal coding order. Encode a sparse temporal anchor lattice first, then recursively fill dyadic midpoint levels. At every midpoint both surrounding coarser samples are already reconstructed, so the predictor may use two-sided interpolation while remaining exactly decoder-replayable. At each scale a small public predictor menu (linear/cubic temporal interpolation, spatial continuation, blends, median and slope-aware rules) is selected by actual residual bytes and its tiny ID is charged. The complete correction sequence is then physically encoded by the current exact residual coder and the source max-error contract is replayed.'}
    json.dump(out,open('universal_multiscale_interpolation_v15.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k not in ('screens','exact')},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
