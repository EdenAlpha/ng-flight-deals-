import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_causal_address_aware_legal_search as q
import imperial_causal_aware_compact_nova as qc
import imperial_causal_aware_rich_compact as rc
import imperial_compact_nova_container as x
import imperial_causal_context_surface as rich

PAIR_PASSES=1
INF=1e300

@njit(cache=True)
def _merge_affected(ac,at,na,c0,t0,Q,dts,dcs):
    C,T=Q.shape
    na=q._add_unique(ac,at,na,c0,t0,C,T)
    for j in range(dts.size):
        tc=t0+int(dts[j]);cc=c0-int(dcs[j])
        na=q._add_unique(ac,at,na,cc,tc,C,T)
    return na

@njit(cache=True)
def _impacted_union(ic,it,ac,at,na,Q):
    ni=0;C,T=Q.shape
    for z in range(na):
        c0=int(ac[z]);t0=int(at[z])
        ni=q._add_unique(ic,it,ni,c0,t0,C,T)
        ni=q._add_unique(ic,it,ni,c0+1,t0,C,T)
        ni=q._add_unique(ic,it,ni,c0,t0+1,C,T)
        ni=q._add_unique(ic,it,ni,c0+1,t0+1,C,T)
    return ni

@njit(cache=True)
def causal_pair_search(Q,lo,hi,D,dts,dcs,co,intercept,scale,modes,logfact,weights,passes):
    cnt=q.init_counts(D,modes,q.NBITS);changes=0;tested=0
    maxa=2*(dts.size+2);maxi=4*maxa+8
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32);oldD=np.empty(maxa,np.int32)
    ic=np.empty(maxi,np.int32);it=np.empty(maxi,np.int32)
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
                    if direction==0:c1,t1,c2,t2=ii,oo,ii,oo+1
                    elif direction==1:c1,t1,c2,t2=ii,oo,ii+1,oo
                    else:c1,t1,c2,t2=ii,oo,ii+1,oo+1
                    if lo[c1,t1]==hi[c1,t1] or lo[c2,t2]==hi[c2,t2]:continue
                    q10=int(Q[c1,t1]);q20=int(Q[c2,t2]);na=0
                    na=_merge_affected(ac,at,na,c1,t1,Q,dts,dcs);na=_merge_affected(ac,at,na,c2,t2,Q,dts,dcs)
                    ni=_impacted_union(ic,it,ac,at,na,Q)
                    for z in range(na):oldD[z]=D[ac[z],at[z]]
                    base=q.score_counts(cnt,modes,logfact,weights);best=base;bq1=q10;bq2=q20
                    for q1 in range(int(lo[c1,t1]),int(hi[c1,t1])+1):
                        for q2 in range(int(lo[c2,t2]),int(hi[c2,t2])+1):
                            if q1==q10 and q2==q20:continue
                            tested+=1
                            q._remove_contexts(cnt,D,ic,it,ni,modes,q.NBITS)
                            Q[c1,t1]=q1;Q[c2,t2]=q2;overflow=False
                            for z in range(na):
                                nv=x.g._defect(Q,int(ac[z]),int(at[z]),dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nv
                                if (q._zig(int(nv))>>q.NBITS)!=0:overflow=True
                            q._add_contexts(cnt,D,ic,it,ni,modes,q.NBITS)
                            sc=INF if overflow else q.score_counts(cnt,modes,logfact,weights)
                            if sc<best-1e-9:best=sc;bq1=q1;bq2=q2
                            q._remove_contexts(cnt,D,ic,it,ni,modes,q.NBITS)
                            Q[c1,t1]=q10;Q[c2,t2]=q20
                            for z in range(na):D[ac[z],at[z]]=oldD[z]
                            q._add_contexts(cnt,D,ic,it,ni,modes,q.NBITS)
                    if bq1!=q10 or bq2!=q20:
                        q._remove_contexts(cnt,D,ic,it,ni,modes,q.NBITS)
                        Q[c1,t1]=bq1;Q[c2,t2]=bq2
                        for z in range(na):D[ac[z],at[z]]=x.g._defect(Q,int(ac[z]),int(at[z]),dts,dcs,co,intercept,scale)
                        q._add_contexts(cnt,D,ic,it,ni,modes,q.NBITS);changes+=1;changed+=1
        if changed==0:break
    return Q,D,cnt,changes,tested,q.score_counts(cnt,modes,logfact,weights)


def compact_nova(Q,D,dts,dcs,co,intercept,X,eps,h):
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);defect,ddetail=rc.compact_rich_defect(D);stream=bytes([rc.VERSION])+model+defect
    pos=1;rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('pair compact parse mismatch')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('pair compact Q mismatch')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('pair hard',me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'maxerr':me},md,ddetail


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);ar32=rc.compact_ar32_bytes(X,eps)
    h,Q,D,dts,dcs,co,intercept,single_meta=qc.reproduce_causal_best(X,eps)
    single,_,_=compact_nova(Q,D,dts,dcs,co,intercept,X,eps,h)
    lo,hi=x.g.legal_q(X,eps,h);lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(q.NBITS,np.float64);Q2=np.ascontiguousarray(Q.copy());D2=np.ascontiguousarray(D.copy())
    Q2,D2,cnt,ch,tested,sc=causal_pair_search(Q2,lo,hi,D2,dts,dcs,co,intercept,x.g.SCALE,q.MODES,lf,w,PAIR_PASSES)
    Dr=x.g._all_defects(Q2,dts,dcs,co,intercept,x.g.SCALE)
    if not np.array_equal(Dr,D2):raise RuntimeError('causal-pair defect mismatch')
    cnt2=q.init_counts(D2,q.MODES,q.NBITS)
    if not np.array_equal(cnt,cnt2):raise RuntimeError('causal-pair context-count mismatch')
    pair,md,ddetail=compact_nova(Q2,D2,dts,dcs,co,intercept,X,eps,h)
    single.update({'delta_vs_compact_ar32':single['bytes']-ar32['bytes'],'gain_vs_compact_ar32':ar32['bytes']/single['bytes']})
    pair.update({'delta_vs_compact_ar32':pair['bytes']-ar32['bytes'],'gain_vs_compact_ar32':ar32['bytes']/pair['bytes'],'gain_vs_sz3':szb/pair['bytes']})
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'compact_ar32':ar32,'single_compact_rich':single,'pair_compact_rich':pair,'single_search':single_meta,'pair_search':{'changes':int(ch),'tested':int(tested),'surrogate_bits':float(sc)},'model_detail':md,'defect_detail':ddetail,'scope':'Exact coordinated legal-pair search using the same decoder-shared causal Laplace objective as PR546, followed by PR541 richer causal context selection and the packed compact NOVA container. Pair updates exactly remove/reinsert all affected causal context counts for changed learned-law defects and their right/down/diagonal dependents; final full defect and full context-count recomputations must match. Compact AR32 is independently rebuilt in the same process. Both final literal streams are decoder replayed and hard-error checked; only physical bytes count.'}
    json.dump(out,open('imperial_causal_pair_rich_compact.json','w'),indent=2)
    print(json.dumps({'summary':{'single_nova':single['bytes'],'pair_nova':pair['bytes'],'compact_ar32':ar32['bytes'],'delta_pair':pair['delta_vs_compact_ar32'],'pair_changes':int(ch),'tested':int(tested),'sz3':int(szb),'maxerr':pair['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
