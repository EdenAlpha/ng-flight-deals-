import json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_activity_timescale_screen as aw

C=128;NT=4096;TB=1024
REGIONS=(('hard',512),('easy',2304))
WINDOWS=(4,8,64)
NZERO=9*9*6
NSIGN=3*3*6
NPREF=6*6*16
NSUFF=16*16*6
OFF_SIGN=NZERO;OFF_PREF=OFF_SIGN+NSIGN;OFF_SUFF=OFF_PREF+NPREF
NCTX=OFF_SUFF+NSUFF


def ac_state(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def sgncat(x):
    x=int(x);return 0 if x<0 else (2 if x>0 else 1)

def magbin(x):
    x=abs(int(x))
    if x==0:return 0
    if x==1:return 1
    if x==2:return 2
    if x<=4:return 3
    if x<=8:return 4
    return 5

def zero_ctx(prev,left,ac):return ((a.clip4(prev)*9+a.clip4(left))*6+ac)
def sign_ctx(prev,left,ac):return OFF_SIGN+((sgncat(prev)*3+sgncat(left))*6+ac)
def pref_ctx(prev,ac,qpos):return OFF_PREF+((magbin(prev)*6+ac)*16+min(qpos,15))
def suff_ctx(q,bitpos,ac):return OFF_SUFF+((min(q,15)*16+min(bitpos,15))*6+ac)


def encode_zsm(K,W):
    E=a.AE(NCTX);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;k=int(K[c,t])
            iszero=1 if k==0 else 0;E.put(iszero,zero_ctx(prev,left,ac))
            if not iszero:
                E.put(1 if k<0 else 0,sign_ctx(prev,left,ac))
                mag=abs(k);q=mag.bit_length()-1
                for j in range(q):E.put(0,pref_ctx(prev,ac,j))
                E.put(1,pref_ctx(prev,ac,q))
                rem=mag-(1<<q)
                for bp in range(q-1,-1,-1):
                    pos=q-1-bp;E.put((rem>>bp)&1,suff_ctx(q,pos,ac))
            old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
    bb,nbit=E.finish();return bb,nbit


def decode_zsm(bb,nbit,W,shape):
    D=a.AD(bb,nbit,NCTX);K=np.zeros(shape,np.int32);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0
            iszero=D.get(zero_ctx(prev,left,ac))
            if iszero:k=0
            else:
                neg=D.get(sign_ctx(prev,left,ac));q=0
                while True:
                    b=D.get(pref_ctx(prev,ac,q))
                    if b:break
                    q+=1
                    if q>30:raise RuntimeError(('gamma overflow',c,t))
                rem=0
                for pos in range(q):rem=(rem<<1)|D.get(suff_ctx(q,pos,ac))
                mag=(1<<q)+rem;k=-mag if neg else mag
            K[c,t]=int(k);old=int(ring[c,rp]);new=abs(int(k));ring[c,rp]=new;sums[c]+=new-old
    return K


def main(path):
    a.NT=NT;aw.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=a.fits(X);R,K=a.run_ar(X,co)
            base,_,_,Kbd=a.arithmetic(K)
            if not np.array_equal(a.decode_source(Kbd,co),R):raise RuntimeError((region,'baseline replay'))
            sz=0
            for t0 in range(0,NT,TB):n,_=a.m.szrun(X[:,t0:min(t0+TB,NT)],eps);sz+=int(n)
            cands=[];controls=[]
            for W in WINDOWS:
                ab,abit,anb,Kad=aw.arithmetic_w(K,W);Rad=a.decode_source(Kad,co);ame=float(np.max(np.abs(X-Rad.astype(np.float64))))
                if ame>eps*(1+1e-12):raise RuntimeError((region,W,'activity hard',ame,eps))
                controls.append({'window':W,'bytes':int(ab),'bps':8*ab/X.size,'gain_vs_baseline':float(base/ab),'gain_vs_sz3':float(sz/ab)})
                bb,nbit=encode_zsm(K,W);Kd=decode_zsm(bb,nbit,W,K.shape)
                if not np.array_equal(Kd,K):raise RuntimeError((region,W,'zsm K decode'))
                Rd=a.decode_source(Kd,co);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,W,'zsm hard',me,eps))
                n=len(bb)+a.MODEL_BYTES+33
                q={'window':W,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':float(base/n),'gain_vs_sz3':float(sz/n),'arithmetic_bits':int(nbit),'zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K.astype(np.float64))),'maxerr':me}
                cands.append(q);print(json.dumps({'region':region,'zsm':q},indent=2),flush=True)
            best=min(cands,key=lambda q:q['bytes']);bestctl=min(controls,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best_activity_control':bestctl,'best_zsm':best,'gain_zsm_vs_best_activity':float(bestctl['bytes']/best['bytes']),'activity_controls':controls,'zsm_candidates':cands}
            rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'global_std':float(gstd),'eps':float(eps),'rows':rows,'scope':'Deployable exact entropy-language gate on the unchanged Huber AR32 step267 K stream. Instead of fixed-width zigzag bitplanes, each symbol emits one adaptive zero/nonzero flag; a nonzero emits one sign bit and an arithmetic-coded Elias-gamma magnitude. All binary probabilities are conditioned only on decoder-known previous/current-left K, rolling six-bin mean-|K| activity, and gamma position. W=4/8/64 are screened with one selector byte charged. Exact K decode, unchanged AR32 source replay and max-error verification are mandatory. The tuned activity bitplane coder at the same windows and matched SZ3 rerun on identical hard/easy 128x4096 regions. No AI. Draft/do not merge.'},open('imperial_ar32_zero_sign_magnitude_arithmetic.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
