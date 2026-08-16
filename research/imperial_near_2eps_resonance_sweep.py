import json,sys
import h5py,numpy as np
import imperial_address_aware_legal_search as a
import imperial_defect_universe_shaping as u
import imperial_defect_restricted_rank_address as rr
import imperial_defect_contour_address as c
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

FACS=(1.55,1.60,1.65,1.70,1.75,1.80,1.85,1.90,1.95,1.975,1.99)
INITS=(0,1)
TOP_REFINE=4


def build_at(X,eps,fac,init):
    h=float(eps*fac);lo,hi=g.legal_q(X,eps,h);Q=g._initial(lo,hi,init);changes=0
    for _ in range(g.ROUNDS):
        dts,dcs,co,intercept=g.fit_model(Q)
        Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    dts,dcs,co,intercept=g.fit_model(Q)
    Q,D,H,score,nz,ch=g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,g.SCALE,False,g.PASSES);changes+=int(ch)
    return {'fac':float(fac),'init':int(init),'h':h,'lo':lo,'hi':hi,'Q':Q,'D':D,'dts':dts,'dcs':dcs,'co':co,'intercept':int(intercept),'changes':changes,'mean_legal':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'max_legal':int(np.max(hi-lo+1)),'defect_std':float(D.std()),'defect_zero':float(np.mean(D==0))}


def rank_materialize(X,eps,z,label):
    rb,rep,RD,detail=rr.restricted_rank_frame(z['D'])
    r=c.validate(X,eps,z['h'],z['Q'],RD,z['dts'],z['dcs'],z['co'],z['intercept'],rb,label,detail)
    r.update({'fac':z['fac'],'init':z['init'],'mean_legal':z['mean_legal'],'max_legal':z['max_legal'],'defect_std_source':z['defect_std'],'defect_zero_source':z['defect_zero']})
    return r


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);arb=g.ar32_baseline(X,eps);screen=[];objs=[]
    for fac in FACS:
        for init in INITS:
            z=build_at(X,eps,fac,init);r=rank_materialize(X,eps,z,f'screen_{fac}_{init}');r['gain_vs_sz3']=szb/r['bytes'];r['gain_vs_ar32']=arb['bytes']/r['bytes'];screen.append(r);objs.append((r['bytes'],z));print(json.dumps({k:v for k,v in r.items() if k!='detail'},indent=2),flush=True)
    objs.sort(key=lambda x:x[0]);refined=[];lf=np.zeros(X.size+1,np.float64);lf[1:]=np.cumsum(np.log(np.arange(1,X.size+1,dtype=np.float64)));logc=a.logcomb_table(X.size)
    used=set()
    for _,z0 in objs:
        key=(z0['fac'],z0['init'])
        if key in used:continue
        used.add(key)
        if len(refined)>=TOP_REFINE:break
        z={k:(v.copy() if isinstance(v,np.ndarray) else v) for k,v in z0.items()}
        Q=np.ascontiguousarray(z['Q'].copy());D=np.ascontiguousarray(z['D'].copy())
        Q,D,bc,bch=a.shape_search(Q,z['lo'],z['hi'],D,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE,logc,a.NBITS,a.PASSES)
        Dr=g._all_defects(Q,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('bit defect',key))
        z['Q']=Q;z['D']=D;z['defect_std']=float(D.std());z['defect_zero']=float(np.mean(D==0));rbit=rank_materialize(X,eps,z,f'bitshape_{z["fac"]}_{z["init"]}');rbit.update({'phase':'bitshape','changes':int(bch),'gain_vs_sz3':szb/rbit['bytes'],'gain_vs_ar32':arb['bytes']/rbit['bytes']});refined.append(rbit);print(json.dumps({k:v for k,v in rbit.items() if k!='detail'},indent=2),flush=True)
        Q,D,hh,hch=u.shape_hist(Q,z['lo'],z['hi'],D,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE,lf,u.PASSES)
        Dr=g._all_defects(Q,z['dts'],z['dcs'],z['co'],z['intercept'],g.SCALE)
        if not np.array_equal(Dr,D):raise RuntimeError(('hist defect',key))
        z['Q']=Q;z['D']=D;z['defect_std']=float(D.std());z['defect_zero']=float(np.mean(D==0));rh=rank_materialize(X,eps,z,f'histshape_{z["fac"]}_{z["init"]}');rh.update({'phase':'histshape','changes':int(hch),'distinct':int(np.count_nonzero(hh)),'gain_vs_sz3':szb/rh['bytes'],'gain_vs_ar32':arb['bytes']/rh['bytes']});refined.append(rh);print(json.dumps({k:v for k,v in rh.items() if k!='detail'},indent=2),flush=True)
    allrows=screen+refined;best=min(allrows,key=lambda r:r['bytes'])
    out={'region':'hard','shape':[g.C,g.T],'global_std':std,'eps':eps,'factors':list(FACS),'inits':list(INITS),'top_refine':TOP_REFINE,'sz3':{'bytes':int(szb),'orientation':ori},'ar32':arb,'screen':screen,'refined':refined,'best':best,'scope':'Corrective near-2epsilon lattice sweep. Earlier learned-law work stopped at h=1.5epsilon despite monotonically improving bytes, while the unchanged hard-error interval has width 2epsilon and AR32 itself uses step267 approximately 2epsilon. This gate tests h/epsilon from 1.55 through 1.99, two legal initializations, with the same fully charged learned sparse generator/projection and exact restricted-rank materialization. The four strongest screened states are then refined using the two demonstrated encoder-only legal-state mechanisms: exact bit-address shaping and whole-symbol multinomial-universe shaping. Every final candidate physically serializes/decodes the defect stream, regenerates exact Q from the charged model, and verifies the unchanged source-domain hard error. No surrogate bytes count.'}
    json.dump(out,open('imperial_near_2eps_resonance_sweep.json','w'),indent=2)
    print(json.dumps({'summary':{'best_bytes':best['bytes'],'best_rep':best['rep'],'fac':best['fac'],'init':best['init'],'ar32':arb['bytes'],'sz3':int(szb),'gain_ar32':arb['bytes']/best['bytes'],'gain_sz3':szb/best['bytes']}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
