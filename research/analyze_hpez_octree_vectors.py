import json, numpy as np, zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32); coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=coords.size or np.unique(coords).size!=q.size: raise SystemExit('invalid coordinate permutation')
center=32768; N=q.size; phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Q=(phys-center).reshape(64,64,512)
Z=zstd.ZstdCompressor(level=19)

def Hcnt(c):
 c=np.asarray(c,dtype=float);c=c[c>0]
 if not c.size:return 0.0
 p=c/c.sum();return float(-(p*np.log2(p)).sum())
def Hvals(a):
 if not a.size:return 0.0
 _,c=np.unique(a,return_counts=True);return Hcnt(c)
def condH(a,b):
 # H(a|b), integer arrays same length; remap compactly
 _,aa=np.unique(a,return_inverse=True);_,bb=np.unique(b,return_inverse=True);ma=int(aa.max())+1;mb=int(bb.max())+1
 return Hcnt(np.bincount(bb.astype(np.int64)*ma+aa.astype(np.int64),minlength=mb*ma))-Hcnt(np.bincount(bb,minlength=mb))
def causal3_binary(M):
 m=M.astype(np.uint8);t=m[1:,1:,1:].ravel();c=(m[1:,1:,:-1].ravel()|(m[1:,:-1,1:].ravel()<<1)|(m[:-1,1:,1:].ravel()<<2)).astype(np.int64)
 return Hcnt(np.bincount(c*2+t,minlength=16))-Hcnt(np.bincount(c,minlength=8))
def uv(x):
 x=int(x);o=bytearray()
 while x>=128:o.append((x&127)|128);x>>=7
 o.append(x);return o
def zz(x):x=int(x);return (x<<1)^(x>>63)
def code_stream(V,order):
 A=V[order]
 # ternary state code per 7-vector: zero=0, neg=1, pos=2, max 2186
 S=(A>0).astype(np.int16)*2+(A<0).astype(np.int16)
 powers=(3**np.arange(7,dtype=np.int64)); tc=(S.astype(np.int64)*powers).sum(1)
 # residual magnitudes only for nonzeros, minus 1 because magnitude 1 is common
 mag=(np.abs(A[A!=0]).astype(np.int16)-1)
 tcdt=np.uint16 if tc.max()>255 else np.uint8
 md=np.uint8 if (mag.size==0 or mag.max()<=255) else np.uint16
 ternz=len(Z.compress(tc.astype(tcdt).tobytes())); magz=len(Z.compress(mag.astype(md).tobytes())) if mag.size else 0
 # exact int8/16 seven-vector stream control
 dt=np.int8 if A.min()>=-128 and A.max()<=127 else np.int16
 rawz=len(Z.compress(A.astype(dt).tobytes()))
 return {'ternary_zstd':ternz,'magnitude_zstd':magz,'ternary_plus_mag':ternz+magz,'raw_vector_zstd':rawz,'best':min(rawz,ternz+magz)}
