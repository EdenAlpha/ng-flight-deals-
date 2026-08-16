import json,sys,math
import h5py,numpy as np
import imperial_causal_restricted_address as ca
import imperial_address_aware_legal_search as a
import imperial_address_aware_pair_search as p
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

CO_DELTAS=(-256,-128,-64,-32,-16,16,32,64,128,256)
INT_DELTAS=(-2048,-1024,-512,-256,-128,128,256,512,1024,2048)
GEN_PASSES=2
NBITS=16
LN2=math.log(2.0)


def _laplace_bits(ids,B,nctx):
    ids=np.asarray(ids,np.int64).ravel();bb=np.asarray(B,np.int64).ravel()
    n=np.bincount(ids,minlength=nctx);k=np.bincount(ids,weights=bb,minlength=nctx).astype(np.int64)
    s=0.0
    for nn,kk in zip(n,k):
        if nn:
            s+=(math.lgamma(int(nn)+2)-math.lgamma(int(kk)+1)-math.lgamma(int(nn-kk)+1))/LN2
    return s


def _plane_score(B,pref,bit):
    C,T=B.shape
    l=np.zeros_like(B,np.uint64);u=np.zeros_like(B,np.uint64);d=np.zeros_like(B,np.uint64)
    l[1:]=B[:-1];u[:,1:]=B[:,:-1];d[1:,1:]=B[:-1,:-1]
    n3=(l<<2)|(u<<1)|d
    cc=np.repeat(np.arange(C,dtype=np.uint64)[:,None],T,axis=1)
    tt=np.repeat(np.arange(T,dtype=np.uint64)[None,:],C,axis=0)
    cand=[]
    cand.append(_laplace_bits(n3,B,8))
    cand.append(_laplace_bits(np.minimum(pref,3)*8+n3,B,32))
    cand.append(_laplace_bits((pref&3)*8+n3,B,32))
    cand.append(_laplace_bits(np.minimum(pref,7)*4+(l<<1)+u,B,32))
    cand.append(_laplace_bits((cc*4//C)*8+n3,B,32))
    cand.append(_laplace_bits((tt*4//T)*8+n3,B,32))
    cand.append(_laplace_bits((np.minimum(pref,3)*2+(cc*2//C))*8+n3,B,64))
    return min(cand)+88.0


def causal_surrogate(D):
    z=m.zig(np.asarray(D,np.int32));mx=int(z.max()) if z.size else 0;nb=max(1,mx.bit_length());s=0.0
    for bit in range(nb-1,-1,-1):
        B=((z>>bit)&1).astype(np.uint64);pref=z>>(bit+1);s+=_plane_score(B,pref,bit)
    return s


def defect(Q,dts,dcs,co,intercept):
    return g._all_defects(np.ascontiguousarray(Q,np.int32),dts,dcs,np.ascontiguousarray(co,np.int32),int(intercept),g.SCALE)


def search_generator(Q,dts,dcs,co,intercept):
    co=np.asarray(co,np.int32).copy();intercept=int(intercept);D=defect(Q,dts,dcs,co,intercept);best=causal_surrogate(D);history=[]
    for ps in range(GEN_PASSES):
        changed=0
        # Coordinate search in the exact transmitted Q12 coefficient lattice.
        for j in range(co.size):
            old=int(co[j]);bv=old;bs=best
            for delta in CO_DELTAS:
                trial=co.copy();trial[j]=np.int32(old+delta);Dt=defect(Q,dts,dcs,trial,intercept);sc=causal_surrogate(Dt)
                if sc<bs-1e-7:bs=sc;bv=int(trial[j])
            if bv!=old:
                co[j]=np.int32(bv);D=defect(Q,dts,dcs,co,intercept);best=causal_surrogate(D);changed+=1
        old=intercept;bi=old;bs=best
        for delta in INT_DELTAS:
            it=old+delta;Dt=defect(Q,dts,dcs,co,it);sc=causal_surrogate(Dt)
            if sc<bs-1e-7:bs=sc;bi=it
        if bi!=old:
            intercept=bi;D=defect(Q,dts,dcs,co,intercept);best=causal_surrogate(D);changed+=1
        history.append({'pass':ps,'changes':changed,'surrogate_bits':float(best)})
        if changed==0:break
    return co,intercept,D,best,history


def materialize(name,X,eps,h,Q,D,dts,dcs,co,intercept):
    b,_,Dd,detail=ca.causal_frame(D)
    r=c.validate(X,eps,h,Q,Dd,dts,dcs,co,intercept,b,name,detail)
    return r


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps)
    # Reproduce the current verified PR530 pair-optimized state and its charged OMP generator.
    h,Q,D,dts,dcs,co0,inter0,search0=ca.build_pair_state(X,eps)
    rows=[]
    r0=materialize('baseline_causal',X,eps,h,Q,D,dts,dcs,co0,inter0);rows.append(r0)
    # Search the generator itself for communication cost while holding the already-legal Q fixed.
    co1,inter1,D1,sur1,gh=search_generator(Q,dts,dcs,co0,inter0)
    r1=materialize('generator_codesigned',X,eps,h,Q,D1,dts,dcs,co1,inter1);rows.append(r1)
    # Then let the legal reconstruction re-adapt to that communication-optimized generator.
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D1.copy())
    Q2,D2,_,single_changes=a.shape_search(Q2,lo,hi,D2,dts,dcs,co1,inter1,g.SCALE,logc,NBITS,a.PASSES)
    Dr=defect(Q2,dts,dcs,co1,inter1)
    if not np.array_equal(Dr,D2):raise RuntimeError('single codesign defect mismatch')
    r2=materialize('generator_plus_legal',X,eps,h,Q2,D2,dts,dcs,co1,inter1);rows.append(r2)
    # Exact coordinated-pair escape with full-defect validation, as in PR530.
    Q3,D3,_,pair_changes,tested,rejected=p.pair_search(np.ascontiguousarray(Q2.copy()),lo,hi,np.ascontiguousarray(D2.copy()),dts,dcs,co1,inter1,g.SCALE,logc,NBITS,1)
    Dr=defect(Q3,dts,dcs,co1,inter1)
    if not np.array_equal(Dr,D3):raise RuntimeError('pair codesign defect mismatch')
    r3=materialize('generator_plus_legal_pairs',X,eps,h,Q3,D3,dts,dcs,co1,inter1);rows.append(r3)
    for r in rows:
        r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'initial_search':search0,'generator_search':{'initial_coef_q12':[int(x) for x in co0],'final_coef_q12':[int(x) for x in co1],'initial_intercept_q12':int(inter0),'final_intercept_q12':int(inter1),'final_surrogate_bits':float(sur1),'history':gh},'legal_search':{'single_changes':int(single_changes),'pair_changes':int(pair_changes),'pair_tested':int(tested),'pair_rejected_exact':int(rejected)},'rows':rows,'best':best,'scope':'Decoder-real NOVA generator/address co-design. Starting from the verified PR530 pair-optimized legal reconstruction, the encoder searches the actual transmitted Q12 sparse-generator coefficients and intercept for lower decoder-shared causal-address cost rather than least-squares error. The causal Laplace-context score is only an encoder search surrogate. Every final model coefficient/tap/intercept is physically serialized and charged by the existing model frame. Candidate final states are physically encoded with PR537 causal bitplane arithmetic, independently decoded, used to regenerate exact Q, and source hard error is checked. The legal reconstruction is then re-optimized around the communication-selected generator and an exact pair search is applied. Only actual final stream bytes determine the winner.'};json.dump(out,open('imperial_generator_causal_codesign.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['rep'],'bytes':best['bytes'],'baseline':r0['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gap_to_ar32':best['bytes']-arb['bytes'],'gain_ar32':best['gain_vs_ar32']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
