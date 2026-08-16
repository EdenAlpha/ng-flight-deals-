import json,sys
import h5py,numpy as np
from numba import njit
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

PASSES=4
OFF=32768
RANGE=65537

@njit(cache=True)
def init_hist(D):
    h=np.zeros(RANGE,np.int64)
    for c0 in range(D.shape[0]):
        for t0 in range(D.shape[1]):
            v=int(D[c0,t0])+OFF
            if v<0 or v>=RANGE:raise RuntimeError('defect range')
            h[v]+=1
    return h

@njit(cache=True)
def hist_score(hist,lf):
    s=0.0
    for i in range(hist.size):
        n=int(hist[i])
        if n>1:s+=lf[n]
    return s

@njit(cache=True)
def shape_hist(Q,lo,hi,D,dts,dcs,co,intercept,scale,lf,passes):
    hist=init_hist(D);changes=0;maxa=dts.size+1
    ac=np.empty(maxa,np.int32);at=np.empty(maxa,np.int32);oldv=np.empty(maxa,np.int32);newv=np.empty(maxa,np.int32)
    vals=np.empty(2*maxa,np.int32);deltas=np.empty(2*maxa,np.int32)
    for ps in range(passes):
        changed=0;rev=ps&1
        for tt0 in range(Q.shape[1]):
            t=tt0 if rev==0 else Q.shape[1]-1-tt0
            for kk in range(Q.shape[0]):
                cc=kk if rev==0 else Q.shape[0]-1-kk;oldq=int(Q[cc,t]);bestq=oldq;bestgain=0.0
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
                    Q[cc,t]=q;ok=True
                    for z in range(na):
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);newv[z]=nv
                        if nv+OFF<0 or nv+OFF>=RANGE:ok=False
                    Q[cc,t]=oldq
                    if not ok:continue
                    nd=0
                    for z in range(na):
                        oi=int(oldv[z])+OFF;ni=int(newv[z])+OFF
                        found=-1
                        for j in range(nd):
                            if vals[j]==oi:found=j;break
                        if found<0:vals[nd]=oi;deltas[nd]=-1;nd+=1
                        else:deltas[found]-=1
                        found=-1
                        for j in range(nd):
                            if vals[j]==ni:found=j;break
                        if found<0:vals[nd]=ni;deltas[nd]=1;nd+=1
                        else:deltas[found]+=1
                    gain=0.0;valid=True
                    for j in range(nd):
                        idx=int(vals[j]);oldn=int(hist[idx]);newn=oldn+int(deltas[j])
                        if newn<0:valid=False;break
                        gain += lf[newn]-lf[oldn]
                    if valid and gain>bestgain+1e-12:bestgain=gain;bestq=q
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
                        nv=g._defect(Q,ac[z],at[z],dts,dcs,co,intercept,scale);D[ac[z],at[z]]=nv;hist[int(oldv[z])+OFF]-=1;hist[int(nv)+OFF]+=1
                    changes+=1;changed+=1
        if changed==0:break
    return Q,D,hist,changes


def materialized_best(X,eps,h,Q,D,dts,dcs,co,intercept,label):
    rb,_,RD,rdetail=rr.restricted_rank_frame(D);r1=c.validate(X,eps,h,Q,RD,dts,dcs,co,intercept,rb,label+'_rank',rdetail)
    fr=m.encode_k(np.ascontiguousarray(D,np.int32));r2=c.validate(X,eps,h,Q,np.asarray(fr[2],np.int32),dts,dcs,co,intercept,int(fr[0]),label+'_dense_'+fr[1])
    return min((r1,r2),key=lambda r:r['bytes']),[r1,r2]


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,_,_,_=c.build_resonant(X,eps)
    lo,hi=g.legal_q(X,eps,h);logc=a.logcomb_table(X.size);Q0=np.ascontiguousarray(Q.copy());D0=np.ascontiguousarray(D.copy());Q0,D0,_,ch0=a.shape_search(Q0,lo,hi,D0,dts,dcs,co,intercept,g.SCALE,logc,a.NBITS,a.PASSES)
    before,breps=materialized_best(X,eps,h,Q0,D0,dts,dcs,co,intercept,'before')
    lf=np.zeros(X.size+1,np.float64);lf[1:]=np.cumsum(np.log(np.arange(1,X.size+1,dtype=np.float64)))
    hb=init_hist(D0);score0=lf[X.size]-hist_score(hb,lf)
    Q1=np.ascontiguousarray(Q0.copy());D1=np.ascontiguousarray(D0.copy());Q1,D1,ha,ch=shape_hist(Q1,lo,hi,D1,dts,dcs,co,intercept,g.SCALE,lf,PASSES)
    Dr=g._all_defects(Q1,dts,dcs,co,intercept,g.SCALE)
    if not np.array_equal(Dr,D1):raise RuntimeError('defect mismatch')
    after,areps=materialized_best(X,eps,h,Q1,D1,dts,dcs,co,intercept,'universe_shaped')
    score1=lf[X.size]-hist_score(ha,lf)
    for r in (before,after):r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    vals=np.flatnonzero(ha);top=sorted(((int(ha[i]),int(i-OFF)) for i in vals),reverse=True)[:20]
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'before':before,'after':after,'before_reps':breps,'after_reps':areps,'search':{'bitshape_changes':int(ch0),'universe_changes':int(ch),'multinomial_bits_before':float(score0/math.log(2.0)) if False else float(score0/np.log(2.0)),'multinomial_bits_after':float(score1/np.log(2.0)),'distinct_before':int(np.count_nonzero(hb)),'distinct_after':int(np.count_nonzero(ha)),'top_symbols_after':top},'scope':'Exact defect-universe shaping gate. Starting from PR518 address-shaped legal reconstruction and the same fully charged learned generator, encoder computation searches remaining hard-error-legal Q choices to minimize the exact multinomial universe log(N! / product_v n_v!) of the emitted signed defect symbols. This directly rewards concentration/repetition of the defect alphabet rather than marginal bit bias. Search trajectory is not transmitted. Final candidates are physically encoded both by exact PR512 restricted ranking and the existing decoder-real dense representation menu; only the smaller actual stream is reported. Decoder recovers identical defects, regenerates exact Q and verifies unchanged source-domain hard error. No multinomial surrogate is counted as compressed bytes.'}
    json.dump(out,open('imperial_defect_universe_shaping.json','w'),indent=2)
    print(json.dumps({'summary':{'before':before['bytes'],'after':after['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'changes':int(ch),'gain_ar32':arb['bytes']/after['bytes'],'distinct_before':out['search']['distinct_before'],'distinct_after':out['search']['distinct_after']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
