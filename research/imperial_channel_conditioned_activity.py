import json,sys
import h5py,numpy as np
import imperial_activity6_full_array as b

a=b.a
C=128;NT=30000;W=8
GROUPS=(1,2,4,8,16)

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def arithmetic_grouped(K,ng):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());nextra=6
    base_ctx=a.nctx(nb)*nextra
    E=a.AE(base_ctx*ng)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t]);g=min(ng-1,(c*ng)//C)
            for bp in range(nb-1,-1,-1):
                bit=(val>>bp)&1;bitpos=nb-1-bp;cx=(a.ctx(prev,left,bitpos,pref,nb)*nextra+ex)*ng+g;E.put(bit,cx);pref=((pref<<1)|bit)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish()
    D=a.AD(bb,nbit,base_ctx*ng);Kd=np.zeros_like(K);ring.fill(0);sums.fill(0)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0;g=min(ng-1,(c*ng)//C)
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=(a.ctx(prev,left,bitpos,pref,nb)*nextra+ex)*ng+g;bit=D.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
            k=(val>>1)^-(val&1);Kd[c,t]=int(k)
            old=int(ring[c,pos]);new=abs(int(k));ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError(('grouped K decode',ng))
    return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd

def main(path,cb):
    cb=int(cb);a.NT=NT;a.C=C
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        X=np.asarray(d[:,cb*C:(cb+1)*C],np.float64).T
        _,hu=a.fits(X);R,K=a.run_ar(X,hu)
        rows=[]
        baseline=None
        for ng in GROUPS:
            size,nbit,nb,Kd=arithmetic_grouped(K,ng);Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if not np.array_equal(Kd,K) or not np.array_equal(Rd,R):raise RuntimeError((cb,ng,'decode'))
            if me>eps*(1+1e-12):raise RuntimeError((cb,ng,'hard',me,eps))
            if ng==1:baseline=size
            row={'cb':cb,'groups':ng,'bytes':int(size),'bps':8*size/X.size,'gain_vs_group1':float(baseline/size if baseline else 1.0),'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'maxerr':me}
            rows.append(row);print(json.dumps(row),flush=True)
        best=min(rows,key=lambda r:r['bytes'])
        out={'cb':cb,'c0':cb*C,'samples':int(X.size),'global_std':gstd,'eps':eps,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K)),'group1_bytes':int(rows[0]['bytes']),'best':best,'rows':rows,'scope':'Exact Huber AR32 step267 reconstruction and exact activity6 bit language. Only change is splitting adaptive arithmetic probability contexts by contiguous decoder-known channel group within each 128-channel cable block. Group identity is derived from channel position, so no labels/tables are transmitted. Every candidate is arithmetic-decoded, full recursive source replayed, and hard error verified.'}
        print('BEST',json.dumps(best),flush=True);json.dump(out,open(f'imperial_channel_conditioned_{cb}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
