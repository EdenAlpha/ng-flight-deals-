import json,sys
import h5py,numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_ar32_nonlocal_zsm_stack as z

P=32;T0=1024;T1=4096;SEL=np.asarray([0,32,64,96],np.int64);REGIONS=(('hard',512),('easy',2304));WINDOWS=(4,8,64)


def zsm_local(K):
    oldc,oldn=z.C,z.NT;z.C,z.NT=K.shape
    try:
        out=[]
        for W in WINDOWS:
            bb,nb=z.encode_zsm(K,W);D=z.decode_zsm(bb,nb,W)
            if not np.array_equal(D,K):raise RuntimeError(('zsm',W))
            out.append({'window':W,'bytes':len(bb)+a.MODEL_BYTES+33,'bps':8*(len(bb)+a.MODEL_BYTES+33)/K.size,'bits':int(nb)})
        return min(out,key=lambda q:q['bytes']),out
    finally:z.C,z.NT=oldc,oldn


def replay(S,seed,co,step):
    C,N=S.shape;R=np.empty((C,N),np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    for c in range(C):
        hist=np.asarray(seed[c],np.int32).copy()
        for i in range(N):
            p=int(np.rint(aa+float(np.dot(b,hist[::-1].astype(np.float32)))))
            r=p+step*int(S[c,i]);R[c,i]=r;hist[:-1]=hist[1:];hist[-1]=r
    return R


def greedy(X,seed,co,eps):
    C,N=X.shape;R=np.empty((C,N),np.int32);D=np.empty((C,N),np.int32);aa=float(co[0]);b=np.asarray(co[1:],np.float32)
    lo=np.ceil(X-eps).astype(np.int64);hi=np.floor(X+eps).astype(np.int64)
    for c in range(C):
        hist=np.asarray(seed[c],np.int32).copy()
        for i in range(N):
            p=int(np.rint(aa+float(np.dot(b,hist[::-1].astype(np.float32)))))
            r=int(lo[c,i]) if p<int(lo[c,i]) else (int(hi[c,i]) if p>int(hi[c,i]) else p)
            D[c,i]=r-p;R[c,i]=r;hist[:-1]=hist[1:];hist[-1]=r
    return R,D


def solve_channel(x,seed,co,eps):
    n=len(x);aa=float(co[0]);b=np.asarray(co[1:],np.float64);nr=2*n
    rr=[];cc=[];vv=[];bub=np.empty(2*n,np.float64)
    for i in range(n):
        const=aa
        # e_i = r_i - const - sum(variable lag terms)
        rr.extend((2*i,2*i+1,2*i,2*i+1));cc.extend((i,i,n+i,n+i));vv.extend((1.0,-1.0,-1.0,-1.0))
        for lag in range(1,P+1):
            j=i-lag;coef=float(b[lag-1])
            if j>=0:
                rr.extend((2*i,2*i+1));cc.extend((j,j));vv.extend((-coef,coef))
            else:const+=coef*float(seed[P+j])
        bub[2*i]=const;bub[2*i+1]=-const
    A=coo_matrix((np.asarray(vv), (np.asarray(rr),np.asarray(cc))),shape=(2*n,nr)).tocsr()
    c=np.zeros(nr,np.float64);c[n:]=1.0
    lo=np.ceil(x-eps).astype(np.int64);hi=np.floor(x+eps).astype(np.int64)
    bounds=[(float(lo[i]),float(hi[i])) for i in range(n)]+[(0,None)]*n
    res=linprog(c,A_ub=A,b_ub=bub,bounds=bounds,method='highs',options={'presolve':True})
    if not res.success:raise RuntimeError(('linprog',res.status,res.message))
    r=np.rint(res.x[:n]).astype(np.int64);r=np.minimum(hi,np.maximum(lo,r)).astype(np.int32)
    # Convert the optimized legal path into exact decoder-real integer corrections.
    D=np.empty(n,np.int32);hist=np.asarray(seed,np.int32).copy();af=float(co[0]);bf=np.asarray(co[1:],np.float32)
    for i in range(n):
        p=int(np.rint(af+float(np.dot(bf,hist[::-1].astype(np.float32)))));D[i]=int(r[i])-p;hist[:-1]=hist[1:];hist[-1]=int(r[i])
    return r,D,float(res.fun)


def main(path):
    a.C=128;a.NT=8192
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=a.m.stats(ds);eps=.1*std;rows=[]
        for region,c0 in REGIONS:
            Xfull=np.asarray(ds[:8192,c0:c0+128],np.float64).T;_,co=a.fits(Xfull);Rb,Kb=a.run_ar(Xfull,co)
            X=Xfull[SEL,T0:T1];seed=Rb[SEL,T0-P:T0].copy();K0=Kb[SEL,T0:T1].copy();R0=replay(K0,seed,co,267)
            if not np.array_equal(R0,Rb[SEL,T0:T1]):raise RuntimeError((region,'base replay'))
            base,_=zsm_local(K0)
            Rg,Dg=greedy(X,seed,co,eps);gre,_=zsm_local(Dg);Rgd=replay(Dg,seed,co,1)
            if not np.array_equal(Rg,Rgd):raise RuntimeError((region,'greedy replay'))
            RL=[];DL=[];objs=[]
            for q,c in enumerate(SEL):
                r,d,obj=solve_channel(X[q],seed[q],co,eps);RL.append(r);DL.append(d);objs.append(obj)
                print(json.dumps({'region':region,'channel':int(c),'lp_objective':obj,'zero_fraction':float(np.mean(d==0)),'mean_abs_correction':float(np.mean(np.abs(d.astype(np.float64))))}),flush=True)
            RL=np.asarray(RL,np.int32);DL=np.asarray(DL,np.int32);Rld=replay(DL,seed,co,1)
            if not np.array_equal(RL,Rld):raise RuntimeError((region,'lp replay'))
            me=float(np.max(np.abs(X-RL.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((region,'lp hard',me,eps))
            lp,lpc=zsm_local(DL)
            sz,_=a.m.szrun(np.ascontiguousarray(X.astype(np.float32)),eps)
            row={'region':region,'c0':c0,'selected_channels':[int(x) for x in SEL],'target_interval':[T0,T1],'samples':int(X.size),'matched_sz3_bytes':int(sz),'matched_sz3_bps':8*int(sz)/X.size,
                 'step267':{**base,'zero_fraction':float(np.mean(K0==0)),'mean_abs_symbol':float(np.mean(np.abs(K0.astype(np.float64))))},
                 'greedy_interval':{**gre,'zero_fraction':float(np.mean(Dg==0)),'mean_abs_correction':float(np.mean(np.abs(Dg.astype(np.float64)))),'maxerr':float(np.max(np.abs(X-Rg.astype(np.float64))))},
                 'l1_optimized_trajectory':{**lp,'candidates':lpc,'zero_fraction':float(np.mean(DL==0)),'mean_abs_correction':float(np.mean(np.abs(DL.astype(np.float64)))),'std_correction':float(np.std(DL.astype(np.float64))),'continuous_l1_objective':float(np.sum(objs)),'maxerr':me},
                 'gain_lp_vs_step267':base['bytes']/lp['bytes'],'gain_lp_vs_greedy':gre['bytes']/lp['bytes'],'gain_lp_vs_sz3':int(sz)/lp['bytes']}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
        out={'global_std':float(std),'eps':float(eps),'ar_order':P,'rows':rows,'scope':'Encoder-heavy legal-trajectory optimization gate. Huber AR32 coefficients and the already decoded t<1024 seed are fixed. For each selected hard/easy channel, scipy/HiGHS solves a global box-constrained linear program over t=1024..4095: choose every reconstruction sample inside its exact integer-safe public error interval while minimizing the L1 norm of the unrounded AR32 innovation over the whole trajectory. The optimized path is rounded/clipped to legal integers, then converted into the exact correction D required by the real rounded decoder recurrence. The decoder does not solve the LP: it only decodes D with the existing exact ZSM backend and recursively replays the source. Full exact replay and max-error checks are mandatory. Incumbent step267 and greedy nearest-boundary interval projection are rerun from the identical seed. This is a small-region gate, not a whole-array claim. No AI.'}
        json.dump(out,open('imperial_ar32_l1_trajectory_optimization.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
