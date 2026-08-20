#!/usr/bin/env python3
from __future__ import annotations
import json,sys
import h5py,numpy as np
import universal_rate_searched_predictor_v1 as u
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

PROGRAM_BYTES=2
TOP_EXACT=6

def at(K,c,t,dc=0,dt=0):
    cc=c+dc;tt=t-dt
    if cc<0 or cc>=K.shape[0] or tt<0:return 0
    if dt==0 and dc>=0:return 0
    return int(K[cc,tt])

def med3(a,b,c):return int(np.median(np.array([a,b,c],np.int32)))
def mode3(a,b,c):
    if a==b or a==c:return a
    if b==c:return b
    return 0

def qpred(K,c,t,pid):
    a=at(K,c,t,0,1);b=at(K,c,t,-1,0);d=at(K,c,t,-1,1);r=at(K,c,t,1,1)
    t2=at(K,c,t,0,2);t3=at(K,c,t,0,3);t4=at(K,c,t,0,4);t6=at(K,c,t,0,6);t7=at(K,c,t,0,7);t8=at(K,c,t,0,8);t16=at(K,c,t,0,16);t17=at(K,c,t,0,17)
    c2=at(K,c,t,-2,0)
    if pid==0:return 0
    if pid==1:return a
    if pid==2:return b
    if pid==3:return t2
    if pid==4:return t6
    if pid==5:return t16
    if pid==6:return d
    if pid==7:return r
    if pid==8:return a+b-d
    if pid==9:return med3(a,b,d)
    if pid==10:return med3(a,d,r)
    if pid==11:return int(round((a+b)/2.0))
    if pid==12:return a if a==b else 0
    if pid==13:return a if abs(a-b)<=1 else 0
    if pid==14:return mode3(a,b,d)
    if pid==15:return 2*a-t2
    if pid==16:return 2*b-c2
    if pid==17:return a+(t6-t7)
    if pid==18:return a+(t16-t17)
    if pid==19:return t6+(a-t7)
    if pid==20:return t16+(a-t17)
    if pid==21:return a+b-med3(a,b,d)
    if pid==22:return a if abs(a-t2)<=abs(b-d) else b
    if pid==23:return b if abs(b-d)<=abs(a-t2) else a
    if pid==24:return a if abs(a)<=abs(b) else b
    if pid==25:return med3(a,b,r)
    if pid==26:return int(round((a+d+r)/3.0))
    if pid==27:return t2+(a-t3)
    if pid==28:return t3+(a-t4)
    if pid==29:return t8+(a-at(K,c,t,0,9))
    if pid==30:return a if abs(a-d)<=1 else med3(a,b,d)
    if pid==31:return a if abs(a-r)<=1 else med3(a,d,r)
    raise ValueError(pid)

NPROG=32

def make_j(K,pid):
    J=np.zeros_like(K,np.int32);Kh=np.zeros_like(K,np.int32)
    for t in range(K.shape[1]):
        for c in range(K.shape[0]):
            p=qpred(Kh,c,t,pid);j=int(K[c,t])-p;J[c,t]=j;Kh[c,t]=p+j
    if not np.array_equal(Kh,K):raise RuntimeError(('encoder K replay',pid))
    return J

def restore(J,pid):
    K=np.zeros_like(J,np.int32)
    for t in range(J.shape[1]):
        for c in range(J.shape[0]):K[c,t]=qpred(K,c,t,pid)+int(J[c,t])
    return K

def h0(a):
    _,n=np.unique(a,return_counts=True);p=n.astype(np.float64)/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);offs,co,sbest,shist=u.search_sample(X);base_total,R,K,mb,ob,cod=sbest
    screens=[];cache={}
    for pid in range(NPROG):
        J=make_j(K,pid);fast=int(m.encode_k(J)[0])+PROGRAM_BYTES;row={'pid':pid,'fast_bytes':fast,'gain_vs_sz3_fast':float(szb/(fast+fair.COMMON_HEADER+1+len(ob)+len(mb))),'zero_fraction':float(np.mean(J==0)),'h0':h0(J),'mean_abs':float(np.mean(np.abs(J.astype(np.float64))))};screens.append(row);cache[pid]=J;print('SCREEN',json.dumps(row),flush=True)
    order=sorted(range(NPROG),key=lambda pid:screens[pid]['fast_bytes']);pick=[]
    for pid in [0]+order:
        if pid not in pick:pick.append(pid)
        if len(pick)>=TOP_EXACT:break
    overhead=fair.COMMON_HEADER+1+len(ob)+len(mb)+PROGRAM_BYTES;exact=[]
    for pid in pick:
        J=cache[pid];fb,Jd,detail=v7.super_frame(J);Kd=restore(Jd,pid)
        if not np.array_equal(Kd,K):raise RuntimeError(('K replay',pid))
        Rd=np.zeros_like(K)
        for t in range(K.shape[1]):
            for c in range(K.shape[0]):Rd[c,t]=u.sample_pred(Rd,c,t,cod,offs)+u.STEP*int(Kd[c,t])
        if not np.array_equal(Rd,R):raise RuntimeError(('source replay',pid))
        me=float(np.max(np.abs(X-Rd.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',pid,me,eps))
        total=overhead+int(fb);row={**screens[pid],'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':float(szb/total),'gain_vs_base':float(base_total/total),'maxerr':me};exact.append(row);print('EXACT',json.dumps(row),flush=True)
    best=min(exact,key=lambda q:q['bytes'])
    out={'kind':'universal-quant-index-program-search-v14','shape':list(X.shape),'eps':eps,'step':u.STEP,'sz3_bytes':int(szb),'sz3_orientation':ori,'base_bytes':int(base_total),'base_offsets':[list(x) for x in offs],'best':best,'exact':exact,'screens':screens,
         'principle':'After the ordinary SZ-style sample predictor and error-bounded quantizer produce exact integer correction indices K, search a public family of reversible causal programs that predicts K itself from already decoded K neighbors and delays. Encode only J=K-predict(K_history). The decoder regenerates K recursively from J and the tiny program ID, then runs the unchanged source predictor. Programs include temporal/spatial continuation, long-delay increments, Lorenzo-like relations, medians, agreement/mode rules, and decoder-known gates. Actual current residual-coder bytes decide the winner; pid=0 preserves the no-index-prediction floor.'}
    json.dump(out,open('universal_quant_index_program_search_v14.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k not in ('screens','exact')},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
