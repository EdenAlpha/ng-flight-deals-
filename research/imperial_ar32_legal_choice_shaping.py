import json,sys,math
import h5py,numpy as np
import imperial_ar32_autocomplexity_address as base
import imperial_defect_autocomplexity_rank as ac
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

STEPS=(192,208,224,232,240,248,256,260,264,267)
RULES=('nearest','zero','prev','left','median','smooth','bitmatch')
TOPK=16
SELECTOR_BYTES=2


def clip_int(v,lo,hi):return lo if v<lo else (hi if v>hi else v)

def zz(v):return 2*int(v) if v>=0 else -2*int(v)-1

def popc(x):return int(int(x).bit_count())

def choose(rule,lo,hi,near,K,c,t):
    if lo==hi:return lo
    p=int(K[c,t-1]) if t>0 else near
    p2=int(K[c,t-2]) if t>1 else p
    l=int(K[c-1,t]) if c>0 else p
    d=int(K[c-1,t-1]) if c>0 and t>0 else p
    if rule=='nearest':return clip_int(near,lo,hi)
    if rule=='zero':return clip_int(0,lo,hi)
    if rule=='prev':return clip_int(p,lo,hi)
    if rule=='left':return clip_int(l,lo,hi)
    if rule=='median':return clip_int(int(np.median(np.asarray([p,l,d],np.int64))),lo,hi)
    best=None
    for k in range(lo,hi+1):
        if rule=='smooth':score=abs(k-p)+abs(k-l)+abs(k-d)+0.15*abs(k-near)
        elif rule=='bitmatch':
            z=zz(k);score=popc(z^zz(p))+popc(z^zz(l))+popc(z^zz(d))+0.05*abs(k-near)
        else:raise ValueError(rule)
        row=(score,abs(k-near),abs(k),k)
        if best is None or row<best[0]:best=(row,k)
    return best[1]


def build_shaped(X,eps,cd,step,rule):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);multi=0;chosen_nonnearest=0
    b=float(eps)*(1-2e-12)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=g.ar.predict_hist(R,c,t,cd,g.P,'shared');x=float(X[c,t]);lo=int(math.ceil((x-b-p)/step));hi=int(math.floor((x+b-p)/step))
            if lo>hi:raise RuntimeError(('empty legal',step,rule,c,t,x,p,lo,hi))
            near=int(np.rint((x-p)/step));near=clip_int(near,lo,hi)
            if hi>lo:multi+=1
            k=choose(rule,lo,hi,near,K,c,t)
            if k!=near:chosen_nonnearest+=1
            K[c,t]=k;R[c,t]=p+step*k
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('hard shaped',step,rule,me,eps))
    return R,K,me,multi,chosen_nonnearest


def h2(k,n):
    if k<=0 or k>=n:return 0.0
    p=k/n;return -p*math.log2(p)-(1-p)*math.log2(1-p)

def screen(K):
    u=m.zig(np.asarray(K,np.int32));mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());tot=0.0
    for bit in range(nb):
        B=((u>>bit)&1).astype(np.uint8);n=B.size;k=int(B.sum());best=n*h2(k,n)
        L=np.zeros_like(B);U=np.zeros_like(B);L[1:]=B[:-1];U[:,1:]=B[:,:-1];ids=(L|(U<<1)).ravel();y=B.ravel();cost=0.0
        for q in range(4):
            mask=(ids==q);nn=int(mask.sum())
            if nn:kk=int(y[mask].sum());cost+=nn*h2(kk,nn)
        best=min(best,cost);tot+=best
    return float(tot)


