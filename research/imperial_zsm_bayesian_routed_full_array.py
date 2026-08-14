import glob,json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_zsm_stack as z
import imperial_ar32_bayesian_context_mixer as m

C=128;NT=30000;NCB=54;BLOCKS_PER_SLOT=6;SCREEN=4096;WINDOWS=(4,8,64)
AUDITED_ZSM_BYTES=67818390
AUDITED_SZ3_BYTES=80604844
TOTAL_SAMPLES=207360000


def zsm_encode(K,W,nt):
    old=z.NT;z.NT=nt
    try:return z.encode_zsm(K[:,:nt],W)
    finally:z.NT=old


def zsm_decode(bb,nbit,W):
    old=z.NT;z.NT=NT
    try:return z.decode_zsm(bb,nbit,W)
    finally:z.NT=old


def mixer_encode(K,W,nt):
    oldnt,oldw=m.NT,m.W;m.NT=nt;m.W=W
    try:return m.arithmetic_mix(K[:,:nt])
    finally:m.NT,m.W=oldnt,oldw


def main(path,slot):
    slot=int(slot);lo=slot*BLOCKS_PER_SLOT;hi=min(NCB,lo+BLOCKS_PER_SLOT)
    a.C=C;a.NT=NT;z.C=C;z.NT=NT;m.C=C;m.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        rows=[]
        for cb in range(lo,hi):
            c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T;_,co=a.fits(X);R,K=a.run_ar(X,co)

            zscreen=[]
            for W in WINDOWS:
                bb,_=zsm_encode(K,W,SCREEN);zscreen.append((len(bb),W))
            _,zw=min(zscreen)
            zbb,zbits=zsm_encode(K,zw,NT);Kz=zsm_decode(zbb,zbits,zw)
            if not np.array_equal(Kz,K):raise RuntimeError((cb,'zsm K',zw))
            Rz=a.decode_source(Kz,co)
            if not np.array_equal(Rz,R):raise RuntimeError((cb,'zsm source',zw))
            zme=float(np.max(np.abs(X-Rz.astype(np.float64))))
            if zme>eps*(1+1e-12):raise RuntimeError((cb,'zsm hard',zme,eps))
            # Same conservative framing convention as PR482: includes a byte for the ZSM-window selector.
            zn=len(zbb)+a.MODEL_BYTES+33

            mscreen=[]
            for W in WINDOWS:
                n,_,_,Kd,_=mixer_encode(K,W,SCREEN)
                if not np.array_equal(Kd,K[:,:SCREEN]):raise RuntimeError((cb,'mixer screen K',W))
                mscreen.append((int(n),W))
            _,mw=min(mscreen)
            mn,mbits,mnb,Km,_=mixer_encode(K,mw,NT)
            if not np.array_equal(Km,K):raise RuntimeError((cb,'mixer K',mw))
            Rm=a.decode_source(Km,co)
            if not np.array_equal(Rm,R):raise RuntimeError((cb,'mixer source',mw))
            mme=float(np.max(np.abs(X-Rm.astype(np.float64))))
            if mme>eps*(1+1e-12):raise RuntimeError((cb,'mixer hard',mme,eps))
            # arithmetic_mix already charges the common model/framing. Add one byte for its selected W.
            mn=int(mn)+1

            # Encoder actually creates both exact candidate streams and transmits the smaller one.
            # Charge one additional byte for the backend selector (ZSM vs Bayesian mixer).
            if zn<=mn:chosen='zsm';payload=zn
            else:chosen='bayesian';payload=mn
            routed=payload+1
            row={'cb':cb,'c0':c0,'samples':int(X.size),'backend':chosen,'routed_bytes':int(routed),'routed_bps':8*routed/X.size,
                 'zsm_bytes':int(zn),'zsm_bps':8*zn/X.size,'zsm_window':int(zw),'zsm_screen_bytes':{str(w):int(v) for v,w in zscreen},
                 'bayesian_bytes':int(mn),'bayesian_bps':8*mn/X.size,'bayesian_window':int(mw),'bayesian_screen_bytes':{str(w):int(v) for v,w in mscreen},
                 'backend_saving_bytes':int(abs(zn-mn)),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),
                 'zsm_arithmetic_bits':int(zbits),'bayesian_arithmetic_bits':int(mbits),'bayesian_symbol_bits':int(mnb),'maxerr':max(zme,mme)}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        samples=sum(r['samples'] for r in rows);routed=sum(r['routed_bytes'] for r in rows);zs=sum(r['zsm_bytes'] for r in rows);bs=sum(r['bayesian_bytes'] for r in rows)
        out={'slot':slot,'blocks':[lo,hi],'samples':samples,'global_std':float(gstd),'eps':float(eps),'routed_bytes':int(routed),'routed_bps':8*routed/samples,
             'zsm_bytes':int(zs),'bayesian_bytes':int(bs),'backend_counts':{q:sum(r['backend']==q for r in rows) for q in ('zsm','bayesian')},
             'zsm_window_counts':{str(w):sum(r['zsm_window']==w for r in rows) for w in WINDOWS},'bayesian_window_counts':{str(w):sum(r['bayesian_window']==w for r in rows) for w in WINDOWS},
             'rows':rows,'scope':'One ninth of a fully deployable entropy-language router on unchanged Huber AR32 reconstruction. For every 128x30000 block the encoder screens ZSM W=4/8/64 and Bayesian-mixer W=4/8/64 only on the first 4096 exact innovations, performs one exact full encode/decode for each selected backend, then transmits the smaller full stream. A conservative byte is charged for each backend internal window selector and another byte for the final ZSM-vs-Bayesian selector. Both K streams are exactly decoded, the complete AR32 source is replayed, and the unchanged max-error contract is verified. No oracle probability, target-trained model, future samples, or AI.'}
        json.dump(out,open(f'imperial_zsm_bayesian_routed_full_{slot}.json','w'),indent=2)
        print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)