rows=[]
for level in [4,3,2,1]:
 s=1<<(level-1); sh=(64//(2*s),64//(2*s),512//(2*s)); C=np.prod(sh)
 V=np.empty((int(C),7),np.int32); cell_origin=np.empty(int(C),np.int32)
 pats=[]
 idx=0
 for a in range(sh[0]):
  for b in range(sh[1]):
   for c in range(sh[2]):
    i,j,t=2*s*a,2*s*b,2*s*c;cell_origin[idx]=Q[i,j,t]
    k=0
    for pi in [0,1]:
     for pj in [0,1]:
      for pt in [0,1]:
       if pi==pj==pt==0:continue
       V[idx,k]=Q[i+pi*s,j+pj*s,t+pt*s];k+=1
    idx+=1
 # Occupancy/sign codewords.
 occ=((V!=0).astype(np.uint8)*(1<<np.arange(7,dtype=np.uint8))).sum(1).astype(np.uint8)
 signstate=(V>0).astype(np.int16)*2+(V<0).astype(np.int16); tern=(signstate.astype(np.int64)*(3**np.arange(7,dtype=np.int64))).sum(1)
 active=(occ!=0).reshape(sh); zero_frac=float(1-active.mean())
 # Parent-origin state, compact 5-class {<=-2,-1,0,+1,>=2}.
 po=cell_origin; pc=np.where(po<=-2,0,np.where(po==-1,1,np.where(po==0,2,np.where(po==1,3,4)))).astype(np.int8)
 # Cell orders: trace-major c(time) inner, time-major, and 2-D Morton trace cells.
 natural=np.arange(int(C))
 grid=np.arange(int(C)).reshape(sh); time_major=grid.transpose(2,0,1).ravel()
 def morton2(i,j):
  z=0
  for bit in range(6):z|=((i>>bit)&1)<<(2*bit);z|=((j>>bit)&1)<<(2*bit+1)
  return z
 tr=sorted((morton2(i,j),i,j) for i in range(sh[0]) for j in range(sh[1])); mort=np.concatenate([grid[i,j,:] for _,i,j in tr]); mort_time=np.concatenate([grid[:,:,t].ravel()[np.argsort([morton2(i,j) for i in range(sh[0]) for j in range(sh[1])])] for t in range(sh[2])]) if sh[0]*sh[1]>0 else natural
 codes={}
 for name,o in [('natural',natural),('time_major',time_major),('morton_trace',mort),('time_morton',mort_time)]:codes[name]=code_stream(V,o)
 # Stable information measures.
 nz=V[V!=0]
 row={'level':level,'stride':s,'cell_shape':list(sh),'cells':int(C),'symbols':int(C*7),'symbol_center_frac':float(np.mean(V==0)),'zero_cell_frac':zero_frac,'active_cell_frac':1-zero_frac,
      'occupancy_H_bits_per_cell':Hvals(occ),'ternary_sign_H_bits_per_cell':Hvals(tern),'exact_vector_H_bits_per_cell':Hvals(np.ascontiguousarray(V).view(np.dtype((np.void,V.dtype.itemsize*7))).ravel()),
      'nonzero_value_H':Hvals(nz),'magnitude_H_nonzero':Hvals(np.abs(nz)),'occupancy_H_given_parent_origin5':condH(occ,pc),'ternary_H_given_parent_origin5':condH(tern,pc),
      'active_flag_H0':Hvals(active.ravel()),'active_flag_H_causal3':causal3_binary(active),'codes':codes}
 row['best_actual_vector_bytes']=min(v['best'] for v in codes.values()); rows.append(row)
# Summaries. Root 4x4x32 symbols are included separately using exact physical values at multiples of16.
root=Q[::16,::16,::16].ravel();rdt=np.int8 if root.min()>=-128 and root.max()<=127 else np.int16;rootz=len(Z.compress(root.astype(rdt).tobytes()))
sum_actual=rootz+sum(r['best_actual_vector_bytes']+32 for r in rows)
# Conservative ideal: code active flag with causal binary context, occupancy pattern among active cells at H0 conditional on active,
# then nonzero signed amplitudes at H0. Compute directly from rows approximately via occupancy entropy decomposition would need raw arrays; use exact vector H0 and parent-conditioned ternary as two lower bounds.
ideal_vec=sum(r['cells']*r['exact_vector_H_bits_per_cell']/8 for r in rows)+rootz
ideal_parent_sign=sum(r['cells']*r['ternary_H_given_parent_origin5']/8 + r['symbols']*(1-r['symbol_center_frac'])*r['magnitude_H_nonzero']/8 for r in rows)+rootz
out={'root_zstd_bytes':rootz,'rows':rows,'sum_actual_vector_bytes':sum_actual,'symbol_only_ratio_plus_5k':8388608/(sum_actual+5000),'ideal_vector_H0_bytes':ideal_vec,'ideal_parent_sign_plus_magnitude_bytes':ideal_parent_sign,'ideal_ratio_plus_5k':8388608/(ideal_parent_sign+5000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_octree_vector_analysis.json','w'),indent=2)
