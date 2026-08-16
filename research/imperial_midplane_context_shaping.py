import json,sys
import h5py,numpy as np
from numba import njit
import imperial_address_aware_pair_search as p
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

BITS=(1,2,3,4)
FAMS=rr.FAMILIES
PASSES=3

@njit(cache=True)
def _logcomb(n,k,lf):
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
def plane_context_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,gid,gn,gk,lf,bit,passes):
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
                        if (u0>>(bit+1))!=(u1>>(bit+1)):ok=False;break
                    if ok:
                        preserving+=1;nu=0
                        for z in range(na):
                            u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(newv[z]))
                            dd=((u1>>bit)&1)-((u0>>bit)&1)
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
                            delta+=_logcomb(n,kn,lf)-_logcomb(n,ko,lf)
                        if valid and delta<bestdelta-1e-12:
                            bestdelta=delta;bestq=q
                    Q[cc,t]=oldq
                if bestq!=oldq:
                    Q[cc,t]=bestq
                    for z in range(na):
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale)
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nv))
                        dd=((u1>>bit)&1)-((u0>>bit)&1)
                        if dd:
                            gi=int(gid[ac[z],at[z]]);gk[gi]+=dd
                        D[ac[z],at[z]]=nv
                    changes+=1;changed+=1
        if changed==0:break
    return Q,D,gk,changes,tested,preserving

def group_map(D,bit,family):
    U=m.zig(np.asarray(D,np.int32)).astype(np.uint64)
    keys=rr.context_keys(U,bit,family)
    _,inv=np.unique(keys,return_inverse=True)
    gid=inv.reshape(D.shape).astype(np.int32)
    ng=int(inv.max())+1 if inv.size else 0
    gn=np.bincount(inv,minlength=ng).astype(np.int32)
    bits=((U.ravel()>>bit)&1).astype(np.int32)
    gk=np.bincount(inv,weights=bits,minlength=ng).astype(np.int32)
    return gid,gn,gk

def lfact(n):
    x=np.zeros(n+1,np.float64)
    if n:x[1:]=np.cumsum(np.log2(np.arange(1,n+1,dtype=np.float64)))
    return x

def pair_baseline(X,eps):
    h,Q,D,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q=np.ascontiguousarray(Q.copy());D=np.ascontiguousarray(D.copy())
    Q,D,_,single_changes=a.shape_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,a.PASSES)
    D=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    Q,_,_,pair_changes,tested,rejected=p.pair_search(np.ascontiguousarray(Q.copy()),lo,hi,np.ascontiguousarray(D.copy()),dts,dcs,co,intercept,g.SCALE,logc,p.NBITS,p.PAIR_PASSES)
    D=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    return h,Q,D,dts,dcs,co,intercept,lo,hi,{'base_changes':int(base_changes),'single_changes':int(single_changes),'pair_changes':int(pair_changes),'pair_tested':int(tested),'pair_rejected':int(rejected)}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    h,Q0,D0,dts,dcs,co,intercept,lo,hi,prior=pair_baseline(X,eps)
    rb0,_,RE0,det0=rr.restricted_rank_frame(D0);base=c.validate(X,eps,h,Q0,RE0,dts,dcs,co,intercept,rb0,'pair_baseline',det0)
    base['gain_vs_sz3']=szb/base['bytes'];base['gain_vs_ar32']=arb['bytes']/base['bytes']
    lf=lfact(X.size);rows=[base];sweeps=[]
    for bit in BITS:
        for fam in FAMS:
            gid,gn,gk=group_map(D0,bit,fam)
            Q=np.ascontiguousarray(Q0.copy());D=np.ascontiguousarray(D0.copy());gkc=np.ascontiguousarray(gk.copy())
            before=sum(float(_logcomb(int(n),int(k),lf)) for n,k in zip(gn,gk))
            Q,D,gka,changes,tested,preserving=plane_context_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,np.ascontiguousarray(gid),np.ascontiguousarray(gn),gkc,lf,int(bit),PASSES)
            Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
            if not np.array_equal(Dr,D):raise RuntimeError(('defect mismatch',bit,fam))
            U0=m.zig(D0).astype(np.uint64);U1=m.zig(D).astype(np.uint64)
            if np.any((U0>>(bit+1))!=(U1>>(bit+1))):raise RuntimeError(('higher bits changed',bit,fam))
            rb,_,RE,detail=rr.restricted_rank_frame(D)
            row=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,f'bit{bit}_shape_{fam}',detail)
            row['gain_vs_sz3']=szb/row['bytes'];row['gain_vs_ar32']=arb['bytes']/row['bytes'];rows.append(row)
            after=sum(float(_logcomb(int(n),int(k),lf)) for n,k in zip(gn,gka))
            plane=next(x for x in detail if x['bit']==bit)
            rec={'bit':int(bit),'family':fam,'groups':int(len(gn)),'changes':int(changes),'tested':int(tested),'higher_preserving_candidates':int(preserving),'context_bits_before':before,'context_bits_after':after,'actual_bytes':int(row['bytes']),'selected_family':plane['family'],'target_plane_stored':int(plane['stored'])}
            sweeps.append(rec);print(json.dumps(rec),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'pair_baseline':base,'best':best,'rows':rows,'sweeps':sweeps,'prior_search':prior,'scope':'Decoder-real midplane context-shaping gate. Starting from the exact PR530 pair-optimized legal reconstruction, each candidate independently targets defect zigzag bitplanes 1-4 under one public PR512 decoder-known context grammar. Encoder moves are permitted only when every affected learned-law defect preserves all zigzag bits above the target plane, so that plane context membership remains fixed and decoder-known. The encoder then minimizes exact enumerative log2 C(n_g,k_g) membership cost within those fixed restricted universes. Lower defect bits may change and are fully charged by the final real PR512 stream, so a target-plane surrogate win is accepted as a codec win only if the physically serialized total stream is smaller. No search path or target-trained context description is transmitted. Every final stream is independently decoded, regenerates Q from the charged learned generator, and passes the unchanged source-domain hard-error bound.'}
    json.dump(out,open('imperial_midplane_context_shaping.json','w'),indent=2)
    print(json.dumps({'summary':{'baseline':base['bytes'],'best_rep':best['rep'],'best':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gap_to_ar32_bytes':int(best['bytes']-arb['bytes']),'gain_vs_ar32':arb['bytes']/best['bytes'],'gain_vs_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
