import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_causal_restricted_address as ca
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NBITS=12
PASSES=3
# Fixed to the exact per-plane context families selected by PR537 on the current hard state:
# bit0 mag4+nbr3; bits1-3 nbr3; bit4 mag8+left/up; bit5 mag4+nbr3;
# bit6 coarse-channel+nbr3; bit7 nbr3; bit8 mag8+left/up. Higher guard planes use nbr3.
MODES=np.asarray([1,0,0,0,2,1,3,0,2,0,0,0],np.int8)
MAXCTX=32
INF=1e300

@njit(cache=True)
def _zig(v):
    return 2*v if v>=0 else -2*v-1

@njit(cache=True)
def _ctx(D,c0,t0,bit,mode):
    C,T=D.shape
    z=_zig(int(D[c0,t0]));pref=z>>(bit+1)
    l=0;u=0;d=0
    if c0>0:l=(_zig(int(D[c0-1,t0]))>>bit)&1
    if t0>0:u=(_zig(int(D[c0,t0-1]))>>bit)&1
    if c0>0 and t0>0:d=(_zig(int(D[c0-1,t0-1]))>>bit)&1
    n3=(l<<2)|(u<<1)|d
    if mode==0:return n3
    if mode==1:
        mp=pref if pref<4 else 3
        return mp*8+n3
    if mode==2:
        mp=pref if pref<8 else 7
        return mp*4+(l<<1)+u
    if mode==3:
        return (c0*4//C)*8+n3
    return n3

@njit(cache=True)
def _nctx(mode):
    return 8 if mode==0 else 32

@njit(cache=True)
def init_counts(D,modes,nbits):
    cnt=np.zeros((nbits,MAXCTX,2),np.int64)
    for bit in range(nbits):
        mode=int(modes[bit])
        for t in range(D.shape[1]):
            for c0 in range(D.shape[0]):
                z=_zig(int(D[c0,t]));b=(z>>bit)&1;k=_ctx(D,c0,t,bit,mode);cnt[bit,k,b]+=1
    return cnt

@njit(cache=True)
def score_counts(cnt,modes,logfact,weights):
    s=0.0
    for bit in range(cnt.shape[0]):
        nc=_nctx(int(modes[bit]));q=0.0
        for k in range(nc):
            n0=int(cnt[bit,k,0]);n1=int(cnt[bit,k,1]);n=n0+n1
            if n>0:q+=logfact[n+1]-logfact[n0]-logfact[n1]
        s+=weights[bit]*q
    return s

@njit(cache=True)
def _add_unique(ac,at,na,c0,t0,C,T):
    if c0<0 or t0<0 or c0>=C or t0>=T:return na
    for z in range(na):
        if ac[z]==c0 and at[z]==t0:return na
    ac[na]=c0;at[na]=t0
    return na+1

@njit(cache=True)
def _affected(ac,at,c0,t0,Q,dts,dcs):
    na=0;C,T=Q.shape
    na=_add_unique(ac,at,na,c0,t0,C,T)
    for j in range(dts.size):
        tc=t0+int(dts[j]);cc=c0-int(dcs[j])
        na=_add_unique(ac,at,na,cc,tc,C,T)
    return na

@njit(cache=True)
def _impacted(ic,it,ac,at,na,Q):
    ni=0;C,T=Q.shape
    for z in range(na):
        c0=int(ac[z]);t0=int(at[z])
        ni=_add_unique(ic,it,ni,c0,t0,C,T)
        ni=_add_unique(ic,it,ni,c0+1,t0,C,T)
        ni=_add_unique(ic,it,ni,c0,t0+1,C,T)
        ni=_add_unique(ic,it,ni,c0+1,t0+1,C,T)
    return ni

@njit(cache=True)
def _remove_contexts(cnt,D,ic,it,ni,modes,nbits):
    for z in range(ni):
        c0=int(ic[z]);t0=int(it[z]);v=_zig(int(D[c0,t0]))
        for bit in range(nbits):
            b=(v>>bit)&1;k=_ctx(D,c0,t0,bit,int(modes[bit]));cnt[bit,k,b]-=1

@njit(cache=True)
def _add_contexts(cnt,D,ic,it,ni,modes,nbits):
    for z in range(ni):
        c0=int(ic[z]);t0=int(it[z]);v=_zig(int(D[c0,t0]))
        for bit in range(nbits):
            b=(v>>bit)&1;k=_ctx(D,c0,t0,bit,int(modes[bit]));cnt[bit,k,b]+=1

@njit(cache=True)
def causal_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,modes,logfact,weights,passes):
    cnt=init_counts(D,modes,NBITS);changes=0
    maxa=dts.size+2;maxi=4*maxa+8
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32);oldD=np.empty(maxa,np.int32)
    ic=np.empty(maxi,np.int32);it=np.empty(maxi,np.int32)
    for ps in range(passes):
        changed=0;rev=ps&1
        for t0 in range(Q.shape[1]):
            for kk in range(Q.shape[0]):
                c0=kk if rev==0 else Q.shape[0]-1-kk
                oldq=int(Q[c0,t0]);bestq=oldq;best=score_counts(cnt,modes,logfact,weights)
                na=_affected(ac,at,c0,t0,Q,dts,dcs);ni=_impacted(ic,it,ac,at,na,Q)
                for z in range(na):oldD[z]=D[ac[z],at[z]]
                for q in range(int(lo[c0,t0]),int(hi[c0,t0])+1):
                    if q==oldq:continue
                    _remove_contexts(cnt,D,ic,it,ni,modes,NBITS)
                    Q[c0,t0]=q;overflow=False
                    for z in range(na):
                        nv=g._defect(Q,int(ac[z]),int(at[z]),dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nv
                        if (_zig(int(nv))>>NBITS)!=0:overflow=True
                    _add_contexts(cnt,D,ic,it,ni,modes,NBITS)
                    sc=INF if overflow else score_counts(cnt,modes,logfact,weights)
                    if sc<best-1e-9:best=sc;bestq=q
                    _remove_contexts(cnt,D,ic,it,ni,modes,NBITS)
                    Q[c0,t0]=oldq
                    for z in range(na):D[ac[z],at[z]]=oldD[z]
                    _add_contexts(cnt,D,ic,it,ni,modes,NBITS)
                if bestq!=oldq:
                    _remove_contexts(cnt,D,ic,it,ni,modes,NBITS)
                    Q[c0,t0]=bestq
                    for z in range(na):D[ac[z],at[z]]=g._defect(Q,int(ac[z]),int(at[z]),dts,dcs,co,intercept,scale)
                    _add_contexts(cnt,D,ic,it,ni,modes,NBITS)
                    changes+=1;changed+=1
        if changed==0:break
    return Q,D,cnt,changes,score_counts(cnt,modes,logfact,weights)


def materialize(name,X,eps,h,Q,D,dts,dcs,co,intercept):
    b,_,Dd,detail=ca.causal_frame(D);r=c.validate(X,eps,h,Q,Dd,dts,dcs,co,intercept,b,name,detail);return r


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q0,D0,dts,dcs,co,intercept,prior=ca.build_pair_state(X,eps)
    base=materialize('baseline_pr537',X,eps,h,Q0,D0,dts,dcs,co,intercept)
    lo,hi=g.legal_q(X,eps,h);lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    profiles=[('causal_exact',np.ones(NBITS,np.float64)),('causal_lowfocus',np.asarray([1.6,1.35,1.1,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0],np.float64))]
    rows=[base];meta=[]
    for name,w in profiles:
        Q=np.ascontiguousarray(Q0.copy());D=np.ascontiguousarray(D0.copy())
        Q,D,cnt,ch,sc=causal_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,MODES,lf,w,PASSES)
        Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError((name,'incremental defect mismatch'))
        r=materialize(name,X,eps,h,Q,D,dts,dcs,co,intercept);rows.append(r);meta.append({'profile':name,'changes':int(ch),'surrogate_bits':float(sc)})
    for r in rows:r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    best=min(rows,key=lambda r:r['bytes']);out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'prior_search':prior,'profiles':meta,'rows':rows,'best':best,'scope':'Decoder-real causal-address-aware legal reconstruction search. It starts from the verified PR530 pair-optimized hard-error-legal Q field and PR537 charged generator, but changes the encoder objective from global bit counts to the actual causal context families selected by PR537. For every legal Q move, the exact directly affected learned-law defects are updated; causal context counts are correspondingly removed/reinserted for affected symbols and their forward left/up/diagonal dependents. The search score is the exact Laplace predictive probability product for those fixed decoder-shared context families, not a transmitted model. Two encoder-only objective profiles are tried. Final candidates are physically encoded with the complete PR537 causal arithmetic menu, independently decoded, used to regenerate exact Q, and hard-error validated. Only real final bytes determine the winner.'};json.dump(out,open('imperial_causal_address_aware_legal_search.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['rep'],'bytes':best['bytes'],'baseline':base['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gap_to_ar32':best['bytes']-arb['bytes'],'gain_ar32':best['gain_vs_ar32']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
