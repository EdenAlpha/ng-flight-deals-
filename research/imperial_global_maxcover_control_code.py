import json,os,sys
import h5py,numpy as np
from scipy.optimize import milp,LinearConstraint,Bounds
from scipy.sparse import lil_matrix,vstack
sys.path.insert(0,os.path.dirname(__file__))
from imperial_correction_free_control_cover import stats,szrun,encode_int

PC=32;PT=64;SAFETY=1-1e-5
HFACT=(1.0,0.5)
PHASES=(1,3)
SPECS=(
 ('hard_start_a',0,512),('hard_start_b',14464,512),
 ('easy_a',0,1280),('easy_b',14464,2560),
 ('medium',14464,4480),('far_edge',14464,6880),
)


def solve_maxcover(ZX,bound,h,phi):
    cc=np.arange(PC)[:,None];tt=np.arange(PT)[None,:]
    mask=((cc+tt)&1)==0
    coords=np.argwhere(mask);n=len(coords)
    idx=-np.ones((PC,PT),np.int32)
    for k,(c,t) in enumerate(coords):idx[c,t]=k
    vals=ZX[mask]
    lo=np.ceil((vals-bound-phi)/h-1e-12).astype(np.int32)
    hi=np.floor((vals+bound-phi)/h+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal control set')
    q0=np.rint((vals-phi)/h).astype(np.int32)
    q0=np.minimum(np.maximum(q0,lo),hi)

    interior=[];neighbors=[];lowreq=[];highreq=[]
    for c in range(1,PC-1):
        for t in range(1,PT-1):
            if mask[c,t]:continue
            nb=np.asarray([idx[c-1,t],idx[c+1,t],idx[c,t-1],idx[c,t+1]],np.int32)
            if int(nb.min())<0:raise RuntimeError('checker topology')
            interior.append((c,t));neighbors.append(nb)
            lowreq.append(4.0*(ZX[c,t]-bound-phi)/h)
            highreq.append(4.0*(ZX[c,t]+bound-phi)/h)
    m=len(interior)

    # Variables: integer legal controls q[n], binary erase flags z[m], continuous |q-q0| deviations d[n].
    N=n+m+n
    cq=np.zeros(n);cz=-np.ones(m);cd=np.full(n,1e-5)
    obj=np.concatenate([cq,cz,cd])
    integ=np.concatenate([np.ones(n,np.int32),np.ones(m,np.int32),np.zeros(n,np.int32)])
    lb=np.concatenate([lo.astype(np.float64),np.zeros(m),np.zeros(n)])
    ub=np.concatenate([hi.astype(np.float64),np.ones(m),np.full(n,np.inf)])

    mats=[];lbs=[];ubs=[]
    A=lil_matrix((2*n,N),dtype=np.float64)
    for i in range(n):
        # q_i - d_i <= q0_i ; -q_i - d_i <= -q0_i
        A[2*i,i]=1.0;A[2*i,n+m+i]=-1.0;lbs.append(-np.inf);ubs.append(float(q0[i]))
        A[2*i+1,i]=-1.0;A[2*i+1,n+m+i]=-1.0;lbs.append(-np.inf);ubs.append(float(-q0[i]))
    mats.append(A.tocsr())

    B=lil_matrix((2*m,N),dtype=np.float64)
    for r,nb in enumerate(neighbors):
        natural_lo=float(lo[nb].sum());natural_hi=float(hi[nb].sum())
        L=float(lowreq[r]);U=float(highreq[r]);zcol=n+r
        # If z=0 these reduce exactly to the natural legal-control bounds.
        # If z=1 they enforce L <= sum(q_neighbors) <= U, which means the omitted
        # sample is already within +/-epsilon and needs no correction symbol.
        for j in nb:B[2*r,j]=1.0
        B[2*r,zcol]=-(L-natural_lo)
        lbs.append(natural_lo);ubs.append(np.inf)
        for j in nb:B[2*r+1,j]=1.0
        B[2*r+1,zcol]=(natural_hi-U)
        lbs.append(-np.inf);ubs.append(natural_hi)
    mats.append(B.tocsr())

    M=vstack(mats,format='csr')
    res=milp(obj,integrality=integ,bounds=Bounds(lb,ub),constraints=LinearConstraint(M,np.asarray(lbs),np.asarray(ubs)),
             options={'time_limit':20.0,'mip_rel_gap':0.0,'presolve':True})
    solved=bool(res.x is not None and np.all(np.isfinite(res.x[:n])))
    q=q0.copy() if not solved else np.rint(res.x[:n]).astype(np.int32)
    z=np.zeros(m,np.int8) if not solved else np.rint(res.x[n:n+m]).astype(np.int8)
    if np.any(q<lo)|np.any(q>hi):raise RuntimeError('illegal optimized control')
    Q=np.zeros((PC,PT),np.int32);Q[mask]=q
    return mask,Q,q0,interior,z,solved,int(getattr(res,'status',-1)),float(np.mean(hi-lo+1)),float(np.mean(q!=q0))


def evaluate(X,eps,hfac,phase):
    bound=eps*SAFETY
    sign=np.where(np.arange(PT)%2==0,1.0,-1.0)
    ZX=X*sign[None,:]
    h=hfac*bound;phi=h*phase/4.0
    mask,Q,q0,interior,z,solved,status,mean_states,changed=solve_maxcover(ZX,bound,h,phi)
    P=np.zeros_like(ZX);P[mask]=phi+h*Q[mask]
    for c,t in np.argwhere(~mask):
        sv=[];tv=[]
        if c>0:sv.append(P[c-1,t])
        if c+1<PC:sv.append(P[c+1,t])
        if t>0:tv.append(P[c,t-1])
        if t+1<PT:tv.append(P[c,t+1])
        ss=sum(sv)/len(sv) if sv else 0.0;ttv=sum(tv)/len(tv) if tv else 0.0
        P[c,t]=(ss+ttv)/2.0 if sv and tv else (ss if sv else ttv)
    miss=~mask
    K=np.rint((ZX[miss]-P[miss])/(2*bound)).astype(np.int32)
    P[miss]+=2*bound*K
    R=P*sign[None,:]
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard error',me,eps))
    km=np.zeros_like(mask,dtype=np.int32);km[miss]=K
    actual_zero=np.asarray([km[c,t]==0 for c,t in interior])
    # Optimizer erase flags are an audited mechanism diagnostic; numeric roundoff can only
    # make this check stricter, never create a compression win.
    claimed=np.asarray(z,dtype=bool)
    bad_claim=int(np.sum(claimed & ~actual_zero))
    if bad_claim:raise RuntimeError(('MILP zero claim failed after reconstruction',bad_claim))
    A0=Q[0::2,0::2];A1=Q[1::2,1::2]
    a0=encode_int(A0);a1=encode_int(A1);kr=encode_int(K)
    total=a0[0]+a1[0]+kr[0]+64
    return {'h_over_eps':hfac,'phase':phase,'bytes':total,'control_bytes':a0[0]+a1[0],
            'control_reps':[a0[1],a1[1]],'correction_bytes':kr[0],'correction_rep':kr[1],
            'correction_nonzero_fraction':float(np.mean(K!=0)),
            'interior_zero_fraction':float(np.mean(actual_zero)),
            'optimizer_erased_fraction':float(np.mean(claimed)),
            'solver_returned_solution':solved,'solver_status':status,
            'mean_legal_control_states':mean_states,'changed_control_fraction':changed,'maxerr':me}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std
        rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+PT,c0:c0+PC],np.float64).T
            sb=szrun(X,eps)
            tiles.append({'tile':name,'t0':t0,'c0':c0,'raw_bytes':X.size*2,'sz3_bytes':sb[0],'sz3_orientation':sb[1]})
            for hf in HFACT:
                for ph in PHASES:
                    r=evaluate(X,eps,hf,ph)
                    r.update({'tile':name,'t0':t0,'c0':c0,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/r['bytes'],'bps':8*r['bytes']/X.size})
                    rows.append(r)
        combos=[]
        for hf in HFACT:
            for ph in PHASES:
                rr=[r for r in rows if r['h_over_eps']==hf and r['phase']==ph]
                b=sum(r['bytes'] for r in rr);s=sum(t['sz3_bytes'] for t in tiles);n=sum(t['raw_bytes']//2 for t in tiles)
                combos.append({'h_over_eps':hf,'phase':ph,'bytes':b,'sz3_bytes':s,'gain_vs_sz3':s/b,'bps':8*b/n,
                               'solution_fraction':float(np.mean([r['solver_returned_solution'] for r in rr])),
                               'median_optimizer_erased_fraction':float(np.median([r['optimizer_erased_fraction'] for r in rr])),
                               'median_actual_interior_zero_fraction':float(np.median([r['interior_zero_fraction'] for r in rr])),
                               'median_all_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),
                               'median_legal_control_states':float(np.median([r['mean_legal_control_states'] for r in rr])),
                               'median_changed_controls':float(np.median([r['changed_control_fraction'] for r in rr])),
                               'control_bytes':sum(r['control_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),
                               'min_patch_gain':min(r['gain_vs_sz3'] for r in rr)})
        combos.sort(key=lambda x:x['bytes'])
        out={'std':std,'eps':eps,'patch_shape':[PC,PT],'specs':[list(x) for x in SPECS],
             'h_factors':list(HFACT),'phases':list(PHASES),'combos':combos,'rows':rows,
             'scope':'Global maximum-coverage legal control codeword screen. Every retained checkerboard control is an integer variable constrained by its own unchanged +/-10%-global-std interval. Every interior omitted sample gets a binary erase flag. One MILP maximizes the number of omitted samples simultaneously generated inside their own hard-error intervals, with a tiny secondary preference for controls near their nearest legal states. Remaining misses get fully counted exact 2epsilon corrections. Control/correction bytes are actually Zstd serialized and final samples are hard-error verified. Patch screen only, no whole-file claim.'}
        print(json.dumps({'best':combos},indent=2),flush=True)
        json.dump(out,open('imperial_global_maxcover_control_code.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
