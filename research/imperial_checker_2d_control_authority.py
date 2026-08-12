import json,math,os,sys
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from numba import njit
from research.imperial_spacetime_control_mesh import stats,szrun,rep2,encode_int

C=128;T=1024;SAFETY=1-1e-5
HF=(2.0,1.5,1.0,0.75);PH=(0,1);LAM=(0.0,0.2);MODES=(0,1);SWEEPS=4
SPECS=(('early',0,3392),('center',14488,3392),('edge',14488,6784),('late',28976,3392))

@njit(cache=True)
def pred_one(q,c,t,h,phi,nc,nt):
    ss=0.;sc=0;ts=0.;tc=0
    if c>0:ss+=phi+h*q[c-1,t];sc+=1
    if c+1<nc:ss+=phi+h*q[c+1,t];sc+=1
    if t>0:ts+=phi+h*q[c,t-1];tc+=1
    if t+1<nt:ts+=phi+h*q[c,t+1];tc+=1
    if sc and tc:return .5*(ss/sc+ts/tc)
    if sc:return ss/sc
    return ts/tc
@njit(cache=True)
def corr_cost(k,mode):
    a=abs(k)
    if a==0:return 0.0
    if mode==0:return 1.0+0.20*a
    return 1.0+math.log2(1.0+a)
@njit(cache=True)
def local_cost(q,c,t,Y,h,phi,hcorr,lam,mode,nc,nt):
    z=0.0
    # This control influences only its four opposite-parity neighbors.
    if c>0:
        p=pred_one(q,c-1,t,h,phi,nc,nt);k=int(np.rint((Y[c-1,t]-p)/hcorr));z+=corr_cost(k,mode)
    if c+1<nc:
        p=pred_one(q,c+1,t,h,phi,nc,nt);k=int(np.rint((Y[c+1,t]-p)/hcorr));z+=corr_cost(k,mode)
    if t>0:
        p=pred_one(q,c,t-1,h,phi,nc,nt);k=int(np.rint((Y[c,t-1]-p)/hcorr));z+=corr_cost(k,mode)
    if t+1<nt:
        p=pred_one(q,c,t+1,h,phi,nc,nt);k=int(np.rint((Y[c,t+1]-p)/hcorr));z+=corr_cost(k,mode)
    if lam>0:
        if c>=2:z+=lam*abs(q[c,t]-q[c-2,t])
        if c+2<nc:z+=lam*abs(q[c,t]-q[c+2,t])
        if t>=2:z+=lam*abs(q[c,t]-q[c,t-2])
        if t+2<nt:z+=lam*abs(q[c,t]-q[c,t+2])
    return z
@njit(cache=True)
def optimize(q,lo,hi,Y,h,phi,hcorr,lam,mode,sweeps):
    nc,nt=q.shape
    changed=0
    for sw in range(sweeps):
        cc=0
        for c in range(nc):
            for t in range(nt):
                if ((c+t)&1)!=0:continue
                old=q[c,t];best=old;bc=local_cost(q,c,t,Y,h,phi,hcorr,lam,mode,nc,nt)
                for v in range(lo[c,t],hi[c,t]+1):
                    if v==old:continue
                    q[c,t]=v;co=local_cost(q,c,t,Y,h,phi,hcorr,lam,mode,nc,nt)
                    if co<bc-1e-12:bc=co;best=v
                q[c,t]=best
                if best!=old:cc+=1
        changed+=cc
        if cc==0:break
    return changed

