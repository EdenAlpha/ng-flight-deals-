import json,sys
import h5py,numpy as np
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

C=128
T=30000
C0=512
P=32
FAC=1.99
NTAPS=20
ROUNDS=2
PASSES=2
SCALE=4096
HEADER=48


def candidate_offsets():
    ds=(1,2,3,4,6,8,12,16,24,32,48,64)
    cs=(-8,-4,-2,-1,0,1,2,4,8)
    return [(dt,dc) for dt in ds for dc in cs]+[(0,-1),(0,-2),(0,-4),(0,-8)]


def fit_model(Q,ntaps=NTAPS):
    Q=np.asarray(Q,np.float64);offs=candidate_offsets();maxdt=64
    ts=np.arange(maxdt,Q.shape[1],64,dtype=np.int32);cs=np.arange(8,Q.shape[0]-8,2,dtype=np.int32)
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


def build(X,eps):
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(ROUNDS):
        dts,dcs,co,intercept=fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,False,PASSES);changes+=int(ch)
    dts,dcs,co,intercept=fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,SCALE,False,PASSES);changes+=int(ch)
    return h,Q,D,dts,dcs,co,intercept,changes,float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))


def materialize(X,eps,h,Q,D,dts,dcs,co,intercept):
    mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
    fr=m.encode_k(np.ascontiguousarray(D,np.int32));Dd=np.asarray(fr[2],np.int32)
    Qd=sc.q_decode(Dd,ddt,ddc,dco,dinter,SCALE)
    if not np.array_equal(Qd,Q):raise RuntimeError('full Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('full hard',me,eps))
    total=int(mb)+int(fr[0])+HEADER
    return {'bytes':total,'bps':8*total/X.size,'model_bytes':int(mb),'model_rep':mrep,'defect_bytes':int(fr[0]),'rep':'dense_'+fr[1],'maxerr':me,'defect_zero_fraction':float(np.mean(D==0)),'defect_std':float(D.std())}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if X.shape!=(C,T):raise RuntimeError(('shape',X.shape))
    szb,ori=m.szrun(X,eps);arb=sc.ar32_baseline(X,eps);h,Q,D,dts,dcs,co,intercept,changes,meanlegal=build(X,eps);ours=materialize(X,eps,h,Q,D,dts,dcs,co,intercept)
    ours['gain_vs_sz3']=szb/ours['bytes'];ours['gain_vs_ar32']=arb['bytes']/ours['bytes']
    out={'region':'hard','c0':C0,'shape':[C,T],'samples':int(X.size),'local_std':float(X.std()),'global_std':std,'eps':eps,'hfac':FAC,'h':h,'mean_legal_states':meanlegal,'projection_changes':int(changes),'sz3':{'bytes':int(szb),'bps':8*szb/X.size,'orientation':ori},'ar32':arb,'near2':ours,'taps':[[int(a),int(b)] for a,b in zip(dts,dcs)],'coef_q12':[int(x) for x in co],'intercept_q12':int(intercept),'scope':'Full hard-region transfer audit of the public h=1.99epsilon learned sparse causal generator that beat AR32 on 32x1024 and 128x4096. The object is the complete 128-channel by 30,000-time-sample canonical hard Imperial region at c0=512 and unchanged survey-global epsilon. The sparse 20-tap generator is learned from a fixed deterministic subsample grid, quantized to Q12, serialized/decoded and charged. The legal reconstruction is globally optimized only within the unchanged hard-error intervals. Because the 128x4096 audit found dense zigzag bitplanes smaller than restricted ranking, this full-scale audit precommits the exact decoder-real dense representation menu rather than spending runtime on the losing small-block rank family. Decoder byte-decodes the complete defect field, causally regenerates exact Q and verifies source hard error. Matched SZ3 and charged AR32 step267 are rerun from scratch on the identical full 128x30000 object.'}
    json.dump(out,open('imperial_near2eps_full_hard_128x30000.json','w'),indent=2)
    print(json.dumps({'summary':{'ours':ours['bytes'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':ours['gain_vs_ar32'],'gain_sz3':ours['gain_vs_sz3'],'maxerr':ours['maxerr'],'mean_legal':meanlegal,'changes':int(changes),'rep':ours['rep']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
