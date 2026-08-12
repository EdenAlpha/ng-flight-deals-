import json,sys,math,hashlib
import h5py,numpy as np
import imperial_dyadic_shared_resonator as r
import imperial_decoder_phase_automaton as m

C=128;TB=1024;P=16;NCB=54

def build_continuous_k(X,coef):
    Cc,T=X.shape;R=np.zeros((Cc,T),np.int32);K=np.zeros((Cc,T),np.int32)
    for c in range(Cc):
        for t in range(T):
            pred=r.predict_hist(R,c,t,coef,P,'shared');k=int(np.rint((float(X[c,t])-pred)/m.STEP));R[c,t]=pred+m.STEP*k;K[c,t]=k
    return R,K

def decode_continuous(K,coef):
    Cc,T=K.shape;R=np.zeros((Cc,T),np.int32)
    for c in range(Cc):
        for t in range(T):R[c,t]=r.predict_hist(R,c,t,coef,P,'shared')+m.STEP*int(K[c,t])
    return R

def main(path,slot):
    slot=int(slot);lo_cb=slot*18;hi_cb=min(NCB,(slot+1)*18)
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        rows=[];model_rows=[];raw_total=ours_total=sz_total=0
        for cb in range(lo_cb,hi_cb):
            c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T;train=X[:,:TB]
            co=r.fit_shared(train,P);mb,cd=r.model_frame(co);digest=hashlib.sha256(np.asarray(cd,np.float32).tobytes()).hexdigest()
            R,K=build_continuous_k(X,cd);Kd=np.empty_like(K);innov_bytes=0;sz_bytes=0;tile_rows=[]
            for tb,t0 in enumerate(range(0,X.shape[1],TB)):
                t1=min(X.shape[1],t0+TB);kf=K[:,t0:t1];fr=m.encode_k(kf);Kd[:,t0:t1]=fr[2];ib=fr[0]+20;innov_bytes+=ib
                sb,ori=m.szrun(X[:,t0:t1],eps);sz_bytes+=sb
                tile_rows.append({'tb':tb,'t0':t0,'ns':t1-t0,'innovation_bytes':ib,'innovation_rep':fr[1],'sz3_bytes':sb,'sz3_orientation':ori,'gain_innovation_only_vs_sz3':sb/ib})
            Rd=decode_continuous(Kd,cd)
            if not np.array_equal(Rd,R):raise RuntimeError(('continuous decode',cb))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError(('hard error',cb,me,eps))
            model_charge=mb;total=innov_bytes+model_charge+32;raw=X.size*2
            raw_total+=raw;ours_total+=total;sz_total+=sz_bytes
            rr={'cb':cb,'c0':c0,'samples':X.size,'raw_bytes':raw,'model_bytes':mb,'model_sha256':digest,'innovation_bytes':innov_bytes,'total_bytes':total,'sz3_bytes':sz_bytes,'ratio':raw/total,'sz3_ratio':raw/sz_bytes,'gain_vs_sz3':sz_bytes/total,'bps':8*total/X.size,'sz3_bps':8*sz_bytes/X.size,'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'coefficients':cd.tolist(),'tiles':tile_rows};rows.append(rr)
            model_rows.append({'cb':cb,'c0':c0,'model_bytes':mb,'sha256':digest,'coefficients':cd.tolist()})
            print(json.dumps({k:v for k,v in rr.items() if k not in ('tiles','coefficients')},indent=2),flush=True)
        out={'slot':slot,'channel_blocks':[lo_cb,hi_cb],'global_std':std,'eps':eps,'order':P,'step':m.STEP,'continuous_state_across_time':True,'raw_bytes':raw_total,'ours_bytes':ours_total,'sz3_bytes':sz_total,'ratio':raw_total/ours_total,'sz3_ratio':raw_total/sz_total,'gain_vs_sz3':sz_total/ours_total,'bps':16*ours_total/raw_total,'sz3_bps':16*sz_total/raw_total,'min_block_gain':min(x['gain_vs_sz3'] for x in rows),'median_block_gain':float(np.median([x['gain_vs_sz3'] for x in rows])),'models':model_rows,'rows':rows,'scope':'One-third channel partition of the complete Imperial Acoustic array. One shared float32 AR16+intercept is fitted from only the first 1024 source samples of each fixed 128-channel block, serialized/decoded once, then reused without retuning across all 30,000 times. Decoder state is continuous across 1024-sample entropy frames; only k=round((X-P)/256) innovations are stored with the existing self-decoding Zstd menu. Exact K frames are byte-decoded, the entire 30k state trajectory regenerated continuously, and <=128 hard error verified. Matched SZ3 is rerun on the same 128x1024 partition. Model bytes and framing fully counted; no AI.'}
        print(json.dumps({k:v for k,v in out.items() if k not in ('models','rows')},indent=2));json.dump(out,open(f'imperial_persistent_ar16_full_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
