import json,sys
import h5py,numpy as np
from numba import njit
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NBITS=16
PAIR_PASSES=2

@njit(cache=True)
def _add_aff(ac,at,na,c0,t0,Q,dts,dcs):
    if c0<0 or c0>=Q.shape[0] or t0<0 or t0>=Q.shape[1]:return na
    for z in range(na):
        if ac[z]==c0 and at[z]==t0:return na
    ac[na]=c0;at[na]=t0;na+=1
    for j in range(dts.size):
        tc=t0+int(dts[j]);cc=c0-int(dcs[j])
        if tc<0 or tc>=Q.shape[1] or cc<0 or cc>=Q.shape[0]:continue
        dup=False
        for z in range(na):
            if ac[z]==cc and at[z]==tc:dup=True;break
        if not dup:
            ac[na]=cc;at[na]=tc;na+=1
    return na

@njit(cache=True)
def pair_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,logc,nbits,passes):
    counts=a.init_counts(D,nbits)
    maxa=2*(dts.size+1)
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32)
    oldv=np.empty(maxa,np.int32);newv=np.empty(maxa,np.int32)
    trial=np.empty(nbits,np.int64)
    changes=0;tested=0
    # temporal, spatial, and one causal diagonal family
    for ps in range(passes):
        changed=0
        for direction in range(3):
            if direction==0:
                nouter=Q.shape[1]-1;ninner=Q.shape[0]
            elif direction==1:
                nouter=Q.shape[1];ninner=Q.shape[0]-1
            else:
                nouter=Q.shape[1]-1;ninner=Q.shape[0]-1
            for oo in range(nouter):
                for ii in range(ninner):
                    if direction==0:
                        c1=ii;t1=oo;c2=ii;t2=oo+1
                    elif direction==1:
                        c1=ii;t1=oo;c2=ii+1;t2=oo
                    else:
                        c1=ii;t1=oo;c2=ii+1;t2=oo+1
                    if lo[c1,t1]==hi[c1,t1] or lo[c2,t2]==hi[c2,t2]:continue
                    q10=int(Q[c1,t1]);q20=int(Q[c2,t2])
                    na=0;na=_add_aff(ac,at,na,c1,t1,Q,dts,dcs);na=_add_aff(ac,at,na,c2,t2,Q,dts,dcs)
                    for z in range(na):oldv[z]=D[ac[z],at[z]]
                    base=a.total_cost(counts,logc);best=base;bq1=q10;bq2=q20
                    for q1 in range(int(lo[c1,t1]),int(hi[c1,t1])+1):
                        for q2 in range(int(lo[c2,t2]),int(hi[c2,t2])+1):
                            if q1==q10 and q2==q20:continue
                            tested+=1;Q[c1,t1]=q1;Q[c2,t2]=q2
                            overflow=False
                            for z in range(na):
                                nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);newv[z]=nv
                                if (a.zigscalar(int(nv))>>nbits)!=0:overflow=True
                            if overflow:score=1e300
                            else:
                                for b in range(nbits):trial[b]=counts[b]
                                for z in range(na):
                                    u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(newv[z]))
                                    for b in range(nbits):trial[b]+=((u1>>b)&1)-((u0>>b)&1)
                                score=a.total_cost(trial,logc)
                            if score<best-1e-10:
                                best=score;bq1=q1;bq2=q2
                            Q[c1,t1]=q10;Q[c2,t2]=q20
                    if bq1!=q10 or bq2!=q20:
                        Q[c1,t1]=bq1;Q[c2,t2]=bq2
                        for z in range(na):
                            nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nv
                            u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nv))
                            for b in range(nbits):counts[b]+=((u1>>b)&1)-((u0>>b)&1)
                        changes+=1;changed+=1
        if changed==0:break
    return Q,D,counts,changes,tested

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy())
    Q,D,counts1,single_changes=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,NBITS,a.PASSES)
    rb1,_,RE1,detail1=rr.restricted_rank_frame(D)
    single=c.validate(X,eps,h,Q,RE1,dts,dcs,co,intercept,rb1,'single_address_search',detail1)
    before_pair_obj=float(a.total_cost(counts1,logc))
    Q2,D2,counts2,pair_changes,tested=pair_search(np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),dts,dcs,co,intercept,g.SCALE,logc,NBITS,PAIR_PASSES)
    Dr=g._all_defects(Q2,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D2):raise RuntimeError('pair incremental defect mismatch')
    rb2,_,RE2,detail2=rr.restricted_rank_frame(D2)
    pair=c.validate(X,eps,h,Q2,RE2,dts,dcs,co,intercept,rb2,'pair_address_search',detail2)
    for r in (single,pair):
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes']
        print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'single':single,'pair':pair,'search':{'base_projection_changes':int(base_changes),'single_changes':int(single_changes),'pair_changes':int(pair_changes),'pair_candidates_tested':int(tested),'before_pair_global_rank_bits':before_pair_obj,'after_pair_global_rank_bits':float(a.total_cost(counts2,logc)),'before_pair_counts':[int(x) for x in counts1],'after_pair_counts':[int(x) for x in counts2]},'scope':'Decoder-real second-order NOVA address search. It reproduces PR518 single-sample address-aware legal search, then searches coordinated pairs of hard-error-legal reconstruction states along temporal, spatial and causal-diagonal neighborhoods. A pair is accepted only when the global combinatorial bitplane address objective decreases after accounting for every causal learned-law defect affected by both changes jointly. This permits moves that single-coordinate descent cannot cross. No search path is transmitted. Final compression is counted only from the physically serialized PR512 restricted-rank defect stream plus the charged learned generator, followed by exact defect/Q replay and unchanged source-domain hard-error validation.'}
    json.dump(out,open('imperial_address_aware_pair_search.json','w'),indent=2)
    print(json.dumps({'summary':{'single':single['bytes'],'pair':pair['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'pair_changes':int(pair_changes),'tested':int(tested),'gain_vs_single':single['bytes']/pair['bytes'],'gain_vs_ar32':arb['bytes']/pair['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
