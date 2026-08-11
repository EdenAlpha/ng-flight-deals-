import json, numpy as np, zstandard as zstd
meta=json.load(open('data/forge_subcube_meta.json'));eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4').reshape(64,64,512)
R=np.fromfile('diagnostic_rec.bin','<f4').reshape(64,64,512)
q=np.fromfile('hpez_final_quant_inds.bin',np.int32);coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=coords.size or np.unique(coords).size!=q.size:raise SystemExit('invalid coordinate map')
center=32768;Z=zstd.ZstdCompressor(level=19)
# Level-1 physical classes. Patterns bits=(i parity,j parity,t parity).
ii,jj,tt=np.indices(X.shape,sparse=False);pat=((ii&1)<<2)|((jj&1)<<1)|(tt&1)
# Decoder order anatomy for the actual level-1 segment.
starts={5:0,4:512,3:4096,2:32768,1:262144};st=starts[1];c=coords[st:].astype(np.int64);i=c//(64*512);rem=c%(64*512);j=rem//512;t=rem%512;seq=((i&1)<<2)|((j&1)<<1)|(t&1)
runstarts=np.flatnonzero(np.r_[True,seq[1:]!=seq[:-1]]);runends=np.r_[runstarts[1:],seq.size]
runs=[{'pat':int(seq[a]),'start':int(a),'n':int(b-a)} for a,b in zip(runstarts,runends)]
order_stats={str(p):{'first':int(np.flatnonzero(seq==p)[0]),'last':int(np.flatnonzero(seq==p)[-1]),'n':int(np.count_nonzero(seq==p))} for p in range(1,8)}
# Interpolation weights at zero for symmetric odd nodes +/-1,+/-3,...
def weights(nodes):
    w=[]
    for k,xk in enumerate(nodes):
        v=1.0
        for m,xm in enumerate(nodes):
            if m!=k:v*=(-xm)/(xk-xm)
        w.append(v)
    return np.asarray(w,dtype=np.float64)
def predict_order(npts):
    h=npts//2; nodes=np.r_[np.arange(-(2*h-1),0,2),np.arange(1,2*h,2)].astype(int);w=weights(nodes)
    P=np.full_like(X,np.nan,dtype=np.float32);valid=np.ones(X.shape,dtype=bool)
    for node in nodes:valid &= (tt+node>=0)&(tt+node<512)
    inds=np.argwhere(valid & ((tt&1)==0))
    # Vectorize by time planes, all spatial points at once.
    for te in range(0,512,2):
        if np.any(te+nodes<0) or np.any(te+nodes>=512):continue
        a=np.zeros((64,64),dtype=np.float64)
        for ww,node in zip(w,nodes):a += ww*R[:,:,te+node]
        P[:,:,te]=a.astype(np.float32)
    return P,valid,w,nodes
def stream_metrics(Q,mask):
    a=Q[mask];lo=int(a.min()) if a.size else 0;hi=int(a.max()) if a.size else 0;dt=np.int8 if lo>=-128 and hi<=127 else np.int16 if lo>=-32768 and hi<=32767 else np.int32
    raw=len(Z.compress(a.astype(dt).tobytes()));nz=a!=0; packed=np.packbits(nz,bitorder='little').tobytes();vals=a[nz].astype(dt).tobytes();mv=len(Z.compress(packed+vals))
    _,cnt=np.unique(a,return_counts=True);p=cnt/cnt.sum();H=float(-(p*np.log2(p)).sum()) if cnt.size else 0
    return {'n':int(a.size),'zero_frac':float(1-nz.mean()) if a.size else 1,'H0_bps':H,'raw_zstd':raw,'maskval_zstd':mv,'best_zstd':min(raw,mv),'min':lo,'max':hi}
rows=[]
spatial_mask=np.isin(pat,[2,4,6]); interior_base=spatial_mask.copy()
# Existing HPEZ symbols mapped physically; sentinel is irrelevant at this diagnostic level, compact q classes are reported separately.
physq=np.empty_like(q);physq[coords.astype(np.int64)]=q;Qh=physq.reshape(X.shape)
for p in [2,4,6]:
    m=pat==p;d=Qh[m];rows.append({'kind':'existing_hpez_q','pat':p,'n':int(d.size),'center_frac':float(np.mean(d==center))})
# New strict residuals use lattice centered on temporal-bridge predictor; q=0 means exact predicted center.
for npts in [2,4,6,8]:
    P,valid,w,nodes=predict_order(npts)
    combined=np.zeros_like(X,dtype=np.int16);rec=R.copy();total_valid=np.zeros_like(spatial_mask)
    bypat={}
    for p in [2,4,6]:
        m=(pat==p)&valid&np.isfinite(P)
        Qn=np.rint((X[m]-P[m])/(2*eps)).astype(np.int16);Yn=P[m]+Qn.astype(np.float32)*(2*eps)
        combined[m]=Qn;rec[m]=Yn;total_valid|=m
        sm=stream_metrics(combined,m);sm['maxerr']=float(np.max(np.abs(X[m]-Yn))) if m.any() else 0;bypat[str(p)]=sm
    smc=stream_metrics(combined,total_valid);smc['maxerr']=float(np.max(np.abs(X[total_valid]-rec[total_valid]))) if total_valid.any() else 0
    # Boundary even-time planes not covered by high order stay on original HPEZ values and are explicitly counted as uncovered.
    rows.append({'kind':'temporal_bridge','npts':npts,'nodes':nodes.tolist(),'weights':w.tolist(),'covered_frac_of_spatial_children':float(total_valid.sum()/spatial_mask.sum()),'combined':smc,'by_pat':bypat})
# Also test a decoder-only adaptive choice between linear and cubic using known odd-sample curvature. No original X enters selector.
P2,v2,_,_=predict_order(2);P4,v4,_,_=predict_order(4);valid=v2&v4&np.isfinite(P2)&np.isfinite(P4)&spatial_mask
# curvature proxy from odd samples around even target: |r[-3]-3r[-1]+3r[+1]-r[+3]|, normalized by local amplitude.
curv=np.full_like(X,np.inf,dtype=np.float32)
for te in range(4,508,2):
    num=np.abs(R[:,:,te-3]-3*R[:,:,te-1]+3*R[:,:,te+1]-R[:,:,te+3]);den=np.abs(R[:,:,te-1])+np.abs(R[:,:,te+1])+eps
    curv[:,:,te]=num/den
for th in [0.02,0.05,0.1,0.2,0.4,0.8]:
    P=np.where(curv<th,P4,P2);m=valid;Qn=np.zeros_like(X,dtype=np.int16);Qn[m]=np.rint((X[m]-P[m])/(2*eps)).astype(np.int16);Y=P[m]+Qn[m].astype(np.float32)*(2*eps);sm=stream_metrics(Qn,m);sm['maxerr']=float(np.max(np.abs(X[m]-Y)));rows.append({'kind':'adaptive_2_4','threshold':th,'selector_cubic_frac':float(np.mean(curv[m]<th)),'combined':sm})
out={'eps':eps,'level1_decoder_runs_first80':runs[:80],'level1_run_count':len(runs),'level1_order_stats':order_stats,'rows':rows}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_temporal_bridge_analysis.json','w'),indent=2)
