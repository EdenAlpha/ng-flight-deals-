import json, numpy as np, zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32)
coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if coords.size!=q.size or np.unique(coords).size!=q.size: raise SystemExit('coordinate mapping invalid')
center=32768; Z=zstd.ZstdCompressor(level=19)
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
    # causal three-neighbour binary context inside dense sublattice: t-1, y-1, x-1
    m=M.astype(np.uint8); tgt=m[1:,1:,1:].ravel()
    c=(m[1:,1:,:-1].ravel() | (m[1:,:-1,1:].ravel()<<1) | (m[:-1,1:,1:].ravel()<<2)).astype(np.int64)
    joint=np.bincount(c*2+tgt,minlength=16); ctx=np.bincount(c,minlength=8)
    return Hcnt(joint)-Hcnt(ctx), int(tgt.size)
def sctx_entropy(A):
    # full signed deviation conditioned on 3 ternary neighbour states {neg,zero,pos}; small 27-context model.
    def st(x): return (x>0).astype(np.int8)*2 + (x==0).astype(np.int8)
    S=st(A); tgt=A[1:,1:,1:].ravel(); c=(S[1:,1:,:-1].ravel()+3*S[1:,:-1,1:].ravel()+9*S[:-1,1:,1:].ravel()).astype(np.int64)
    vals=np.unique(A); vi=np.searchsorted(vals,tgt); m=len(vals)
    joint=np.bincount(c*m+vi,minlength=27*m); ctx=np.bincount(c,minlength=27)
    return Hcnt(joint)-Hcnt(ctx), int(tgt.size)
def dense_class(level,pat,segq,segc):
    s=1<<(level-1)
    c=segc.astype(np.int64); i=c//(64*512); rem=c%(64*512); j=rem//512; t=rem%512
    u0=i//s;u1=j//s;u2=t//s
    p=((u0&1)<<2)|((u1&1)<<1)|(u2&1)
    sel=p==pat
    if not np.any(sel): return None
    a0=(u0[sel]//2);a1=(u1[sel]//2);a2=(u2[sel]//2)
    shape=(64//(2*s),64//(2*s),512//(2*s))
    A=np.empty(shape,np.int32);A[a0,a1,a2]=segq[sel]-center
    if A.size!=sel.sum(): raise SystemExit(f'class fill mismatch L{level} p{pat}: {A.size} != {sel.sum()}')
    return A
rows=[];st=0
for level,e in ends:
    segq=q[st:e];segc=coords[st:e]
    if level<=4: # refinement levels; level5 is root grid
      for pat in range(1,8):
        A=dense_class(level,pat,segq,segc)
        if A is None: continue
        M=A!=0; hb,nctx=bctx_entropy(M); hs,_=sctx_entropy(A)
        nz=A[M]
        # Physical dense ordering and time-major alternatives.
        raw=A.astype(np.int8 if A.min()>=-128 and A.max()<=127 else np.int16).tobytes()
        tm=A.transpose(2,0,1);rawtm=tm.astype(np.int8 if A.min()>=-128 and A.max()<=127 else np.int16).tobytes()
        mask=np.packbits(M.ravel(),bitorder='little').tobytes(); vals=nz.astype(np.int8 if nz.size and nz.min()>=-128 and nz.max()<=127 else np.int16).tobytes()
        masktm=np.packbits(M.transpose(2,0,1).ravel(),bitorder='little').tobytes(); valstm=tm[tm!=0].astype(np.int8 if nz.size and nz.min()>=-128 and nz.max()<=127 else np.int16).tobytes()
        row={'level':level,'pat':pat,'shape':list(A.shape),'n':int(A.size),'center_frac':float(1-M.mean()),'symbol_H0':Hvals(A.ravel()),'mask_H0':Hvals(M.ravel()),'nonzero_value_H':Hvals(nz),'mask_H_causal3':hb,'symbol_H_given_neighbor_sign3':hs,'raw_zstd':len(Z.compress(raw)),'raw_time_major_zstd':len(Z.compress(rawtm)),'maskval_zstd':len(Z.compress(mask+vals)),'maskval_time_major_zstd':len(Z.compress(masktm+valstm))}
        row['best_zstd']=min(row['raw_zstd'],row['raw_time_major_zstd'],row['maskval_zstd'],row['maskval_time_major_zstd']);rows.append(row)
    st=e
# Root separately.
root=q[:ends[0][1]]-center
root_bytes=len(Z.compress(root.astype(np.int8 if root.min()>=-128 and root.max()<=127 else np.int16).tobytes()))
# Sum independent class streams; conservative 32 bytes header/class.
sum_best=root_bytes+sum(r['best_zstd']+32 for r in rows)
# Stable theoretical decomposition: binary mask conditional entropy + exact nonzero amplitude H0; no overfit large symbol contexts.
ideal_mask3=0.0;ideal_val0=0.0
for r in rows:
    ideal_mask3 += r['n']*r['mask_H_causal3']/8
    nz_n=int(round(r['n']*(1-r['center_frac'])));ideal_val0 += nz_n*r['nonzero_value_H']/8
out={'root_zstd_bytes':root_bytes,'rows':rows,'sum_best_class_zstd_bytes':sum_best,'ratio_if_symbols_only_plus_5k':8388608/(sum_best+5000),'ideal_class_mask_causal3_plus_value_H0_bytes':ideal_mask3+ideal_val0,'ratio_ideal_plus_5k':8388608/(ideal_mask3+ideal_val0+5000)}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_dyadic_class_analysis.json','w'),indent=2)