def exact(X,eps,mb,cd,step,rule,R,K,me,multi,changed,score):
    ab,rep,Kd,detail=ac.autocomplexity_frame(K);Kd=np.asarray(Kd,np.int32)
    if not np.array_equal(Kd,K):raise RuntimeError(('shaped K replay',step,rule))
    Rd=np.zeros_like(R)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):Rd[c,t]=g.ar.predict_hist(Rd,c,t,cd,g.P,'shared')+step*int(Kd[c,t])
    if not np.array_equal(Rd,R):raise RuntimeError(('shaped AR replay',step,rule))
    me2=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me2>eps*(1+5e-6):raise RuntimeError(('shaped hard replay',step,rule,me2,eps))
    total=int(mb)+int(ab)+base.HEADER+SELECTOR_BYTES
    return {'step':int(step),'rule':rule,'bytes':int(total),'bps':8*total/X.size,'model_bytes':int(mb),'address_bytes':int(ab),'selector_bytes':SELECTOR_BYTES,'maxerr':me2,'multi_legal_fraction':multi/X.size,'nonnearest_fraction':changed/X.size,'screen_bits':float(score),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'rep':rep,'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);co=g.ar.fit_shared(X[:,:g.TRAIN],g.P);mb,cd=g.ar.model_frame(co)
    # Exact current fixed267 AUTO reference, no selector.
    _,_,R0,K0=base.build_ar32(X);ab0,rep0,Kd0,d0=ac.autocomplexity_frame(K0)
    if not np.array_equal(Kd0,K0):raise RuntimeError('reference K replay')
    incumbent={'bytes':int(mb+ab0+base.HEADER),'address_bytes':int(ab0),'step':267,'rule':'nearest','maxerr':float(np.max(np.abs(X-R0.astype(np.float64))))}
    screened=[];cache={}
    for step in STEPS:
        for rule in RULES:
            R,K,me,multi,changed=build_shaped(X,eps,cd,step,rule);sc=screen(K);cache[(step,rule)]=(R,K,me,multi,changed,sc);screened.append((sc,step,rule))
    screened.sort();keys=[(267,'nearest')]+[(s,r) for _,s,r in screened[:TOPK]];rows=[];seen=set()
    for step,rule in keys:
        if (step,rule) in seen:continue
        seen.add((step,rule));R,K,me,multi,changed,sc=cache[(step,rule)];z=exact(X,eps,mb,cd,step,rule,R,K,me,multi,changed,sc);z['gain_vs_incumbent']=incumbent['bytes']/z['bytes'];z['gain_vs_sz3']=szb/z['bytes'];rows.append(z);print(json.dumps({k:v for k,v in z.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'samples':int(X.size),'global_std':std,'eps':eps,'steps':list(STEPS),'rules':list(RULES),'topk_exact':TOPK,'selector_bytes':SELECTOR_BYTES,'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'incumbent':incumbent,'screen_top':[{'screen_bits':float(sc),'step':int(s),'rule':r} for sc,s,r in screened[:32]],'rows':rows,'best':best,'scope':'Exact legal-reconstruction shaping gate on the frozen shared AR32 carrier. Instead of assuming nearest quantization is the correct reconstruction, every sample computes the full integer K interval whose decoded R=pred+step*K stays inside the unchanged +/-epsilon source box. For several public steps and public causal selection rules, the encoder chooses one legal K trajectory designed to create a simpler address (nearest, minimum magnitude, previous innovation, left innovation, causal median, numeric smoothness, or bit-pattern agreement). The selected K is still fully transmitted with the exact AUTO-COMPLEXITY rank stream; no legal choice is assumed known to the decoder. A 2-byte step/rule selector is charged. Exact top candidates are chosen only after a cheap screen; every reported candidate byte-decodes identical K, recursively regenerates identical R, and passes source max error. This tests the central constrained-universe idea at the correct layer: use distortion freedom to choose the easiest-to-address legal reconstruction, rather than treating nearest rounding as mandatory.'}
    json.dump(out,open('imperial_ar32_legal_choice_shaping.json','w'),indent=2)
    print(json.dumps({'summary':{'best_step':best['step'],'best_rule':best['rule'],'best_bytes':best['bytes'],'incumbent_bytes':incumbent['bytes'],'sz3_bytes':int(szb),'gain_incumbent':incumbent['bytes']/best['bytes'],'gain_sz3':int(szb)/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
