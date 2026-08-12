import json,math,os,sys
import numpy as np

# Reuse PR #195's exact factorized container, parity coder/decoder, refined
# run/Rice grammar, geometry and coarse outlier path without running its CLI.
src=open('research/soda_tight_factorized_state.py').read().rsplit('\nmain(sys.argv[1])',1)[0]
exec(compile(src,'soda_tight_factorized_state.py','exec'),globals())

# Precommitted scalar tradeoffs.  Segment boundaries are fixed by the exact
# minimum-change interval partition; these weights only choose WHICH legal
# integer state represents each already-fixed segment.
WEIGHTS=(1,2,4,8,16,32,64)


def trace_segments(x,eps,step):
    xd=x.astype(np.float64,copy=False);lo=np.ceil((xd-eps)/step-1e-12).astype(np.int32);hi=np.floor((xd+eps)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty parity-aware legal interval')
    n=x.size;segs=[];a=0;L=int(lo[0]);H=int(hi[0])
    for t in range(1,n):
        nL=max(L,int(lo[t]));nH=min(H,int(hi[t]))
        if nL<=nH:L,H=nL,nH
        else:segs.append((a,t,L,H));a=t;L=int(lo[t]);H=int(hi[t])
    segs.append((a,n,L,H));return segs


def edge_terms(d):
    a=abs(int(d));odd=a&1;v=(a+1)//2
    # Approximate the real normalized-value grammar: ±1 is cheap, larger V
    # enters the exception/magnitude side. Support event count is fixed by the
    # segment partition, so it is deliberately absent from the objective.
    exc=1 if v>1 else 0;tail=max(0,v-1)
    return odd,exc,tail


def solve_segments(segs,odd_weight):
    # Exact shortest path over every legal integer in each segment intersection.
    # Legal intersections are tiny for step=eps; no candidate is pruned.
    cand=[np.arange(L,H+1,dtype=np.int32) for _,_,L,H in segs]
    prev=cand[0];cost=np.empty(prev.size,np.float64);back=[]
    for j,q in enumerate(prev.tolist()):
        odd,exc,tail=edge_terms(q);cost[j]=odd_weight*odd+2.0*exc+float(tail)
    for si in range(1,len(cand)):
        cur=cand[si];nc=np.empty(cur.size,np.float64);bi=np.empty(cur.size,np.int16)
        for j,q in enumerate(cur.tolist()):
            best=1e300;bk=0
            for k,p in enumerate(prev.tolist()):
                odd,exc,tail=edge_terms(q-p);v=cost[k]+odd_weight*odd+2.0*exc+float(tail)
                if v<best-1e-12 or (abs(v-best)<=1e-12 and abs(q-p)<abs(q-int(prev[bk]))):best=v;bk=k
            nc[j]=best;bi[j]=bk
        back.append(bi);prev=cur;cost=nc
    j=int(np.argmin(cost));chosen=np.empty(len(cand),np.int32);chosen[-1]=cand[-1][j]
    for si in range(len(cand)-1,0,-1):j=int(back[si-1][j]);chosen[si-1]=cand[si-1][j]
    q=np.empty(segs[-1][1],np.int32)
    for v,(a,b,L,H) in zip(chosen.tolist(),segs):q[a:b]=v
    return q


def build_weight_states(X,tm,shape,eps,weight):
    step=eps;G=np.zeros(shape,np.int32);segments=0
    for tid,c,l,s in tm:
        segs=trace_segments(X[tid],eps,step);q=solve_segments(segs,weight);G[c,l,s]=q;segments+=len(segs)
        me=float(np.max(np.abs(X[tid].astype(np.float64)-q.astype(np.float64)*step)))
        if me>eps*(1+1e-10):raise RuntimeError(('parity-aware state legality',weight,tid,me,eps))
    return G,step,segments


def eval_weight(X,tm,outids,shape,internal_eps,weight,O,bo):
    G,step,segments=build_weight_states(X,tm,shape,internal_eps,weight);D=delta(G,3);V,R=normalize_delta(D,2);mb,parts=prepare_refined_main(V);RV=decode_refined_main(mb)
    if not np.array_equal(RV,V):raise RuntimeError(('parity-aware V decode',weight))
    pb,pmode,pmethod,pdiag=encode_parity(V,D);top=encode_top(internal_eps,step,mb,pb,pmode,pmethod,bo);ee,ss,DV,RD,RO=decode_top(top,O.shape)
    if not np.array_equal(DV,V) or not np.array_equal(RD,D) or not np.array_equal(RO,O):raise RuntimeError(('parity-aware integer decode',weight))
    Q=np.cumsum(RD,axis=3,dtype=np.int64).astype(np.int32);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=Q[c,l,s].astype(np.float32)*np.float32(ss)
    Y[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-Y)))
    return {'odd_weight':int(weight),'segments':int(segments),'container_bytes':len(top),'main_bytes':len(mb),'parity_bytes':len(pb),'outlier_bytes':int(bo[0]),'K_nonzero_fraction':float(np.mean(D!=0)),'normalized_V_abs_mean_events':float(np.mean(np.abs(V[V!=0]).astype(np.float64))) if np.any(V) else 0.0,'normalized_exception_fraction':float(np.mean(np.abs(V[V!=0])>1)) if np.any(V) else 0.0,'parity_ones_fraction':float(np.mean((np.abs(D[D!=0])&1)!=0)) if np.any(D) else 0.0,'parity_diag':pdiag,'main_parts':parts,'maxerr':me,'valid':bool(me<=internal_eps/INTERNAL_SAFETY*(1+3e-6))}


