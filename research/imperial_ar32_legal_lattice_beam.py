import json,sys,math
import h5py,numpy as np
from numba import njit
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=2048;TRAIN=1024;P=32;TB=1024;BEAM=4;NB_COST=16
REGIONS=(('hard',512),('easy',2304));STEPS=(240,256)

def zig1(k):
    k=int(k);return (k<<1)^(k>>63)

def train_bit_cost(K):
    nctx=9*9*NB_COST*4;cnt=np.full((nctx,2),0.5,np.float64)
    for t in range(min(TRAIN,K.shape[1])):
        for c in range(C):
            prev=int(K[c,t-1]) if t else 0;left=int(K[c-1,t]) if c else 0;pref=0;val=zig1(int(K[c,t]))
            for bp in range(NB_COST-1,-1,-1):
                bit=(val>>bp)&1;pos=NB_COST-1-bp;cx=a.ctx(prev,left,pos,pref,NB_COST);cnt[cx,bit]+=1.;pref=((pref<<1)|bit)&3
    p=cnt/cnt.sum(axis=1,keepdims=True)
    return -np.log2(p).astype(np.float64)

@njit(cache=True)
def clip4n(x):
    if x<-4:return 0
    if x>4:return 8
    return x+4

@njit(cache=True)
def bitcost(k,prev,left,cost):
    u=(k<<1)^(k>>63);pref=0;s=0.0
    for bp in range(NB_COST-1,-1,-1):
        bit=(u>>bp)&1;pos=NB_COST-1-bp;cx=(((clip4n(prev)*9+clip4n(left))*NB_COST+pos)*4+pref);s+=cost[cx,bit];pref=((pref<<1)|bit)&3
    return s

@njit(cache=True)
def optimize_channel(x,co,left,step,eps,cost):
    # Beam state keeps the exact last 32 reconstructed source values.
    hist=np.zeros((BEAM,P),np.int32);bcost=np.full(BEAM,1e300,np.float64);prevk=np.zeros(BEAM,np.int32);bcost[0]=0.;nstate=1
    parent=np.full((NT,BEAM),-1,np.int16);pick=np.zeros((NT,BEAM),np.int32)
    a0=float(co[0]);b=co[1:].astype(np.float32)
    for t in range(NT):
        ecost=np.full(BEAM*3,1e300,np.float64);eparent=np.full(BEAM*3,-1,np.int16);ek=np.zeros(BEAM*3,np.int32);er=np.zeros(BEAM*3,np.int32);ne=0
        for s0 in range(nstate):
            pred=0
            if t>=P:
                z=a0
                for j in range(P):z+=float(b[j])*float(hist[s0,P-1-j])
                pred=int(np.rint(z))
            lo=int(math.ceil((float(x[t])-eps-float(pred))/float(step)))
            hi=int(math.floor((float(x[t])+eps-float(pred))/float(step)))
            if hi<lo:continue
            # h>=240 and 2eps<268 => at most two legal integers, but allow 3 defensively.
            for k in range(lo,hi+1):
                if ne>=BEAM*3:break
                r=pred+step*k
                ecost[ne]=bcost[s0]+bitcost(k,int(prevk[s0]),int(left[t]),cost)
                eparent[ne]=s0;ek[ne]=k;er[ne]=r;ne+=1
        if ne==0:raise RuntimeError('no legal beam state')
        order=np.argsort(ecost[:ne]);newn=min(BEAM,ne);nh=np.zeros_like(hist);nc=np.full(BEAM,1e300,np.float64);npk=np.zeros(BEAM,np.int32)
        for q in range(newn):
            e=int(order[q]);ps=int(eparent[e]);nc[q]=ecost[e];npk[q]=ek[e];parent[t,q]=ps;pick[t,q]=ek[e]
            if t>=P:
                for j in range(P-1):nh[q,j]=hist[ps,j+1]
                nh[q,P-1]=er[e]
            else:
                # Maintain the newest values right-aligned until the history is full.
                for j in range(P-1):nh[q,j]=hist[ps,j+1]
                nh[q,P-1]=er[e]
        hist=nh;bcost=nc;prevk=npk;nstate=newn
    state=0
    best=bcost[0]
    for s0 in range(1,nstate):
        if bcost[s0]<best:best=bcost[s0];state=s0
    out=np.zeros(NT,np.int32)
    for t in range(NT-1,-1,-1):
        out[t]=pick[t,state];state=int(parent[t,state])
        if t and state<0:raise RuntimeError('bad backpointer')
    return out

@njit(cache=True)
def decode_step(K,co,step):
    R=np.zeros(K.shape,np.int32);aa=float(co[0]);b=co[1:].astype(np.float32)
    for c in range(K.shape[0]):
        for t in range(K.shape[1]):
            p=0
            if t>=P:
                z=aa
                for j in range(P):z+=float(b[j])*float(R[c,t-1-j])
                p=int(np.rint(z))
            R[c,t]=p+step*int(K[c,t])
    return R

def main(path):
    a.C=C;a.NT=NT;a.TRAIN=TRAIN
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gs=a.m.stats(d);eps=.1*gs;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=a.fits(X);R0,K0=a.run_ar(X,co);base,_,_,K0d=a.arithmetic(K0);R0d=a.decode_source(K0d,co)
            me0=float(np.max(np.abs(X-R0d.astype(np.float64))))
            if not np.array_equal(K0d,K0) or me0>eps*(1+1e-12):raise RuntimeError((region,'baseline',me0,eps))
            costs=train_bit_cost(K0);sz=0
            for t0 in range(0,NT,TB):bb,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(bb)
            vv=[]
            for step in STEPS:
                K=np.zeros_like(K0)
                for c in range(C):
                    left=K[c-1] if c else np.zeros(NT,np.int32)
                    K[c]=optimize_channel(X[c],co,left,step,eps,costs)
                R=decode_step(K,co,step);me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,step,'beam hard',me,eps))
                bb,nbits,sbits,Kd=a.arithmetic(K);Rd=decode_step(Kd,co,step);dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((region,step,'decode',dme,eps))
                total=bb+1
                z={'step':step,'beam':BEAM,'bytes':int(total),'bps':8*total/X.size,'gain_vs_step267':float(base/total),'gain_vs_sz3':float(sz/total),'ratio_to_2x':float(total/(sz/2)),'k_zero':float(np.mean(K==0)),'k_std':float(np.std(K)),'maxerr':dme,'arithmetic_bits':int(nbits),'symbol_bits':int(sbits)}
                vv.append(z);print(json.dumps({'region':region,'candidate':z},indent=2),flush=True)
            best=min(vv,key=lambda z:z['bytes']);row={'region':region,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':vv};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'eps':eps,'beam':BEAM,'steps':list(STEPS),'rows':rows,'scope':'Decoder-real sequence-level legal reconstruction gate. The shared prefix-only Huber AR32 model is unchanged, but step240 and step256 lattices are dense enough that many source +/-epsilon intervals contain multiple legal decoder states. A width-4 beam is run independently per channel while preserving the exact recursive AR32 state. Beam branch costs use a static bit cross-entropy table trained only from the baseline t<1024 K prefix with the same clipped previous-K/current-left/bit-position/two-bit-prefix context geometry as the real arithmetic coder; this score is encoder-side only and contributes zero claimed bytes. The selected complete K path is then encoded from scratch by the real cold-start adaptive arithmetic coder, exactly decoded, replayed through the candidate step, and independently hard-error checked. One step-selector byte is charged. This tests sequence-coupled reconstruction freedom, not memoryless scalar cell redesign. No AI. Draft/do not merge.'},open('imperial_ar32_legal_lattice_beam.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])