import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_address_aware_pair_search as p
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

PASSES=4
FAMS=rr.FAMILIES

@njit(cache=True)
def _logcomb_lf(n,k,lf):
    if k<0 or k>n:return 1e300
    return lf[n]-lf[k]-lf[n-k]

@njit(cache=True)
def _add_aff(ac,at,na,c0,t0,Q,dts,dcs):
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
def bit0_context_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,gid,gn,gk,lf,passes):
    maxa=dts.size+1
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32)
    oldv=np.empty(maxa,np.int32);newv=np.empty(maxa,np.int32)
    ug=np.empty(maxa,np.int32);dk=np.empty(maxa,np.int32)
    changes=0;tested=0;preserving=0
    for ps in range(passes):
        changed=0;rev=ps&1
        for t in range(Q.shape[1]):
            for ii in range(Q.shape[0]):
                cc=ii if rev==0 else Q.shape[0]-1-ii
                oldq=int(Q[cc,t]);bestq=oldq;bestdelta=0.0
                na=0;na=_add_aff(ac,at,na,cc,t,Q,dts,dcs)
                for z in range(na):oldv[z]=D[ac[z],at[z]]
                for q in range(int(lo[cc,t]),int(hi[cc,t])+1):
                    if q==oldq:continue
                    tested+=1;Q[cc,t]=q;ok=True
                    for z in range(na):
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);newv[z]=nv
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nv))
                        if (u0>>1)!=(u1>>1):ok=False;break
                    if ok:
                        preserving+=1;nu=0
                        for z in range(na):
                            u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(newv[z]));dd=(u1&1)-(u0&1)
                            if dd==0:continue
                            gi=int(gid[ac[z],at[z]]);found=-1
                            for u in range(nu):
                                if ug[u]==gi:found=u;break
                            if found<0:
                                ug[nu]=gi;dk[nu]=dd;nu+=1
                            else:dk[found]+=dd
                        delta=0.0;valid=True
                        for u in range(nu):
                            gi=ug[u];ko=int(gk[gi]);kn=ko+int(dk[u]);n=int(gn[gi])
                            if kn<0 or kn>n:valid=False;break
                            delta+=_logcomb_lf(n,kn,lf)-_logcomb_lf(n,ko,lf)
                        if valid and delta<bestdelta-1e-12:
                            bestdelta=delta;bestq=q
                    Q[cc,t]=oldq
                if bestq!=oldq:
                    Q[cc,t]=bestq
                    for z in range(na):
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale)
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nv));dd=(u1&1)-(u0&1)
                        if dd:
                            gi=int(gid[ac[z],at[z]]);gk[gi]+=dd
                        D[ac[z],at[z]]=nv
                    changes+=1;changed+=1
        if changed==0:break
    return Q,D,gk,changes,tested,preserving

def group_map(D,family):
    U=m.zig(np.asarray(D,np.int32)).astype(np.uint64)
    known=U & np.uint64(0xFFFFFFFFFFFFFFFE)
    keys=rr.context_keys(known,0,family)
    _,inv=np.unique(keys,return_inverse=True)
    gid=inv.reshape(D.shape).astype(np.int32)
    ng=int(inv.max())+1 if inv.size else 0
    gn=np.bincount(inv,minlength=ng).astype(np.int32)
    bits=(U.ravel()&1).astype(np.int32)
    gk=np.bincount(inv,weights=bits,minlength=ng).astype(np.int32)
    return gid,gn,gk

def lfact(n):
    x=np.zeros(n+1,np.float64)
    if n:x[1:]=np.cumsum(np.log2(np.arange(1,n+1,dtype=np.float64)))
    return x

def build_pair_baseline(X,eps):
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy())
    Q,D,counts1,single_changes=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,a.PASSES)
    D=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    Q,Dcache,_,pair_changes,tested,rejected=p.pair_search(np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,p.PAIR_PASSES)
    D=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    return h,Q,D,dts,dcs,co,intercept,lo,hi,{'base_changes':base_changes,'single_changes':single_changes,'pair_changes':pair_changes,'pair_tested':tested,'pair_rejected':rejected}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    h,Q0,D0,dts,dcs,co,intercept,lo,hi,search0=build_pair_baseline(X,eps)
    rb0,_,RE0,det0=rr.restricted_rank_frame(D0);base=c.validate(X,eps,h,Q0,RE0,dts,dcs,co,intercept,rb0,'pair_baseline',det0)
    lf=lfact(X.size);rows=[base];sweeps=[]
    for fam in FAMS:
        gid,gn,gk=group_map(D0,fam)
        Q=np.ascontiguousarray(Q0.copy());D=np.ascontiguousarray(D0.copy());gkc=np.ascontiguousarray(gk.copy())
        before=sum(_logcomb_lf(int(n),int(k),lf) for n,k in zip(gn,gk))
        Q,D,gka,changes,tested,preserving=bit0_context_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,np.ascontiguousarray(gid),np.ascontiguousarray(gn),gkc,lf,PASSES)
        Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('defect mismatch',fam))
        U0=m.zig(D0).astype(np.uint64);U1=m.zig(D).astype(np.uint64)
        if np.any((U0>>1)!=(U1>>1)):raise RuntimeError(('higher bits changed',fam))
        rb,_,RE,detail=rr.restricted_rank_frame(D)
        row=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,'bit0_shape_'+fam,detail)
        row['gain_vs_sz3']=szb/row['bytes'];row['gain_vs_ar32']=arb['bytes']/row['bytes'];rows.append(row)
        after=sum(_logcomb_lf(int(n),int(k),lf) for n,k in zip(gn,gka))
        sweeps.append({'family':fam,'groups':int(len(gn)),'changes':int(changes),'tested':int(tested),'higher_preserving_candidates':int(preserving),'context_bits_before':float(before),'context_bits_after':float(after),'actual_bytes':int(row['bytes']),'bit0_selected_family':next(x['family'] for x in detail if x['bit']==0),'bit0_stored':int(next(x['stored'] for x in detail if x['bit']==0))})
        print(json.dumps(sweeps[-1],indent=2),flush=True)
    for r in rows:
        r.setdefault('gain_vs_sz3',szb/r['bytes']);r.setdefault('gain_vs_ar32',arb['bytes']/r['bytes'])
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'pair_baseline':base,'rows':rows,'best':best,'family_sweeps':sweeps,'prior_search':search0,'scope':'Decoder-real Complexity-Weapon/NOVA context-shaping gate. It first reproduces the PR530 pair-optimized legal reconstruction. Then, independently for each public PR512 context family, it searches only hard-error-legal Q changes whose complete affected learned-law defect set preserves every zigzag bit above bit 0. Therefore higher defect planes and all bit-0 decoder context keys remain exactly fixed. Such moves can only reshape the LSB membership inside already decoder-known restricted universes. The exact combinatorial sum log2 C(n_g,k_g) for that fixed context partition is optimized; no search path or target-derived context model is transmitted. Each final candidate is physically serialized by the unchanged PR512 exact restricted-rank codec, independently decoded, used with the charged learned generator to regenerate Q, and checked against the unchanged source hard-error bound. Only actual final bytes count.'}
    json.dump(out,open('imperial_bit0_context_shaping.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base['bytes'],'best_rep':best['rep'],'best':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_vs_ar32':arb['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
