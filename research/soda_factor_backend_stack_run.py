import json,os,struct,sys
import numpy as np

# Load PR #160 implementation without invoking its main.  The original file's
# stack header used SHS, which is also the audited sparse codec's header-size
# global.  Preserve both values explicitly and switch only at the call boundary.
src=open('research/soda_factor_backend_stack.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_factor_backend_stack.py','exec'),globals())
STACK_SHS=SHS
SPARSE_SHS=struct.calcsize(SH)

def main(path):
    order=(0,1,2);X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes;G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    globals()['SHS']=STACK_SHS
    mb,parts=encode_main_stack(K,order,4);RK=decode_main_stack(mb)
    if not np.array_equal(RK,K):raise RuntimeError('stack main exact decode')
    globals()['SHS']=SPARSE_SHS
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('stack outlier exact decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+len(mb)+int(bo[0]);baseline=133225;gate=baseline/2
    out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'main_parts':parts,'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'strongest_verified_p75_baseline_bytes':baseline,'gain_vs_strongest_verified_p75_baseline':float(baseline/container),'two_x_gate_bytes':gate,'prior_record_bytes':65715,'clears_two_x_gate':bool(container<gate)}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_factor_backend_stack.json','w'),indent=2)

main(sys.argv[1])
