import json,sys
import h5py,numpy as np
from numba import njit
import imperial_huber_ar32_coldstart_arithmetic_regions as base

SPECS=(("hard",512),("easy",2304))
C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
MUS=(0.0,0.01,0.05,0.20);SELECTOR_BYTES=1
base.NT=NT

@njit(cache=True)
def init_state(Rprefix,co):
    scales=np.empty(C,np.float64);W=np.empty((C,P+1),np.float64)
    for c in range(C):
        s=float(np.std(Rprefix[c,:TRAIN].astype(np.float64)))
        if s<1.0:s=1.0
        scales[c]=s;W[c,0]=float(co[0])/s
        for j in range(P):W[c,j+1]=float(co[j+1])
    return scales,W

@njit(cache=True)
def run_tail_encode(X,Rprefix,Kprefix,co,mu):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32)
    R[:,:TRAIN]=Rprefix[:,:TRAIN];K[:,:TRAIN]=Kprefix[:,:TRAIN]
    scales,W=init_state(Rprefix,co)
    for c in range(C):
        s=scales[c]
        for t in range(TRAIN,NT):
            pred=W[c,0];norm=1.0
            for j in range(P):
                x=float(R[c,t-1-j])/s;pred += W[c,j+1]*x;norm += x*x
            p=int(np.rint(pred*s))
            if p>2147000000:p=2147000000
            if p<-2147000000:p=-2147000000
            k=int(np.rint((float(X[c,t])-float(p))/STEP));K[c,t]=k;R[c,t]=p+STEP*k
            if mu>0.0:
                err=float(R[c,t])/s-pred;g=mu*err/norm;W[c,0]+=g
                for j in range(P):W[c,j+1]+=g*(float(R[c,t-1-j])/s)
    return R,K,W,scales

@njit(cache=True)
def run_tail_decode(K,Rprefix,co,mu):
    R=np.zeros((C,NT),np.int32);R[:,:TRAIN]=Rprefix[:,:TRAIN]
    scales,W=init_state(Rprefix,co)
    for c in range(C):
        s=scales[c]
        for t in range(TRAIN,NT):
            pred=W[c,0];norm=1.0
            for j in range(P):
                x=float(R[c,t-1-j])/s;pred += W[c,j+1]*x;norm += x*x
            p=int(np.rint(pred*s))
            if p>2147000000:p=2147000000
            if p<-2147000000:p=-2147000000
            R[c,t]=p+STEP*int(K[c,t])
            if mu>0.0:
                err=float(R[c,t])/s-pred;g=mu*err/norm;W[c,0]+=g
                for j in range(P):W[c,j+1]+=g*(float(R[c,t-1-j])/s)
    return R,W,scales

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=base.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=base.fits(X);Rb,Kb=base.run_ar(X,co)
            bbytes,_,_,Kbd=base.arithmetic(Kb);Rbd=base.decode_source(Kbd,co)
            if not np.array_equal(Rbd,Rb):raise RuntimeError((region,'baseline replay'))
            candidates=[]
            for mu in MUS:
                R,K,Wenc,sc=run_tail_encode(X,Rb,Kb,np.asarray(co,np.float32),float(mu))
                me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,mu,'encoder hard',me,eps))
                n,bits,nb,Kd=base.arithmetic(K);n+=SELECTOR_BYTES
                audited_prefix=base.decode_source(Kd[:,:TRAIN],co)
                if not np.array_equal(audited_prefix,R[:,:TRAIN]):raise RuntimeError((region,mu,'prefix mismatch'))
                Rd,Wdec,scd=run_tail_decode(Kd,audited_prefix,np.asarray(co,np.float32),float(mu))
                if not np.array_equal(Rd,R):raise RuntimeError((region,mu,'decoder replay'))
                if not np.array_equal(sc,scd) or not np.allclose(Wenc,Wdec,rtol=0,atol=0):raise RuntimeError((region,mu,'state mismatch'))
                dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                tail=K[:,TRAIN:]
                q={'mu':float(mu),'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':bbytes/n,'zero_fraction_tail':float(np.mean(tail==0)),'k_std_tail':float(np.std(tail.astype(np.float64))),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':dme};candidates.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=base.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes']);mu0=[q for q in candidates if q['mu']==0.0][0]
            for q in candidates:q['gain_vs_static_tail']=mu0['bytes']/q['bytes']
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(bbytes),'baseline_bps':8*bbytes/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'static_normalized_tail':mu0,'best':best,'candidates':candidates};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'scope':'Decoder-synchronized nonstationary temporal gate. The audited Huber AR32 step267 path reconstructs the first 1024 samples exactly. Encoder and decoder then initialize one normalized 32-tap AR state per channel from those decoded samples and update it causally with normalized LMS using only reconstructed samples after each exact K is known. No adaptive coefficients, scales, or training targets are transmitted; per-channel scale is derived from the decoded prefix. mu={0,.01,.05,.20} is screened and one selector byte is charged. Exact arithmetic K decode, independently regenerated adaptive states, complete source replay and unchanged max error are mandatory. mu=0 is included to separate adaptation from the alternate deterministic tail arithmetic. Hard/easy 128x4096. No AI. Draft/do not merge.'},open('imperial_ar32_decoder_nlms.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
