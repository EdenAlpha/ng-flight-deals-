import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_residual_stencil as s

C=128;NT=8192;TB=1024;W=8
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def arithmetic_activity(K):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());nextra=6
    E=a.AE(a.nctx(nb)*nextra);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                b=(val>>bp)&1;bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;E.put(b,cx);pref=((pref<<1)|b)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish();D=a.AD(bb,nbit,a.nctx(nb)*nextra);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
            k=(val>>1)^-(val&1);Kd[c,t]=int(k);old=int(ring[c,pos]);new=abs(int(k));ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError('activity K decode')
    return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd

def main(path):
    a.NT=NT;s.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rb,Kb=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(Kb);base_act,_,_,Kab=arithmetic_activity(Kb)
            if not np.array_equal(a.decode_source(Kbd,hu),Rb) or not np.array_equal(a.decode_source(Kab,hu),Rb):raise RuntimeError((region,'baseline replay'))
            models=s.fit_models(X,Rb,Kb);screen=[]
            for ids,co,trmse in models:
                extra=18+5*len(ids)
                for strength in s.STRENGTHS:
                    R,K=s.run_model(X,hu,ids,co,strength);me=float(np.max(np.abs(X-R.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,'hard',len(ids),strength,me,eps))
                    bb=s.backend(K,extra);screen.append((bb,ids,co,trmse,strength,R,K,extra))
            screen.sort(key=lambda x:x[0]);bb,ids,co,trmse,strength,R,K,extra=screen[0]
            normal,_,_,Knd=a.arithmetic(K);normal+=extra
            activity_bytes,_,_,Kad=arithmetic_activity(K);activity_bytes+=extra
            Rn=s.decode_model(Knd,hu,ids,co,strength);Ra=s.decode_model(Kad,hu,ids,co,strength)
            if not np.array_equal(Rn,R) or not np.array_equal(Ra,R):raise RuntimeError((region,'stack replay'))
            me=float(np.max(np.abs(X-Ra.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'stack hard',me,eps))
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            row={'region':region,'c0':c0,'samples':int(X.size),'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'baseline_activity_bytes':int(base_act),'baseline_activity_bps':8*base_act/X.size,'nonlocal_normal_bytes':int(normal),'nonlocal_normal_bps':8*normal/X.size,'stack_bytes':int(activity_bytes),'stack_bps':8*activity_bytes/X.size,'gain_stack_vs_baseline':base/activity_bytes,'gain_stack_vs_nonlocal':normal/activity_bytes,'gain_stack_vs_activity_only':base_act/activity_bytes,'gain_stack_vs_sz3':sz/activity_bytes,'taps':int(len(ids)),'strength':float(strength),'tap_ids':[int(i) for i in ids],'tap_offsets':[list(s.BANK[int(i)]) for i in ids],'train_rmse_k':float(trmse),'k_zero_fraction':float(np.mean(K==0)),'k_std':float(K.std()),'maxerr':me};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'rows':rows,'scope':'Four-regime promotion of the two independently positive mechanisms proven in PR #442: stabilized prefix-trained bounded nonlocal residual stencil plus decoder-known rolling 8-sample activity6 arithmetic. Hard/easy/medium/far 128x8192 regions are run identically. The nonlocal model is selected only by the exact incumbent-backend screen, then exact K is encoded with ordinary and activity-conditioned cold-start arithmetic. All tap IDs/float32 coefficients/framing are charged; exact K is decoded, full recursive source replay and unchanged max-error verification are mandatory, with matched SZ3 and activity-only/nonlocal-only controls. No AI.'},open('imperial_ar32_nonlocal_activity_stack.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
