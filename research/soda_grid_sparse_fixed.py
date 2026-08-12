import json,os,struct,sys,numpy as np
# Reuse audited definitions, stopping before its median-shot CLI body.
src=open('research/soda_grid_sparse.py').read().split('\npath=sys.argv[1]')[0]
exec(compile(src,'soda_grid_sparse.py','exec'),globals())
path=sys.argv[1];X,gx,gy,dt=load(path);std=float(X.astype(np.float64).std());eps=.1*std;step=2*eps;raw=X.nbytes
G,tm,outids,geom=geometry_map(X,gx,gy)
for tid,c,l,s in tm:G[c,l,s]=np.rint(X[tid]/step).astype(np.int32)
O=np.rint(X[outids]/step).astype(np.int32);K=delta(G,3)
# Frozen from median-shot discovery: L,S,C,T ordering; sparse support/value representation; zstd-22.
main_perm=(1,2,0,3);main_rep=1;main_level=22
# Frozen outlier rule from median: direct lattice states, trace-major, raw integer stream, zstd-22.
out_perm=(0,1,2,3);out_rep=0;out_level=22;out_tdiff=False
mb=encode_array(K,main_perm,main_rep,main_level);OA=O;ob=encode_out_sparse(OA,out_perm,out_rep,out_level);top=struct.pack('<8sdQQ',b'STOPv001',eps,len(mb),len(ob))+mb+ob
p=struct.calcsize('<8sdQQ');_,ee,lm,lo=struct.unpack('<8sdQQ',top[:p]);RK=decode_array(top[p:p+lm]);RO=decode_out_sparse(top[p+lm:p+lm+lo]);RG=undelta(RK,3)
recon=np.empty_like(X)
for tid,c,l,s in tm:recon[tid]=RG[c,l,s].astype(np.float32)*np.float32(2*ee)
recon[outids]=RO.astype(np.float32)*np.float32(2*ee);me=float(np.max(np.abs(X-recon)));szb,sze=sz3_bytes(X,eps)
vals,counts=np.unique(K,return_counts=True);order=np.argsort(counts)[::-1]
out={'file':os.path.basename(path),'shape':list(X.shape),'raw_bytes':raw,'eps':eps,'geometry':geom,'main_bytes':len(mb),'outlier_bytes':len(ob),'container_bytes':len(top),'ratio':raw/len(top),'K_nonzero_fraction':float(np.mean(K!=0)),'K_top_values':[{'v':int(vals[i]),'count':int(counts[i])} for i in order[:8]],'maxerr':me,'valid':bool(me<=eps*(1+3e-6)),'frozen_mode':{'main_perm':list(main_perm),'main_rep':'sparse','main_level':main_level,'out_tdiff':out_tdiff,'out_rep':'raw','out_level':out_level},'sz3_file':{'bytes':szb,'ratio':raw/szb,'maxerr':sze}}
print(json.dumps(out,indent=2),flush=True);json.dump(out,open('soda_grid_sparse_fixed.json','w'),indent=2)
