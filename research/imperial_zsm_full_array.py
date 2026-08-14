import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_zero_sign_magnitude_arithmetic as z

C=128;NT=30000;NCB=54;BLOCKS_PER_SLOT=6;SCREEN=4096;WINDOWS=(4,8,64)
AUDITED_ACTIVITY_BYTES=68076409
AUDITED_SZ3_BYTES=80604844
TOTAL_SAMPLES=207360000


def encode_for_nt(K,W,nt):
    old=z.NT;z.NT=nt
    try:bb,nbit=z.encode_zsm(K[:,:nt],W)
    finally:z.NT=old
    return bb,nbit


def decode_full(bb,nbit,W):
    old=z.NT;z.NT=NT
    try:Kd=z.decode_zsm(bb,nbit,W,(C,NT))
    finally:z.NT=old
    return Kd


def main(path,slot):
    slot=int(slot);lo=slot*BLOCKS_PER_SLOT;hi=min(NCB,lo+BLOCKS_PER_SLOT)
    a.C=C;a.NT=NT;z.C=C;z.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        rows=[];total=0
        for cb in range(lo,hi):
            c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T;_,co=a.fits(X);R,K=a.run_ar(X,co)
            screen=[]
            for W in WINDOWS:
                bb,_=encode_for_nt(K,W,SCREEN);screen.append((len(bb),W))
            _,W=min(screen)
            bb,nbit=encode_for_nt(K,W,NT);Kd=decode_full(bb,nbit,W)
            if not np.array_equal(Kd,K):raise RuntimeError((cb,'K decode',W))
            Rd=a.decode_source(Kd,co)
            if not np.array_equal(Rd,R):raise RuntimeError((cb,'source replay',W))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((cb,'hard',me,eps))
            n=len(bb)+a.MODEL_BYTES+33;total+=n
            row={'cb':cb,'c0':c0,'samples':int(X.size),'zsm_bytes':int(n),'zsm_bps':8*n/X.size,'selected_window':int(W),
                 'screen_payload_bytes':{str(w):int(v) for v,w in screen},'k_zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),
                 'arithmetic_bits':int(nbit),'maxerr':me}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        samples=sum(r['samples'] for r in rows)
        out={'slot':slot,'blocks':[lo,hi],'samples':samples,'global_std':float(gstd),'eps':float(eps),'zsm_bytes':int(total),'zsm_bps':8*total/samples,
             'window_counts':{str(w):sum(r['selected_window']==w for r in rows) for w in WINDOWS},'rows':rows,
             'scope':'One ninth of the complete Imperial array promoting the exact zero/sign/Elias-gamma magnitude entropy language from PR474 without changing Huber AR32 step267 reconstruction. For each 128x30000 block the encoder screens W=4/8/64 using only the first 4096 exact K symbols, transmits one selector byte (included in the same +33 model/framing convention as PR474), then performs one full-block ZSM arithmetic encode/decode at the selected W. Exact K decode, complete AR32 source replay and unchanged max-error validation are mandatory. Aggregate comparison is against the already-audited PR444 activity6 full-array bytes and matched full-array SZ3 bytes. No AI. Draft/do not merge.'}
        json.dump(out,open(f'imperial_zsm_full_{slot}.json','w'),indent=2)
        print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)


def aggregate():
    import glob
    rows=[]
    for p in sorted(glob.glob('imperial_zsm_full_[0-9].json')):rows.extend(json.load(open(p))['rows'])
    rows=sorted(rows,key=lambda r:r['cb'])
    if len(rows)!=NCB:raise RuntimeError(('blocks',len(rows)))
    total=sum(r['zsm_bytes'] for r in rows);samples=sum(r['samples'] for r in rows)
    out={'blocks':len(rows),'samples':samples,'zsm_bytes':int(total),'zsm_bps':8*total/samples,
         'audited_activity_bytes':AUDITED_ACTIVITY_BYTES,'audited_activity_bps':8*AUDITED_ACTIVITY_BYTES/TOTAL_SAMPLES,
         'audited_sz3_bytes':AUDITED_SZ3_BYTES,'audited_sz3_bps':8*AUDITED_SZ3_BYTES/TOTAL_SAMPLES,
         'gain_zsm_vs_activity':AUDITED_ACTIVITY_BYTES/total,'gain_zsm_vs_sz3':AUDITED_SZ3_BYTES/total,
         'bytes_saved_vs_activity':AUDITED_ACTIVITY_BYTES-total,'strict_2x_target_bytes':AUDITED_SZ3_BYTES/2.0,
         'bytes_above_2x_target':total-AUDITED_SZ3_BYTES/2.0,'fraction_reduction_still_needed':1-(AUDITED_SZ3_BYTES/2.0)/total,
         'window_counts':{str(w):sum(r['selected_window']==w for r in rows) for w in WINDOWS},'rows':rows}
    json.dump(out,open('imperial_zsm_full_aggregate.json','w'),indent=2)
    print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':
    if len(sys.argv)==2 and sys.argv[1]=='aggregate':aggregate()
    else:main(sys.argv[1],sys.argv[2])