def main(path):
    frac=.05;X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=frac*std;internal_eps=public_eps*INTERNAL_SAFETY;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy);szb,sze=sz3_bytes(X,public_eps)
    # Exact PR #189 incumbent and exact PR #195 greedy factorized result for audit.
    inc0=eval_no_phase(X,tm,outids,G0.shape,internal_eps);incp=eval_phase(X,tm,outids,G0.shape,internal_eps);inc=min(inc0['container_bytes'],incp['container_bytes'])
    O=np.rint(X[outids].astype(np.float64)/(2*internal_eps)).astype(np.int32);bo=best_out(O);RO=decode_out_exact(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('parity-aware outlier exact decode')
    # Greedy PR #195 state selector, recomputed as control.
    GG,gs,gseg=build_fine_main(X,tm,G0.shape,internal_eps);GD=delta(GG,3);GV,GR=normalize_delta(GD,2);gmb,gparts=prepare_refined_main(GV);gpb,gpm,gpmet,gpd=encode_parity(GV,GD);gtop=encode_top(internal_eps,gs,gmb,gpb,gpm,gpmet,bo)
    greedy={'container_bytes':len(gtop),'main_bytes':len(gmb),'parity_bytes':len(gpb),'parity_ones_fraction':float(np.mean((np.abs(GD[GD!=0])&1)!=0)),'K_nonzero_fraction':float(np.mean(GD!=0))}
    rows=[]
    for w in WEIGHTS:
        print('WEIGHT',w,flush=True);r=eval_weight(X,tm,outids,G0.shape,internal_eps,w,O,bo)
        if not r['valid']:raise RuntimeError(('parity-aware hard error',w,r['maxerr'],public_eps));rows.append(r)
        print(json.dumps({k:r[k] for k in ('odd_weight','container_bytes','main_bytes','parity_bytes','parity_ones_fraction','normalized_exception_fraction','maxerr')},indent=2),flush=True)
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];target=szb/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':frac,'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'incumbent_best_bytes':int(inc),'greedy_factorized_control':greedy,'weights':rows,'best':best,'saving_vs_incumbent_bytes':int(inc-best['container_bytes']),'saving_vs_greedy_factorized_bytes':int(greedy['container_bytes']-best['container_bytes']),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/best['container_bytes']),'two_x_target_bytes':target,'clears_2x':bool(best['container_bytes']<=target)}
    print(json.dumps({'incumbent':inc,'greedy_factorized':greedy,'best_weight':best['odd_weight'],'best_bytes':best['container_bytes'],'parity_bytes':best['parity_bytes'],'parity_ones':best['parity_ones_fraction'],'saving_vs_incumbent':out['saving_vs_incumbent_bytes'],'gain_sz3':out['gain_vs_direct_sz3'],'target':target,'clears_2x':out['clears_2x']},indent=2),flush=True);json.dump(out,open('soda_tight_parity_aware_minchange.json','w'),indent=2)

main(sys.argv[1])
