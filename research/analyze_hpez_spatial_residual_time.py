import json,numpy as np,zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=coords.size or np.unique(coords).size!=q.size:raise SystemExit('bad coords')
center=32768;gvals=np.unique(q);gm=len(gvals);phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Q=phys.reshape(64,64,512);Z=zstd.ZstdCompressor(level=19)

def Hc(c):
 c=np.asarray(c,dtype=float);c=c[c>0]
 if not c.size:return 0.
 p=c/c.sum();return float(-(p*np.log2(p)).sum())
def Hid(a):
 _,c=np.unique(a,return_counts=True);return Hc(c)
def cond(target,*contexts):
 t=np.asarray(target).ravel();cs=[np.asarray(x).ravel() for x in contexts]
 _,ti=np.unique(t,return_inverse=True);mt=int(ti.max())+1
 C=np.stack(cs,1);v=C.view(np.dtype((np.void,C.dtype.itemsize*C.shape[1]))).ravel();_,ci=np.unique(v,return_inverse=True)
 return Hc(np.bincount(ci.astype(np.int64)*mt+ti,minlength=(int(ci.max())+1)*mt))-Hc(np.bincount(ci))
def make_class(p):
 # exact level1 parity class -> dense 32x32x256 array, preserving the two varying spatial cell coordinates and even-time index.
 ii,jj,tt=np.indices(Q.shape);m=(((ii&1)<<2)|((jj&1)<<1)|(tt&1))==p
 c=np.argwhere(m);A=np.empty((32,32,256),np.int32)
 # Map target coordinates to cell coordinates; odd/even parity both reduce by floor(/2).
 A[c[:,0]//2,c[:,1]//2,c[:,2]//2]=Q[m]
 return A
def compact(A): return np.searchsorted(gvals,A).astype(np.uint8 if gm<=256 else np.uint16)
def stream(A):
 ids=compact(A);raw=len(Z.compress(ids.tobytes()));tm=len(Z.compress(ids.transpose(2,0,1).tobytes()))
 # Temporal first difference in actual quantized lattice offsets, with sentinel split to its own mask.
 sentinel=A==0;D=np.where(sentinel,0,A-center).astype(np.int16);d=np.diff(D,axis=2,prepend=D[:,:,:1]);lo,hi=int(d.min()),int(d.max());dt=np.int8 if lo>=-128 and hi<=127 else np.int16
 dz=len(Z.compress(d.astype(dt).tobytes()));dzt=len(Z.compress(d.transpose(2,0,1).astype(dt).tobytes()))
 return {'raw_trace_major':raw,'raw_time_major':tm,'time_delta_trace_major':dz,'time_delta_time_major':dzt,'best':min(raw,tm,dz,dzt)}
rows=[]
for p in [2,4,6]:
 A=make_class(p);ids=compact(A);M=A!=center
 # Strict within-trace temporal information; no cross-trace boundary contamination.
 cur=ids[:,:,1:];prev=ids[:,:,:-1];h0=Hid(ids);h1=cond(cur,prev)
 h2=cond(ids[:,:,2:],ids[:,:,1:-1],ids[:,:,:-2])
 B=M.astype(np.uint8);bh0=Hid(B);bh1=cond(B[:,:,1:],B[:,:,:-1]);bh2=cond(B[:,:,2:],B[:,:,1:-1],B[:,:,:-2])
 same=float(np.mean(cur==prev));mask_same=float(np.mean(B[:,:,1:]==B[:,:,:-1]))
 # Causal space-time contexts on the dense residual grid. Keep context to center/activity/signed class to avoid huge overfit.
 S=np.where(A==0,3,np.where(A==center,0,np.where(A<center,1,2))).astype(np.uint8)
 tgt=ids[1:,1:,1:];h_st=cond(tgt,S[1:,1:,:-1],S[1:,:-1,1:],S[:-1,1:,1:])
 tgtb=B[1:,1:,1:];hb_st=cond(tgtb,B[1:,1:,:-1],B[1:,:-1,1:],B[:-1,1:,1:])
 # Search whether active masks propagate with small time shifts across neighbouring residual traces (dip in residual topology).
 shifts=[]
 for axis in [0,1]:
  if axis==0: X0=B[:-1];X1=B[1:]
  else:X0=B[:,:-1];X1=B[:,1:]
  best=None
  for lag in range(-6,7):
   if lag<0:a=X0[:,:,:lag];b=X1[:,:,-lag:]
   elif lag>0:a=X0[:,:,lag:];b=X1[:,:,:-lag]
   else:a=X0;b=X1
   # Jaccard and agreement; mutual information for binary variables.
   inter=np.count_nonzero(a&b);uni=np.count_nonzero(a|b);jac=inter/uni if uni else 1.0;mi=Hid(a)-cond(a,b)
   r={'lag':lag,'jaccard':jac,'MI_bits':mi,'agreement':float(np.mean(a==b))}
   if best is None or r['MI_bits']>best['MI_bits']:best=r
  shifts.append({'axis':axis,'best':best})
 # Run stats along time per spatial residual trace.
 runs=[];active_runs=[]
 for a in range(32):
  for b in range(32):
   x=ids[a,b];cut=np.flatnonzero(np.r_[True,x[1:]!=x[:-1],True]);runs.extend(np.diff(cut).tolist())
   z=B[a,b];cut=np.flatnonzero(np.r_[True,z[1:]!=z[:-1],True]);rr=np.diff(cut);vv=z[cut[:-1]];active_runs.extend(rr[vv==1].tolist())
 row={'pat':p,'n':int(A.size),'center_frac':float(np.mean(A==center)),'unpred_frac':float(np.mean(A==0)),'H0':h0,'H_time1':h1,'H_time2':h2,'same_time_frac':same,'mask_H0':bh0,'mask_H_time1':bh1,'mask_H_time2':bh2,'mask_same_time_frac':mask_same,'H_symbol_given_causal_space_time_state':h_st,'H_mask_given_causal_space_time':hb_st,'shifted_neighbor_mask':shifts,'mean_symbol_run':float(np.mean(runs)),'p90_symbol_run':float(np.quantile(runs,.9)),'mean_active_run':float(np.mean(active_runs)) if active_runs else 0,'p90_active_run':float(np.quantile(active_runs,.9)) if active_runs else 0,'streams':stream(A)}
 rows.append(row)
out={'rows':rows,'sum_best_stream_bytes':sum(r['streams']['best'] for r in rows),'ratio_if_only_spatial_level1_plus_80k':8388608/(sum(r['streams']['best'] for r in rows)+80000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_spatial_residual_time_analysis.json','w'),indent=2)
