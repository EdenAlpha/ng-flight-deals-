import json,os,struct,sys
import numpy as np

# Freeze PR #160 exactly.  The only per-file adaptation is the already serialized
# per-frame choice among the same seven lossless backends.
src=open('research/soda_factor_backend_stack.py').read().split('\ndef main(path):')[0]
exec(compile(src,'soda_factor_backend_stack.py','exec'),globals())
STACK_SHS=SHS
SPARSE_SHS=struct.calcsize(SH)
EXPECTED={
  35:'F3622R1.SGY',
  45:'F4371R1.SGY',
  75:'F6618R1.SGY',
  85:'F7367R1.SGY',
}

def main(path,pct):
    pct=int(pct);order=(0,1,2)
    X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;rawbytes=X.nbytes
    G,tm,outids,geom=geometry_map(X,gx,gy)
    for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
    O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
    globals()['SHS']=STACK_SHS
    mb,parts=encode_main_stack(K,order,4);RK=decode_main_stack(mb)
    if not np.array_equal(RK,K):raise RuntimeError('hard4 main exact decode')
    globals()['SHS']=SPARSE_SHS
    bo=best_out(O);RO=decode_out_best(bo,O.shape)
    if not np.array_equal(RO,O):raise RuntimeError('hard4 outlier exact decode')
    RG=undelta(RK,3);recon=np.empty_like(X)
    for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(step)
    recon[outids]=RO.astype(np.float32)*np.float32(step)
    me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps);container=TOPS+len(mb)+int(bo[0])
    out={'percentile':pct,'expected_member':EXPECTED[pct],'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':rawbytes,'eps':eps,'geometry':geom,'K_nonzero_fraction':float(np.mean(K!=0)),'main_bytes':len(mb),'main_parts':parts,'outlier_bytes':int(bo[0]),'top_header_bytes':TOPS,'container_bytes':container,'ratio':float(rawbytes/container),'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'sz3':{'bytes':int(szb),'ratio':float(rawbytes/szb),'maxerr':float(sze)},'gain_vs_direct_sz3':float(szb/container),'frozen_representation':{'lattice_step':'2*eps','main_order':'C/L/S','inter_gap_context_mode':4,'first_arrival':'component-reset-delta','inter_run_value':'gap-minus-2','run_length_grammar':'singleton-and-length2-implicit','value_context':'run-phase','frame_backends':'serialized smallest of raw/zstd22/zstd19/lzma9e/bz2-9/zlib9/brotli11'}}
    if not out['valid']:raise RuntimeError(('hard error',me,eps))
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open(f'soda_factor_backend_p{pct}.json','w'),indent=2)

main(sys.argv[1],sys.argv[2])
