import json,sys
import h5py,numpy as np
from numba import njit
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TB=1024
REGIONS=(("hard",512,4),("easy",2304,64))
MODES=((1,"prev4_activity"),(2,"prev4_left4_activity"),(3,"prev8_activity"))
MAX=(1<<32)-1;HALF=1<<31;Q1=1<<30;Q3=3<<30
MODEL_BYTES=a.MODEL_BYTES;FRAMING_BYTES=32;RANGE_BYTES=8;SELECTOR_BYTES=1

@njit(cache=True)
def clipv(x,n):
    if x < -n:return 0
    if x > n:return 2*n
    return int(x)+n

@njit(cache=True)
def act_state(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    qs=(1,3,7,15,31)
    for i in range(5):
        if z<=qs[i]*count:return i
    return 5

@njit(cache=True)
def context_id(mode,prev,left,act):
    if mode==1:return clipv(prev,4)*6+act
    if mode==2:return (clipv(prev,4)*9+clipv(left,4))*6+act
    return clipv(prev,8)*6+act

@njit(cache=True)
def mode_nctx(mode):
    if mode==1:return 9*6
    if mode==2:return 9*9*6
    return 17*6

@njit(cache=True)
def fenwick_init(nctx,M):
    tree=np.empty((nctx,M+1),np.int32)
    tree[:,0]=0
    for i in range(1,M+1):
        v=i & -i
        for c in range(nctx):tree[c,i]=v
    return tree

@njit(cache=True)
def fw_sum(tree,cx,i):
    # count in [0,i), i is number of symbols included
    s=0
    while i>0:
        s+=int(tree[cx,i]);i-=i&-i
    return s

@njit(cache=True)
def fw_add(tree,cx,idx,M):
    i=idx+1
    while i<=M:
        tree[cx,i]+=1;i+=i&-i

@njit(cache=True)
def fw_find(tree,cx,M,target):
    # largest prefix count <= target, yielding zero-based symbol index
    idx=0;bit=1
    while (bit<<1)<=M:bit<<=1
    while bit:
        nxt=idx+bit
        if nxt<=M and int(tree[cx,nxt])<=target:
            target-=int(tree[cx,nxt]);idx=nxt
        bit>>=1
    if idx>=M:idx=M-1
    return idx

@njit(cache=True)
def putbit(buf,bitpos,b):
    if b:buf[bitpos>>3]|=np.uint8(1<<(7-(bitpos&7)))
    return bitpos+1

@njit(cache=True)
def getbit(buf,nbit,bitpos):
    if bitpos>=nbit:return 0,bitpos+1
    b=(int(buf[bitpos>>3])>>(7-(bitpos&7)))&1
    return b,bitpos+1

@njit(cache=True)
def encode_symbols(K,mode,W,kmin,kmax):
    M=kmax-kmin+1;nctx=mode_nctx(mode);tree=fenwick_init(nctx,M)
    N=K.size;buf=np.zeros(max(1024,(N*24+7)//8),np.uint8);bitpos=0
    lo=np.uint64(0);hi=np.uint64(MAX);pending=0
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;ac=act_state(sums[c],cnt)
            cx=context_id(mode,prev,left,ac);sym=int(K[c,t])-kmin
            cumlo=fw_sum(tree,cx,sym);cumhi=fw_sum(tree,cx,sym+1);tot=fw_sum(tree,cx,M)
            rng=int(hi-lo+np.uint64(1));oldlo=lo
            hi=oldlo+np.uint64((rng*cumhi)//tot-1);lo=oldlo+np.uint64((rng*cumlo)//tot)
            while True:
                if hi<np.uint64(HALF):
                    bitpos=putbit(buf,bitpos,0)
                    for _ in range(pending):bitpos=putbit(buf,bitpos,1)
                    pending=0
                elif lo>=np.uint64(HALF):
                    bitpos=putbit(buf,bitpos,1)
                    for _ in range(pending):bitpos=putbit(buf,bitpos,0)
                    pending=0;lo-=np.uint64(HALF);hi-=np.uint64(HALF)
                elif lo>=np.uint64(Q1) and hi<np.uint64(Q3):
                    pending+=1;lo-=np.uint64(Q1);hi-=np.uint64(Q1)
                else:break
                lo=(lo<<np.uint64(1))&np.uint64(MAX);hi=((hi<<np.uint64(1))&np.uint64(MAX))|np.uint64(1)
            fw_add(tree,cx,sym,M)
            old=int(ring[c,rp]);new=abs(int(K[c,t]));ring[c,rp]=new;sums[c]+=new-old
    pending+=1
    if lo<np.uint64(Q1):
        bitpos=putbit(buf,bitpos,0)
        for _ in range(pending):bitpos=putbit(buf,bitpos,1)
    else:
        bitpos=putbit(buf,bitpos,1)
        for _ in range(pending):bitpos=putbit(buf,bitpos,0)
    return buf[:(bitpos+7)//8].copy(),bitpos

@njit(cache=True)
def decode_symbols(buf,nbit,mode,W,kmin,kmax):
    M=kmax-kmin+1;nctx=mode_nctx(mode);tree=fenwick_init(nctx,M);Kd=np.zeros((C,NT),np.int32)
    lo=np.uint64(0);hi=np.uint64(MAX);val=np.uint64(0);bitpos=0
    for _ in range(32):
        b,bitpos=getbit(buf,nbit,bitpos);val=((val<<np.uint64(1))&np.uint64(MAX))|np.uint64(b)
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(NT):
        rp=t%W;cnt=min(t,W)
        for c in range(C):
            prev=int(Kd[c,t-1]) if t else 0;left=int(Kd[c-1,t]) if c else 0;ac=act_state(sums[c],cnt);cx=context_id(mode,prev,left,ac)
            tot=fw_sum(tree,cx,M);rng=int(hi-lo+np.uint64(1));scaled=((int(val-lo)+1)*tot-1)//rng
            sym=fw_find(tree,cx,M,scaled);cumlo=fw_sum(tree,cx,sym);cumhi=fw_sum(tree,cx,sym+1);oldlo=lo
            hi=oldlo+np.uint64((rng*cumhi)//tot-1);lo=oldlo+np.uint64((rng*cumlo)//tot)
            while True:
                if hi<np.uint64(HALF):pass
                elif lo>=np.uint64(HALF):lo-=np.uint64(HALF);hi-=np.uint64(HALF);val-=np.uint64(HALF)
                elif lo>=np.uint64(Q1) and hi<np.uint64(Q3):lo-=np.uint64(Q1);hi-=np.uint64(Q1);val-=np.uint64(Q1)
                else:break
                lo=(lo<<np.uint64(1))&np.uint64(MAX);hi=((hi<<np.uint64(1))&np.uint64(MAX))|np.uint64(1)
                b,bitpos=getbit(buf,nbit,bitpos);val=((val<<np.uint64(1))&np.uint64(MAX))|np.uint64(b)
            k=sym+kmin;Kd[c,t]=k;fw_add(tree,cx,sym,M)
            old=int(ring[c,rp]);new=abs(k);ring[c,rp]=new;sums[c]+=new-old
    return Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0,W in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,_,_,Kbd=a.arithmetic(K)
            if not np.array_equal(Kbd,K) or not np.array_equal(a.decode_source(Kbd,hu),R):raise RuntimeError((region,'baseline replay'))
            kmin=int(K.min());kmax=int(K.max());M=kmax-kmin+1;cands=[]
            for mode,name in MODES:
                bb,nbit=encode_symbols(K,int(mode),int(W),kmin,kmax);Kd=decode_symbols(bb,int(nbit),int(mode),int(W),kmin,kmax)
                if not np.array_equal(Kd,K):raise RuntimeError((region,name,'K decode'))
                Rd=a.decode_source(Kd,hu);me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,name,'source replay',me,eps))
                n=len(bb)+MODEL_BYTES+FRAMING_BYTES+RANGE_BYTES+SELECTOR_BYTES
                q={'context':name,'bytes':int(n),'payload_bytes':int(len(bb)),'bps':8*n/X.size,'gain_vs_bitwise_baseline':base/n,'kmin':kmin,'kmax':kmax,'alphabet_size':M,'arithmetic_bits':int(nbit),'activity_window':int(W),'maxerr':me};cands.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in cands:q['gain_vs_sz3']=sz/q['bytes']
            best=min(cands,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'bitwise_baseline_bytes':int(base),'bitwise_baseline_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':cands};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'scope':'Exact whole-symbol entropy gate on the unchanged Huber AR32 step267 K field. Instead of zigzag bitplanes, K is arithmetic-coded as one adaptive categorical symbol over the transmitted [Kmin,Kmax] alphabet using unit cold-start Fenwick counts. Three decoder-known contexts are tested: prevK clipped +/-4 + activity6; prevK4 + current-leftK4 + activity6; and prevK8 + activity6. Activity uses the independently measured W=4 hard / W=64 easy timescale. K range (8 bytes), ordinary model/framing and one selector byte are fully charged. Exact categorical arithmetic decode, bit-identical K/source replay and unchanged max-error checks are mandatory on hard/easy 128x4096, with matched bitwise incumbent and SZ3. Numba only accelerates exact arithmetic/Fenwick operations. No AI. Draft/do not merge.'},open('imperial_ar32_categorical_symbol_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
