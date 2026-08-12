import json,math,struct,sys
import numpy as np

# Reuse PR #176's exact modern run/Rice/backend codec and geometry/outlier
# machinery. This experiment changes only how legal reconstruction states are
# selected before those lossless integer coders see them.
src=open('research/soda_tight_rice_frames.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_rice_frames.py','exec'),globals())

SMAG=b'STICKY01'
SHDR='<8sddBBBQQ'
SHS=struct.calcsize(SHDR)
MODES={0:('nearest-2eps',2.0),1:('sticky-1.5eps',1.5),2:('sticky-1.0eps',1.0),3:('sticky-0.5eps',0.5)}


def sticky_trace(x,eps,step):
    xd=np.asarray(x,np.float64)
    lo=np.ceil((xd-eps)/step-1e-12).astype(np.int32)
    hi=np.floor((xd+eps)/step+1e-12).astype(np.int32)
    if np.any(lo>hi):raise RuntimeError('empty legal sticky interval')
    q=np.empty(xd.size,np.int32)
    q[0]=int(np.clip(np.rint(xd[0]/step),lo[0],hi[0]))
    for t in range(1,xd.size):
        p=int(q[t-1]);L=int(lo[t]);H=int(hi[t])
        q[t]=L if p<L else (H if p>H else p)
    me=float(np.max(np.abs(xd-q.astype(np.float64)*step)))
    if me>eps*(1+1e-10):raise RuntimeError(('sticky legality',me,eps,step))
    return q


def make_states(X,tm,outids,shape,eps,mode):
    name,mult=MODES[mode];step=eps*mult;G=np.zeros(shape,np.int32)
    if mode==0:
        for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
        O=np.rint(X[outids]/step).astype(np.int32)
    else:
        for tid,c,l,s in tm:G[c,l,s]=sticky_trace(X[tid],eps,step)
        O=np.empty((len(outids),X.shape[1]),np.int32)
        for j,tid in enumerate(outids.tolist()):O[j]=sticky_trace(X[tid],eps,step)
    return G,O,step,name


def best_integer_container(K,O):
    bo=best_out(O);RO=decode_outlier(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('sticky outlier exact decode')
    cache=structural_sequences(K);rows=[]
    for r2 in (0,1):
        for r9 in (0,1):
            mb,parts=encode_main_candidate(K,r2,r9,cache);RK=decode_main_candidate(mb)
            if not np.array_equal(RK,K):raise RuntimeError(('sticky main exact K',r2,r9))
            rows.append((len(mb),r2,r9,mb,parts))
    rows.sort(key=lambda r:r[0]);return rows[0],bo,RO


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;raw=int(X.nbytes);G0,tm,outids,geom=geometry_map(X,gx,gy);results=[]
    for mode in sorted(MODES):
        G,O,step,name=make_states(X,tm,outids,G0.shape,internal_eps,mode);K=delta(G,3);best,bo,RO=best_integer_container(K,O);lm,r2,r9,mb,parts=best;outblob=bo[6];ok=0 if bo[1]=='gap' else 1;td=1 if bo[2] else 0
        top=struct.pack(SHDR,SMAG,internal_eps,step,mode,ok,td,len(mb),len(outblob))+mb+outblob
        # Full byte decode of the chosen integer representation.
        magic,ee,ss,mm,ook,tt,llm,llo=struct.unpack(SHDR,top[:SHS]);p=SHS;RK=decode_main_candidate(top[p:p+llm]);p+=llm;obb=top[p:p+llo];p+=llo
        if magic!=SMAG or p!=len(top) or mm!=mode:raise RuntimeError('sticky top header')
        Q=np.cumsum(RK,axis=3,dtype=np.int64).astype(np.int32)
        if ook==0:A=decode(obb).reshape(O.shape);RO2=undelta(A,1) if tt else A
        else:A=decode_out_sparse(obb);RO2=undelta(A,1) if tt else A
        if not np.array_equal(RO2,O):raise RuntimeError('sticky top outlier')
        Y=np.empty_like(X)
        for tid,c,l,s in tm:Y[tid]=Q[c,l,s].astype(np.float32)*np.float32(ss)
        Y[outids]=RO2.astype(np.float32)*np.float32(ss);me=float(np.max(np.abs(X-Y)))
        results.append({'mode':mode,'name':name,'step':step,'main_bytes':lm,'outlier_bytes':int(bo[0]),'container_bytes':len(top),'ratio':float(raw/len(top)),'K_nonzero_fraction':float(np.mean(K!=0)),'K_abs_mean':float(np.mean(np.abs(K.astype(np.float64)))),'rep_inter_rice':bool(r2),'rep_magnitude_rice':bool(r9),'main_parts':parts,'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6))})
        if not results[-1]['valid']:raise RuntimeError(('sticky final hard error',mode,me,public_eps))
    results.sort(key=lambda r:r['container_bytes']);best=results[0];szb,sze=sz3_bytes(X,public_eps);inc=[r for r in results if r['mode']==0][0]
    out={'file':path.split('/')[-1],'shape':list(X.shape),'std':std,'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'best':best,'all':results,'incumbent_nearest_2eps_bytes':inc['container_bytes'],'gain_vs_incumbent':float(inc['container_bytes']/best['container_bytes']),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/best['container_bytes'])}
    print(json.dumps({'epsilon_fraction_of_std':out['epsilon_fraction_of_std'],'best_name':best['name'],'best_bytes':best['container_bytes'],'incumbent_bytes':inc['container_bytes'],'gain_vs_incumbent':out['gain_vs_incumbent'],'gain_vs_direct_sz3':out['gain_vs_direct_sz3'],'K_nonzero_fraction':best['K_nonzero_fraction'],'maxerr':best['maxerr']},indent=2),flush=True);json.dump(out,open('soda_tight_sticky_lattice.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
