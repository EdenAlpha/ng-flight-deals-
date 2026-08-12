import json, os, subprocess, numpy as np

CENTER = 32768
RAW_BYTES = 64 * 64 * 512 * 4
HEADER_BYTES = 64


def zbytes_bytes(b: bytes) -> int:
    return len(subprocess.run(
        ['zstd', '-q', '-f', '-19', '-T0', '-c'],
        input=b, stdout=subprocess.PIPE, check=True
    ).stdout)


def zroundtrip(b: bytes) -> bytes:
    c = subprocess.run(
        ['zstd', '-q', '-f', '-19', '-T0', '-c'],
        input=b, stdout=subprocess.PIPE, check=True
    ).stdout
    return subprocess.run(
        ['zstd', '-q', '-d', '-c'], input=c,
        stdout=subprocess.PIPE, check=True
    ).stdout


def sym_state_np(a):
    a = np.asarray(a)
    d = a.astype(np.int64) - CENTER
    out = np.empty(a.shape, np.uint8)
    out[a == CENTER] = 0
    out[a == 0] = 7
    m = (a != CENTER) & (a != 0)
    ad = np.abs(d)
    out[m & (d < 0) & (ad == 1)] = 1
    out[m & (d > 0) & (ad == 1)] = 2
    out[m & (d < 0) & (ad >= 2) & (ad <= 3)] = 3
    out[m & (d > 0) & (ad >= 2) & (ad <= 3)] = 4
    out[m & (d < 0) & (ad > 3)] = 5
    out[m & (d > 0) & (ad > 3)] = 6
    return out


def sym_state_scalar(v):
    v = int(v)
    if v == CENTER: return 0
    if v == 0: return 7
    d = v - CENTER; ad = abs(d)
    if ad == 1: return 1 if d < 0 else 2
    if ad <= 3: return 3 if d < 0 else 4
    return 5 if d < 0 else 6


def cell_state_np(V):
    # V shape (...,7). Compact, fixed, decoder-reproducible cell signature.
    active = V != CENTER
    cnt = np.minimum(active.sum(axis=-1), 3).astype(np.uint16)
    neg = ((V < CENTER) & (V != 0)).sum(axis=-1)
    pos = (V > CENTER).sum(axis=-1)
    sign = np.where((neg == 0) & (pos == 0), 0,
           np.where(neg > pos, 1, np.where(pos > neg, 2, 3))).astype(np.uint16)
    mag = np.where(active, np.abs(V.astype(np.int64) - CENTER), 0).max(axis=-1)
    mb = np.where(mag == 0, 0, np.where(mag == 1, 1, np.where(mag <= 3, 2, 3))).astype(np.uint16)
    unpred = (V == 0).any(axis=-1).astype(np.uint16)
    return (cnt + 4*sign + 16*mb + 64*unpred).astype(np.uint16)


def cell_state_scalar(vals):
    vals = [int(v) for v in vals]
    active = [v for v in vals if v != CENTER]
    cnt = min(len(active), 3)
    neg = sum(v < CENTER and v != 0 for v in vals)
    pos = sum(v > CENTER for v in vals)
    sign = 0 if neg == 0 and pos == 0 else (1 if neg > pos else (2 if pos > neg else 3))
    mag = max([abs(v - CENTER) for v in active] or [0])
    mb = 0 if mag == 0 else (1 if mag == 1 else (2 if mag <= 3 else 3))
    unpred = int(any(v == 0 for v in vals))
    return cnt + 4*sign + 16*mb + 64*unpred


def hash_bucket_np(features, B):
    if B == 1: return np.zeros_like(features[0], dtype=np.uint16)
    h = np.full(features[0].shape, np.uint32(2166136261), dtype=np.uint32)
    for f in features:
        x = np.asarray(f, dtype=np.uint32)
        h ^= x + np.uint32(0x9e3779b9) + (h << np.uint32(6)) + (h >> np.uint32(2))
    return (h & np.uint32(B - 1)).astype(np.uint16)


