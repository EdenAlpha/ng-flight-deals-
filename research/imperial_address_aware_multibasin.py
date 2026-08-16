import json,sys
import h5py,numpy as np
from numba import njit
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

NBITS=16

@njit(cache=True)
def weighted_cost(counts,logc,w):
    s=0.0
    for b in range(counts.size):s+=w[b]*logc[int(counts[b])]
    return s

@njit(cache=True)
def weighted_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,logc,w,nbits,passes):
    counts=a.init_counts(D,nbits);changes=0
    maxa=dts.size+1;ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32);newd=np.empty(maxa,np.int32);oldv=np.empty(maxa,np.int32);trial=np.empty(nbits,np.int64)
    for ps in range(passes):
        changed=0;rev=ps&1
        for t in range(Q.shape[1]):
            for kk in range(Q.shape[0]):
                cc=kk if rev==0 else Q.shape[0]-1-kk;oldq=int(Q[cc,t]);bestq=oldq;best=weighted_cost(counts,logc,w)
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
                    Q[cc,t]=q;overflow=False
                    for z in range(na):
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);newd[z]=nv
                        if (a.zigscalar(int(nv))>>nbits)!=0:overflow=True
                    if overflow:score=1e300
                    else:
                        for b in range(nbits):trial[b]=counts[b]
                        for z in range(na):
                            u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(newd[z]))
                            for b in range(nbits):trial[b]+=((u1>>b)&1)-((u0>>b)&1)
                        score=weighted_cost(trial,logc,w)
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
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nv
                        u0=a.zigscalar(int(oldv[z]));u1=a.zigscalar(int(nv))
                        for b in range(nbits):counts[b]+=((u1>>b)&1)-((u0>>b)&1)
                    changed+=1;changes+=1
        if changed==0:break
    return Q,D,counts,changes

def profile(name):
    w=np.ones(NBITS,np.float64)
    if name=='uniform':pass
    elif name=='bit0x4':w[0]=4
    elif name=='bit0x8':w[0]=8
    elif name=='evenlow':w[0]=3;w[2]=2;w[4]=1.5
    elif name=='lowbalanced':w[:5]=2
    elif name=='bit02':w[0]=4;w[2]=3
    else:raise ValueError(name)
    return w

def materialize(name,X,eps,h,Q,D,dts,dcs,co,intercept,szb,arb,changes,logc):
    rb,_,RE,detail=rr.restricted_rank_frame(D);r=c.validate(X,eps,h,Q,RE,dts,dcs,co,intercept,rb,name,detail)
    r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];r['search_changes']=int(changes);r['global_rank_bits']=float(a.total_cost(a.init_counts(D,NBITS),logc));return r

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q0,D0,dts,dcs,co,intercept,score,nz,base_changes=c.build_resonant(X,eps);lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size)
    rows=[]
    # Independent basins from the same legitimate starting reconstruction.
    for name in ('uniform','bit0x4','bit0x8','evenlow','lowbalanced','bit02'):
        Q=np.ascontiguousarray(Q0.copy());D=np.ascontiguousarray(D0.copy());w=profile(name)
        Q,D,counts,ch=weighted_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,w,NBITS,5)
        Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('incremental',name))
        r=materialize(name,X,eps,h,Q,D,dts,dcs,co,intercept,szb,arb,ch,logc);rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    # Staged basin: deliberately bias parity first, then release to the true uniform objective.
    Q=np.ascontiguousarray(Q0.copy());D=np.ascontiguousarray(D0.copy());w=profile('bit0x8')
    Q,D,_,ch1=weighted_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,w,NBITS,3)
    Q,D,_,ch2=weighted_search(Q,lo,hi,D,dts,dcs,co,intercept,g.SCALE,logc,profile('uniform'),NBITS,5)
    Dr=g._all_defects(Q,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('incremental staged')
    r=materialize('staged_bit0_then_uniform',X,eps,h,Q,D,dts,dcs,co,intercept,szb,arb,ch1+ch2,logc);rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    rows.sort(key=lambda x:x['bytes']);best=rows[0]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'h':h,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'rows':rows,'best':best,'scope':'Decoder-real multi-basin computation-for-communication search. All candidates share the same charged learned generator and unchanged hard-error legal set. Encoder-only coordinate searches use several weighted combinatorial bitplane objectives solely to enter different legal-reconstruction basins, including parity-biased and staged parity-then-uniform searches. Search paths/objectives are never counted as compression. Every final candidate is physically serialized by the exact PR512 restricted-rank stream, independently decoded, used to regenerate the exact learned-law Q field, and hard-error validated. The reported winner is selected only by actual final bytes; no surrogate or oracle rate is promoted.'}
    json.dump(out,open('imperial_address_aware_multibasin.json','w'),indent=2)
    print(json.dumps({'summary':{'best':best['rep'],'bytes':best['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':best['gain_vs_ar32'],'gain_sz3':best['gain_vs_sz3']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
