import json,sys,struct
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_universe_shaping as u
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FACS=(1.75,1.85,1.90,1.95,1.975,1.99)
NPHASE=32
TOP_REFINE=6
PHASE_SELECTOR_BYTES=2


def build_at(X,eps,fac,pj):
    h=float(eps*fac);phi=float(h*pj/NPHASE);Xs=X-phi
    lo,hi=g.legal_q(Xs,eps,h);Q=g._initial(lo,hi,0);changes=0
    for _ in range(g.ROUNDS):
        dts,dcs,co,intercept=g.fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    dts,dcs,co,intercept=g.fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    return {'fac':float(fac),'phase_index':int(pj),'phi':phi,'h':h,'Xs':Xs,'lo':lo,'hi':hi,'Q':Q,'D':D,'dts':dts,'dcs':dcs,'co':co,'intercept':int(intercept),'projection_changes':int(changes),'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1))}


def materialize(z,X,eps,label,szb,arb):
    rb,rep,RD,detail=rr.restricted_rank_frame(z['D'])
    r=c.validate(z['Xs'],eps,z['h'],z['Q'],RD,z['dts'],z['dcs'],z['co'],z['intercept'],rb,label,detail)
    r['bytes']+=PHASE_SELECTOR_BYTES;r['defect_bytes']+=PHASE_SELECTOR_BYTES;r['bps']=8*r['bytes']/X.size
    R=z['Q'].astype(np.float64)*z['h']+z['phi'];me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('phase hard',z['fac'],z['phase_index'],me,eps))
    r.update({'maxerr':me,'fac':z['fac'],'phase_index':z['phase_index'],'phi':z['phi'],'mean_legal':z['mean_legal'],'gain_vs_sz3':szb/r['bytes'],'gain_vs_ar32':arb['bytes']/r['bytes']})
    return r


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);screen=[];objs=[]
    for fac in FACS:
        for pj in range(NPHASE):
            z=build_at(X,eps,fac,pj);r=materialize(z,X,eps,f'phase_{fac}_{pj}',szb,arb);screen.append(r);objs.append((r['bytes'],z));print(json.dumps({k:v for k,v in r.items() if k!='detail'}),flush=True)
    objs.sort(key=lambda x:x[0]);refined=[];logc=a.logcomb_table(X.size);lf=np.zeros(X.size+1,np.float64);lf[1:]=np.cumsum(np.log(np.arange(1,X.size+1,dtype=np.float64)))
    for _,z0 in objs[:TOP_REFINE]:
        z={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in z0.items()}
        Q=np.ascontiguousarray(z['Q'].copy());D=np.ascontiguousarray(z['D'].copy())
        Q,D,bc,bch=a.shape_search(Q,z['lo'],z['hi'],D,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE,logc,a.NBITS,a.PASSES)
        if not np.array_equal(g._all_defects(Q,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE),D):raise RuntimeError('bit defect replay')
        z['Q']=Q;z['D']=D;r=materialize(z,X,eps,f'phase_bit_{z["fac"]}_{z["phase_index"]}',szb,arb);r.update({'phase':'bitshape','search_changes':int(bch)});refined.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'}),flush=True)
        Q,D,hh,hch=u.shape_hist(Q,z['lo'],z['hi'],D,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE,lf,u.PASSES)
        if not np.array_equal(g._all_defects(Q,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE),D):raise RuntimeError('hist defect replay')
        z['Q']=Q;z['D']=D;r=materialize(z,X,eps,f'phase_hist_{z["fac"]}_{z["phase_index"]}',szb,arb);r.update({'phase':'histshape','search_changes':int(hch),'distinct':int(np.count_nonzero(hh))});refined.append(r);print(json.dumps({k:v for k,v in r.items() if k!='detail'}),flush=True)
    allrows=screen+refined;best=min(allrows,key=lambda r:r['bytes'])
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'factors':list(FACS),'nphase':NPHASE,'selector_bytes':PHASE_SELECTOR_BYTES,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'screen':screen,'refined':refined,'best':best,'scope':'Decoder-real global lattice-origin search. Previous learned-law reconstruction always used R=h*Q with phase zero. For each public h/epsilon and one of 32 public phase indices, this gate uses R=h*Q+phi, derives exact hard-error legal Q intervals from X-phi, relearns the same fully charged sparse causal generator, globally projects the legal reconstruction, and exact-rank materializes the defect. The phase/factor selector is explicitly charged. The decoder-replay contract is checked both in shifted coordinates and independently in source coordinates after adding phi. The six strongest phase/factor states are further refined by the successful bit-address and whole-symbol universe searches. No epsilon relaxation or ideal bytes are used.'}
    json.dump(out,open('imperial_lattice_phase_search.json','w'),indent=2)
    print(json.dumps({'summary':{'bytes':best['bytes'],'fac':best['fac'],'phase_index':best['phase_index'],'phi':best['phi'],'rep':best['rep'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
