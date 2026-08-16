import json,sys
import h5py,numpy as np
import imperial_near2_native128 as n
import imperial_address_aware_legal_search as a
import imperial_persistent_ar32_full_array_jit as pa
import imperial_decoder_phase_automaton as m
import imperial_resonant_learned_law_address as g

C0=512
C=128
NT=30000
TB=1024
FAC=1.9995


def persistent_ar32(X,eps):
    co=g.ar.fit_shared(X[:,:TB],32);mb,cd=g.ar.model_frame(co)
    Xc=np.ascontiguousarray(X,np.float64);cf=np.ascontiguousarray(cd,np.float32)
    R,K=pa._build(Xc,cf,32,267)
    # Candidate A: one whole exact K frame.
    fw=m.encode_k(np.ascontiguousarray(K,np.int32));whole_bytes=int(fw[0])+20;Kwhole=np.asarray(fw[2],np.int32)
    Rwhole=pa._decode(Kwhole,cf,32,267)
    if not np.array_equal(Rwhole,R):raise RuntimeError('persistent whole replay')
    # Candidate B: continuous predictor state but fixed 1024-sample entropy frames.
    Ktile=np.empty_like(K);tile_bytes=0;tile_reps=[]
    for t0 in range(0,X.shape[1],TB):
        t1=min(X.shape[1],t0+TB);fr=m.encode_k(np.ascontiguousarray(K[:,t0:t1],np.int32));Ktile[:,t0:t1]=fr[2];tile_bytes+=int(fr[0])+20;tile_reps.append(fr[1])
    Rtile=pa._decode(Ktile,cf,32,267)
    if not np.array_equal(Rtile,R):raise RuntimeError('persistent tiled replay')
    if whole_bytes<=tile_bytes:
        ib=whole_bytes;method='whole';Rd=Rwhole
    else:
        ib=tile_bytes;method='tiled1024';Rd=Rtile
    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
    if me>eps*(1+5e-6):raise RuntimeError(('persistent hard',me,eps))
    # One byte selects the stronger of the two fully decodable entropy framings.
    total=int(mb)+int(ib)+32+1
    return {'bytes':total,'model_bytes':int(mb),'innovation_bytes':int(ib),'method':method,'whole_innovation_bytes':whole_bytes,'tiled_innovation_bytes':tile_bytes,'maxerr':me,'bps':8*total/X.size}


def ours_portfolio(X,eps):
    rows=[];total=0;maxerr=0.0
    lc=a.logcomb_table(C*TB)
    for t0 in range(0,29696,TB):
        B=np.ascontiguousarray(X[:,t0:t0+TB],np.float64)
        h,lo,hi,Q,D,dt,dc,co,it,gchg=n.build(B,eps)
        Q,D,_,achg=a.shape_search(Q.copy(),lo,hi,D.copy(),dt,dc,co,it,g.SCALE,lc,a.NBITS,a.PASSES)
        D=np.ascontiguousarray(g._all_defects(Q,dt,dc,co,it,g.SCALE))
        r=n.validate(B,eps,h,Q,D,dt,dc,co,it)
        rec={'t0':t0,'nt':TB,'bytes':int(r['bytes']),'model_bytes':int(r['model_bytes']),'defect_bytes':int(r['defect_bytes']),'maxerr':float(r['maxerr']),'generator_changes':int(gchg),'address_changes':int(achg)}
        rows.append(rec);total+=int(r['bytes']);maxerr=max(maxerr,float(r['maxerr']));print(json.dumps({'ours_block':rec}),flush=True)
    tail=np.ascontiguousarray(X[:,29696:30000],np.float64)
    tr=n.ar32_dyn(tail,eps)
    rec={'t0':29696,'nt':304,'bytes':int(tr['bytes']),'model_bytes':int(tr['model_bytes']),'innovation_bytes':int(tr['innovation_bytes']),'maxerr':float(tr['maxerr']),'fallback':'AR32-step267'}
    rows.append(rec);total+=int(tr['bytes']);maxerr=max(maxerr,float(tr['maxerr']));print(json.dumps({'ours_tail':rec}),flush=True)
    return {'bytes':total,'bps':8*total/X.size,'maxerr':maxerr,'blocks':rows,'native_near2_blocks':29,'fallback_blocks':1}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,C0:C0+C],np.float64).T
    if X.shape!=(C,NT):raise RuntimeError(('shape',X.shape))
    ours=ours_portfolio(X,eps)
    ar=persistent_ar32(X,eps)
    sz,ori=m.szrun(np.ascontiguousarray(X,np.float64),eps)
    out={'shape':[C,NT],'samples':int(X.size),'c0':C0,'hfac':FAC,'eps':eps,'ours':{k:v for k,v in ours.items() if k!='blocks'},'persistent_ar32':ar,'native_sz3':{'bytes':int(sz),'orientation':ori,'bps':8*int(sz)/X.size},'gain_vs_persistent_ar32':ar['bytes']/ours['bytes'],'gain_vs_native_sz3':int(sz)/ours['bytes'],'ours_blocks':ours['blocks'],'scope':'Strict full 128x30000 Imperial hard-region comparison. Ours uses 29 non-overlapping native 128x1024 near-2epsilon learned-generator/restricted-address blocks plus one exact charged AR32 fallback for the final 128x304 tail. Every near2 block independently serializes/decodes its charged model and exact address and checks hard source error. The comparator is a stronger continuous-state AR32 step267 codec fitted once from only the first 1024 samples, run without predictor resets across all 30,000 times, model charged once, with the smaller of one whole innovation frame or continuous-state 1024 entropy frames selected by a charged byte. SZ3 is rerun once natively on the complete 128x30000 object. No overlap, omitted tail, oracle bits, or reset-weakened comparator is used.'}
    json.dump(out,open('imperial_near2_fullhard_strict.json','w'),indent=2)
    print(json.dumps({'summary':{'ours':ours['bytes'],'persistent_ar32':ar['bytes'],'native_sz3':int(sz),'gain_ar32':out['gain_vs_persistent_ar32'],'gain_sz3':out['gain_vs_native_sz3'],'ours_maxerr':ours['maxerr'],'ar_maxerr':ar['maxerr']}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
