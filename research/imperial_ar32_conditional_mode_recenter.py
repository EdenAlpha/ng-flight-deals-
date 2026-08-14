import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;W=8;TB=1024
REGIONS=(('hard',512),('easy',2304))
SELECTOR_BYTES=1

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def clip8(x):return int(max(-8,min(8,int(x))))+8

def build_modes(K,use_activity):
    # Exact deterministic model from the already-decoded prefix only.
    # Candidate modes are exact K values -8..8; outliers do not alias into edge modes.
    counts=np.zeros((17,6 if use_activity else 1,17),np.int64)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(TRAIN):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt) if use_activity else 0
            prev=int(K[c,t-1]) if t else 0
            k=int(K[c,t])
            if -8<=k<=8:counts[clip8(prev),ac,k+8]+=1
            old=int(ring[c,pos]);new=abs(k);ring[c,pos]=new;sums[c]+=new-old
    modes=np.zeros((17,6 if use_activity else 1),np.int32)
    for p in range(17):
        for ac in range(modes.shape[1]):
            row=counts[p,ac]
            if int(row.sum())>0:modes[p,ac]=int(np.argmax(row))-8
    return modes

def arithmetic_mode(K,use_activity):
    modes=build_modes(K,use_activity)
    # Build J exactly as decoder will, only to determine the fixed bit width.
    J=np.zeros_like(K)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt)
            prev=int(K[c,t-1]) if t else 0
            m=0 if t<TRAIN else int(modes[clip8(prev),ac if use_activity else 0])
            J[c,t]=int(K[c,t])-m
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    u=a.zig(J);nb=max(1,int(u.max()).bit_length())
    E=a.AE(a.nctx(nb)*6);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0
            val=int(u[c,t]);pref=0
            for bp in range(nb-1,-1,-1):
                b=(val>>bp)&1;bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*6+ac;E.put(b,cx);pref=((pref<<1)|b)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish()
    # Decoder derives the mode table from its exact first TRAIN K values, then reconstructs K=J+mode.
    D=a.AD(bb,nbit,a.nctx(nb)*6);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64);modes_d=None
    for t in range(NT):
        if t==TRAIN:modes_d=build_modes(Kd,use_activity)
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*6+ac;b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
            j=int((val>>1)^-(val&1));m=0 if t<TRAIN else int(modes_d[clip8(prev),ac if use_activity else 0]);k=j+m;Kd[c,t]=k
            old=int(ring[c,pos]);new=abs(k);ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError(('conditional-mode K decode',use_activity))
    # No mode bytes: decoder derives the table from decoded prefix. Charge ordinary model/framing + selector.
    return len(bb)+a.MODEL_BYTES+33+SELECTOR_BYTES,int(nbit),int(nb),Kd,modes,J

def arithmetic_activity_control(K):
    # Same exact activity-specialized backend, but J=K (zero mode), to isolate recentering.
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());E=a.AE(a.nctx(nb)*6);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                b=(val>>bp)&1;bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*6+ac;E.put(b,cx);pref=((pref<<1)|b)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish();D=a.AD(bb,nbit,a.nctx(nb)*6);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*6+ac;b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
            k=int((val>>1)^-(val&1));Kd[c,t]=k;old=int(ring[c,pos]);new=abs(k);ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError('activity control decode')
    return len(bb)+a.MODEL_BYTES+33,int(nbit),int(nb),Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(K);act,_,_,Kad=arithmetic_activity_control(K)
            if not np.array_equal(a.decode_source(Kbd,hu),R) or not np.array_equal(a.decode_source(Kad,hu),R):raise RuntimeError((region,'control replay'))
            candidates=[]
            for ua in (False,True):
                n,bits,nb,Kd,modes,J=arithmetic_mode(K,ua);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,ua,'hard',me,eps))
                tail=J[:,TRAIN:]
                modevals=modes.ravel();nz=int(np.count_nonzero(modevals));
                q={'mode_context':'prev8_activity6' if ua else 'prev8','bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'gain_vs_activity_control':act/n,'j_zero_fraction_tail':float(np.mean(tail==0)),'k_zero_fraction_tail':float(np.mean(K[:,TRAIN:]==0)),'j_std_tail':float(np.std(tail.astype(np.float64))),'k_std_tail':float(np.std(K[:,TRAIN:].astype(np.float64))),'nonzero_mode_contexts':nz,'mode_min':int(modevals.min()),'mode_max':int(modevals.max()),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me};candidates.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'activity_control_bytes':int(act),'activity_control_bps':8*act/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'scope':'Exact lossless recentering of the incumbent AR32 innovation alphabet. The first 1024 K samples are coded unchanged. From that already-decoded prefix, encoder and decoder deterministically derive the exact modal next-K value in [-8,8] conditioned on previous K clipped to +/-8, optionally plus the same decoder-known rolling activity6 state. For later samples the coded symbol is J=K-mode(context), while source reconstruction remains bit-for-bit identical because the decoder restores K before AR replay. No mode table is transmitted; one selector byte is charged. A byte-identical activity6 arithmetic control on ordinary K isolates whether recentering helps the real bitplane coder. Hard/easy 128x4096, exact J/K arithmetic decode and unchanged max-error source replay. No AI. Draft/do not merge.'},open('imperial_ar32_conditional_mode_recenter.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