def build(X,bound,hfac,phase,lam,mode):
    nt=X.shape[1];sign=np.where(np.arange(nt)%2==0,1.0,-1.0);Y=X*sign[None,:];h=hfac*bound;phi=h*phase/4.0;hcorr=2*bound
    cc=np.arange(C)[:,None];tt=np.arange(nt)[None,:];mask=((cc+tt)&1)==0
    lo=np.zeros(X.shape,np.int32);hi=np.zeros(X.shape,np.int32);q=np.zeros(X.shape,np.int32)
    lo[mask]=np.ceil((Y[mask]-bound-phi)/h).astype(np.int32);hi[mask]=np.floor((Y[mask]+bound-phi)/h).astype(np.int32)
    if np.any(lo[mask]>hi[mask]):raise RuntimeError(('empty control state',hfac,phase))
    q[mask]=np.rint((Y[mask]-phi)/h).astype(np.int32);q[mask]=np.minimum(np.maximum(q[mask],lo[mask]),hi[mask])
    before=q.copy();changed=optimize(q,lo,hi,Y,h,phi,hcorr,lam,mode,SWEEPS)
    P=np.zeros_like(Y);P[mask]=phi+h*q[mask]
    for c,t in np.argwhere(~mask):P[c,t]=pred_one(q,int(c),int(t),h,phi,C,nt)
    K=np.rint((Y[~mask]-P[~mask])/hcorr).astype(np.int32);P[~mask]+=hcorr*K;R=P*sign[None,:]
    me=float(np.max(np.abs(X-R)))
    if not math.isfinite(me) or me>bound/SAFETY*(1+5e-6):raise RuntimeError(('hard',hfac,phase,lam,mode,me,bound/SAFETY))
    if float(np.max(np.abs(Y[mask]-(phi+h*q[mask]))))>bound*(1+1e-9):raise RuntimeError('control legal')
    A0=q[0::2,0::2].copy();A1=q[1::2,1::2].copy();a0=rep2(A0);a1=rep2(A1);kr=encode_int(K);total=a0[0]+a1[0]+kr[0]+160
    return {'h_over_eps':hfac,'phase':phase,'lambda':lam,'cost_mode':mode,'bytes':total,'control_bytes':a0[0]+a1[0],'correction_bytes':kr[0],'control_reps':[a0[1],a1[1]],'correction_rep':kr[1],'correction_nonzero_fraction':float(np.mean(K!=0)),'correction_abs1_fraction':float(np.mean(np.abs(K)==1)),'mean_legal_states':float(np.mean((hi-lo+1)[mask])),'changed_control_fraction':float(np.mean(q[mask]!=before[mask])),'optimizer_changes':int(changed),'maxerr':me}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;bound=eps*SAFETY;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb=szrun(X,eps);tiles.append((name,sb))
   for hf in HF:
    for ph in PH:
     for lam in LAM:
      for mode in MODES:
       r=build(X,bound,hf,ph,lam,mode);r.update(tile=name,sz3_bytes=sb,gain_vs_sz3=sb/r['bytes'],bps=8*r['bytes']/X.size);rows.append(r)
  ss=sum(x[1] for x in tiles);comb=[]
  for hf in HF:
   for ph in PH:
    for lam in LAM:
     for mode in MODES:
      rr=[r for r in rows if r['h_over_eps']==hf and r['phase']==ph and r['lambda']==lam and r['cost_mode']==mode];bb=sum(r['bytes'] for r in rr)
      comb.append({'h_over_eps':hf,'phase':ph,'lambda':lam,'cost_mode':mode,'bytes':bb,'sz3_bytes':ss,'gain_vs_sz3':ss/bb,'bps':8*bb/(C*T*len(rr)),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'control_bytes':sum(r['control_bytes'] for r in rr),'correction_bytes':sum(r['correction_bytes'] for r in rr),'median_correction_nonzero':float(np.median([r['correction_nonzero_fraction'] for r in rr])),'median_legal_states':float(np.median([r['mean_legal_states'] for r in rr])),'median_changed_controls':float(np.median([r['changed_control_fraction'] for r in rr]))})
  comb.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'parent_pr236_gain':1.1172624554910702,'parent_pr236_bps':2.7211761474609375,'two_x_target_bps':1.6659195794753086,'combos':comb,'rows':rows,'scope':'2-D legal-control authority screen. Checkerboard controls are no longer nearest fixed states: each retained control selects among all legal lattice states and a 2-D coordinate-descent objective spends that freedom on the four surrounding omitted samples plus optional same-sublattice smoothness. Missing corrections remain exact 2eps symbols; control and correction streams use the parent PR236 realized backends and all final hard errors are verified. One fixed definition across four tiles; no AI.'};print(json.dumps({'best':comb[:12]},indent=2),flush=True);json.dump(out,open('imperial_checker_2d_control_authority.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
