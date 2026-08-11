import json, math, numpy as np
try:
    import zstandard as zstd
except Exception:
    zstd=None
q=np.fromfile('hpez_final_quant_inds.bin',dtype=np.int32)
N=q.size
vals,cnt=np.unique(q,return_counts=True); center=int(vals[np.argmax(cnt)])

def H_counts(c):
    c=np.asarray(c,dtype=np.float64); c=c[c>0]
    if not c.size:return 0.0
    p=c/c.sum(); return float(-(p*np.log2(p)).sum())
H0=H_counts(cnt)
# Compact alphabet and exact first-/second-order conditional entropies.
_,s=np.unique(q,return_inverse=True); s=s.astype(np.int64); m=int(s.max())+1
pair=s[:-1]*m+s[1:]; pc=np.bincount(pair,minlength=m*m)
Hpair=H_counts(pc); Hprev=H_counts(np.bincount(s[:-1],minlength=m)); H1=Hpair-Hprev
ctx=s[:-2]*m+s[1:-1]; tri=ctx*m+s[2:]
cc=np.bincount(ctx,minlength=m*m); tc=np.bincount(tri,minlength=m*m*m)
H2=H_counts(tc)-H_counts(cc)
# Center/noncenter binary conditional entropy.
b=(q!=center).astype(np.int64)
bpair=b[:-1]*2+b[1:]; Hb1=H_counts(np.bincount(bpair,minlength=4))-H_counts(np.bincount(b[:-1],minlength=2))
# Same-symbol runs.
chg=np.flatnonzero(np.r_[True,q[1:]!=q[:-1],True]); runlen=np.diff(chg); runsym=q[chg[:-1]]
# Center-run lengths before each noncenter symbol.
non=np.flatnonzero(q!=center)
pre=[]; last=-1
for i in non:
    pre.append(int(i-last-1)); last=int(i)
trail=N-last-1
pre=np.asarray(pre,dtype=np.int64)
# Integer coders.
def uvarint(x):
    out=bytearray(); x=int(x)
    while x>=128: out.append((x&127)|128); x>>=7
    out.append(x); return out
def zz(x):
    x=int(x); return (x<<1) ^ (x>>63)
def zbytes(buf):
    if zstd is None:return None
    return len(zstd.ZstdCompressor(level=19).compress(bytes(buf)))
# Grammar A: center-run length then noncenter deviation; final trailing center run.
g=bytearray()
for r,v in zip(pre,q[non]):
    g += uvarint(r); g += uvarint(zz(int(v)-center))
g += uvarint(trail)
# Grammar B: every same-symbol run = length + symbol deviation.
sr=bytearray()
for r,v in zip(runlen,runsym):
    sr += uvarint(int(r)); sr += uvarint(zz(int(v)-center))
# Grammar C: bitmask of noncenter positions + deviations.
mask=np.packbits(q!=center,bitorder='little').tobytes(); dv=bytearray()
for v in q[non]: dv += uvarint(zz(int(v)-center))
maskdev=bytearray(mask)+dv
# Conditional entropy lower bounds converted to bytes, plus tiny alphabet/context overhead omitted explicitly.
out={
 'N':int(N),'alphabet':int(m),'center':center,'center_frac':float(np.mean(q==center)),
 'same_frac':float(np.mean(q[1:]==q[:-1])),
 'H0_bps':H0,'H1_bps':H1,'H2_bps':H2,'binary_center_H1_bps':Hb1,
 'ideal_H0_bytes':H0*N/8,'ideal_H1_bytes':H1*N/8,'ideal_H2_bytes':H2*N/8,
 'run_count':int(runlen.size),'mean_same_run':float(runlen.mean()),'median_same_run':float(np.median(runlen)),'p90_same_run':float(np.quantile(runlen,.9)),'max_same_run':int(runlen.max()),
 'noncenter_count':int(non.size),'mean_center_run_before_noncenter':float(pre.mean()) if pre.size else 0.0,'p90_center_run':float(np.quantile(pre,.9)) if pre.size else 0.0,'max_center_run':int(max(pre.max() if pre.size else 0,trail)),
 'center_run_raw_bytes':len(g),'center_run_zstd19_bytes':zbytes(g),
 'same_run_raw_bytes':len(sr),'same_run_zstd19_bytes':zbytes(sr),
 'maskdev_raw_bytes':len(maskdev),'maskdev_zstd19_bytes':zbytes(maskdev),
}
print(json.dumps(out,indent=2));json.dump(out,open('hpez_symbol_analysis.json','w'),indent=2)
