import json,sys
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;STEP=256
GROUPS=(8,16,32,64,128)
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stats(d):
    s=ss=0.;n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mean=s/n
    return mean,float(np.sqrt(max(0.,ss/n-mean*mean)))

def dtype_for(a):
    a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
    for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
        ii=np.iinfo(dt)
        if mn>=ii.min and mx<=ii.max:return dt
    return np.dtype('<i8')

def zzenc(a):
    x=np.asarray(a,np.int64);return ((x<<1)^(x>>63)).astype(np.uint64)

def zzdec(z):
    z=np.asarray(z,np.uint64);return ((z>>1).astype(np.int64)^(-(z&1).astype(np.int64)))

def encode_array(a):
    a=np.asarray(a,np.int64);shape=a.shape;cands=[]
    def signed_candidate(x,rep):
        dt=dtype_for(x);blob=ZC.compress(np.ascontiguousarray(x.astype(dt)).tobytes());r=np.frombuffer(ZD.decompress(blob),dtype=dt,count=x.size).astype(np.int64).reshape(shape)
        if rep=='raw':q=r
        elif rep=='dt':q=np.cumsum(r,axis=1,dtype=np.int64)
        elif rep=='dc':q=np.cumsum(r,axis=0,dtype=np.int64)
        else:q=np.cumsum(np.cumsum(r,axis=0,dtype=np.int64),axis=1,dtype=np.int64)
        if not np.array_equal(q,a):raise RuntimeError(('frame roundtrip',rep))
        cands.append((len(blob)+16,rep+'_'+dt.str))
    signed_candidate(a,'raw')
    if a.shape[1]>1:
        x=a.copy();x[:,1:]=a[:,1:]-a[:,:-1];signed_candidate(x,'dt')
    if a.shape[0]>1:
        x=a.copy();x[1:,:]=a[1:,:]-a[:-1,:];signed_candidate(x,'dc')
    if a.shape[0]>1 and a.shape[1]>1:
        x=a.copy();x[1:,1:]=a[1:,1:]-a[:-1,1:]-a[1:,:-1]+a[:-1,:-1];x[0,1:]=a[0,1:]-a[0,:-1];x[1:,0]=a[1:,0]-a[:-1,0];signed_candidate(x,'lor')
    u=zzenc(a);mx=int(u.max()) if u.size else 0;udt=np.dtype('u1') if mx<256 else (np.dtype('<u2') if mx<65536 else np.dtype('<u4'))
    blob=ZC.compress(np.ascontiguousarray(u.astype(udt)).tobytes());uu=np.frombuffer(ZD.decompress(blob),dtype=udt,count=u.size).astype(np.uint64).reshape(shape);q=zzdec(uu)
    if not np.array_equal(q,a):raise RuntimeError('zigzag roundtrip')
    cands.append((len(blob)+16,'zz_'+udt.str))
    nbits=max(1,mx.bit_length())
    for tr in (False,True):
        z=u.T if tr else u;n=z.size;per=(n+7)//8;planes=[]
        for bit in range(nbits-1,-1,-1):planes.append(np.packbits(((z>>bit)&1).astype(np.uint8).ravel(),bitorder='little').tobytes())
        payload=b''.join(planes);blob=ZC.compress(payload);raw=ZD.decompress(blob);back=np.zeros(n,np.uint64)
        for j,bit in enumerate(range(nbits-1,-1,-1)):
            bits=np.unpackbits(np.frombuffer(raw[j*per:(j+1)*per],np.uint8),bitorder='little')[:n].astype(np.uint64);back|=bits<<bit
        back=back.reshape(z.shape)
        if tr:back=back.T
        if not np.array_equal(zzdec(back),a):raise RuntimeError(('bitplane roundtrip',tr))
        cands.append((len(blob)+20,'bpT' if tr else 'bp'))
    return min(cands,key=lambda x:x[0])

def szrun(X,eps):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
        b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
        if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
        r=(int(b.size),'T' if tr else 'CT')
        if best is None or r[0]<best[0]:best=r
    return best

