import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=8192;TB=1024
REGIONS=(('hard',512),('easy',2304))
MODES=('mean','full')

def clip4v(x): return int(max(-4,min(4,int(x))))+4

def ctx_mean(prev,left,right,pos,pref,nb,stage):
    m=int(np.rint((float(left)+float(right))/2.0))
    return ((((stage*9+clip4v(prev))*9+clip4v(m))*nb+pos)*4+pref)

def nctx_mean(nb): return 2*9*9*nb*4

def ctx_full(prev,left,right,pos,pref,nb,stage):
    return (((((stage*9+clip4v(prev))*9+clip4v(left))*9+clip4v(right))*nb+pos)*4+pref)

def nctx_full(nb): return 2*9*9*9*nb*4

def context(mode,prev,left,right,pos,pref,nb,stage):
    if mode=='mean': return ctx_mean(prev,left,right,pos,pref,nb,stage)
    return ctx_full(prev,left,right,pos,pref,nb,stage)

def nctx(mode,nb): return nctx_mean(nb) if mode=='mean' else nctx_full(nb)

def neighbors_anchor(K,c,t,phase):
    # Same-parity current-left anchor is already decoded in the first pass.
    left=int(K[c-2,t]) if c-2>=0 and ((c-2)&1)==phase else 0
    return left,0

def neighbors_target(K,c,t):
    left=int(K[c-1,t]) if c>0 else 0
    right=int(K[c+1,t]) if c+1<C else 0
    return left,right

def arithmetic_checker(K,phase,mode):
    u=a.zig(K);nb=max(1,int(u.max()).bit_length());E=a.AE(nctx(mode,nb))
    anchors=list(range(phase,C,2));targets=list(range(1-phase,C,2))
    for t in range(NT):
        for stage,chs in ((0,anchors),(1,targets)):
            for c in chs:
                prev=int(K[c,t-1]) if t else 0
                if stage==0:left,right=neighbors_anchor(K,c,t,phase)
                else:left,right=neighbors_target(K,c,t)
                pref=0;val=int(u[c,t])
                for bp in range(nb-1,-1,-1):
                    b=(val>>bp)&1;pos=nb-1-bp;cx=context(mode,prev,left,right,pos,pref,nb,stage);E.put(b,cx);pref=((pref<<1)|b)&3
    bb,nbit=E.finish();D=a.AD(bb,nbit,nctx(mode,nb));Kd=np.zeros_like(K)
    for t in range(NT):
        for stage,chs in ((0,anchors),(1,targets)):
            for c in chs:
                prev=int(Kd[c,t-1]) if t else 0
                if stage==0:left,right=neighbors_anchor(Kd,c,t,phase)
                else:left,right=neighbors_target(Kd,c,t)
                pref=0;val=0
                for bp in range(nb-1,-1,-1):
                    pos=nb-1-bp;cx=context(mode,prev,left,right,pos,pref,nb,stage);b=D.get(cx);val=(val<<1)|b;pref=((pref<<1)|b)&3
                Kd[c,t]=int(a.unzig(np.asarray([val],np.uint64))[0])
    if not np.array_equal(Kd,K):raise RuntimeError(('checker K decode',phase,mode))
    # incumbent framing + one selector byte for phase/mode
    return len(bb)+a.MODEL_BYTES+33,nbit,nb,Kd

def main(path):
    a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
        for region,c0 in REGIONS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
            base,basebits,basenb,Kbd=a.arithmetic(K);Rbd=a.decode_source(Kbd,hu)
            if not np.array_equal(Rbd,R):raise RuntimeError((region,'base replay'))
            candidates=[]
            for phase in (0,1):
                for mode in MODES:
                    n,bits,nb,Kd=arithmetic_checker(K,phase,mode);Rd=a.decode_source(Kd,hu)
                    me=float(np.max(np.abs(X-Rd.astype(np.float64))))
                    if me>eps*(1+1e-12):raise RuntimeError((region,phase,mode,'hard',me,eps))
                    candidates.append({'phase':phase,'mode':mode,'bytes':int(n),'bps':8*n/X.size,'gain_vs_baseline':base/n,'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me})
            sz=0
            for t0 in range(0,NT,TB):z,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(z)
            for q in candidates:q['gain_vs_sz3']=sz/q['bytes']
            best=min(candidates,key=lambda q:q['bytes'])
            row={'region':region,'c0':c0,'samples':int(X.size),'baseline_bytes':int(base),'baseline_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':candidates};rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':gstd,'eps':eps,'rows':rows,'scope':'Lossless parity-reordered entropy gate on the exact unchanged Huber AR32 step267 K field. At each time sample one channel parity is arithmetic-decoded first using previous-time K and same-parity current-left K. The opposite parity is then decoded with both immediate current left and right anchor K already known. Tests both anchor parities and either a compact rounded neighbor-mean context or the full clipped left/right pair. No source predictor, quantizer, or reconstruction changes; one selector byte is charged, exact K is decoded and the complete AR32 source is replayed under the unchanged hard-error bound. Hard/easy fast gate. No AI.'};json.dump(out,open('imperial_ar32_checkerboard_k_arithmetic.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
