import json,sys
import h5py,numpy as np
from numba import njit
import imperial_resonant_learned_law_address as g
import imperial_defect_restricted_rank_address as rr
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as ar

C=128
T=4096
C0=512
T0=14488
P=32
TRAIN=1024
AR_STEP=267
FAC=1.99
NTAPS=20
ROUNDS=2
PASSES=2
HEADER=48
SCALE=4096

@njit(cache=True)
def arpred(R,c,t,co,p):
    if t<p:return 0
    v=float(co[-1])
    for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
    return int(np.rint(v))

@njit(cache=True)
def ar_quant(X,co,p,step):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            pred=arpred(R,c,t,co,p);k=int(np.rint((float(X[c,t])-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    return R,K

@njit(cache=True)
def ar_decode(K,co,p,step):
    R=np.zeros(K.shape,np.int32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):R[c,t]=arpred(R,c,t,co,p)+step*int(K[c,t])
    return R

@njit(cache=True)
def q_decode(D,dts,dcs,co,intercept,scale):
    Q=np.empty(D.shape,np.int32)
    for t in range(D.shape[1]):
        for c in range(D.shape[0]):Q[c,t]=g._pred(Q,c,t,dts,dcs,co,intercept,scale)+int(D[c,t])
    return Q


def candidate_offsets():
    ds=(1,2,3,4,6,8,12,16,24,32,48,64)
    cs=(-8,-4,-2,-1,0,1,2,4,8)
    return [(dt,dc) for dt in ds for dc in cs]+[(0,-1),(0,-2),(0,-4),(0,-8)]


def fit_model(Q,ntaps=NTAPS):
    Q=np.asarray(Q,np.float64);offs=candidate_offsets();maxdt=64
    ts=np.arange(maxdt,Q.shape[1],16,dtype=np.int32);cs=np.arange(8,Q.shape[0]-8,2,dtype=np.int32)
    tt=np.repeat(ts,cs.size);cc=np.tile(cs,ts.size);y=Q[cc,tt]
    A=np.empty((y.size,len(offs)),np.float64)
    for j,(dt,dc) in enumerate(offs):A[:,j]=Q[cc+dc,tt-dt]
    ym=float(y.mean());y0=y-ym;means=A.mean(axis=0);scales=A.std(axis=0)+1e-8;An=(A-means)/scales
    selected=[];avail=np.ones(An.shape[1],bool);resid=y0.copy()
    for _ in range(ntaps):
        corr=np.abs(An.T@resid);corr[~avail]=-1;j=int(np.argmax(corr));selected.append(j);avail[j]=False
        B=An[:,selected];beta=np.linalg.lstsq(B,y0,rcond=1e-4)[0];resid=y0-B@beta
    B=A[:,selected];M=np.column_stack([np.ones(B.shape[0]),B]);ridge=1e-5*np.eye(M.shape[1]);ridge[0,0]=0
    beta=np.linalg.solve(M.T@M+ridge,M.T@y)
    dts=np.asarray([offs[j][0] for j in selected],np.int16);dcs=np.asarray([offs[j][1] for j in selected],np.int16)
    co=np.rint(beta[1:]*SCALE).astype(np.int32);intercept=int(np.rint(beta[0]*SCALE))
    return dts,dcs,co,intercept


def ar32_baseline(X,eps):
    co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=ar_quant(X,cd,P,AR_STEP)
    fr=m.encode_k(K);Kd=np.asarray(fr[2],np.int32);Rd=ar_decode(Kd,cd,P,AR_STEP)
    if not np.array_equal(Rd,R):raise RuntimeError('AR32 replay')
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('AR32 hard',me,eps))
    return {'bytes':int(mb)+int(fr[0])+32,'model_bytes':int(mb),'innovation_bytes':int(fr[0]),'rep':fr[1],'maxerr':me,'bps':8*(int(mb)+int(fr[0])+32)/X.size}


def build_near2(X,eps):
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(ROUNDS):
        dts,dcs,co,intercept=fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,False,PASSES);changes+=int(ch)
    dts,dcs,co,intercept=fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,False,PASSES);changes+=int(ch)
    return h,Q,D,dts,dcs,co,intercept,changes,float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))


def materialize(X,eps,h,Q,D,dts,dcs,co,intercept):
    mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
    dense=m.encode_k(np.ascontiguousarray(D,np.int32));denseD=np.asarray(dense[2],np.int32)
    rb,rrep,RD,rdetail=rr.restricted_rank_frame(D)
    options=[(int(dense[0]),'dense_'+dense[1],denseD),(int(rb),'restricted_rank',RD)]
    rows=[]
    for db,rep,Dd in options:
        Qd=q_decode(Dd,ddt,ddc,dco,dinter,SCALE)
        if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',rep))
        me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',rep,me,eps))
        total=int(mb)+db+HEADER
        rows.append({'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'model_rep':mrep,'defect_bytes':db,'rep':rep,'maxerr':me})
    rows.sort(key=lambda r:r['bytes'])
    return rows[0],rows,rdetail


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[T0:T0+T,C0:C0+C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,changes,meanlegal=build_near2(X,eps);best,rows,rdetail=materialize(X,eps,h,Q,D,dts,dcs,co,intercept)
    best['gain_vs_sz3']=szb/best['bytes'];best['gain_vs_ar32']=arb['bytes']/best['bytes']
    out={'region':'hard','c0':C0,'t0':T0,'shape':[C,T],'samples':int(X.size),'local_std':float(X.std()),'global_std':std,'eps':eps,'hfac':FAC,'h':h,'mean_legal_states':meanlegal,'projection_changes':int(changes),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'near2':best,'near2_reps':rows,'taps':[[int(a),int(b)] for a,b in zip(dts,dcs)],'coef_q12':[int(x) for x in co],'intercept_q12':int(intercept),'rank_detail':rdetail,'scope':'Scale-transfer audit of the exact near-2epsilon learned-law construction that beat AR32 on the 32x1024 hard gate. The object is enlarged 16x to 128x4096 at the same canonical hard Imperial location and unchanged survey-global epsilon. A 20-tap sparse causal generator is learned from deterministic subsamples, quantized to Q12 and fully serialized. The legal reconstruction lattice remains fixed at the precommitted h=1.99epsilon; the encoder globally chooses among the rare multi-state legal points under the same exact defect objective. Both dense and exact restricted-rank defect streams are physically encoded/decoded; the smaller valid representation wins. Decoder regenerates Q causally from only the charged model+defect and source hard error is checked. Matched SZ3 and a charged shared AR32 step267 are rerun on the identical 128x4096 object. No result from the 32x1024 gate is reused as a comparator.'}
    json.dump(out,open('imperial_near2eps_scale_128x4096.json','w'),indent=2)
    print(json.dumps({'summary':{'ours':best['bytes'],'rep':best['rep'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':best['gain_vs_ar32'],'gain_sz3':best['gain_vs_sz3'],'maxerr':best['maxerr'],'mean_legal':meanlegal,'changes':int(changes)}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
