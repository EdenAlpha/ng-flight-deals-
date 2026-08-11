import json, numpy as np, zstandard as zstd
q=np.fromfile('hpez_final_quant_inds.bin',np.int32)
coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
N=q.size
if coords.size!=N: raise SystemExit(f'coordinate mismatch q={N} coords={coords.size}')
if coords.min()!=0 or coords.max()!=N-1 or np.unique(coords).size!=N: raise SystemExit('coordinates are not a permutation')
vals=np.unique(q); m=len(vals); ids=np.searchsorted(vals,q); center=32768; center_id=int(np.searchsorted(vals,center)); codebook_bytes=int(4*m+16)
zctx=zstd.ZstdCompressor(level=19)

def Hc(c):
    c=np.asarray(c,dtype=np.float64);c=c[c>0]
    if not c.size:return 0.0
    p=c/c.sum();return float(-(p*np.log2(p)).sum())
def ents(a):
    s=np.searchsorted(vals,a).astype(np.int64)
    h0=Hc(np.bincount(s,minlength=m))
    pc=np.bincount(s[:-1]*m+s[1:],minlength=m*m);h1=Hc(pc)-Hc(np.bincount(s[:-1],minlength=m))
    ctx=s[:-2]*m+s[1:-1];tc=np.bincount(ctx*m+s[2:],minlength=m*m*m);h2=Hc(tc)-Hc(np.bincount(ctx,minlength=m*m))
    return h0,h1,h2

def uv(x):
    x=int(x);o=bytearray()
    while x>=128:o.append((x&127)|128);x>>=7
    o.append(x);return o
def metrics(name,a):
    sid=np.searchsorted(vals,a).astype(np.uint8 if m<=256 else np.uint16)
    rawz=len(zctx.compress(sid.tobytes()))
    nz=a!=center; mask=np.packbits(nz,bitorder='little').tobytes(); nonid=sid[nz]
    maskz=len(zctx.compress(mask+nonid.tobytes()))
    # Same-symbol run grammar: run length + compact alphabet ID, never reinterpret sentinel 0 as -32768.
    cut=np.flatnonzero(np.r_[True,a[1:]!=a[:-1],True]);rl=np.diff(cut);rs=np.searchsorted(vals,a[cut[:-1]])
    rb=bytearray()
    for r,v in zip(rl,rs): rb+=uv(r);rb+=uv(v)
    rlez=len(zctx.compress(bytes(rb)))
    h0,h1,h2=ents(a)
    stream=min(rawz,maskz,rlez);best=stream+codebook_bytes
    return {'name':name,'H0':h0,'H1':h1,'H2':h2,'center_frac':float(np.mean(a==center)),'unpred_frac':float(np.mean(a==0)),'same_frac':float(np.mean(a[1:]==a[:-1])),'raw_symbol_id_zstd':rawz,'mask_plus_noncenter_id_zstd':maskz,'same_run_id_zstd':rlez,'alphabet_codebook_bytes':codebook_bytes,'best_stream_plus_codebook_bytes':best,'projected_plus_5k':best+5000,'projected_ratio_plus_5k':8388608/(best+5000)}
# q indexed by original flat physical sample index (cache 64x64x512, time fastest).
byidx=np.empty_like(q);byidx[coords.astype(np.int64)]=q
Q=byidx.reshape(64,64,512)
def morton2(i,j):
    z=0
    for b in range(6):z|=((i>>b)&1)<<(2*b);z|=((j>>b)&1)<<(2*b+1)
    return z
traces=sorted([(morton2(i,j),i,j) for i in range(64) for j in range(64)])
ti=np.array([x[1] for x in traces]);tj=np.array([x[2] for x in traces])
orders=[('hpez_traversal',q),('physical_trace_major',byidx),('physical_time_major',Q.transpose(2,0,1).ravel()),('trace_morton_time_inner',Q[ti,tj,:].ravel()),('time_major_trace_morton',Q[ti,tj,:].T.ravel())]
ends=[]
for line in open('hpez_level_ends.txt'):
    lev,e=line.split();ends.append((int(lev),int(e)))
segs=[];st=0
for lev,e in ends:
    c=coords[st:e];segs.append(q[st:e][np.argsort(c,kind='stable')]);st=e
if st<N:segs.append(q[st:][np.argsort(coords[st:],kind='stable')])
orders.append(('level_then_physical',np.concatenate(segs)))
rank=np.empty((64,64),np.int64)
for r,(_,i,j) in enumerate(traces):rank[i,j]=r
segs=[];st=0
for lev,e in ends:
    c=coords[st:e].astype(np.int64);ii=c//(64*512);rem=c%(64*512);jj=rem//512;tt=rem%512;key=tt.astype(np.int64)*4096+rank[ii,jj]
    segs.append(q[st:e][np.argsort(key,kind='stable')]);st=e
if st<N:
    c=coords[st:].astype(np.int64);ii=c//(64*512);rem=c%(64*512);jj=rem//512;tt=rem%512;key=tt*4096+rank[ii,jj];segs.append(q[st:][np.argsort(key,kind='stable')])
orders.append(('level_then_time_morton',np.concatenate(segs)))
rows=[metrics(n,a) for n,a in orders];rows.sort(key=lambda r:r['best_stream_plus_codebook_bytes'])
out={'N':int(N),'center':center,'alphabet':int(m),'coord_permutation_valid':True,'rows':rows}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_coordinate_order_analysis.json','w'),indent=2)