def rank_transform(Q,G):
    Q=np.asarray(Q,np.int64);S=np.empty_like(Q);perm=np.empty(Q.shape,np.int64);rank=np.empty(Q.shape,np.int64)
    for t in range(Q.shape[1]):
        for g in range(0,Q.shape[0],G):
            x=Q[g:g+G,t];idx=np.argsort(x,kind='stable');S[g:g+G,t]=x[idx];perm[g:g+G,t]=idx
            inv=np.empty(G,np.int64);inv[idx]=np.arange(G,dtype=np.int64);rank[g:g+G,t]=inv
    R=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for g in range(0,Q.shape[0],G):
            p=perm[g:g+G,t]
            for r in range(G):R[g+int(p[r]),t]=S[g+r,t]
    if not np.array_equal(R,Q):raise RuntimeError('rank roundtrip')
    return S,perm,rank

def stability(rank,G):
    if rank.shape[1]<2:return {}
    d=rank[:,1:]-rank[:,:-1];unchanged=float(np.mean(d==0));mad=float(np.mean(np.abs(d)));vals=[]
    for g in range(0,rank.shape[0],G):
        a=rank[g:g+G,:-1].astype(np.float64);b=rank[g:g+G,1:].astype(np.float64);aa=a-a.mean(axis=0,keepdims=True);bb=b-b.mean(axis=0,keepdims=True)
        den=np.sqrt((aa*aa).sum(axis=0)*(bb*bb).sum(axis=0));vals.append((aa*bb).sum(axis=0)/np.maximum(den,1e-12))
    return {'rank_unchanged_fraction':unchanged,'mean_abs_rank_motion':mad,'median_consecutive_spearman':float(np.median(np.concatenate(vals)))}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;Q=np.rint(X/STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            sb,ori=szrun(X,eps);base_b,base_rep=encode_array(Q)
            tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/Q.size,'fixed256_bytes':base_b,'fixed256_bps':8*base_b/Q.size,'fixed256_rep':base_rep})
            for G in GROUPS:
                S,P,RK=rank_transform(Q,G);sv_b,sv_rep=encode_array(S);p_b,p_rep=encode_array(P);r_b,r_rep=encode_array(RK)
                if p_b<=r_b:ib,irep,kind=p_b,p_rep,'sorted_to_physical_perm'
                else:ib,irep,kind=r_b,r_rep,'physical_to_rank'
                total=sv_b+ib+64
                row={'tile':name,'group':G,'bytes':total,'bps':8*total/Q.size,'sorted_value_bytes':sv_b,'sorted_value_rep':sv_rep,'index_bytes':ib,'index_rep':irep,'index_kind':kind,'sz3_bytes':sb,'gain_vs_sz3':sb/total,'gain_vs_fixed256':base_b/total,'fixed256_bytes':base_b,'maxerr':me};row.update(stability(RK,G));rows.append(row);print(json.dumps(row),flush=True)
        combos=[];szb=sum(t['sz3_bytes'] for t in tiles);fb=sum(t['fixed256_bytes'] for t in tiles);n=C*T*len(tiles)
        for G in GROUPS:
            rr=[r for r in rows if r['group']==G];b=sum(r['bytes'] for r in rr)
            combos.append({'group':G,'bytes':b,'bps':8*b/n,'sz3_bytes':szb,'fixed256_bytes':fb,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,'median_rank_unchanged':float(np.median([r['rank_unchanged_fraction'] for r in rr])),'median_abs_rank_motion':float(np.median([r['mean_abs_rank_motion'] for r in rr])),'median_spearman':float(np.median([r['median_consecutive_spearman'] for r in rr])),'sorted_value_bps':8*sum(r['sorted_value_bytes'] for r in rr)/n,'index_bps':8*sum(r['index_bytes'] for r in rr)/n})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'groups':list(GROUPS),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Order-statistic coordinate codec screen. Each source tile is first mapped to the legal fixed 256 grid (<=128 max error). Within fixed channel groups at every time sample, amplitudes are stably sorted. The decoder receives the sorted amplitude field plus whichever exact rank/permutation field is smaller under a self-contained self-decoding integer frame menu, then reconstructs every physical channel exactly before the hard-error check. This tests whether DAS is simpler as evolving order statistics plus rank motion rather than fixed sensor coordinates. All index bytes and framing are charged; matched SZ3 and fixed-grid bytes are rerun. No AI; four-tile screen only.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_rank_motion_coordinate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
