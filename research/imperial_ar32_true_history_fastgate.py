import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

REGIONS=(('hard',512),('easy',2304));C=128;NT=2048;TRAIN=1024;P=32;STEP=267;TB=1024

def oracle_k(X,co):
    a=float(co[0]);b=np.asarray(co[1:],np.float32);K=np.zeros(X.shape,np.int32);R=np.zeros(X.shape,np.int32)
    for c in range(C):
        x=np.asarray(X[c],np.float64);pred=np.zeros(NT,np.float64)
        # True-history oracle is nonrecursive, so convolution computes the exact same dot products.
        for t in range(P,NT):pred[t]=a+float(np.dot(b,x[t-P:t][::-1].astype(np.float32)))
        pi=np.rint(pred).astype(np.int32);K[c]=np.rint((x-pi)/STEP).astype(np.int32);R[c]=pi+STEP*K[c]
    return R,K

def main(path):
    h.C=C;h.NT=NT;h.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
        for name,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=h.fits(X)
            R,K=h.run_ar(X,co);rb,_,_,Kd=h.arithmetic(K);Rd=h.decode_source(Kd,co)
            if not np.array_equal(R,Rd):raise RuntimeError((name,'real decode'))
            OR,OK=oracle_k(X,co);ob,_,_,OKd=h.arithmetic(OK)
            if not np.array_equal(OK,OKd):raise RuntimeError((name,'oracle K decode'))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))));ome=float(np.max(np.abs(X-OR.astype(np.float64))))
            if me>eps*(1+1e-12) or ome>eps*(1+1e-12):raise RuntimeError((name,'hard',me,ome,eps))
            sz=0
            for t0 in range(0,NT,TB):bb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            row={'region':name,'samples':int(X.size),'real_bps':8*rb/X.size,'oracle_bps':8*ob/X.size,
                 'oracle_gain_vs_real':float(rb/ob),'sz3_bps':8*sz/X.size,'oracle_gain_vs_sz3':float(sz/ob),
                 'oracle_ratio_to_2x':float(ob/(sz/2)),'real_zero':float(np.mean(K==0)),'oracle_zero':float(np.mean(OK==0)),
                 'real_k_std':float(np.std(K)),'oracle_k_std':float(np.std(OK)),'maxerr':ome}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'eps':eps,'rows':rows,'scope':'Fast directional version of the impossible true-source-history AR32 oracle. Hard/easy 128x2048 only; exact same prefix-trained Huber AR32, step267, cold-start arithmetic, matched SZ3 and hard-error checks. Previous ORIGINAL source samples are free side information. Not a compression claim.'},open('imperial_ar32_true_history_fastgate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])