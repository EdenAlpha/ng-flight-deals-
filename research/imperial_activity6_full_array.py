import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=30000;NCB=54;TB=1024;BLOCKS_PER_SLOT=6;W=8

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def arithmetic_activity6(K):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());nextra=6
    E=a.AE(a.nctx(nb)*nextra)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=int(u[c,t])
            for bp in range(nb-1,-1,-1):
                bit=(val>>bp)&1;bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;E.put(bit,cx);pref=((pref<<1)|bit)&3
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    bb,nbit=E.finish();D=a.AD(bb,nbit,a.nctx(nb)*nextra);Kd=np.zeros_like(K)
    ring.fill(0);sums.fill(0)
    for t in range(NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ex=activity(sums[c],cnt);prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;pref=0;val=0
            for bp in range(nb-1,-1,-1):
                bitpos=nb-1-bp;cx=a.ctx(prev,left,bitpos,pref,nb)*nextra+ex;bit=D.get(cx);val=(val<<1)|bit;pref=((pref<<1)|bit)&3
            k=(val>>1)^-(val&1);Kd[c,t]=int(k)
            old=int(ring[c,pos]);new=abs(int(k));ring[c,pos]=new;sums[c]+=new-old
    if not np.array_equal(Kd,K):raise RuntimeError('activity6 K decode')
    # Same AR model payload as baseline, plus one selector byte over its 32-byte framing.
    return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd

def main(path,slot):
    slot=int(slot);lo=slot*BLOCKS_PER_SLOT;hi=min(NCB,lo+BLOCKS_PER_SLOT);a.NT=NT;a.C=C
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd
        if tuple(d.shape)!=(30000,6912):raise RuntimeError(('shape',d.shape))
        rows=[];base_total=act_total=sz_total=0
        for cb in range(lo,hi):
            c0=cb*C;X=np.asarray(d[:,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,_,_,K0=a.arithmetic(K);R0=a.decode_source(K0,hu)
            act,nbits,sbits,Kd=arithmetic_activity6(K);Rd=a.decode_source(Kd,hu)
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if not np.array_equal(K0,K) or not np.array_equal(R0,R):raise RuntimeError((cb,'baseline decode'))
            if not np.array_equal(Kd,K) or not np.array_equal(Rd,R):raise RuntimeError((cb,'activity decode'))
            if me>eps*(1+1e-12):raise RuntimeError((cb,'hard',me,eps))
            sz=0
            for t0 in range(0,NT,TB):bb,_=a.m.szrun(X[:,t0:min(NT,t0+TB)],eps);sz+=int(bb)
            base_total+=base;act_total+=act;sz_total+=sz
            row={'cb':cb,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'activity6_bytes':int(act),'activity6_bps':8*act/X.size,'gain_activity_vs_baseline':float(base/act),'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'gain_activity_vs_sz3':float(sz/act),'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K)),'arithmetic_bits':int(nbits),'symbol_bits':int(sbits)}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        samples=sum(r['samples'] for r in rows)
        out={'slot':slot,'channel_blocks':[lo,hi],'samples':samples,'global_std':gstd,'eps':eps,'baseline_bytes':base_total,'activity6_bytes':act_total,'sz3_bytes':sz_total,'baseline_bps':8*base_total/samples,'activity6_bps':8*act_total/samples,'sz3_bps':8*sz_total/samples,'gain_activity_vs_baseline':float(base_total/act_total),'gain_activity_vs_sz3':float(sz_total/act_total),'improved_blocks':sum(r['activity6_bytes']<r['baseline_bytes'] for r in rows),'rows':rows,'scope':'One ninth of the complete Imperial array promoting the exact positive activity6 K-language mechanism from PR #434 without changing the Huber AR32 step267 reconstruction. The baseline arithmetic context is augmented only by a decoder-known six-bin activity state derived from the rolling previous 8 absolute innovations of the same channel. No activity field or probability model is transmitted; encoder and decoder update identical state after each exact K. One selector byte is charged. Baseline and activity6 K are independently arithmetic-decoded, the full 30,000-sample recursive source is regenerated, and unchanged max-error is verified. Matched SZ3 is rerun on identical blocks. No AI. Draft/do not merge.'}
        print(json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True);json.dump(out,open(f'imperial_activity6_full_{slot}.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])