import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAC=1.9995
TAPS=(8,12,16,20,24,28,32,40,48)


def build(X,eps,ntaps):
    h=float(eps*FAC);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(g.ROUNDS):
        dt,dc,co,it=g.fit_model(Q,ntaps=ntaps);Q,D,H,s,n,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    dt,dc,co,it=g.fit_model(Q,ntaps=ntaps);Q,D,H,s,n,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE));return h,lo,hi,np.ascontiguousarray(Q),D,dt,dc,co,it,changes


def validate(X,eps,h,Q,D,dt,dc,co,it):
    db,rep,Ed,detail=rr.restricted_rank_frame(D);mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it);Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):Qd[c,t]=g._pred(Qd,c,t,ddt,ddc,dco,dit,g.SCALE)+int(Ed[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('tap Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('tap hard',me,eps))
    return {'bytes':int(mb)+int(db)+g.HEADER,'model_bytes':int(mb),'defect_bytes':int(db),'maxerr':me,'model_rep':mrep,'defect_rep':rep}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps);lc=a.logcomb_table(X.size);rows=[]
    for ntaps in TAPS:
        h,lo,hi,Q,D,dt,dc,co,it,gchg=build(X,eps,ntaps)
        Q,D,_,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES);D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE));r=validate(X,eps,h,Q,D,dt,dc,co,it)
        rec={'ntaps':ntaps,'bytes':r['bytes'],'model_bytes':r['model_bytes'],'defect_bytes':r['defect_bytes'],'generator_changes':int(gchg),'address_changes':int(achg),'gain_ar32':ar['bytes']/r['bytes'],'gain_sz3':sz/r['bytes'],'maxerr':r['maxerr']};rows.append(rec);print(json.dumps(rec),flush=True)
    rows.sort(key=lambda z:z['bytes']);best=rows[0];out={'hfac':FAC,'tap_counts':list(TAPS),'rows':rows,'best':best,'ar32':ar,'sz3':{'bytes':int(sz),'orientation':ori},'scope':'Decoder-real charged generator-capacity sweep at fixed h=1.9995epsilon. Each tap count relearns the sparse causal OMP generator, serializes every selected tap/coefficient/intercept through the existing model frame, performs legal address search, serializes the exact restricted-rank defect, independently decodes Q and checks the unchanged hard source error. More taps are accepted only if final total bytes fall after their model cost.'};json.dump(out,open('imperial_near2_tap_sweep.json','w'),indent=2);print(json.dumps({'summary':{'best_ntaps':best['ntaps'],'bytes':best['bytes'],'ar32':ar['bytes'],'sz3':int(sz),'gain_ar32':best['gain_ar32'],'gain_sz3':best['gain_sz3']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
