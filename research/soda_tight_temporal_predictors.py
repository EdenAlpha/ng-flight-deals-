import json,sys
import numpy as np

# Reuse PR #175's exact loader, legal Q construction, outlier codec and audited
# residual representations/backends.  We intentionally stop before its main.
src=open('research/soda_tight_mixed_derivative.py').read().split('\ndef main(path,frac):')[0]
exec(compile(src,'soda_tight_mixed_derivative.py','exec'),globals())

PRED_NAMES={
  0:'diff2', 1:'diff3', 2:'diff4',
  3:'ar2_c1.5', 4:'ar2_c1.75', 5:'ar2_c1.875', 6:'ar2_c2.0'
}
AR={3:(3,2),4:(7,4),5:(15,8),6:(2,1)}


def time_diff_order(Q,order):
    R=np.asarray(Q,np.int32)
    for _ in range(order):R=delta_axis(R,3)
    return R

def undo_time_diff(R,order):
    Q=np.asarray(R,np.int32)
    for _ in range(order):Q=undelta_axis(Q,3)
    return Q


def ar_residual(Q,num,den):
    Q=np.asarray(Q,np.int32);R=np.empty_like(Q);R[...,0]=Q[...,0]
    if Q.shape[-1]>1:R[...,1]=Q[...,1]
    # floor division is deterministic for negative integers in Python/NumPy;
    # decoder uses the identical operation.  int64 avoids multiply overflow.
    for t in range(2,Q.shape[-1]):
        pred=np.floor_divide(num*Q[...,t-1].astype(np.int64),den)-Q[...,t-2].astype(np.int64)
        R[...,t]=(Q[...,t].astype(np.int64)-pred).astype(np.int32)
    return R

def undo_ar(R,num,den):
    R=np.asarray(R,np.int32);Q=np.empty_like(R);Q[...,0]=R[...,0]
    if R.shape[-1]>1:Q[...,1]=R[...,1]
    for t in range(2,R.shape[-1]):
        pred=np.floor_divide(num*Q[...,t-1].astype(np.int64),den)-Q[...,t-2].astype(np.int64)
        Q[...,t]=(R[...,t].astype(np.int64)+pred).astype(np.int32)
    return Q


def make_residual(Q,kind):
    if kind==0:return time_diff_order(Q,2)
    if kind==1:return time_diff_order(Q,3)
    if kind==2:return time_diff_order(Q,4)
    num,den=AR[kind];return ar_residual(Q,num,den)

def undo_residual(R,kind):
    if kind==0:return undo_time_diff(R,2)
    if kind==1:return undo_time_diff(R,3)
    if kind==2:return undo_time_diff(R,4)
    num,den=AR[kind];return undo_ar(R,num,den)


def encode_predictor(Q,kind,rep):
    R=make_residual(Q,kind)
    # mask=0 tells PR #175's audited residual container to return the residual
    # array exactly; predictor kind is an explicit counted byte outside it.
    rb,diag=encode_residual(R,0,rep);blob=bytes([kind])+rb
    RR=decode_residual(blob[1:]);RQ=undo_residual(RR,int(blob[0]))
    if not np.array_equal(RQ,Q):raise RuntimeError(('predictor exact decode',kind,rep))
    diag={**diag,'predictor_kind':kind,'predictor':PRED_NAMES[kind],'residual_nonzero_fraction':float(np.mean(R!=0)),'residual_abs_mean':float(np.mean(np.abs(R.astype(np.float64))))}
    return blob,diag


def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes)
    G0,tm,outids,geom=geometry_map(X,gx,gy);Q=np.asarray(G0,np.int32)
    for tid,c,l,s in tm:Q[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier exact decode')
    K=delta(Q,3);run_blob,run_parts=encode_main_fixed(K);RK=decode_main(run_blob)
    if not np.array_equal(RK,K):raise RuntimeError('incumbent exact decode')
    candidates=[{'kind':'frozen_run','bytes':len(run_blob),'blob':run_blob,'parts':run_parts,'predictor':'first-difference run grammar'}]
    # Precommitted predictor dictionary; representations are PR #175's four
    # exact dense/sparse/ternary/bitplane forms with raw/Zstd22/Brotli11.
    for kind in sorted(PRED_NAMES):
        for rep in range(4):
            b,d=encode_predictor(Q,kind,rep);candidates.append({'kind':'temporal_predictor','bytes':len(b),'blob':b,'diag':d})
    candidates.sort(key=lambda r:r['bytes']);best=candidates[0]
    if best['kind']=='frozen_run':BQ=undelta(decode_main(best['blob']),3)
    else:
        b=best['blob'];BQ=undo_residual(decode_residual(b[1:]),int(b[0]))
    Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=BQ[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-Y)));container=TOPS+int(best['bytes'])+int(bo[0]);inc=TOPS+len(run_blob)+int(bo[0]);szb,sze=sz3_bytes(X,public_eps)
    top=[]
    for r in candidates[:14]:
        x={k:v for k,v in r.items() if k not in ('blob','parts')};top.append(x)
    out={'file':path.split('/')[-1],'shape':list(X.shape),'std':std,'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'raw_bytes':raw,'geometry':geom,'Q_time_delta_nonzero_fraction':float(np.mean(K!=0)),'incumbent_container_bytes':inc,'best_kind':best['kind'],'best_main_bytes':int(best['bytes']),'best_detail':{k:v for k,v in best.items() if k not in ('blob','parts')},'top_candidates':top,'outlier_bytes':int(bo[0]),'container_bytes':container,'ratio':float(raw/container),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'gain_vs_incumbent':float(inc/container)}
    if not out['valid']:raise RuntimeError(('hard error',me,public_eps))
    print(json.dumps({k:out[k] for k in ('epsilon_fraction_of_std','best_kind','best_detail','incumbent_container_bytes','container_bytes','ratio','gain_vs_direct_sz3','gain_vs_incumbent','maxerr')},indent=2),flush=True);json.dump(out,open('soda_tight_temporal_predictors.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
