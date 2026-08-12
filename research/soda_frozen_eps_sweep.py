import json,os,struct,sys
import numpy as np

src=open('research/soda_intergap_backend_hybrid.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_intergap_backend_hybrid.py','exec'),globals())

FROZEN_METHODS=(3,3,3,3,3,3,0,3,3,3)
FROZEN_ORDER=(0,1,2)
FROZEN_CTXMODE=4
# Numerical safety only: public fidelity remains frac*std. The lattice uses a
# slightly smaller internal epsilon so float32 reconstruction cannot overshoot
# the requested public hard bound by rounding at very tight tolerances.
INTERNAL_SAFETY=1.0-1e-4

def encode_main_fixed(K):
    sh,dc,rawframes,meta=prepare_raw_frames(K,FROZEN_ORDER,FROZEN_CTXMODE);frames=[]
    for i,(r,m) in enumerate(zip(rawframes,FROZEN_METHODS)):
        b=comp_one(r,m)
        if decomp_one(b,m)!=r:raise RuntimeError(('backend roundtrip',i,m))
        frames.append(b)
    oc=int(FROZEN_ORDER[0]|(FROZEN_ORDER[1]<<2)|(FROZEN_ORDER[2]<<4));h=struct.pack(HHDR,HMAG,1,oc,dc,FROZEN_CTXMODE,*K.shape,*FROZEN_METHODS,*[len(x) for x in frames])
    names=['run_counts','first_starts','inter_starts','long_support','very_support','long_residual','sign_first','sign_repeat','exception_support','exception_magnitude']
    parts={names[i]:len(frames[i]) for i in range(10)};parts['timing_bytes']=sum(len(x) for x in frames[:6]);parts['value_bytes']=sum(len(x) for x in frames[6:]);parts['header_bytes']=HHS;parts.update(meta)
    return h+b''.join(frames),parts

def main(path,frac):
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());public_eps=float(frac)*std;internal_eps=public_eps*INTERNAL_SAFETY;step=2*internal_eps;raw=int(X.nbytes)
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('outlier decode')
    mb,parts=encode_main_fixed(K);RK=decode_main(mb)
    if not np.array_equal(RK,K):raise RuntimeError('main decode')
    RG=undelta(RK,3);Y=np.empty_like(X)
    for tid,c,l,s in tm:Y[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    Y[outids]=RO.astype(np.float32)*np.float32(step)
    me=float(np.max(np.abs(X-Y)));container=TOPS+len(mb)+int(bo[0]);szb,sze=sz3_bytes(X,public_eps)
    out={'file':os.path.basename(path),'shape':list(X.shape),'std':std,'epsilon_fraction_of_std':float(frac),'public_eps':public_eps,'internal_eps':internal_eps,'internal_safety':INTERNAL_SAFETY,'step':step,'raw_bytes':raw,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'main_parts':parts,'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(raw/container),'maxerr':me,'valid':bool(me<=public_eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(raw/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'frozen_definition':{'order':list(FROZEN_ORDER),'context_mode':FROZEN_CTXMODE,'backend_method_ids':list(FROZEN_METHODS)}}
    if not out['valid']:raise RuntimeError(('hard error',me,public_eps,internal_eps))
    print(json.dumps({'frac':frac,'public_eps':public_eps,'internal_eps':internal_eps,'bytes':container,'ratio':out['ratio'],'sz3_bytes':int(szb),'gain_sz3':out['gain_vs_direct_sz3'],'K_nonzero_fraction':out['K_nonzero_fraction'],'maxerr':me},indent=2),flush=True)
    json.dump(out,open('soda_frozen_eps_sweep.json','w'),indent=2)

main(sys.argv[1],float(sys.argv[2]))
