import sys,math,numpy as np
import imperial_256lane_interrogator_topology as q

# All actual K compression candidates in q.main still use every 256x8192 sample.
# Only the information-diagnostic functions below deterministically thin their
# input to avoid repeatedly sorting millions of symbol pairs.
DIAG_STRIDE=8

def _sample(a):
    a=np.asarray(a,np.int32)
    # Keep every eighth time sample for every channel; main passes 2-D [channel,time].
    if a.ndim==2:return np.ascontiguousarray(a[:,::DIAG_STRIDE])
    return np.ascontiguousarray(a.ravel()[::DIAG_STRIDE])

def entropy_int_fast(x):
    z=_sample(x).ravel()
    _,cnt=np.unique(z,return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())

def conditional_entropy_fast(x,y):
    x=_sample(x).ravel();y=_sample(y).ravel()
    if x.size!=y.size:raise RuntimeError('diagnostic sample mismatch')
    # Pack the exact signed int32 pair into a sortable uint64 key.
    ux=x.view(np.uint32).astype(np.uint64);uy=y.view(np.uint32).astype(np.uint64)
    key=(ux<<np.uint64(32))|uy
    _,cxy=np.unique(key,return_counts=True);p=cxy.astype(np.float64)/cxy.sum()
    hxy=float(-(p*np.log2(p)).sum())
    return hxy-entropy_int_fast(x)

def bitplane_xor_entropy_fast(x,y):
    x=_sample(x);y=_sample(y)
    def zz(v):
        z=np.asarray(v,np.int64);return np.where(z>=0,2*z,-2*z-1).astype(np.uint64)
    a0=zz(x);b0=zz(y);rows=[]
    for bit in range(8):
        z=((a0>>bit)^(b0>>bit))&1;pf=float(np.mean(z))
        h=0.0 if pf in (0.0,1.0) else float(-pf*math.log2(pf)-(1-pf)*math.log2(1-pf))
        rows.append({'bit':bit,'xor_one_fraction':pf,'xor_entropy_bps':h,'diagnostic_time_stride':DIAG_STRIDE})
    return rows

q.entropy_int=entropy_int_fast
q.conditional_entropy=conditional_entropy_fast
q.bitplane_xor_entropy=bitplane_xor_entropy_fast

if __name__=='__main__':q.main(sys.argv[1])
