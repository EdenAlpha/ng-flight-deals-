import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
q.f.q_decode=sc.q_decode
TUNE_NT=512
W_TUNE=8
CO_DELTAS=(-64,-32,-16,-8,-4,-2,-1,1,2,4,8,16,32,64)
IT_DELTAS=(-512,-256,-128,-64,-32,-16,16,32,64,128,256,512)

def prefix_bits(Q,dts,dcs,co,intercept):
    D=g._all_defects(np.ascontiguousarray(Q[:,:TUNE_NT],np.int32),dts,dcs,co,int(intercept),g.SCALE)
    _,nb=q.encode_zsm(D,W_TUNE,TUNE_NT)
    return int(nb)

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+q.C],np.float64).T
    h,Q,D,dts,dcs,co,intercept,changes,meanlegal=q.build_full(X,eps)
    if meanlegal!=1.0 or changes!=0:raise RuntimeError(('expected fixed Q',meanlegal,changes))
    co=np.asarray(co,np.int32).copy();intercept=int(intercept)
    base_bits=prefix_bits(Q,dts,dcs,co,intercept);trace=[]
    for ps in range(2):
        improved=0
        for j in range(co.size):
            old=int(co[j]);bestv=old;best=base_bits
            for delta in CO_DELTAS:
                trial=old+int(delta);co[j]=trial;b=prefix_bits(Q,dts,dcs,co,intercept)
                if b<best:best=b;bestv=trial
            co[j]=bestv
            if best<base_bits:
                trace.append({'pass':ps,'kind':'coef','index':j,'old':old,'new':bestv,'bits_before':base_bits,'bits_after':best});base_bits=best;improved+=1
            else:co[j]=old
        old=intercept;bestv=old;best=base_bits
        for delta in IT_DELTAS:
            trial=old+int(delta);b=prefix_bits(Q,dts,dcs,co,trial)
            if b<best:best=b;bestv=trial
        if best<base_bits:
            intercept=bestv;trace.append({'pass':ps,'kind':'intercept','old':old,'new':bestv,'bits_before':base_bits,'bits_after':best});base_bits=best;improved+=1
        if improved==0:break
    D=np.ascontiguousarray(g._all_defects(Q,dts,dcs,co,intercept,g.SCALE))
    mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
    screens=[]
    for W in q.WINDOWS:
        bb,nb=q.encode_zsm(D,W,q.SCREEN);screens.append((len(bb),int(nb),int(W)))
    _,_,W=min(screens)
    bb,nbit=q.encode_zsm(D,W,q.NT);Dd=q.decode_zsm(bb,nbit,W,D.shape)
    if not np.array_equal(Dd,D):raise RuntimeError('defect decode')
    Qd=q.f.q_decode(Dd,ddt,ddc,dco,dinter,q.f.SCALE)
    if not np.array_equal(Qd,Q):raise RuntimeError('Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=int(mb)+len(bb)+q.HEADER+1;hist=2478995;sz3=2767977
    out={'shape':[q.C,q.NT],'samples':int(X.size),'eps':eps,'hfac':q.FAC,'tune_nt':TUNE_NT,'tune_window':W_TUNE,'base_prefix_bits':trace[0]['bits_before'] if trace else base_bits,'final_prefix_bits':base_bits,'tuning_steps':trace,'model_bytes':int(mb),'model_rep':mrep,'selected_window':int(W),'screen_payload_bytes':{str(w):int(n) for n,_,w in screens},'zsm_payload_bytes':len(bb),'arithmetic_bits':int(nbit),'total_bytes':total,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/total,'matched_sz3_bytes':sz3,'gain_vs_sz3':sz3/total,'maxerr':me,'coef_q12':[int(x) for x in co],'intercept_q12':int(intercept),'scope':'Rate-objective model tuning on the exact full hard Imperial block. The near-2epsilon Q field and selected causal tap coordinates from PR551 are fixed. Instead of accepting least-squares Q12 coefficients as final, the encoder performs deterministic coordinate search over the serialized coefficient/intercept integers to reduce the ACTUAL historical ZSM arithmetic bits on the first 512 time samples at W=8. Two public coordinate passes and finite delta sets are used. The tuned coefficients themselves are the only model information transmitted, through the normal charged model frame; no search path is sent. After tuning, W=4/8/64 is screened on the first 4096 times, exactly one full ZSM stream is materialized/decoded, Q is causally regenerated and the unchanged source hard error is verified. Only final physical bytes count.'}
    json.dump(out,open('imperial_near2eps_zsm_rate_tuned_model.json','w'),indent=2)
    print(json.dumps({'summary':{'prefix_bits':base_bits,'steps':len(trace),'W':W,'bytes':total,'historical':hist,'gain_historical':hist/total,'sz3':sz3,'gain_sz3':sz3/total,'maxerr':me}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
