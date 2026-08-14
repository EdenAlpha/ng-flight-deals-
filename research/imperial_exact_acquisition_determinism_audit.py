import hashlib,json,math,sys
from collections import defaultdict
import h5py,numpy as np

CHUNK=1024

def entropy_from_counts(counts):
    c=np.asarray(counts,dtype=np.float64);s=float(c.sum())
    if s<=0:return 0.0
    p=c[c>0]/s
    return float(-np.sum(p*np.log2(p)))

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];nt,nc=d.shape
        hashes=[hashlib.sha256() for _ in range(nc)]
        cmin=np.full(nc,np.iinfo(np.int64).max,dtype=np.int64)
        cmax=np.full(nc,np.iinfo(np.int64).min,dtype=np.int64)
        czero=np.zeros(nc,dtype=np.int64)
        pair_dmin=np.full(nc-1,np.iinfo(np.int64).max,dtype=np.int64)
        pair_dmax=np.full(nc-1,np.iinfo(np.int64).min,dtype=np.int64)
        pair_smin=np.full(nc-1,np.iinfo(np.int64).max,dtype=np.int64)
        pair_smax=np.full(nc-1,np.iinfo(np.int64).min,dtype=np.int64)
        residues={m:np.zeros(m,dtype=np.int64) for m in (2,4,8,16,32,256)}
        value_counts=defaultdict(int)
        total=0;eq_time=0;eq_space=0;gval=0;gdt=0
        prev=None
        for t0 in range(0,nt,CHUNK):
            X=np.asarray(d[t0:min(t0+CHUNK,nt),:],dtype=np.int64)
            total+=X.size
            cmin=np.minimum(cmin,X.min(axis=0));cmax=np.maximum(cmax,X.max(axis=0));czero+=np.sum(X==0,axis=0)
            for j in range(nc):hashes[j].update(np.ascontiguousarray(X[:,j]).tobytes())
            u,c=np.unique(X,return_counts=True)
            for vv,cc in zip(u.tolist(),c.tolist()):value_counts[int(vv)]+=int(cc)
            for m,h in residues.items():h+=np.bincount(np.mod(X,m).ravel(),minlength=m)
            av=np.abs(X.ravel());gval=math.gcd(gval,int(np.gcd.reduce(av)))
            if X.shape[0]>1:
                dt=np.diff(X,axis=0);eq_time+=int(np.sum(dt==0));gdt=math.gcd(gdt,int(np.gcd.reduce(np.abs(dt).ravel())))
            if prev is not None:
                bd=X[0]-prev;eq_time+=int(np.sum(bd==0));gdt=math.gcd(gdt,int(np.gcd.reduce(np.abs(bd))))
            prev=X[-1].copy()
            ds=X[:,1:]-X[:,:-1];ss=X[:,1:]+X[:,:-1]
            eq_space+=int(np.sum(ds==0))
            pair_dmin=np.minimum(pair_dmin,ds.min(axis=0));pair_dmax=np.maximum(pair_dmax,ds.max(axis=0))
            pair_smin=np.minimum(pair_smin,ss.min(axis=0));pair_smax=np.maximum(pair_smax,ss.max(axis=0))

        digest_groups=defaultdict(list)
        for j,h in enumerate(hashes):digest_groups[h.hexdigest()].append(j)
        duplicate_groups=[v for v in digest_groups.values() if len(v)>1]
        constants=np.where(cmin==cmax)[0].tolist()
        adjacent_constant_offset=np.where(pair_dmin==pair_dmax)[0].tolist()
        adjacent_sign_offset=np.where(pair_smin==pair_smax)[0].tolist()
        values=sorted(value_counts)
        counts=np.array([value_counts[v] for v in values],dtype=np.int64)
        order=np.argsort(counts)[::-1][:20]
        top=[{'value':int(values[i]),'count':int(counts[i]),'fraction':float(counts[i]/total)} for i in order]
        gmin=int(values[0]);gmax=int(values[-1])
        residue_report={str(m):{'occupied':int(np.sum(h>0)),'entropy_bits':entropy_from_counts(h),'max_fraction':float(h.max()/h.sum()),'counts':h.tolist() if m<=32 else None} for m,h in residues.items()}
        out={
            'shape':[int(nt),int(nc)],'samples':int(total),'dtype':str(d.dtype),'global_min':gmin,'global_max':gmax,
            'unique_raw_values':int(len(values)),'raw_value_entropy_bits':entropy_from_counts(counts),
            'raw_zero_fraction':float(value_counts.get(0,0)/total),'global_min_fraction':float(value_counts[gmin]/total),'global_max_fraction':float(value_counts[gmax]/total),
            'raw_value_gcd':int(gval),'temporal_difference_gcd':int(gdt),
            'exact_temporal_repeat_fraction':float(eq_time/(nc*(nt-1))),
            'exact_adjacent_channel_equal_fraction':float(eq_space/(nt*(nc-1))),
            'constant_channels':constants,'constant_channel_count':len(constants),
            'exact_duplicate_channel_groups':duplicate_groups,'exact_duplicate_channel_group_count':len(duplicate_groups),
            'adjacent_constant_offset_pairs':[{'left':int(i),'right':int(i+1),'offset':int(pair_dmin[i])} for i in adjacent_constant_offset],
            'adjacent_sign_plus_constant_pairs':[{'left':int(i),'right':int(i+1),'sum':int(pair_smin[i])} for i in adjacent_sign_offset],
            'residue_classes':residue_report,'top_raw_values':top,
            'channel_zero_fraction_min':float(np.min(czero/nt)),'channel_zero_fraction_median':float(np.median(czero/nt)),'channel_zero_fraction_max':float(np.max(czero/nt)),
            'scope':'Exact full-record acquisition determinism audit over all Imperial Acoustic samples. Streams the HDF5 without lossy reconstruction and measures exact duplicate/constant channels, constant-offset and sign+offset adjacent channel relations, temporal repeated-sample density, adjacent-channel equality, raw-value and temporal-difference GCD, clipping/extreme-value occupancy, raw alphabet entropy, and low-bit residue occupancy/entropy. SHA256 is used only to identify byte-identical channel traces. This is a diagnostic for exact hardware/ADC redundancy, not a codec and not an AI model.'
        }
        json.dump(out,open('imperial_exact_acquisition_determinism_audit.json','w'),indent=2)
        print(json.dumps(out,indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
