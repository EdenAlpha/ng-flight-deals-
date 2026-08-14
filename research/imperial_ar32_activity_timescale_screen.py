import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TB=1024
REGIONS=(('hard',512),('easy',2304))
WINDOWS=(1,2,4,8,16,32,64)

def activity_from_sum(sumabs,count):
    z=2*sumabs
    out=np.full(sumabs.shape,5,np.int8)
    for i,q in reversed(list(enumerate((1,3,7,15,31)))):
        out[z<=q*count]=i
    out=np.where(count>0,out,0).astype(np.int8)
    return out

def activity_matrix(K,W):
    A=np.abs(K.astype(np.int64));cs=np.zeros((C,NT+1),np.int64);cs[:,1:]=np.cumsum(A,axis=1)
    t=np.arange(NT);lo=np.maximum(0,t-W);s=cs[:,t]-cs[:,lo];cnt=np.minimum(t,W)[None,:]
    return activity_from_sum(s,cnt)

def oracle_bit_cost(K,W):
    act=activity_matrix(K,W);u=a.zig(K);nb=max(1,int(u.max()).bit_length())
    prev=np.zeros_like(K);prev[:,1:]=K[:,:-1]
    left=np.zeros_like(K);left[1:,:]=K[:-1,:]
    pc=np.clip(prev,-4,4).astype(np.int64)+4;lc=np.clip(left,-4,4).astype(np.int64)+4
    pref=np.zeros(K.shape,np.int64);bits=0.0
    for bp in range(nb-1,-1,-1):
        b=((u>>bp)&1).astype(np.int64);pos=nb-1-bp
        base=(((pc*9+lc)*nb+pos)*4+pref);cx=(base*6+act.astype(np.int64)).ravel(order='F');br=b.ravel(order='F')
        nctx=a.nctx(nb)*6;cnt=np.bincount(cx*2+br,minlength=nctx*2).reshape(nctx,2).astype(np.float64);tot=cnt.sum(axis=1)
        nz=cnt>0
        # target-trained conditional entropy only for choosing which deterministic W to real-code.
        for j in (0,1):
            m=nz[:,j];bits-=float(np.sum(cnt[m,j]*np.log2(cnt[m,j]/tot[m])))
        pref=((pref<<1)|b)&3
    return bits/K.size

def arithmetic_w(K,W):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());E=a.AE(a.nctx(nb)*6)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            z=2*int(sums[c]);ac=5
            if cnt<=0:ac=0
            else:
                for i,q in enumerate((1,3,7,15,31)):
                    if z<=q*cnt:ac=i;break
            prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                bit=(val>>bp)&1;p=nb-1-bp;cx=a.ctx(prev,left,p,pref,nb)*6+ac;E.put(bit,cx);pref=((pref<<1)|bit)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish();D=a.AD(bb,nbit,a.nctx(nb)*6);Kd=np.zeros_like(K);ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            z=2*int(sums[c]);ac=5
            if cnt<=0:ac=0
            else:
                for i,q in enumerate((1,3,7,15,31)):
                    if z<=q*cnt:ac=i;break
            prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                p=nb-1-bp;cx=a.ctx(prev,left,p,pref,nb)*6+ac;bit=D.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
            k=(val>>1)^-(val&1);Kd[c,t]=int(k);old=int(ring[c,pos]);new=abs(int(k));ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError(('activity decode',W))
    return len(bb)+a.MODEL_BYTES+33,int(nbit),int(nb),Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu);base,_,_,Kbd=a.arithmetic(K)
            if not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'base replay'))
            screen={str(W):oracle_bit_cost(K,W) for W in WINDOWS};rank=sorted(WINDOWS,key=lambda W:screen[str(W)])
            chosen=[]
            for W in rank[:2]+[8]:
                if W not in chosen:chosen.append(W)
            candidates=[]
            for W in chosen:
                n,bits,nb,Kd=arithmetic_w(K,W);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,W,'hard',me,eps))
                candidates.append({'window':W,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':bits,'symbol_bits':nb,'oracle_screen_bps':screen[str(W)],'maxerr':me})
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'oracle_window_screen':screen,'real_coded_windows':chosen,'best':best,'candidates':candidates};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        json.dump({'global_std':gstd,'eps':eps,'windows':list(WINDOWS),'rows':rows,'scope':'Timescale refinement of the independently positive decoder-known activity arithmetic mechanism. For each hard/easy 128x8192 K field, W in {1,2,4,8,16,32,64} is first ranked by a fast target-trained conditional bit-entropy diagnostic using the exact incumbent prev4/left4/bitpos/prefix2 context plus the same six-bin rolling mean-|K| activity definition. That diagnostic is only a compute screen, not a rate claim. The two best-ranked windows plus the original W=8 control are then each fully cold-start arithmetic encoded/decoded; a selector byte is charged, exact K and recursive source replay are verified under unchanged max error, and matched SZ3 is rerun. No AI.'},open('imperial_ar32_activity_timescale_screen.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
