import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_residual_stencil as s
import imperial_ar32_bayesian_context_mixer as m

C=128;NT=8192;TB=1024
REGIONS=(('hard',512),('easy',2304))
WINDOWS=(4,8,64)
NZERO=9*9*6;NSIGN=3*3*6;NPREF=6*6*16;NSUFF=16*16*6
OFF_SIGN=NZERO;OFF_PREF=OFF_SIGN+NSIGN;OFF_SUFF=OFF_PREF+NPREF;NCTX=OFF_SUFF+NSUFF


def ac_state(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def sgncat(x):x=int(x);return 0 if x<0 else (2 if x>0 else 1)
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
            iz=1 if k==0 else 0;E.put(iz,zero_ctx(prev,left,ac))
            if not iz:
                E.put(1 if k<0 else 0,sign_ctx(prev,left,ac));mag=abs(k);q=mag.bit_length()-1
                for j in range(q):E.put(0,pref_ctx(prev,ac,j))
                E.put(1,pref_ctx(prev,ac,q));rem=mag-(1<<q)
                for bp in range(q-1,-1,-1):E.put((rem>>bp)&1,suff_ctx(q,q-1-bp,ac))
            old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
    return E.finish()


def decode_zsm(bb,nbit,W):
    D=a.AD(bb,nbit,NCTX);K=np.zeros((C,NT),np.int32);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            ac=ac_state(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0
            iz=D.get(zero_ctx(prev,left,ac))
            if iz:k=0
            else:
                neg=D.get(sign_ctx(prev,left,ac));q=0
                while not D.get(pref_ctx(prev,ac,q)):
                    q+=1
                    if q>30:raise RuntimeError(('gamma overflow',c,t))
                rem=0
                for pos in range(q):rem=(rem<<1)|D.get(suff_ctx(q,pos,ac))
                mag=(1<<q)+rem;k=-mag if neg else mag
            K[c,t]=k;old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
    return K


def main(path):
    a.NT=NT;s.NT=NT;m.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(Kb)
            if not np.array_equal(a.decode_source(Kbd,hu),Rb):raise RuntimeError((region,'baseline replay'))
            models=s.fit_models(X,Rb,Kb);screen=[]
            for ids,co,trmse in models:
                extra=18+5*len(ids)
                for strength in s.STRENGTHS:
                    R,K=s.run_model(X,hu,ids,co,strength);me=float(np.max(np.abs(X-R.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,'hard',len(ids),strength,me,eps))
                    screen.append((s.backend(K,extra),ids,co,trmse,strength,R,K,extra))
            screen.sort(key=lambda x:x[0]);_,ids,co,trmse,strength,R,K,extra=screen[0]
            normal,_,_,Knd=a.arithmetic(K);normal+=extra
            mixed,mbits,mnb,Kmd,_=m.arithmetic_mix(K);mixed+=extra
            if not np.array_equal(s.decode_model(Knd,hu,ids,co,strength),R) or not np.array_equal(s.decode_model(Kmd,hu,ids,co,strength),R):raise RuntimeError((region,'existing replay'))
            zc=[]
            for W in WINDOWS:
                bb,nbit=encode_zsm(K,W);Kd=decode_zsm(bb,nbit,W)
                if not np.array_equal(Kd,K):raise RuntimeError((region,W,'zsm K'))
                Rd=s.decode_model(Kd,hu,ids,co,strength)
                if not np.array_equal(Rd,R):raise RuntimeError((region,W,'zsm replay'))
                me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,W,'zsm hard',me,eps))
                n=len(bb)+a.MODEL_BYTES+33+extra
                zc.append({'window':W,'bytes':int(n),'bps':8*n/X.size,'arithmetic_bits':int(nbit),'maxerr':me})
            best=min(zc,key=lambda q:q['bytes'])
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'nonlocal_normal_bytes':int(normal),'nonlocal_normal_bps':8*normal/X.size,'nonlocal_mixer_bytes':int(mixed),'nonlocal_mixer_bps':8*mixed/X.size,'nonlocal_zsm':best,'zsm_candidates':zc,'gain_zsm_vs_mixer':mixed/best['bytes'],'gain_zsm_vs_baseline':base/best['bytes'],'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'gain_zsm_vs_sz3':sz/best['bytes'],'taps':int(len(ids)),'strength':float(strength),'tap_ids':[int(i) for i in ids],'train_rmse_k':float(trmse),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std())};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':float(gstd),'eps':float(eps),'rows':rows,'scope':'Deployable stack of PR457 nonlocal predictor and PR474 zero/sign/Elias-gamma magnitude arithmetic. The nonlocal K stream is selected exactly as in PR457 using the incumbent backend screen. The unchanged exact K is then encoded by the variable-length zero/sign/magnitude coder at W=4/8/64, with one selector byte and all nonlocal model/framing bytes charged. Exact K decode, nonlocal source replay and max-error verification are mandatory. Existing nonlocal ordinary arithmetic and nonlocal Bayesian mixer are rerun on identical hard/easy 128x8192 for direct comparison. No AI. Draft/do not merge.'},open('imperial_ar32_nonlocal_zsm_stack.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
