import json,math,os,struct,sys
import numpy as np
from numba import njit

# Reuse PR #176's exact structural byte codec, Rice options, geometry,
# outlier dictionary and direct-SZ3 benchmark.  Stop before its CLI main.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

OV_MAGIC=b'OVLAP001'; OV_HDR='<8sdBBQQ'; OV_HS=struct.calcsize(OV_HDR)
ALPHAS=(1.95,1.90,1.80,1.70,1.60,1.50)

@njit(cache=True)
def minchange_matrix(X,tol,step):
    # Exact minimum-number-of-segments path on a fixed overlapping integer
    # lattice.  A segment ends iff the intersection of all legal state
    # intervals becomes empty.  Within each new segment choose the legal state
    # closest to the previous state, minimizing that forced jump locally.
    ntr,nt=X.shape;Q=np.empty((ntr,nt),np.int32)
    for i in range(ntr):
        x0=float(X[i,0]);L=int(math.ceil((x0-tol)/step-1e-12));H=int(math.floor((x0+tol)/step+1e-12))
        if L>H:raise ValueError('empty first legal interval')
        start=0;have_prev=False;prev=0
        for t in range(1,nt):
            x=float(X[i,t]);l=int(math.ceil((x-tol)/step-1e-12));h=int(math.floor((x+tol)/step+1e-12))
            if l>h:raise ValueError('empty legal interval')
            nL=L if L>l else l;nH=H if H<h else h
            if nL<=nH:
                L=nL;H=nH
            else:
                if have_prev:
                    v=prev
                    if v<L:v=L
                    elif v>H:v=H
                else:
                    v=0
                    if v<L:v=L
                    elif v>H:v=H
                for u in range(start,t):Q[i,u]=v
                prev=v;have_prev=True;start=t;L=l;H=h
        if have_prev:
            v=prev
            if v<L:v=L
            elif v>H:v=H
        else:
            v=0
            if v<L:v=L
            elif v>H:v=H
        for u in range(start,nt):Q[i,u]=v
    return Q

def best_main_for_K(K):
    cache=structural_sequences(K);rows=[]
    for rep2 in (0,1):
        for rep9 in (0,1):
            b,parts=encode_main_candidate(K,rep2,rep9,cache);R=decode_main_candidate(b)
            if not np.array_equal(R,K):raise RuntimeError(('main exact decode',rep2,rep9))
            rows.append((len(b),rep2,rep9,b,parts))
    rows.sort(key=lambda r:r[0]);return rows[0],rows

def encode_assignment(X,Q,gx,gy,step,public_eps,internal_eps,szb,sze,label,alpha):
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=Q[tid]
    O=np.ascontiguousarray(Q[outids]);K=delta(G,3)
    bm,allm=best_main_for_K(K);mb=bm[3];parts=bm[4];bo=best_out(O);RO=decode_outlier(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError(('outlier exact decode',label))
    outblob=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0
    top=struct.pack(OV_HDR,OV_MAGIC,float(step),ok,td,len(mb),len(outblob))+mb+outblob
    magic,ss,ok2,td2,lm,lo=struct.unpack(OV_HDR,top[:OV_HS]);p=OV_HS;RK=decode_main_candidate(top[p:p+lm]);p+=lm;obb=top[p:p+lo];p+=lo
    if magic!=OV_MAGIC or p!=len(top) or not np.array_equal(RK,K):raise RuntimeError(('top main decode',label))
    if ok2==0:A=decode(obb).reshape(O.shape);RO2=undelta(A,1) if td2 else A
    else:A=decode_out_sparse(obb);RO2=undelta(A,1) if td2 else A
    if not np.array_equal(RO2,O):raise RuntimeError(('top outlier decode',label))
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(ss)
    Y[outids]=RO2.astype(np.float32)*np.float32(ss)
    me=float(np.max(np.abs(X-Y)));internal_me=float(np.max(np.abs(X.astype(np.float64)-Q.astype(np.float64)*float(step))))
    if internal_me>internal_eps*(1+2e-9):raise RuntimeError(('internal legal-state violation',label,internal_me,internal_eps))
    valid=bool(me<=public_eps*(1+3e-6))
    if not valid:raise RuntimeError(('public hard error',label,me,public_eps))
    return {'label':label,'alpha':alpha,'step':float(step),'container_bytes':len(top),'ratio':float(X.nbytes/len(top)),'gain_vs_direct_sz3':float(szb/len(top)),'maxerr':me,'internal_maxerr':internal_me,'valid':valid,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'outlier_bytes':len(outblob),'main_rep':{'inter_rice':bool(bm[1]),'magnitude_rice':bool(bm[2])},'main_parts':parts,'geometry':geom,'sz3_bytes':int(szb),'sz3_maxerr':float(sze)}

def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;szb,sze=sz3_bytes(X,public_eps);rows=[]
    # Incumbent: the ordinary nearest 2*internal_eps lattice, but judged by the
    # same exact PR #176 representation/backend dictionary as every challenger.
    step0=2.0*internal_eps;Q0=np.rint(X/step0).astype(np.int32)
    rows.append(encode_assignment(X,Q0,gx,gy,step0,public_eps,internal_eps,szb,sze,'nearest-2.0eps',2.0))
    for a in ALPHAS:
        step=float(a)*internal_eps;print('OVERLAP alpha',a,'step',step,flush=True);Q=minchange_matrix(X,internal_eps,step)
        r=encode_assignment(X,Q,gx,gy,step,public_eps,internal_eps,szb,sze,'minchange-overlap',float(a));rows.append(r)
        print(json.dumps({'alpha':a,'bytes':r['container_bytes'],'gain_sz3':r['gain_vs_direct_sz3'],'K_nonzero_fraction':r['K_nonzero_fraction'],'main_rep':r['main_rep']},indent=2),flush=True)
    rows.sort(key=lambda r:r['container_bytes']);best=rows[0];base=next(r for r in rows if r['alpha']==2.0)
    out={'file':os.path.basename(path),'shape':list(X.shape),'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'internal_safety':INTERNAL_SAFETY,'raw_bytes':int(X.nbytes),'sz3':{'bytes':int(szb),'ratio':float(X.nbytes/szb),'maxerr':float(sze)},'baseline':base,'best':best,'improvement_vs_nearest':float(base['container_bytes']/best['container_bytes']),'all':rows}
    print(json.dumps({'frac':frac,'baseline_bytes':base['container_bytes'],'baseline_gain':base['gain_vs_direct_sz3'],'best_alpha':best['alpha'],'best_bytes':best['container_bytes'],'best_gain':best['gain_vs_direct_sz3'],'improvement':out['improvement_vs_nearest']},indent=2),flush=True)
    json.dump(out,open('soda_tight_overlap_lattice.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