def hash_bucket_scalar(features, B):
    if B == 1: return 0
    h = 2166136261
    for x in features:
        h ^= (int(x) + 0x9e3779b9 + ((h << 6) & 0xffffffff) + (h >> 2)) & 0xffffffff
        h &= 0xffffffff
    return h & (B - 1)


def select_features(mode, parent, xp, yp, tp, sibling):
    if mode == 'none': return [parent]
    if mode == 'parent': return [parent]
    if mode == 'neighbors': return [xp, yp, tp]
    if mode == 'parent_neighbors': return [parent, xp, yp, tp]
    if mode == 'sibling': return [sibling]
    if mode == 'full': return [parent, xp, yp, tp, sibling]
    raise ValueError(mode)


def make_features(Q, alphabet):
    syms=[]; bases=[]; parents=[]; xps=[]; yps=[]; tps=[]; siblings=[]
    visited=np.zeros(Q.shape,np.uint8)

    # The 32-spaced coarse grid is the root state for levels 5..1.
    R=Q[0::32,0::32,0::32]
    visited[0::32,0::32,0::32] += 1
    syms.append(np.searchsorted(alphabet,R.ravel()).astype(np.uint8))
    n=R.size
    bases.append(np.zeros(n,np.uint8)); parents.append(np.zeros(n,np.uint16))
    xps.append(np.zeros(n,np.uint16)); yps.append(np.zeros(n,np.uint16)); tps.append(np.zeros(n,np.uint16)); siblings.append(np.zeros(n,np.uint16))

    for level in [5,4,3,2,1]:
        s=1 << (level-1); step=2*s
        sh=(64//step,64//step,512//step)
        P=Q[0:sh[0]*step:step,0:sh[1]*step:step,0:sh[2]*step:step]
        V=[]; parity=[]
        for pi in [0,1]:
            for pj in [0,1]:
                for pt in [0,1]:
                    if pi==pj==pt==0: continue
                    A=Q[pi*s:pi*s+sh[0]*step:step,
                        pj*s:pj*s+sh[1]*step:step,
                        pt*s:pt*s+sh[2]*step:step]
                    assert A.shape == sh
                    V.append(A); parity.append((pi,pj,pt))
                    visited[pi*s:pi*s+sh[0]*step:step,
                            pj*s:pj*s+sh[1]*step:step,
                            pt*s:pt*s+sh[2]*step:step] += 1
        V=np.stack(V,axis=-1)
        cs=cell_state_np(V)
        xp=np.zeros(sh,np.uint16); yp=np.zeros(sh,np.uint16); tp=np.zeros(sh,np.uint16)
        xp[1:,:,:]=cs[:-1,:,:]; yp[:,1:,:]=cs[:,:-1,:]; tp[:,:,1:]=cs[:,:,:-1]
        pstate=sym_state_np(P).astype(np.uint16)
        sib=np.zeros(sh,np.uint16)
        for k in range(7):
            A=V[...,k]
            syms.append(np.searchsorted(alphabet,A.ravel()).astype(np.uint8))
            bases.append(np.full(A.size, 1+(level-1)*7+k, np.uint8))
            parents.append(pstate.ravel()); xps.append(xp.ravel()); yps.append(yp.ravel()); tps.append(tp.ravel()); siblings.append(sib.ravel().copy())
            sib=((sib.astype(np.uint32)*131 + sym_state_np(A).astype(np.uint32)+1) & 255).astype(np.uint16)

    if visited.min()!=1 or visited.max()!=1:
        raise SystemExit(f'coverage failure min={visited.min()} max={visited.max()} countbad={np.count_nonzero(visited!=1)}')
    out=[np.concatenate(x) for x in [syms,bases,parents,xps,yps,tps,siblings]]
    if out[0].size != Q.size: raise SystemExit('symbol count mismatch')
    return out


def context_ids(mode,B,base,parent,xp,yp,tp,sibling):
    ctx=np.zeros(base.shape,np.uint16)
    m=base!=0
    if not np.any(m): return ctx,1
    fs=select_features(mode,parent[m],xp[m],yp[m],tp[m],sibling[m])
    b=hash_bucket_np(fs,B)
    ctx[m]=(1+(base[m].astype(np.uint16)-1)*B+b).astype(np.uint16)
    return ctx,1+35*B


def verify_decoder(mode,B,counts,grouped,alphabet,Qref):
    # Split grouped ID bytes into per-context queues.
    offs=np.concatenate(([0],np.cumsum(counts,dtype=np.int64)))
    streams=[np.frombuffer(grouped[offs[i]:offs[i+1]],dtype=np.uint8) for i in range(len(counts))]
    curs=np.zeros(len(counts),np.int64)
    Q=np.full(Qref.shape, CENTER, np.int32)

    def pull(ctx):
        j=int(curs[ctx]); a=streams[ctx]
        if j>=a.size: raise RuntimeError(f'context underflow {ctx}')
        curs[ctx]=j+1
        return int(alphabet[int(a[j])])

    # root context 0
    for a in range(0,64,32):
        for b in range(0,64,32):
            for c in range(0,512,32):
                Q[a,b,c]=pull(0)

    for level in [5,4,3,2,1]:
        s=1<<(level-1); step=2*s
        na,nb,nc=64//step,64//step,512//step
        cellstates=np.zeros((na,nb,nc),np.uint16)
        for a in range(na):
            for b in range(nb):
                for c in range(nc):
                    i,j,t=a*step,b*step,c*step
                    parent=sym_state_scalar(Q[i,j,t])
                    xp=int(cellstates[a-1,b,c]) if a else 0
                    yp=int(cellstates[a,b-1,c]) if b else 0
                    tp=int(cellstates[a,b,c-1]) if c else 0
                    vals=[]; sib=0; k=0
                    for pi in [0,1]:
                        for pj in [0,1]:
                            for pt in [0,1]:
                                if pi==pj==pt==0: continue
                                base=1+(level-1)*7+k
                                fs=select_features(mode,parent,xp,yp,tp,sib)
                                bucket=hash_bucket_scalar(fs,B)
                                ctx=1+(base-1)*B+bucket
                                v=pull(ctx); Q[i+pi*s,j+pj*s,t+pt*s]=v; vals.append(v)
                                sib=((sib*131 + sym_state_scalar(v)+1) & 255)
                                k+=1
                    cellstates[a,b,c]=cell_state_scalar(vals)
    if np.any(curs != counts):
        raise RuntimeError(f'context cursor mismatch {np.count_nonzero(curs!=counts)}')
    return bool(np.array_equal(Q,Qref))


meta=json.load(open('data/forge_subcube_meta.json'))
eps=float(meta['eps_10pct_std'])
X=np.fromfile('data/forge_subcube_f32.bin','<f4')
R=np.fromfile('stock_rec.bin','<f4')
maxerr=float(np.max(np.abs(X-R)))
if maxerr > eps*1.00001: raise SystemExit(f'stock HPEZ hard error violation {maxerr} > {eps}')

q=np.fromfile('hpez_final_quant_inds.bin',np.int32)
coords=np.fromfile('hpez_final_quant_coords_u64.bin',np.uint64)
if q.size!=64*64*512 or coords.size!=q.size or np.unique(coords).size!=q.size:
    raise SystemExit(f'invalid q/coord dump q={q.size} coords={coords.size}')
phys=np.empty_like(q); phys[coords.astype(np.int64)]=q
Q=phys.reshape(64,64,512)
alphabet=np.unique(q).astype(np.int32)
if alphabet.size>256: raise SystemExit(f'alphabet too large for u8 pilot: {alphabet.size}')

symbols,base,parent,xp,yp,tp,sibling=make_features(Q,alphabet)
prefix=open('hpez_prefix.bin','rb').read()
prefix_z=zbytes_bytes(prefix)
alpha_z=zbytes_bytes(alphabet.astype('<i4').tobytes())
stock_bytes=os.path.getsize('stock.hpez')

# Controls: same dense alphabet, but no causal context separation.
q_dense=np.searchsorted(alphabet,q).astype(np.uint8)
phys_dense=np.searchsorted(alphabet,Q.ravel()).astype(np.uint8)
control=[]
for name,a in [('traversal_dense_zstd',q_dense),('physical_dense_zstd',phys_dense)]:
    ib=zbytes_bytes(a.tobytes())+alpha_z+16
    total=prefix_z+ib+HEADER_BYTES
    control.append({'name':name,'index_bytes':ib,'total_bytes':total,'ratio':RAW_BYTES/total})

configs=[('none',1)]
for B in [2,4,8,16,32]: configs.append(('parent',B))
for B in [2,4,8,16,32]: configs.append(('neighbors',B))
for B in [2,4,8,16,32]: configs.append(('parent_neighbors',B))
for B in [2,4,8,16,32]: configs.append(('sibling',B))
for B in [2,4,8,16,32]: configs.append(('full',B))

rows=[]
for mode,B in configs:
    ctx,nctx=context_ids(mode,B,base,parent,xp,yp,tp,sibling)
    counts=np.bincount(ctx,minlength=nctx).astype('<u4')
    order=np.argsort(ctx,kind='stable')
    grouped=symbols[order].tobytes()
    # Actual compressed bytes for context-directory and grouped symbol payload.
    payload_c=subprocess.run(['zstd','-q','-f','-19','-T0','-c'],input=grouped,stdout=subprocess.PIPE,check=True).stdout
    payload_z=len(payload_c)
    counts_z=zbytes_bytes(counts.tobytes())
    index_bytes=payload_z+counts_z+alpha_z+32
    total=prefix_z+index_bytes+HEADER_BYTES
    # Verify Zstd round-trip and causal reconstruction for every candidate.
    grouped_rt=subprocess.run(['zstd','-q','-d','-c'],input=payload_c,stdout=subprocess.PIPE,check=True).stdout
    ok=verify_decoder(mode,B,counts,grouped_rt,alphabet,Q)
    if not ok: raise SystemExit(f'decoder mismatch {mode} B={B}')
    row={'mode':mode,'B':B,'contexts':nctx,'payload_z':payload_z,'counts_z':counts_z,'alphabet_z':alpha_z,
         'index_bytes':index_bytes,'prefix_z':prefix_z,'total_bytes':total,'ratio':RAW_BYTES/total,'decoder_exact':ok}
    rows.append(row); print('CAUSALCELL',json.dumps(row),flush=True)

rows.sort(key=lambda r:r['total_bytes'])
out={'shape':[64,64,512],'raw_bytes':RAW_BYTES,'eps':eps,'stock_hpez_bytes':stock_bytes,'stock_hpez_ratio':RAW_BYTES/stock_bytes,
     'stock_hpez_maxerr':maxerr,'prefix_raw':len(prefix),'prefix_z':prefix_z,'alphabet_size':int(alphabet.size),
     'controls':control,'best':rows[:12],'all':rows,
     'accounting_note':'Projected integrated container: separately Zstd-compressed HPEZ metadata+quantizer/unpredictable prefix + fixed-spec causal context index frame + 64-byte container header. Every context-coded index frame is decoder-causally reconstructed exactly; HPEZ stock reconstruction independently satisfies original hard epsilon.'}
json.dump(out,open('forge_hpez_causal_cell_results.json','w'),indent=2)
print('BEST',json.dumps(out['best'][:5],indent=2),flush=True)
