import json, numpy as np
q=np.fromfile('hpez_final_quant_inds.bin',np.int32); coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=coords.size or np.unique(coords).size!=q.size: raise SystemExit('invalid coordinate map')
center=32768; phys=np.empty_like(q);phys[coords.astype(np.int64)]=q;Q=phys.reshape(64,64,512)

def H_labels(x):
    _,c=np.unique(x,return_counts=True);p=c.astype(float)/c.sum();return float(-(p*np.log2(p)).sum()) if c.size else 0.0
def row_ids(A):
    A=np.ascontiguousarray(A)
    if A.ndim==1:return A
    v=A.view(np.dtype((np.void,A.dtype.itemsize*A.shape[-1]))).reshape(A.shape[:-1])
    _,ids=np.unique(v,return_inverse=True);return ids.reshape(A.shape[:-1])
def condH(target,ctx):
    t=np.asarray(target).ravel();c=np.asarray(ctx).ravel()
    if t.size!=c.size:raise ValueError('shape mismatch')
    _,ti=np.unique(t,return_inverse=True);_,ci=np.unique(c,return_inverse=True);mt=int(ti.max())+1
    joint=ci.astype(np.int64)*mt+ti.astype(np.int64)
    return H_labels(joint)-H_labels(ci)
def joint_ctx(*arrs):
    cols=np.stack([np.asarray(a).ravel() for a in arrs],axis=1)
    return row_ids(cols).ravel()
def cell_vectors(level):
    s=1<<(level-1); sh=(64//(2*s),64//(2*s),512//(2*s)); V=np.empty(sh+(7,),np.int32)
    for a in range(sh[0]):
      for b in range(sh[1]):
        for c in range(sh[2]):
          i,j,t=2*s*a,2*s*b,2*s*c;k=0
          for pi in [0,1]:
            for pj in [0,1]:
              for pt in [0,1]:
                if pi==pj==pt==0:continue
                V[a,b,c,k]=Q[i+pi*s,j+pj*s,t+pt*s];k+=1
    return V
rows=[]
for level in [1,2,3,4]:
    V=cell_vectors(level); sh=V.shape[:3]; C=int(np.prod(sh))
    # Columns map exactly to parity patterns 1..7. Odd-time children: 1,3,5,7 -> cols 0,2,4,6. Pure spatial: 2,4,6 -> cols1,3,5.
    T=V[..., [0,2,4,6]]; S=V[..., [1,3,5]]
    Vid=row_ids(V);Tid=row_ids(T);Sid=row_ids(S)
    Hv=H_labels(Vid);Ht=H_labels(Tid);Hs=H_labels(Sid);HsT=condH(Sid,Tid)
    # Individual causal neighbour codeword contexts on the cell grid.
    metrics={}
    for name,sl_t,sl_c in [
      ('time_prev',(slice(None),slice(None),slice(1,None)),(slice(None),slice(None),slice(None,-1))),
      ('y_prev',(slice(None),slice(1,None),slice(None)),(slice(None),slice(None,-1),slice(None))),
      ('x_prev',(slice(1,None),slice(None),slice(None)),(slice(None,-1),slice(None),slice(None)))]:
        tgt=Vid[sl_t];prev=Vid[sl_c];metrics[f'H_V_given_{name}_V']=condH(tgt,prev)
        ts=Sid[sl_t];tt=Tid[sl_t];ps=Sid[sl_c];pv=Vid[sl_c]
        metrics[f'H_S_given_T_{name}_S']=condH(ts,joint_ctx(tt,ps))
        metrics[f'H_S_given_T_{name}_V']=condH(ts,joint_ctx(tt,pv))
    # Full three causal neighbours, but compress neighbours to coarse activity/signature states to avoid overfit.
    if min(sh)>=2:
      tgtS=Sid[1:,1:,1:]; tgtT=Tid[1:,1:,1:]
      nT=Vid[1:,1:,:-1];nY=Vid[1:,:-1,1:];nX=Vid[:-1,1:,1:]
      metrics['H_S_given_T_3neighbor_V']=condH(tgtS,joint_ctx(tgtT,nT,nY,nX))
      tgtV=Vid[1:,1:,1:];metrics['H_V_given_3neighbor_V']=condH(tgtV,joint_ctx(nT,nY,nX))
    # Occupancy-only geometry.
    To=row_ids((T!=center).astype(np.uint8));So=row_ids((S!=center).astype(np.uint8));Vo=row_ids((V!=center).astype(np.uint8))
    HoV=H_labels(Vo);HoT=H_labels(To);HoS=H_labels(So);HoST=condH(So,To)
    # Sign-state vector (center=0, neg=1,pos=2,sentinel=3).
    St=np.where(V==center,0,np.where(V==0,3,np.where(V<center,1,2))).astype(np.uint8);Stid=row_ids(St)
    Tst=row_ids(St[..., [0,2,4,6]]);Sst=row_ids(St[..., [1,3,5]])
    Hstate=H_labels(Stid);HstateT=H_labels(Tst);HstateSgivenT=condH(Sst,Tst)
    # Best measured first-order decomposition. This is information-only, not a file-size claim.
    candidates={'independent_vector_H':Hv,'T_plus_S_given_T':Ht+HsT}
    for k,v in metrics.items():
        if k.startswith('H_S_given_T_'): candidates['T_plus_'+k]=Ht+v
    best_name,best_bpc=min(candidates.items(),key=lambda kv:kv[1])
    row={'level':level,'cell_shape':list(sh),'cells':C,'H_full7_bits_per_cell':Hv,'H_time4_bits_per_cell':Ht,'H_spatial3_bits_per_cell':Hs,'H_spatial3_given_time4':HsT,'mutual_info_S_T_bits_per_cell':Hs-HsT,
         'H_occupancy7':HoV,'H_time_occupancy4':HoT,'H_spatial_occupancy3':HoS,'H_spatial_occupancy3_given_time4':HoST,'occupancy_MI_S_T':HoS-HoST,
         'H_state4_full7':Hstate,'H_state4_time4':HstateT,'H_state4_spatial3_given_time4':HstateSgivenT,'metrics':metrics,'best_info_decomposition':best_name,'best_info_bits_per_cell':best_bpc,'best_info_bytes_for_level':best_bpc*C/8}
    rows.append(row)
out={'rows':rows,'sum_best_info_bytes_levels1to4':sum(r['best_info_bytes_for_level'] for r in rows),'ratio_if_only_these_info_bits_plus_20k':8388608/(sum(r['best_info_bytes_for_level'] for r in rows)+20000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_cell_context_analysis.json','w'),indent=2)
