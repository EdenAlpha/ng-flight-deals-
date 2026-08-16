import json,sys,math
import h5py,numpy as np
import imperial_exact2_fair_rich_ar32 as e

NPHASE=64
VERSION=6


def legal_phase(X,eps,h,phase):
    b=eps*(1-2e-12)
    lo=np.ceil((X-b-phase)/h).astype(np.int32)
    hi=np.floor((X+b-phase)/h).astype(np.int32)
    return lo,hi


def build_phase(X,eps,h,phase):
    lo,hi=legal_phase(X,eps,h,phase)
    if np.any(lo>hi):return None
    Q=e.x.g._initial(lo,hi,0);pchg=0
    for _ in range(e.x.g.ROUNDS):
        dts,dcs,co,intercept=e.x.g.fit_model(Q)
        Q,D,H,score,nz,ch=e.x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,e.x.g.SCALE,False,e.x.g.PASSES);pchg+=int(ch)
    dts,dcs,co,intercept=e.x.g.fit_model(Q)
    Q,D,H,score,nz,ch=e.x.g._optimize_from(Q,lo,hi,dts,dcs,co,intercept,e.x.g.SCALE,False,e.x.g.PASSES);pchg+=int(ch)
    D=np.ascontiguousarray(e.x.g._all_defects(Q,dts,dcs,co,intercept,e.x.g.SCALE))
    lf=np.zeros(X.size+2,np.float64)
    for i in range(2,lf.size):lf[i]=lf[i-1]+math.log2(i)
    w=np.ones(e.q.NBITS,np.float64)
    Q,D,cnt,cchg,sc=e.q.causal_search(np.ascontiguousarray(Q),lo,hi,D,dts,dcs,co,intercept,e.x.g.SCALE,e.q.MODES,lf,w,e.q.PASSES)
    Dr=e.x.g._all_defects(Q,dts,dcs,co,intercept,e.x.g.SCALE)
    if not np.array_equal(Dr,D):raise RuntimeError('phase defect mismatch')
    return lo,hi,np.ascontiguousarray(Q),np.ascontiguousarray(D),dts,dcs,co,intercept,pchg,int(cchg),float(sc)


def materialize(X,eps,h,phase_index,phase,Q,D,dts,dcs,co,intercept):
    model,_,_,_,_,md=e.x.compact_model(dts,dcs,co,intercept);defect,dd=e.x.compact_defect(D)
    stream=bytes([VERSION,int(phase_index)])+model+defect
    pos=0
    if stream[pos]!=VERSION:raise RuntimeError('version')
    pos+=1;pid=int(stream[pos]);pos+=1
    if pid!=phase_index or pid>=NPHASE:raise RuntimeError('phase selector')
    dts2,dcs2,co2,inter2,pos=e.decode_model(stream,pos)
    DD,pos=e.x.decode_compact_defect(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError('phase compact parse')
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c in range(Q.shape[0]):Qd[c,t]=e.x.g._pred(Qd,c,t,dts2,dcs2,co2,inter2,e.x.g.SCALE)+int(DD[c,t])
    if not np.array_equal(Qd,Q):raise RuntimeError('phase Q replay')
    phase2=(pid/NPHASE)*h;R=phase2+Qd.astype(np.float64)*h;me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('phase hard',pid,me,eps))
    return {'bytes':len(stream),'model_bytes':len(model),'defect_bytes':len(defect),'header_bytes':2,'maxerr':me,'model_detail':md,'defect_detail':dd}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=e.x.m.stats(ds);eps=.1*std;X=np.asarray(ds[e.x.g.T0:e.x.g.T0+e.x.g.T,e.x.g.C0:e.x.g.C0+e.x.g.C],np.float64).T
    h=2.0*eps;szb,ori=e.x.m.szrun(X,eps);ar=e.rich_ar32(X,eps);rows=[];invalid=[]
    for j in range(NPHASE):
        phase=(j/NPHASE)*h;b=build_phase(X,eps,h,phase)
        if b is None:
            invalid.append(j);continue
        lo,hi,Q,D,dts,dcs,co,intercept,pchg,cchg,score=b;r=materialize(X,eps,h,j,phase,Q,D,dts,dcs,co,intercept)
        r.update({'phase_index':j,'phase_fraction':j/NPHASE,'phase':phase,'mean_legal_states':float(np.mean(hi.astype(np.int64)-lo.astype(np.int64)+1)),'projection_changes':pchg,'causal_changes':cchg,'causal_surrogate_bits':score,'delta_vs_rich_ar32':r['bytes']-ar['bytes'],'gain_vs_rich_ar32':ar['bytes']/r['bytes'],'gain_vs_sz3':szb/r['bytes']});rows.append(r)
        print(json.dumps({k:v for k,v in r.items() if k not in ('model_detail','defect_detail')},sort_keys=True),flush=True)
    if not rows:raise RuntimeError('no valid phases')
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[e.x.g.C,e.x.g.T],'global_std':std,'eps':eps,'h':h,'phase_count':NPHASE,'invalid_phases':invalid,'rich_causal_ar32':ar,'sz3':{'bytes':int(szb),'orientation':ori},'rows':rows,'best':best,'scope':'Decoder-real exact-2epsilon lattice phase search. The reconstruction spacing is fixed at h=2*epsilon. Encoder searches 64 public phase offsets j*h/64; one literal byte transmits the selected phase ID. For every valid phase the sparse causal generator is independently fit and fully charged, the exact compact causal defect stream is materialized, parsed to EOF, Q is causally replayed, and reconstruction phase+hQ is checked against the unchanged source hard-error bound. Rich-causal AR32 is rebuilt in the same process as the strongest comparator. This is a pure shared-coordinate search: no target-derived phase model or search path is transmitted.'}
    json.dump(out,open('imperial_exact2_phase_causal.json','w'),indent=2)
    print(json.dumps({'summary':{'best_phase':best['phase_index'],'phase_fraction':best['phase_fraction'],'bytes':best['bytes'],'rich_ar32':ar['bytes'],'sz3':int(szb),'delta_vs_rich_ar32':best['delta_vs_rich_ar32'],'gain_vs_rich_ar32':best['gain_vs_rich_ar32'],'gain_vs_sz3':best['gain_vs_sz3'],'invalid_phases':invalid}},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
