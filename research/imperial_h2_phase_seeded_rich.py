import json,sys
import h5py,numpy as np
import imperial_compact_nova_container as x
import imperial_causal_aware_rich_compact as rc
import imperial_h2_rich_causal_headtohead as h2

NPHASE=16
HFAC=2.0
VERSION=11


def build_phase(X,eps,idx):
    h=float(HFAC*eps);phase=h*float(idx)/NPHASE
    Q=np.rint((X-phase)/h).astype(np.int32)
    R=Q.astype(np.float64)*h+phase
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('phase hard precheck',idx,me,eps))
    dts,dcs,co,intercept=x.g.fit_model(Q)
    D=x.g._all_defects(np.ascontiguousarray(Q),dts,dcs,co,intercept,x.g.SCALE)
    return h,phase,Q,D,dts,dcs,co,intercept,me


def materialize(X,eps,idx):
    h,phase,Q,D,dts,dcs,co,intercept,pre=build_phase(X,eps,idx)
    model,_,_,_,_,md=x.compact_model(dts,dcs,co,intercept);field,fd=rc.compact_rich_defect(D)
    # One header byte is physically charged for the public 4-bit phase selector + codec version family.
    header=bytes([idx & 15]);stream=header+model+field
    pos=0;idx2=int(stream[pos]&15);pos+=1
    if idx2!=idx:raise RuntimeError('phase selector')
    phase2=h*float(idx2)/NPHASE
    rank=int.from_bytes(stream[pos:pos+x.SET_BYTES],'little');pos+=x.SET_BYTES;ids=x.unrank_combination(rank,x.NGRAM,x.K);co2=[]
    for _ in range(x.K):v,pos=x.get_svar(stream,pos);co2.append(v)
    inter2,pos=x.get_svar(stream,pos);dts2=np.asarray([x.OFFS[i][0] for i in ids],np.int16);dcs2=np.asarray([x.OFFS[i][1] for i in ids],np.int16);co2=np.asarray(co2,np.int32)
    DD,pos=rc.decode_compact_rich(stream,pos,Q.shape)
    if pos!=len(stream) or not np.array_equal(DD,D):raise RuntimeError(('phase field replay',idx))
    Qd=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for c0 in range(Q.shape[0]):Qd[c0,t]=x.g._pred(Qd,c0,t,dts2,dcs2,co2,int(inter2),x.g.SCALE)+int(DD[c0,t])
    if not np.array_equal(Qd,Q):raise RuntimeError(('phase Q replay',idx))
    me=float(np.max(np.abs(X-(Qd.astype(np.float64)*h+phase2))))
    if me>eps*(1+5e-6):raise RuntimeError(('phase final hard',idx,me,eps))
    return {'phase_index':idx,'phase_fraction':idx/NPHASE,'phase':phase,'bytes':len(stream),'model_bytes':len(model),'field_bytes':len(field),'header_bytes':1,'maxerr':me,'precheck_maxerr':pre,'model_detail':md,'field_detail':fd}


def main(path):
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=x.m.stats(ds);eps=.1*std;X=np.asarray(ds[x.g.T0:x.g.T0+x.g.T,x.g.C0:x.g.C0+x.g.C],np.float64).T
    szb,ori=x.m.szrun(X,eps);ar32,_=h2.encode_ar32(X,eps)
    rows=[]
    for idx in range(NPHASE):
        r=materialize(X,eps,idx);r['delta_vs_ar32']=r['bytes']-ar32['bytes'];r['gain_vs_ar32']=ar32['bytes']/r['bytes'];r['gain_vs_sz3']=szb/r['bytes'];rows.append(r);print(json.dumps({k:v for k,v in r.items() if k not in ('model_detail','field_detail')},indent=2),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'region':'hard','shape':[x.g.C,x.g.T],'global_std':std,'eps':eps,'h_factor':HFAC,'n_public_phases':NPHASE,'sz3':{'bytes':int(szb),'orientation':ori},'ar32_rich':ar32,'rows':rows,'best':best,'scope':'Exact Session-Seeded-GPS-style shared-coordinate search. The public reconstruction family is h=2epsilon with 16 equally spaced global lattice phases. For each public phase, the nearest lattice state is deterministic and satisfies the unchanged hard error; there is no per-sample hidden legal choice. Encoder computes all 16 candidates, fits/charges the same learned sparse generator, and physically encodes the defect with the same rich causal coder given to AR32. The selected phase index occupies a real one-byte stream header. Decoder reads the selector, reconstructs the exact phase, model, defect and Q, then verifies the source error. All 16 actual stream sizes are materialized; only the smallest real stream wins.'}
    json.dump(out,open('imperial_h2_phase_seeded_rich.json','w'),indent=2)
    print(json.dumps({'summary':{'best_phase':best['phase_index'],'best_fraction':best['phase_fraction'],'NOVA':best['bytes'],'AR32':ar32['bytes'],'delta':best['delta_vs_ar32'],'gain_ar32':best['gain_vs_ar32'],'SZ3':int(szb),'model':best['model_bytes'],'field':best['field_bytes'],'maxerr':best['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
