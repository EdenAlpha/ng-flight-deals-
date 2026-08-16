import json,sys
import h5py,numpy as np
from numba import njit
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NBITS=16
TARGET_PASSES=3

@njit(cache=True)
def total_cost_w(counts,logc,w):
    s=0.0
    for b in range(counts.size):s+=w[b]*logc[int(counts[b])]
    return s

@njit(cache=True)
def shape_search_w(Q,lo,hi,D,dts,dcs,co,intercept,scale,logc,w,nbits,passes):
    counts=a.init_counts(D,nbits);changes=0
    maxa=dts.size+1
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32);newd=np.empty(maxa,np.int32);oldv=np.empty(maxa,np.int32);trial=np.empty(nbits,np.int64)
    for ps in range(passes):
        changed=0;rev=ps&1
        for tt0 in range(Q.shape[1]):
            t=tt0 if rev==0 else Q.shape[1]-1-tt0
            for kk in range(Q.shape[0]):
                cc=kk if rev==0 else Q.shape[0]-1-kk
                oldq=int(Q[cc,t]);bestq=oldq;best=total_cost_w(counts,logc,w)
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
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(newd[z]))
                        if (u1>>nbits)!=0:overflow=True;break
                        for b in range(nbits):trial[b]+=((u1>>b)&1)-((u0>>b)&1)
                    score=1e300 if overflow else total_cost_w(trial,logc,w)
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
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nd))
                        for b in range(nbits):counts[b]+=((u1>>b)&1)-((u0>>b)&1)
                    changes+=1;changed+=1
        if changed==0:break
    return Q,D,counts,changes


def encode_candidate(name,X,eps,h,Q,D,dts,dcs,co,intercept,szb,arb,changes):
    Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError(('defect mismatch',name))
    rb,_,RE,detail=rr.restricted_rank_frame(D)
    r=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,name,detail)
    r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];r['search_changes']=int(changes)
    return r


def weights_for(kind):
    w=np.ones(NBITS,np.float64)
    if kind.startswith('b'):
        b=int(kind[1:]);w[b]=6.0
    elif kind=='low_even':
        for b in (0,2,4):w[b]=3.0
    elif kind=='low_all':w[:5]=2.5
    elif kind=='protect_b1':
        w[:5]=2.0;w[1]=5.0
    return w


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    # First reproduce the successful all-plane address-aware search from PR518.
    Q0=np.ascontiguousarray(Q.copy());D0=np.ascontiguousarray(D.copy())
    Q0,D0,counts0,ch0=a.shape_search(Q0,lo,hi,D0,dts,dcs,co,intercept,g.SCALE,logc,NBITS,a.PASSES)
    rows=[encode_candidate('all_plane_anchor',X,eps,h,Q0,D0,dts,dcs,co,intercept,szb,arb,ch0)]
    kinds=('b0','b2','b3','b4','low_even','low_all','protect_b1')
    for kind in kinds:
        w=weights_for(kind);Qx=np.ascontiguousarray(Q0.copy());Dx=np.ascontiguousarray(D0.copy())
        Qx,Dx,cnt,ch=shape_search_w(Qx,lo,hi,Dx,dts,dcs,co,intercept,g.SCALE,logc,w,NBITS,TARGET_PASSES)
        r=encode_candidate(kind,X,eps,h,Qx,Dx,dts,dcs,co,intercept,szb,arb,ch);r['counts']=[int(x) for x in cnt[:10]];rows.append(r)
        print(json.dumps({k:v for k,v in r.items() if k not in ('detail','counts')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'anchor':rows[[r['rep']=='all_plane_anchor' for r in rows].index(True)] if any(r['rep']=='all_plane_anchor' for r in rows) else None,'rows':rows,'best':best,'scope':'Encoder-only multi-objective continuation of PR518. The charged learned generator and hard-error legal set are unchanged. Starting from the successful all-plane address-shaped reconstruction, independent searches overweight different low signed-zigzag defect planes, or combinations of them, in the exact global combinatorial surrogate. Every candidate is judged only by the final physical PR512 restricted-rank byte stream; search weights and trajectories are not decoder side information. The best final stream must independently recover the exact defect/Q field and satisfy the unchanged hard source error. This directly tests NOVA-style compute-for-communication search over multiple address-shaping basins rather than assuming one local objective is sufficient.'}
    json.dump(out,open('imperial_multiplane_address_shaping.json','w'),indent=2)
    print(json.dumps({'summary':{'best_rep':best['rep'],'best_bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