def aggregate():
    rows=[]
    for p in sorted(glob.glob('imperial_zsm_bayesian_routed_full_[0-9].json')):rows.extend(json.load(open(p))['rows'])
    rows=sorted(rows,key=lambda r:r['cb'])
    if len(rows)!=NCB:raise RuntimeError(('blocks',len(rows)))
    samples=sum(r['samples'] for r in rows);rt=sum(r['routed_bytes'] for r in rows);zs=sum(r['zsm_bytes'] for r in rows);bs=sum(r['bayesian_bytes'] for r in rows)
    out={'blocks':len(rows),'samples':samples,'routed_bytes':int(rt),'routed_bps':8*rt/samples,'zsm_candidate_bytes':int(zs),'bayesian_candidate_bytes':int(bs),
         'audited_zsm_bytes':AUDITED_ZSM_BYTES,'audited_zsm_bps':8*AUDITED_ZSM_BYTES/TOTAL_SAMPLES,'audited_sz3_bytes':AUDITED_SZ3_BYTES,'audited_sz3_bps':8*AUDITED_SZ3_BYTES/TOTAL_SAMPLES,
         'bytes_saved_vs_audited_zsm':int(AUDITED_ZSM_BYTES-rt),'gain_vs_audited_zsm':AUDITED_ZSM_BYTES/rt,'gain_vs_sz3':AUDITED_SZ3_BYTES/rt,
         'strict_2x_target_bytes':AUDITED_SZ3_BYTES/2.0,'bytes_above_2x_target':rt-AUDITED_SZ3_BYTES/2.0,'fraction_reduction_still_needed':1-(AUDITED_SZ3_BYTES/2.0)/rt,
         'backend_counts':{q:sum(r['backend']==q for r in rows) for q in ('zsm','bayesian')},
         'zsm_window_counts':{str(w):sum(r['zsm_window']==w for r in rows) for w in WINDOWS},'bayesian_window_counts':{str(w):sum(r['bayesian_window']==w for r in rows) for w in WINDOWS},'rows':rows}
    json.dump(out,open('imperial_zsm_bayesian_routed_full_aggregate.json','w'),indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='aggregate':aggregate()
    else:main(sys.argv[1],sys.argv[2])
