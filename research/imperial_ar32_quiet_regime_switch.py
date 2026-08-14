import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128
NT=4096
P=32
STEP=267
TB=1024
REGIONS=(('hard',512),('easy',2304))
CANDIDATES=(
    ('zero',8,2.0),('zero',8,4.0),('zero',32,2.0),('zero',32,4.0),
    ('hold',8,2.0),('hold',32,2.0),
)
a.NT=NT


def run_switch(X,co,eps,quiet_mode,W,threshold_ratio):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    threshold=float(threshold_ratio)*float(eps)
    quiet_count=0
    for c in range(C):
        ring=np.zeros(W,np.float64);rs=0.0;rc=0;rp=0
        for t in range(NT):
            if t<P:
                p=0
            else:
                p_ar=int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
                activity=rs/max(rc,1)
                quiet=(activity<=threshold)
                if quiet:
                    quiet_count+=1
                    p=0 if quiet_mode=='zero' else int(R[c,t-1])
                else:
                    p=p_ar
            k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
            v=abs(float(R[c,t]))
            if rc<W:
                ring[rp]=v;rs+=v;rc+=1;rp=(rp+1)%W
            else:
                rs-=ring[rp];ring[rp]=v;rs+=v;rp=(rp+1)%W
    return R,K,quiet_count/(C*NT)


def decode_switch(K,co,eps,quiet_mode,W,threshold_ratio):
    R=np.zeros(K.shape,np.int32)
    aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    threshold=float(threshold_ratio)*float(eps)
    for c in range(C):
        ring=np.zeros(W,np.float64);rs=0.0;rc=0;rp=0
        for t in range(NT):
            if t<P:
                p=0
            else:
                p_ar=int(np.rint(aa+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
                activity=rs/max(rc,1)
                if activity<=threshold:
                    p=0 if quiet_mode=='zero' else int(R[c,t-1])
                else:p=p_ar
            R[c,t]=p+STEP*int(K[c,t])
            v=abs(float(R[c,t]))
            if rc<W:
                ring[rp]=v;rs+=v;rc+=1;rp=(rp+1)%W
            else:
                rs-=ring[rp];ring[rp]=v;rs+=v;rp=(rp+1)%W
    return R


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            _,co=a.fits(X);Rb,Kb=a.run_ar(X,co);bb,_,_,Kbd=a.arithmetic(Kb);Rbd=a.decode_source(Kbd,co)
            bme=float(np.max(np.abs(X-Rbd.astype(np.float64))))
            if bme>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',bme,eps))
            sz=0
            for t0 in range(0,NT,TB):n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
            cands=[]
            for mode,W,tr in CANDIDATES:
                R,K,qf=run_switch(X,co,eps,mode,W,tr)
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,mode,W,tr,'hard',me,eps))
                n,nbit,nb,Kd=a.arithmetic(K);n+=1
                Rd=decode_switch(Kd,co,eps,mode,W,tr)
                if not np.array_equal(Rd,R):raise RuntimeError((region,mode,W,tr,'replay'))
                dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if dme>eps*(1+1e-12):raise RuntimeError((region,mode,W,tr,'decoded hard',dme,eps))
                q={'mode':mode,'window':W,'threshold_eps':tr,'bytes':int(n),'bps':8*n/X.size,
                   'gain_vs_baseline':float(bb/n),'gain_vs_sz3':float(sz/n),'quiet_fraction':float(qf),
                   'zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),
                   'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'maxerr':dme}
                cands.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            best=min(cands,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),
                 'baseline':{'bytes':int(bb),'bps':8*bb/X.size,'zero_fraction':float(np.mean(Kb==0)),'maxerr':bme},
                 'sz3':{'bytes':int(sz),'bps':8*sz/X.size},'best':best,'candidates':cands}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        out={'rows':rows,'scope':'Causal intra-trace representation-switch gate motivated by the whole-array result that AR32 and frozen source-lattice coding win on different blocks. No per-sample selector is transmitted. Encoder and decoder compute the same rolling mean absolute reconstructed amplitude; below a fixed public threshold they switch from Huber AR32 either to a zero predictor or a hold-last reconstructed-value predictor, otherwise AR32 is used. All candidates retain exact step267 innovations, one candidate selector byte is charged, K is arithmetic-decoded exactly, full recursive source replay is verified, and the unchanged max-error contract is enforced. Hard/easy 128x4096 with matched AR32 and SZ3. No AI. Draft/do not merge.'}
        json.dump(out,open('imperial_ar32_quiet_regime_switch.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
