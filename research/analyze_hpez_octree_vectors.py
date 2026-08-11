import json, numpy as np, zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32); coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=coords.size or np.unique(coords).size!=q.size: raise SystemExit('invalid coordinate permutation')
center=32768; N=q.size; phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Q=phys.reshape(64,64,512)
Z=zstd.ZstdCompressor(level=19);gvals=np.unique(q);gm=len(gvals);gidtype=np.uint8 if gm<=256 else np.uint16;codebook_bytes=4*gm+16;unpred_raw_bytes=int(np.count_nonzero(q==0)*4)

def Hcnt(c):
 c=np.asarray(c,dtype=float);c=c[c>0]
 if not c.size:return 0.0
 p=c/c.sum();return float(-(p*np.log2(p)).sum())
def Hvals(a):
 if not a.size:return 0.0
 _,c=np.unique(a,return_counts=True);return Hcnt(c)
def condH(a,b):
 _,aa=np.unique(a,return_inverse=True);_,bb=np.unique(b,return_inverse=True);ma=int(aa.max())+1;mb=int(bb.max())+1
 return Hcnt(np.bincount(bb.astype(np.int64)*ma+aa.astype(np.int64),minlength=mb*ma))-Hcnt(np.bincount(bb,minlength=mb))
def causal3_binary(M):
 m=M.astype(np.uint8);t=m[1:,1:,1:].ravel();c=(m[1:,1:,:-1].ravel()|(m[1:,:-1,1:].ravel()<<1)|(m[:-1,1:,1:].ravel()<<2)).astype(np.int64)
 return Hcnt(np.bincount(c*2+t,minlength=16))-Hcnt(np.bincount(c,minlength=8))
def state4(A):
 # 0=center, 1=negative predictable, 2=positive predictable, 3=unpredictable sentinel.
 return np.where(A==0,3,np.where(A==center,0,np.where(A<center,1,2))).astype(np.uint8)
def code_stream(V,order):
 A=V[order]; S=state4(A); powers=(4**np.arange(7,dtype=np.int64)); sc=(S.astype(np.int64)*powers).sum(1).astype(np.uint16)
 prednz=(A!=center)&(A!=0); mag=(np.abs(A[prednz].astype(np.int64)-center)-1)
 md=np.uint8 if (mag.size==0 or mag.max()<=255) else np.uint16
 statez=len(Z.compress(sc.tobytes()));magz=len(Z.compress(mag.astype(md).tobytes())) if mag.size else 0
 ids=np.searchsorted(gvals,A).astype(gidtype);rawz=len(Z.compress(ids.tobytes()))
 return {'state4_zstd':statez,'predictable_magnitude_zstd':magz,'state4_plus_magnitude':statez+magz,'compact_id_vector_zstd':rawz,'best_without_global_codebook':min(rawz,statez+magz)}
rows=[]
for level in [4,3,2,1]:
 s=1<<(level-1); sh=(64//(2*s),64//(2*s),512//(2*s)); C=int(np.prod(sh));V=np.empty((C,7),np.int32);cell_origin=np.empty(C,np.int32);idx=0
 for a in range(sh[0]):
  for b in range(sh[1]):
   for c in range(sh[2]):
    i,j,t=2*s*a,2*s*b,2*s*c;cell_origin[idx]=Q[i,j,t];k=0
    for pi in [0,1]:
     for pj in [0,1]:
      for pt in [0,1]:
       if pi==pj==pt==0:continue
       V[idx,k]=Q[i+pi*s,j+pj*s,t+pt*s];k+=1
    idx+=1
 M=V!=center;occ=(M.astype(np.uint8)*(1<<np.arange(7,dtype=np.uint8))).sum(1).astype(np.uint8);S=state4(V);statecode=(S.astype(np.int64)*(4**np.arange(7,dtype=np.int64))).sum(1);active=(occ!=0).reshape(sh);zero_frac=float(1-active.mean())
 po=cell_origin;pc=np.where(po==0,0,np.where(po<center-1,1,np.where(po==center-1,2,np.where(po==center,3,np.where(po==center+1,4,5))))).astype(np.int8)
 natural=np.arange(C);grid=np.arange(C).reshape(sh);time_major=grid.transpose(2,0,1).ravel()
 def morton2(i,j):
  z=0
  for bit in range(6):z|=((i>>bit)&1)<<(2*bit);z|=((j>>bit)&1)<<(2*bit+1)
  return z
 tr=sorted((morton2(i,j),i,j) for i in range(sh[0]) for j in range(sh[1]));mort=np.concatenate([grid[i,j,:] for _,i,j in tr]);spord=np.argsort([morton2(i,j) for i in range(sh[0]) for j in range(sh[1])]);mort_time=np.concatenate([grid[:,:,tt].ravel()[spord] for tt in range(sh[2])])
 codes={name:code_stream(V,o) for name,o in [('natural',natural),('time_major',time_major),('morton_trace',mort),('time_morton',mort_time)]}
 nz=V[M];prednzvals=V[(V!=center)&(V!=0)];mags=np.abs(prednzvals.astype(np.int64)-center)
 row={'level':level,'stride':s,'cell_shape':list(sh),'cells':C,'symbols':C*7,'symbol_center_frac':float(np.mean(V==center)),'unpred_frac':float(np.mean(V==0)),'zero_cell_frac':zero_frac,'active_cell_frac':1-zero_frac,
      'occupancy_H_bits_per_cell':Hvals(occ),'state4_H_bits_per_cell':Hvals(statecode),'exact_vector_H_bits_per_cell':Hvals(np.ascontiguousarray(V).view(np.dtype((np.void,V.dtype.itemsize*7))).ravel()),
      'noncenter_symbol_H':Hvals(nz),'predictable_magnitude_H':Hvals(mags),'occupancy_H_given_parent_origin6':condH(occ,pc),'state4_H_given_parent_origin6':condH(statecode,pc),'active_flag_H0':Hvals(active.ravel()),'active_flag_H_causal3':causal3_binary(active),'codes':codes}
 row['best_actual_vector_bytes']=min(v['best_without_global_codebook'] for v in codes.values());rows.append(row)
root=Q[::16,::16,::16].ravel();root_ids=np.searchsorted(gvals,root).astype(gidtype);rootz=len(Z.compress(root_ids.tobytes()))
sum_actual=rootz+codebook_bytes+unpred_raw_bytes+sum(r['best_actual_vector_bytes']+32 for r in rows)
ideal_vec=sum(r['cells']*r['exact_vector_H_bits_per_cell']/8 for r in rows)+rootz+codebook_bytes+unpred_raw_bytes
ideal_parent_state=sum(r['cells']*r['state4_H_given_parent_origin6']/8 + r['symbols']*(1-r['symbol_center_frac']-r['unpred_frac'])*r['predictable_magnitude_H']/8 for r in rows)+rootz+unpred_raw_bytes
out={'alphabet':int(gm),'alphabet_codebook_bytes':int(codebook_bytes),'unpredictable_raw_bytes':unpred_raw_bytes,'root_zstd_bytes':rootz,'rows':rows,'sum_actual_vector_bytes':sum_actual,'symbol_only_ratio_plus_5k':8388608/(sum_actual+5000),'ideal_vector_H0_bytes':ideal_vec,'ideal_parent_state_plus_magnitude_bytes':ideal_parent_state,'ideal_ratio_plus_5k':8388608/(ideal_parent_state+5000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_octree_vector_analysis.json','w'),indent=2)
