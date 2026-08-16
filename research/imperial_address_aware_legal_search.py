import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NBITS=16
PASSES=4


def logcomb_table(n):
    a=np.zeros(n+1,np.float64)
    for k in range(1,n+1):a[k]=a[k-1]+math.log2((n-k+1)/k)
    return a

@njit(cache=True)
def zigscalar(v):
    return 2*v if v>=0 else -2*v-1

@njit(cache=True)
def init_counts(D,nbits):
    out=np.zeros(nbits,np.int64)
    for c0 in range(D.shape[0]):
        for t0 in range(D.shape[1]):
            u=zigscalar(int(D[c0,t0]))
            for b in range(nbits):out[b]+=(u>>b)&1
    return out

@njit(cache=True)
def total_cost(counts,logc):
    s=0.0
    for b in range(counts.size):s+=logc[int(counts[b])]
    return s

@njit(cache=True)
def shape_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,logc,nbits,passes):
    counts=init_counts(D,nbits);changes=0
    maxa=dts.size+1
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32)
    newd=np.empty(maxa,np.int32);oldv=np.empty(maxa,np.int32)
    trial=np.empty(nbits,np.int64)
    for ps in range(passes):
        changed=0
        rev=ps&1
        for t in range(Q.shape[1]):
            for kk in range(Q.shape[0]):
                cc=kk if rev==0 else Q.shape[0]-1-kk
                oldq=int(Q[cc,t]);bestq=oldq;best=total_cost(counts,logc)
                for q in range(int(lo[cc,t]),int(hi[cc,t])+1):
                    if q==oldq:continue
                    na=1;ac[0]=cc;at[0]=t
                    for j in range(dts.size):
                        tc=t+int(dts[j]);cx=cc-int(dcs[j])
                        if tc<0 or tc>=Q.shape[1] or cx<0 or cx>=Q.shape[0]:continue
                        dup=False
                        for z in range(na):
                            if ac[z]==cx and at[z]==tc:dup=True;break
                        if not dup:ac[na]=cx;at[na]=tc;na+=1
                    for z in range(na):oldv[z]=D[ac[z],at[z]]
                    Q[cc,t]=q
                    for z in range(na):newd[z]=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale)
                    for b in range(nbits):trial[b]=counts[b]
                    overflow=False
                    for z in range(na):
                        u0=zigscalar(int(oldv[z]));u1=zigscalar(int(newd[z]))
                        if (u1>>nbits)!=0:overflow=True;break
                        for b in range(nbits):trial[b]+=((u1>>b)&1)-((u0>>b)&1)
                    if overflow:score=1e300
                    else:score=total_cost(trial,logc)
                    if score<best-1e-10:best=score;bestq=q
                    Q[cc,t]=oldq
                if bestq!=oldq:
                    na=1;ac[0]=cc;at[0]=t
                    for j in range(dts.size):
                        tc=t+int(dts[j]);cx=cc-int(dcs[j])
                        if tc<0 or tc>=Q.shape[1] or cx<0 or cx>=Q.shape[0]:continue
                        dup=False
                        for z in range(na):
                            if ac[z]==cx and at[z]==tc:dup=True;break
                        if not dup:ac[na]=cx;at[na]=tc;na+=1
                    for z in range(na):oldv[z]=D[ac[z],at[z]]
                    Q[cc,t]=bestq
                    for z in range(na):
                        nd=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nd
                        u0=zigscalar(int(oldv[z]));u1=zigscalar(int(nd))
                        for b in range(nbits):counts[b]+=((u1>>b)&1)-((u0>>b)&1)
                    changed+=1;changes+=1
        if changed==0:break
    return Q,D,counts,changes


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps)
    rb0,_,RE0,detail0=rr.restricted_rank_frame(D)
    base=c.validate(X,eps,h,Q,RE0,dts,dcs,co,intercept,rb0,'restricted_rank_before',detail0)
    lo,hi=g.legal_q(X,eps,h);logc=logcomb_table(X.size)
    Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy())
    before_counts=init_counts(D2,NBITS);before_objective=total_cost(before_counts,logc)
    Q2,D2,after_counts,changes=shape_search(Q2,lo,hi,D2,dts,dcs,co,intercept,g.SCALE,logc,NBITS,PASSES)
    # Recompute from scratch under the fixed charged model to verify incremental updates.
    Dr=g._all_defects(Q2,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D2):raise RuntimeError('incremental defect mismatch')
    rb,_,RE,detail=rr.restricted_rank_frame(D2)
    shaped=c.validate(X,eps,h,Q2,RE,dts,dcs,co,intercept,rb,'address_shaped_restricted_rank',detail)
    for r in (base,shaped):
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes']
        print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'nbits':NBITS,'passes':PASSES,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'before':base,'after':shaped,'address_search':{'changes':int(changes),'base_projection_changes':int(base_changes),'before_global_rank_bits':float(before_objective),'after_global_rank_bits':float(total_cost(after_counts,logc)),'before_counts':[int(x) for x in before_counts],'after_counts':[int(x) for x in after_counts]},'scope':'Decoder-real NOVA/computation-for-communication gate. Start from the exact PR498 learned-law legal reconstruction and freeze its fully charged sparse generator. Unlike prior gates, the encoder then searches the remaining per-sample legal hard-error choices using the final address family itself as the objective: coordinate updates are accepted only when they reduce the exact global combinatorial bitplane objective sum_b log2 C(N,k_b) of the signed zigzag defect field, accounting for every causal defect changed by that legal reconstruction choice. No search trajectory is transmitted because the decoder needs only the final charged model plus exact defect address. After search, the defect is physically encoded/decoded by PR512 restricted ranking, the exact Q field is regenerated, and the unchanged source-domain hard error is verified. Reported bytes are the actual PR512 stream, not the surrogate objective.'}
    json.dump(out,open('imperial_address_aware_legal_search.json','w'),indent=2)
    print(json.dumps({'summary':{'before':base['bytes'],'after':shaped['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'changes':int(changes),'gain_vs_before':base['bytes']/shaped['bytes'],'gain_vs_ar32':arb['bytes']/shaped['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
