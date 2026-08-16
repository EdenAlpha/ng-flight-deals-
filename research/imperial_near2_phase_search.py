import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_restricted_rank_address as rr
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FAC=1.9995
NPHASE=16


def legal_phase(X,eps,h,phase):
    b=eps*(1-2e-12)
    lo=np.ceil((X-b-phase)/h).astype(np.int32)
    hi=np.floor((X+b-phase)/h).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError(('empty legal phase',phase))
    return lo,hi


def build(X,eps,h,phase):
    lo,hi=legal_phase(X,eps,h,phase);Q=g._initial(lo,hi,0);changes=0
    for _ in range(g.ROUNDS):
        dt,dc,co,it=g.fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    dt,dc,co,it=g.fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dt,dc,co,it,g.SCALE,False,g.PASSES);changes+=int(ch)
    D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
    return lo,hi,np.ascontiguousarray(Q),D,dt,dc,co,it,changes


def validate(X,eps,h,phase,Q,D,dt,dc,co,it):
    db,rep,Ed,detail=rr.restricted_rank_frame(D)
    mb,mrep,ddt,ddc,dco,dit=g.model_frame(dt,dc,co,it)
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):Qd[c,t]=g._pred(Qd,c,t,ddt,ddc,dco,dit,g.SCALE)+int(Ed[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('phase Q replay')
    R=phase+Qd.astype(np.float64)*h
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('phase hard',me,eps))
    # 1 byte is a real selector among the fixed public 16-phase grid.
    total=int(mb)+int(db)+g.HEADER+1
    return {'bytes':total,'model_bytes':int(mb),'defect_bytes':int(db),'maxerr':me,'rep':rep,'model_rep':mrep,'detail':detail}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    sz,ori=m.szrun(X,eps);ar=g.ar32_baseline(X,eps);h=float(eps*FAC);lc=a.logcomb_table(X.size);rows=[]
    for j in range(NPHASE):
        phase=h*j/NPHASE
        lo,hi,Q,D,dt,dc,co,it,gchg=build(X,eps,h,phase)
        Q,D,_,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES)
        D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
        r=validate(X,eps,h,phase,Q,D,dt,dc,co,it)
        rec={'phase_index':j,'phase_fraction':j/NPHASE,'bytes':r['bytes'],'model_bytes':r['model_bytes'],'defect_bytes':r['defect_bytes'],'maxerr':r['maxerr'],'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'generator_changes':int(gchg),'address_changes':int(achg),'gain_ar32':ar['bytes']/r['bytes'],'gain_sz3':sz/r['bytes']}
        rows.append(rec);print(json.dumps(rec),flush=True)
    rows.sort(key=lambda z:z['bytes']);best=rows[0]
    out={'hfac':FAC,'nphase':NPHASE,'eps':eps,'rows':rows,'best':best,'ar32':ar,'sz3':{'bytes':int(sz),'orientation':ori},'scope':'Decoder-real NOVA coordinate-phase search. Spacing is fixed public h=1.9995epsilon; a one-byte selector chooses one of 16 public phase offsets j*h/16. Each phase constructs the exact hard-error legal integer Q lattice, relearns and fully charges the sparse causal generator, performs legal address search, physically serializes the exact restricted-rank defect, independently decodes Q, and reconstructs R=phase+hQ under the unchanged source-domain hard error. The selector byte is included in every reported stream. No phase value or search trajectory is free.'};json.dump(out,open('imperial_near2_phase_search.json','w'),indent=2)
    print(json.dumps({'summary':{'best_phase_index':best['phase_index'],'bytes':best['bytes'],'ar32':ar['bytes'],'sz3':int(sz),'gain_ar32':best['gain_ar32'],'gain_sz3':best['gain_sz3']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
