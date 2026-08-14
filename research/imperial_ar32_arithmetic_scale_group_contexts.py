import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TB=1024;W=8
SPECS=(('hard',512),('easy',2304))
MODES=('group32','group16','activity6','group32_activity4','group16_activity4')

def activity(sumabs,count,n):
    if count<=0:return 0
    z=2*int(sumabs)
    cuts=(1,3,7) if n==4 else (1,3,7,15,31)
    for i,q in enumerate(cuts):
        if z<=q*count:return i
    return len(cuts)

def extra_state(mode,c,sumabs,count):
    if mode=='group32':return c//32,4
    if mode=='group16':return c//16,8
    if mode=='activity6':return activity(sumabs,count,6),6
    if mode=='group32_activity4':return (c//32)*4+activity(sumabs,count,4),16
    if mode=='group16_activity4':return (c//16)*4+activity(sumabs,count,4),32
    raise ValueError(mode)

def arithmetic_extra(K,mode):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length())
    # nextra is fixed by mode; ask once with empty history
    _,nextra=extra_state(mode,0,0,0)
    E=a.AE(a.nctx(nb)*nextra)
    ring=np.zeros((C,W),np.int32); sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex,_=extra_state(mode,c,sums[c],cnt)
            prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                b=(val>>bp)&1;bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;E.put(b,cx);pref=((pref<<1)|b)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish()
    D=a.AD(bb,nbit,a.nctx(nb)*nextra);Kd=np.zeros_like(K)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex,_=extra_state(mode,c,sums[c],cnt)
            prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
            k=(val>>1)^-(val&1);Kd[c,t]=int(k)
            old=int(ring[c,pos]);new=abs(int(k));ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError((mode,'K decode'))
    return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,bbits,bnb,Kbd=a.arithmetic(K);Rbd=a.decode_source(Kbd,hu)
            if not np.array_equal(Rbd,R):raise RuntimeError((region,'baseline source decode'))
            candidates=[]
            for mode in MODES:
                n,bits,nb,Kd=arithmetic_extra(K,mode);Rd=a.decode_source(Kd,hu)
                me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,mode,'hard',me,eps))
                candidates.append({'mode':mode,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me})
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'window':W,'modes':list(MODES),'rows':rows,'scope':'Lossless K-language pilot on the unchanged Huber AR32 step267 reconstruction. Baseline cold-start arithmetic conditions on clipped previous-time K, current-left K, bit position and two-bit prefix. Candidate deterministic contexts additionally split probability tables by fixed 32- or 16-channel group, decoder-known rolling 8-sample same-channel absolute-K activity, or their combination. No probability model or scale field is transmitted; encoder and decoder update the same rolling state after each exactly decoded K. One selector byte is charged. Full K and recursive source replay plus unchanged hard-error verification are mandatory. Hard/easy fast gate only. No AI.'};json.dump(out,open('imperial_ar32_arithmetic_scale_group_contexts.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
