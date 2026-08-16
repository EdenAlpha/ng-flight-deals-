import json,sys,math
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(262,263,264,265,266)
BEAM=64
SELECTOR_BYTES=3
ALPHA=0.5
# bit0..bit7 winners from the current exact AR32 AUTO stream.
WINNER=('lu','global','global','global','lu','lud_hi1','lud_hi1','lud_hi1')

def zz(v):return 2*int(v) if v>=0 else -2*int(v)-1

def state_for(bit,fam,k,pk,lk,dk):
    if fam=='global':return 0
    z=zz(k);pu=(zz(pk)>>bit)&1;pl=(zz(lk)>>bit)&1;pd=(zz(dk)>>bit)&1
    if fam=='lu':return int(pl|(pu<<1))
    if fam=='lud_hi1':
        hi=(z>>(bit+1))&1
        return int(pl|(pu<<1)|(pd<<2)|(hi<<3))
    raise ValueError(fam)

def build_guide(K):
    u=m.zig(np.asarray(K,np.int32));nb=max(1,int(u.max()).bit_length())
    if nb!=len(WINNER):raise RuntimeError(('unexpected nbits',nb,len(WINNER)))
    tables=[];globals=[]
    for bit in range(nb):
        fam=WINNER[bit];ct={};g0=[0,0]
        for c in range(K.shape[0]):
            for t in range(K.shape[1]):
                k=int(K[c,t]);pk=int(K[c,t-1]) if t>0 else 0;lk=int(K[c-1,t]) if c>0 else 0;dk=int(K[c-1,t-1]) if c>0 and t>0 else 0
                b=(int(u[c,t])>>bit)&1;q=state_for(bit,fam,k,pk,lk,dk);a=ct.get(q)
                if a is None:a=[0,0];ct[q]=a
                a[b]+=1;g0[b]+=1
        tables.append(ct);globals.append(g0)
    return nb,tables,globals

def bit_cost(k,pk,lk,dk,nb,tables,globals):
    z=zz(k);cost=0.0
    for bit in range(nb):
        fam=WINNER[bit];q=state_for(bit,fam,k,pk,lk,dk);a=tables[bit].get(q,globals[bit]);b=(z>>bit)&1
        den=a[0]+a[1]+2*ALPHA;num=a[b]+ALPHA;cost-=math.log2(num/den)
    return cost

def legal(x,p,eps,step):
    b=float(eps)*(1-2e-12)
    return int(math.ceil((float(x)-b-p)/step)),int(math.floor((float(x)+b-p)/step))

def beam_channel(x,coef,eps,step,leftK,nb,tables,globals):
    P=32;hist=np.zeros((1,P),np.int32);lastk=np.zeros(1,np.int32);scores=np.zeros(1,np.float64);parents=[];kvals=[]
    for t in range(x.size):
        if t<P:pred=np.zeros(hist.shape[0],np.int64)
        else:pred=np.rint(float(coef[-1])+hist.astype(np.float64)@np.asarray(coef[:P],np.float64)).astype(np.int64)
        lk=int(leftK[t]) if leftK is not None else 0;dk=int(leftK[t-1]) if leftK is not None and t>0 else 0
        cs=[];cp=[];ck=[];cr=[]
        for i in range(hist.shape[0]):
            lo,hi=legal(x[t],int(pred[i]),eps,step)
            if lo>hi:raise RuntimeError(('empty legal',step,t,int(pred[i]),lo,hi))
            pk=int(lastk[i])
            for k in range(lo,hi+1):
                cs.append(float(scores[i])+bit_cost(k,pk,lk,dk,nb,tables,globals));cp.append(i);ck.append(k);cr.append(int(pred[i])+step*k)
        order=np.argsort(np.asarray(cs),kind='stable')[:BEAM];par=np.asarray(cp,np.int32)[order];kv=np.asarray(ck,np.int32)[order];rv=np.asarray(cr,np.int32)[order]
        nh=np.zeros((len(order),P),np.int32);nh[:,1:]=hist[par,:P-1];nh[:,0]=rv
        hist=nh;lastk=kv;scores=np.asarray(cs,np.float64)[order];parents.append(par);kvals.append(kv)
    idx=int(np.argmin(scores));K=np.empty(x.size,np.int32)
    for t in range(x.size-1,-1,-1):K[t]=kvals[t][idx];idx=int(parents[t][idx])
    return K,float(np.min(scores))

def build(X,eps,coef,step,nb,tables,globals):
    K=np.zeros(X.shape,np.int32);score=0.0
    for c in range(X.shape[0]):K[c],s=beam_channel(X[c],coef,eps,step,K[c-1] if c>0 else None,nb,tables,globals);score+=s
    R=np.zeros_like(K)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=g.ar.predict_hist(R,c,t,coef,32,'shared')+step*int(K[c,t])
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('guided hard',step,me,eps))
    return R,K,me,score

def exact(X,eps,mb,coef,step,R,K,me,score):
    ab,rep,Kd,detail=ac.autocomplexity_frame(K);Kd=np.asarray(Kd,np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError(('guided K replay',step))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,coef,32,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('guided AR replay',step))
    me2=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me2>eps*(1+5e-6):raise RuntimeError(('guided replay hard',step,me2,eps))
    total=int(mb)+int(ab)+base.HEADER+SELECTOR_BYTES
    return {'step':step,'beam':BEAM,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(ab),'selector_bytes':SELECTOR_BYTES,'maxerr':me2,'guide_nll_bits':float(score),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'rep':rep,'detail':detail}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=g.ar.fit_shared(X[:,:g.TRAIN],32);mb,coef=g.ar.model_frame(co);_,_,R0,K0=base.build_ar32(X);ab0,_,Kd0,_=ac.autocomplexity_frame(K0)
    if not np.array_equal(Kd0,K0):raise RuntimeError('incumbent replay')
    incumbent={'bytes':int(mb+ab0+base.HEADER),'address_bytes':int(ab0),'step':267};nb,tables,globals=build_guide(K0);rows=[]
    for step in STEPS:
        R,K,me,score=build(X,eps,coef,step,nb,tables,globals);z=exact(X,eps,mb,coef,step,R,K,me,score);z['gain_vs_incumbent']=incumbent['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'steps':list(STEPS),'beam':BEAM,'guide_alpha':ALPHA,'guide_winner_families':list(WINNER),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'incumbent':incumbent,'rows':rows,'best':best,'scope':'AUTO-guided non-greedy legal path search. The frozen current step267 K field is used only at the encoder to estimate bit probabilities for the exact AUTO context families that currently win each plane. Those probability tables are never claimed as decoder models and are never counted as compression; they are a search heuristic only. For steps 262-266, a width-64 beam keeps complete legal AR32 causal states and scores every legal K branch by this frozen approximate AUTO negative log-likelihood, including previous-time/current-left/diagonal bit contexts. After a complete path is selected, the guide is discarded: the full K field is physically encoded/decoded with the ordinary exact AUTO-COMPLEXITY stream, selector bytes are charged, identical R is regenerated and source hard error is verified. Only the final real byte count can establish a win.'}
    json.dump(out,open('imperial_ar32_auto_guided_legal_beam.json','w'),indent=2)
    print(json.dumps({'summary':{'best_step':best['step'],'best_bytes':best['bytes'],'incumbent_bytes':incumbent['bytes'],'sz3_bytes':int(szb),'gain_incumbent':incumbent['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
