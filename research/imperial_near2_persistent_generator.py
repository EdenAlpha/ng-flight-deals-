import json,sys
import h5py,numpy as np
import imperial_near2_native128 as n
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

C0=512; C=128; NT=30000; TB=1024; FAC=1.9995; NTAPS=20

def fit_sampled(Q,ntaps=NTAPS):
    Q=np.asarray(Q,np.float64);offs=g.candidate_offsets();maxdt=64
    ts=np.arange(maxdt,Q.shape[1],32,dtype=np.int32)
    cs=np.arange(8,Q.shape[0]-8,2,dtype=np.int32)
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
    dt=np.asarray([offs[j][0] for j in selected],np.int16);dc=np.asarray([offs[j][1] for j in selected],np.int16)
    co=np.rint(beta[1:]*g.SCALE).astype(np.int32);it=int(np.rint(beta[0]*g.SCALE))
    return dt,dc,co,it,int(y.size)

def encode_with_model(X,eps,h,Q,dt,dc,co,it,label):
    D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE));mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it)
    Qd=np.empty_like(Q);defect_bytes=0;frames=[]
    for t0 in range(0,NT,TB):
        t1=min(NT,t0+TB);db,rep,Ed,detail=rr.restricted_rank_frame(np.ascontiguousarray(D[:,t0:t1],np.int32));defect_bytes+=int(db)+4
        for lt in range(t1-t0):
            t=t0+lt
            for c in range(C):Qd[c,t]=g._pred(Qd,c,t,ddt,ddc,dco,dit,g.SCALE)+int(Ed[c,lt])
        frames.append({'t0':t0,'nt':t1-t0,'bytes':int(db)+4,'rep':rep})
    if not np.array_equal(Qd,Q):raise RuntimeError(('persistent learned replay',label))
    R=Qd.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('persistent learned hard',label,me,eps))
    total=int(mb)+defect_bytes+g.HEADER+1
    return {'label':label,'bytes':total,'model_bytes':int(mb),'defect_frame_bytes':defect_bytes,'bps':8*total/X.size,'maxerr':me,'model_rep':mrep,'frames':frames}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0)
    dt0,dc0,co0,it0=n.fit_model_dyn(Q[:,:TB],ntaps=NTAPS)
    dt1,dc1,co1,it1,nsamp=fit_sampled(Q,NTAPS)
    rows=[encode_with_model(X,eps,h,Q,dt0,dc0,co0,it0,'prefix1024_model'),encode_with_model(X,eps,h,Q,dt1,dc1,co1,it1,'whole_sampled_model')]
    rows.sort(key=lambda z:z['bytes']);best=rows[0]
    out={'shape':[C,NT],'samples':int(X.size),'c0':C0,'eps':eps,'hfac':FAC,'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'max_legal_states':int(np.max(hi-lo+1)),'whole_fit_samples':nsamp,'candidates':[{k:v for k,v in r.items() if k!='frames'} for r in rows],'best':{k:v for k,v in best.items() if k!='frames'},'best_frames':best['frames'],'scope':'Persistent learned-generator diagnostic on the complete 128x30000 hard region. A single public near-2epsilon legal Q field is used continuously across all times. Two fully charged one-model candidates are tested: a law fitted from the first 1024 samples only, and a target-trained law fitted from a deterministic sparse sample of the full Q field. Target training is legal because the complete final Q12 model is serialized. Decoder state is continuous across all 30,000 times; only the exact restricted-rank defect witness is entropy-framed by time, with 4 bytes charged per frame. Each frame is physically encoded/decoded, the single model regenerates the complete Q trajectory continuously, and source hard error is verified. This isolates model/reset amortization; it deliberately does not yet coordinate the rare multi-legal-state samples.'};json.dump(out,open('imperial_near2_persistent_generator.json','w'),indent=2);print(json.dumps({'summary':out['best']},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
