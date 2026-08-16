import json,sys,math
from collections import defaultdict
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(224,240,248,256,260,264,267)
BS=(4,8,12,16)
CONTEXTS=('global','prev4','prev8','prev4_left4')
TOPK=14
REFRESH=32
SELECTOR_BYTES=3
HEADER=40


def clip(v,r):return max(-r,min(r,int(v)))+r

def context_id(K,c,t,name):
    p=int(K[c,t-1]) if t>0 else 0;l=int(K[c-1,t]) if c>0 else 0
    if name=='global':return 0
    if name=='prev4':return clip(p,4)
    if name=='prev8':return clip(p,8)
    if name=='prev4_left4':return clip(p,4)*9+clip(l,4)
    raise ValueError(name)

def local_suggestions(K,c,t):
    p=int(K[c,t-1]) if t>0 else 0;p2=int(K[c,t-2]) if t>1 else p
    l=int(K[c-1,t]) if c>0 else p;d=int(K[c-1,t-1]) if c>0 and t>0 else p
    med=sorted((p,l,d))[1]
    return (0,p,l,d,med,2*p-p2,p-1,p+1,l-1,l+1,1,-1,2,-2,3,-3)

def observed_top(counts,B):
    if not counts:return []
    return [v for v,n in sorted(counts.items(),key=lambda z:(-z[1],abs(z[0]),z[0]))[:max(1,B//2)]]

def candidates(K,c,t,name,B,counts,cache,idx):
    q=context_id(K,c,t,name);epoch=idx//REFRESH;key=(q,epoch)
    if key not in cache:cache[key]=observed_top(counts[q],B)
    out=[];seen=set()
    for v in cache[key]+list(local_suggestions(K,c,t)):
        v=int(v)
        if v not in seen:seen.add(v);out.append(v)
        if len(out)>=B:break
    return q,out

def legal_interval(x,p,eps,step):
    b=float(eps)*(1-2e-12);return int(math.ceil((float(x)-b-p)/step)),int(math.floor((float(x)+b-p)/step))

def build(X,eps,cd,step,name,B):
    C,T=X.shape;R=np.zeros((C,T),np.int32);K=np.zeros((C,T),np.int32);tok=np.zeros((C,T),np.int32);esc=[];counts=defaultdict(dict);cache={};hits=0;multi=0
    idx=0
    for c in range(C):
        for t in range(T):
            p=g.ar.predict_hist(R,c,t,cd,g.P,'shared');lo,hi=legal_interval(X[c,t],p,eps,step)
            if lo>hi:raise RuntimeError(('empty legal',step,name,B,c,t,lo,hi))
            if hi>lo:multi+=1
            q,cand=candidates(K,c,t,name,B,counts,cache,idx);chosen=None;token=None
            for j,v in enumerate(cand):
                if lo<=v<=hi:chosen=v;token=j;break
            if chosen is None:
                near=int(np.rint((float(X[c,t])-p)/step));chosen=max(lo,min(hi,near));token=B;esc.append(chosen)
            else:hits+=1
            K[c,t]=chosen;tok[c,t]=token;R[c,t]=p+step*chosen
            d=counts[q];d[chosen]=d.get(chosen,0)+1;idx+=1
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('candidate GPS hard',step,name,B,me,eps))
    return R,K,tok,np.asarray(esc,np.int32),me,hits,multi

def entropy(a):
    a=np.asarray(a).ravel()
    if not a.size:return 0.0
    _,n=np.unique(a,return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def screen(tok,esc):return tok.size*entropy(tok)+esc.size*entropy(esc)+16*esc.size

def frame_array(A):
    A=np.asarray(A,np.int32)
    if A.size==0:return 0,'none',A.copy()
    if A.ndim==1:A=A[None,:]
    fr=m.encode_k(A);return int(fr[0]),fr[1],np.asarray(fr[2],np.int32)

def decode_candidate(tok,esc,shape,name,B):
    C,T=shape;K=np.zeros((C,T),np.int32);counts=defaultdict(dict);cache={};ei=0;idx=0
    for c in range(C):
        for t in range(T):
            q,cand=candidates(K,c,t,name,B,counts,cache,idx);z=int(tok[c,t])
            if z<B:
                if z>=len(cand):raise RuntimeError(('candidate index',name,B,z,len(cand),c,t))
                k=int(cand[z])
            elif z==B:
                if ei>=len(esc):raise RuntimeError('escape eof')
                k=int(esc[ei]);ei+=1
            else:raise RuntimeError(('token range',z,B))
            K[c,t]=k;d=counts[q];d[k]=d.get(k,0)+1;idx+=1
    if ei!=len(esc):raise RuntimeError(('escape trailing',ei,len(esc)))
    return K

def exact(X,eps,mb,cd,step,name,B,R,K,tok,esc,me,hits,multi,sc):
    tb,tr,tokd=frame_array(tok);eb,er,escd2=frame_array(esc);escd=escd2.ravel();Kd=decode_candidate(tokd,escd,K.shape,name,B)
    if not np.array_equal(Kd,K):raise RuntimeError(('candidate GPS K replay',step,name,B))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('candidate GPS AR replay',step,name,B))
    me2=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me2>eps*(1+5e-6):raise RuntimeError(('candidate GPS hard replay',me2,eps))
    total=int(mb)+tb+eb+HEADER+SELECTOR_BYTES
    return {'step':int(step),'context':name,'B':int(B),'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'token_bytes':tb,'escape_bytes':eb,'header_bytes':HEADER,'selector_bytes':SELECTOR_BYTES,'token_rep':tr,'escape_rep':er,'maxerr':me2,'candidate_hit_fraction':hits/X.size,'escape_fraction':len(esc)/X.size,'multi_legal_fraction':multi/X.size,'screen_bits':float(sc),'token_entropy':entropy(tok),'escape_entropy':entropy(esc),'k_zero_fraction':float(np.mean(K==0))}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=g.ar.fit_shared(X[:,:g.TRAIN],g.P);mb,cd=g.ar.model_frame(co)
    _,_,R0,K0=base.build_ar32(X);ab0,arep,Kd0,ad=ac.autocomplexity_frame(K0)
    if not np.array_equal(Kd0,K0):raise RuntimeError('incumbent replay')
    incumbent={'bytes':int(mb+ab0+base.HEADER),'address_bytes':int(ab0),'bps':8*(mb+ab0+base.HEADER)/X.size}
    pool=[];cache={}
    for step in STEPS:
        for name in CONTEXTS:
            for B in BS:
                z=build(X,eps,cd,step,name,B);sc=screen(z[2],z[3]);cache[(step,name,B)]=(*z,sc);pool.append((sc,step,name,B))
    pool.sort();rows=[]
    for sc,step,name,B in pool[:TOPK]:
        R,K,tok,esc,me,hits,multi,_=cache[(step,name,B)];z=exact(X,eps,mb,cd,step,name,B,R,K,tok,esc,me,hits,multi,sc);z['gain_vs_incumbent']=incumbent['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps(z,indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'steps':list(STEPS),'contexts':list(CONTEXTS),'branching':list(BS),'refresh':REFRESH,'topk_exact':TOPK,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'incumbent':incumbent,'screen_top':[{'screen_bits':float(sc),'step':int(s),'context':n,'B':int(B)} for sc,s,n,B in pool[:32]],'rows':rows,'best':best,'scope':'Decoder-real candidate-space GPS / finite-state candidate trellis on the frozen shared AR32 model. At each causal sample a small candidate list is generated entirely from decoder-known state: an online frequency table for a public context plus fixed local continuations such as 0, previous K, current-left K, diagonal K, causal median and nearby values. The online table is learned from already decoded K and requires no transmitted histogram. The encoder computes the complete hard-error-legal K interval and, if any shared candidate lies inside it, emits only that candidate index; otherwise it emits an escape token and the exact K correction. Candidate rankings refresh deterministically every 32 causal symbols. Public step/context/branching selectors are charged. Token and escape arrays are actually serialized/byte-decoded through the existing exact representation menu, then the decoder rebuilds the same evolving candidate universe, identical K and identical AR32 reconstruction and verifies source hard error. This is a computationally searchable approximation to the uploaded NOVA Adaptive GPS idea in its correct domain: candidate reconstructions, not spatial positions.'}
    json.dump(out,open('imperial_ar32_candidate_gps_trellis.json','w'),indent=2)
    print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_step':best['step'],'best_context':best['context'],'best_B':best['B'],'hit_fraction':best['candidate_hit_fraction'],'incumbent_bytes':incumbent['bytes'],'sz3_bytes':int(szb),'gain_incumbent':incumbent['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
