import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TB=1024;MODEL_BYTES=a.MODEL_BYTES
REGIONS=(("hard",512,4),("easy",2304,64))
RESETS=(0,256,1024);SELECTOR_BYTES=1

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def arithmetic(K,W,reset_t):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());E=a.AE(a.nctx(nb)*6)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        if reset_t and t and t%reset_t==0:E.c.fill(1)
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                b=(val>>bp)&1;p=nb-1-bp;cx=a.ctx(prev,left,p,pref,nb)*6+ac;E.put(b,cx);pref=((pref<<1)|b)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish();D=a.AD(bb,nbit,a.nctx(nb)*6);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        if reset_t and t and t%reset_t==0:D.c.fill(1)
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                p=nb-1-bp;cx=a.ctx(prev,left,p,pref,nb)*6+ac;b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
            k=int((val>>1)^-(val&1));Kd[c,t]=k;old=int(ring[c,pos]);new=abs(k);ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError(("reset arithmetic decode",W,reset_t))
    return len(bb)+MODEL_BYTES+33+SELECTOR_BYTES,int(nbit),int(nb),Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0,W in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);base,_,_,Kb=a.arithmetic(K)
            if not np.array_equal(a.decode_source(Kb,hu),R):raise RuntimeError((region,'baseline replay'))
            candidates=[]
            for reset in RESETS:
                n,bits,nb,Kd=arithmetic(K,W,reset);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,reset,'hard',me,eps))
                q={'activity_window':W,'reset_samples':int(reset),'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me};candidates.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes']);noreset=[q for q in candidates if q['reset_samples']==0][0]
            for q in candidates:q['gain_vs_no_reset_activity']=noreset['bytes']/q['bytes']
            row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'no_reset_activity':noreset,'best':best,'candidates':candidates};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'scope':'Decoder-real probability-forgetting gate on unchanged Huber AR32 K. Uses the empirically best activity timescale from PR #455 (W=4 hard, W=64 easy) and compares cumulative adaptive arithmetic against deterministic probability-table resets every 256 or 1024 time samples. Only probability counts reset; K history/activity and source reconstruction remain continuous. No reset schedule bits or probability tables are transmitted; one selector byte is charged. Exact arithmetic decode, full AR32 source replay and unchanged max error are mandatory on hard/easy 128x4096, with matched incumbent and SZ3. No AI. Draft/do not merge.'},open('imperial_ar32_activity_reset_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
