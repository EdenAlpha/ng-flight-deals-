import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_zsm_stack as z

C=128;NT=8192;P=32;TB=1024;WINDOWS=(4,8,64);REGIONS=(('hard',512),('easy',2304))


def run_projection(X,co,eps):
    R=np.zeros(X.shape,np.int32);D=np.zeros(X.shape,np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    lo=np.ceil(X-eps).astype(np.int64);hi=np.floor(X+eps).astype(np.int64)
    for c in range(C):
        for t in range(NT):
            p=0 if t<P else int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            if p<int(lo[c,t]):r=int(lo[c,t])
            elif p>int(hi[c,t]):r=int(hi[c,t])
            else:r=p
            D[c,t]=r-p;R[c,t]=r
    return R,D


def decode_projection(D,co):
    R=np.zeros(D.shape,np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        for t in range(D.shape[1]):
            p=0 if t<P else int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            R[c,t]=p+int(D[c,t])
    return R


def zsm(K,W):
    old=z.NT;z.NT=NT
    try:
        bb,nbit=z.encode_zsm(K,W);Kd=z.decode_zsm(bb,nbit,W)
    finally:z.NT=old
    if not np.array_equal(Kd,K):raise RuntimeError(('zsm rt',W))
    return len(bb)+a.MODEL_BYTES+33,int(nbit),Kd


def main(path):
    a.C=C;a.NT=NT;z.C=C;z.NT=NT
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=a.m.stats(ds);eps=.1*std;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(ds[:NT,c0:c0+C],np.float64).T;_,co=a.fits(X)
            Rb,Kb=a.run_ar(X,co);bme=float(np.max(np.abs(X-Rb.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'base hard'))
            bz=[]
            for W in WINDOWS:
                n,nb,Kd=zsm(Kb,W);Rd=a.decode_source(Kd,co)
                if not np.array_equal(Rd,Rb):raise RuntimeError((region,'base replay',W))
                bz.append({'window':W,'bytes':n,'bps':8*n/X.size,'bits':nb})
            base=min(bz,key=lambda q:q['bytes'])

            Rp,D=run_projection(X,co,eps);pme=float(np.max(np.abs(X-Rp.astype(np.float64))))
            if pme>eps*(1+1e-12):raise RuntimeError((region,'projection hard',pme,eps))
            dz=[]
            for W in WINDOWS:
                n,nb,Dd=zsm(D,W);Rd=decode_projection(Dd,co)
                if not np.array_equal(Rd,Rp):raise RuntimeError((region,'projection replay',W))
                me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,'projection decode hard',W,me,eps))
                dz.append({'window':W,'bytes':n,'bps':8*n/X.size,'bits':nb,'maxerr':me})
            best=min(dz,key=lambda q:q['bytes'])
            # Generic integer-frame control, also exactly decoded.
            generic,rep=a.backend_bytes(D)
            sz=0
            for t0 in range(0,NT,TB):bb,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,
                 'step267_zsm':base,'step267_zero_fraction':float(np.mean(Kb==0)),'step267_mean_abs_symbol':float(np.mean(np.abs(Kb.astype(np.float64)))),'step267_std':float(np.std(Kb.astype(np.float64))),
                 'interval_projection_zsm':best,'projection_candidates':dz,'projection_zero_fraction':float(np.mean(D==0)),'projection_mean_abs_correction':float(np.mean(np.abs(D.astype(np.float64)))),'projection_std':float(np.std(D.astype(np.float64))),'projection_max_abs_correction':int(np.max(np.abs(D))),
                 'projection_generic_backend_bytes':int(generic),'projection_generic_backend_bps':8*generic/X.size,'projection_generic_reps':rep,
                 'gain_projection_vs_step267':base['bytes']/best['bytes'],'gain_projection_vs_sz3':sz/best['bytes'],'maxerr':pme}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':float(std),'eps':float(eps),'ar_order':P,'rows':rows,'scope':'Decoder-real interval-projection representation gate. The Huber AR32 coefficients are unchanged. Instead of forcing each correction onto the incumbent 267-spaced innovation lattice, the encoder computes the exact integer source interval [ceil(X-eps), floor(X+eps)]. If the decoder-known AR prediction lies inside that interval, reconstruction equals the prediction and correction D=0. Otherwise reconstruction is the nearest legal integer boundary, making D the smallest correction that can possibly satisfy the public hard-error contract at that state. D is transmitted losslessly with the same exact ZSM arithmetic backend at W=4/8/64; exact D decode, recursive source replay and max-error verification are mandatory. The incumbent step267 ZSM and matched SZ3 are rerun on identical hard/easy regions. No oracle information is required by the decoder beyond the transmitted correction stream and existing AR model. No AI.'}
        json.dump(out,open('imperial_ar32_interval_projection_corrections.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
