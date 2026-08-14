import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;P=32;STEP=267;TB=1024
REGIONS=(("hard",512,4),("easy",2304,64))
PHASES=np.arange(-128,129,16,dtype=np.int32)
SELECTOR_BYTES=1

def activity(sumabs,count):
    if count<=0:return 0
    z=2*int(sumabs)
    for i,q in enumerate((1,3,7,15,31)):
        if z<=q*count:return i
    return 5

def clip4(x):return int(max(-4,min(4,int(x))))+4

def predictor(R,c,t,co):
    if t<P:return 0
    aa=float(co[0]);bb=np.asarray(co[1:],np.float32)
    return int(np.rint(aa+float(np.dot(bb,R[c,t-P:t][::-1].astype(np.float32)))))

def entropy_bits(vals):
    if len(vals)==0:return 0.0
    _,cnt=np.unique(vals,return_counts=True);p=cnt.astype(np.float64)/float(len(vals))
    return float(-np.sum(cnt*np.log2(p)))

def train_phases(X,Rb,Kb,co,W,use_activity):
    nact=6 if use_activity else 1
    buckets=[[[] for _ in range(nact)] for _ in range(9)]
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(TRAIN):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt) if use_activity else 0
            prev=int(Kb[c,t-1]) if t else 0
            p=int(Rb[c,t])-STEP*int(Kb[c,t])
            buckets[clip4(prev)][ac].append(float(X[c,t])-float(p))
            old=int(ring[c,pos]);new=abs(int(Kb[c,t]));ring[c,pos]=new;sums[c]+=new-old
    table=np.zeros((9,nact),np.int16);diag=[]
    for pc in range(9):
        for ac in range(nact):
            e=np.asarray(buckets[pc][ac],np.float64)
            if e.size<64:
                ph=0;best=entropy_bits(np.rint(e/STEP).astype(np.int32)) if e.size else 0.0
            else:
                scores=[]
                for ph0 in PHASES:
                    q=np.rint((e-float(ph0))/STEP).astype(np.int32)
                    scores.append(entropy_bits(q))
                ii=int(np.argmin(scores));ph=int(PHASES[ii]);best=float(scores[ii])
            table[pc,ac]=ph;diag.append({'prev_clip':pc-4,'activity':ac,'n':int(e.size),'phase':int(ph),'train_entropy_bits':float(best)})
    return table,diag

def run_phase(X,co,Rb,Kb,table,W,use_activity):
    R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32);R[:,:TRAIN]=Rb[:,:TRAIN];K[:,:TRAIN]=Kb[:,:TRAIN]
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    # Seed rolling state from decoded prefix exactly.
    for t in range(TRAIN):
        pos=t%W
        for c in range(C):
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    for t in range(TRAIN,NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt) if use_activity else 0;prev=int(K[c,t-1]);ph=int(table[clip4(prev),ac]);p=predictor(R,c,t,co)
            k=int(np.rint((float(X[c,t])-float(p)-ph)/STEP));K[c,t]=k;R[c,t]=p+ph+STEP*k
            old=int(ring[c,pos]);new=abs(k);ring[c,pos]=new;sums[c]+=new-old
    return R,K

def decode_phase(K,co,table,W,use_activity):
    R=np.zeros((C,NT),np.int32)
    # Prefix stays ordinary AR32.
    for c in range(C):
        for t in range(TRAIN):
            p=0 if t<P else predictor(R,c,t,co);R[c,t]=p+STEP*int(K[c,t])
    ring=np.zeros((C,W),np.int32);sums=np.zeros(C,np.int64)
    for t in range(TRAIN):
        pos=t%W
        for c in range(C):
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    for t in range(TRAIN,NT):
        pos=t%W;cnt=min(t,W)
        for c in range(C):
            ac=activity(sums[c],cnt) if use_activity else 0;prev=int(K[c,t-1]);ph=int(table[clip4(prev),ac]);p=predictor(R,c,t,co);R[c,t]=p+ph+STEP*int(K[c,t])
            old=int(ring[c,pos]);new=abs(int(K[c,t]));ring[c,pos]=new;sums[c]+=new-old
    return R

def arithmetic_activity(K,W):
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
    if not np.array_equal(Kd,K):raise RuntimeError('activity arithmetic decode')
    return len(bb)+a.MODEL_BYTES+33,int(nbit),int(nb),Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0,W in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,co=a.fits(X);Rb,Kb=a.run_ar(X,co)
            base,_,_,Kbd=a.arithmetic(Kb);act,_,_,Kad=arithmetic_activity(Kb,W)
            if not np.array_equal(a.decode_source(Kbd,co),Rb) or not np.array_equal(a.decode_source(Kad,co),Rb):raise RuntimeError((region,'control replay'))
            candidates=[]
            for ua in (False,True):
                table,diag=train_phases(X,Rb,Kb,co,W,ua);R,K=run_phase(X,co,Rb,Kb,table,W,ua);me=float(np.max(np.abs(X-R.astype(np.float64))))
                if me>eps*(1+1e-12):raise RuntimeError((region,ua,'encoder hard',me,eps))
                n,bits,nb,Kd=arithmetic_activity(K,W);n+=int(table.nbytes)+SELECTOR_BYTES
                Rd=decode_phase(Kd,co,table,W,ua)
                if not np.array_equal(Rd,R):raise RuntimeError((region,ua,'decoder replay'))
                dme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                tail=K[:,TRAIN:];q={'phase_context':'prev4_activity6' if ua else 'prev4','bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'gain_vs_activity_control':act/n,'phase_table_bytes':int(table.nbytes),'nonzero_phase_cells':int(np.count_nonzero(table)),'phase_min':int(table.min()),'phase_max':int(table.max()),'tail_zero_fraction':float(np.mean(tail==0)),'tail_k_std':float(np.std(tail.astype(np.float64))),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':dme};candidates.append(q);print(json.dumps({'region':region,'candidate':q},indent=2),flush=True)
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':float(eps),'activity_window':W,'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'activity_control_bytes':int(act),'activity_control_bps':8*act/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
        json.dump({'rows':rows,'phase_candidates':PHASES.tolist(),'scope':'Representation-level context-dependent legal lattice gate. The first 1024 samples use unchanged Huber AR32 step267. Encoder trains small phase tables from original prefix residuals, conditioned on previous K clipped +/-4, optionally plus decoder-known activity6; phase candidates are multiples of 16 in [-128,128] and each context chooses the phase minimizing prefix K empirical entropy. The table is transmitted raw int16 and fully charged. Tail reconstruction uses p+phase(context)+267*K, so nearest-lattice error remains <=133.5<epsilon. Candidate K and ordinary K are both coded with the same tuned activity arithmetic backend (W=4 hard, W=64 easy), exactly decoded, and full source replay/max-error checked. No AI. Draft/do not merge.'},open('imperial_ar32_context_phase_quantizer.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
