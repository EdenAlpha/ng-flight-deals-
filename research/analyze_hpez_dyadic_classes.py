import json, numpy as np, zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32)
coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if coords.size!=q.size or np.unique(coords).size!=q.size: raise SystemExit('coordinate mapping invalid')
center=32768; Z=zstd.ZstdCompressor(level=19); gvals=np.unique(q); gm=len(gvals); codebook_bytes=4*gm+16
ends=[]
for line in open('hpez_level_ends.txt'):
    l,e=line.split();ends.append((int(l),int(e)))

def Hcnt(c):
    c=np.asarray(c,dtype=float);c=c[c>0]
    if not c.size:return 0.0
    p=c/c.sum();return float(-(p*np.log2(p)).sum())
def Hvals(a):
    if not a.size:return 0.0
    _,c=np.unique(a,return_counts=True);return Hcnt(c)
def bctx_entropy(M):
    m=M.astype(np.uint8); tgt=m[1:,1:,1:].ravel(); c=(m[1:,1:,:-1].ravel() | (m[1:,:-1,1:].ravel()<<1) | (m[:-1,1:,1:].ravel()<<2)).astype(np.int64)
    return Hcnt(np.bincount(c*2+tgt,minlength=16))-Hcnt(np.bincount(c,minlength=8)),int(tgt.size)
def sctx_entropy(A):
    # Four stable neighbour states: negative predictable, center, positive predictable, unpredictable sentinel.
    S=np.where(A==0,3,np.where(A<center,0,np.where(A==center,1,2))).astype(np.int8)
    tgt=A[1:,1:,1:].ravel(); c=(S[1:,1:,:-1].ravel()+4*S[1:,:-1,1:].ravel()+16*S[:-1,1:,1:].ravel()).astype(np.int64)
    vi=np.searchsorted(gvals,tgt); joint=np.bincount(c*gm+vi,minlength=64*gm); ctx=np.bincount(c,minlength=64)
    return Hcnt(joint)-Hcnt(ctx),int(tgt.size)
def dense_class(level,pat,segq,segc):
    s=1<<(level-1); c=segc.astype(np.int64); i=c//(64*512); rem=c%(64*512); j=rem//512; t=rem%512
    u0=i//s;u1=j//s;u2=t//s; p=((u0&1)<<2)|((u1&1)<<1)|(u2&1); sel=p==pat
    if not np.any(sel): return None
    a0=u0[sel]//2;a1=u1[sel]//2;a2=u2[sel]//2;shape=(64//(2*s),64//(2*s),512//(2*s))
    A=np.empty(shape,np.int32);A[a0,a1,a2]=segq[sel]
    if A.size!=sel.sum(): raise SystemExit(f'class fill mismatch L{level} p{pat}: {A.size} != {sel.sum()}')
    return A
rows=[];st=0
for level,e in ends:
    segq=q[st:e];segc=coords[st:e]
    if level<=4:
      for pat in range(1,8):
        A=dense_class(level,pat,segq,segc)
        if A is None: continue
        M=A!=center; hb,_=bctx_entropy(M); hs,_=sctx_entropy(A); nz=A[M]
        ids=np.searchsorted(gvals,A).astype(np.uint8 if gm<=256 else np.uint16); tmids=ids.transpose(2,0,1)
        mask=np.packbits(M.ravel(),bitorder='little').tobytes(); nonids=ids[M].tobytes()
        mt=M.transpose(2,0,1);masktm=np.packbits(mt.ravel(),bitorder='little').tobytes(); nonidstm=tmids[mt].tobytes()
        row={'level':level,'pat':pat,'shape':list(A.shape),'n':int(A.size),'center_frac':float(1-M.mean()),'unpred_frac':float(np.mean(A==0)),'symbol_H0':Hvals(A.ravel()),'mask_H0':Hvals(M.ravel()),'noncenter_value_H':Hvals(nz),'mask_H_causal3':hb,'symbol_H_given_neighbor_state3':hs,
             'id_zstd':len(Z.compress(ids.tobytes())),'id_time_major_zstd':len(Z.compress(tmids.tobytes())),'maskval_id_zstd':len(Z.compress(mask+nonids)),'maskval_id_time_major_zstd':len(Z.compress(masktm+nonidstm))}
        row['best_zstd']=min(row['id_zstd'],row['id_time_major_zstd'],row['maskval_id_zstd'],row['maskval_id_time_major_zstd']);rows.append(row)
    st=e
root=q[:ends[0][1]];root_ids=np.searchsorted(gvals,root).astype(np.uint8 if gm<=256 else np.uint16);root_bytes=len(Z.compress(root_ids.tobytes()))
sum_best=root_bytes+codebook_bytes+sum(r['best_zstd']+32 for r in rows)
ideal_mask3=0.0;ideal_val0=0.0
for r in rows:
    ideal_mask3 += r['n']*r['mask_H_causal3']/8
    nz_n=int(round(r['n']*(1-r['center_frac'])));ideal_val0 += nz_n*r['noncenter_value_H']/8
out={'alphabet':int(gm),'alphabet_codebook_bytes':int(codebook_bytes),'root_zstd_bytes':root_bytes,'rows':rows,'sum_best_class_zstd_bytes':sum_best,'ratio_if_symbols_only_plus_5k':8388608/(sum_best+5000),'ideal_class_mask_causal3_plus_value_H0_bytes':ideal_mask3+ideal_val0+codebook_bytes,'ratio_ideal_plus_5k':8388608/(ideal_mask3+ideal_val0+codebook_bytes+5000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_dyadic_class_analysis.json','w'),indent=2)
