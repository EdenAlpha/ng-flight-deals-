import json,sys,heapq
import h5py,numpy as np,zstandard as zstd
import imperial_rank_motion_coordinate as b

C=128;T=1024
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stable_interval_order(prev,lo,hi):
    n=len(prev);prio=np.empty(n,np.int32);prio[prev]=np.arange(n,dtype=np.int32)
    # Mandatory precedence i->j exactly when interval i lies wholly below j.
    indeg=np.zeros(n,np.int32)
    for j in range(n):indeg[j]=int(np.count_nonzero(hi < lo[j]))
    hp=[(int(prio[i]),int(i)) for i in range(n) if indeg[i]==0];heapq.heapify(hp)
    out=[];used=np.zeros(n,bool)
    while hp:
        _,i=heapq.heappop(hp)
        if used[i]:continue
        used[i]=True;out.append(i)
        js=np.flatnonzero((hi[i] < lo) & (~used))
        for j in js:
            indeg[j]-=1
            if indeg[j]==0:heapq.heappush(hp,(int(prio[j]),int(j)))
    if len(out)!=n:raise RuntimeError(('interval-order cycle',len(out),n))
    return np.asarray(out,np.int32)

def choose_sorted_values(order,lo,hi,prevS=None):
    l=lo[order].astype(np.int64);h=hi[order].astype(np.int64)
    cap=np.minimum.accumulate(h[::-1])[::-1]
    y=np.empty(len(order),np.int64);last=-(1<<60)
    for r in range(len(order)):
        target=int(l[r]) if prevS is None else int(prevS[r])
        v=max(last,int(l[r]),target)
        v=min(v,int(cap[r]))
        if v<last or v<int(l[r]) or v>int(h[r]):
            # Canonical feasibility fallback: smallest legal nondecreasing value.
            v=max(last,int(l[r]))
        if v>int(h[r]):raise RuntimeError(('isotonic infeasible',r,v,l[r],h[r],cap[r]))
        y[r]=v;last=v
    return y

def lis_keep(seq):
    # Exact LIS indices, sufficient because prev/curr are permutations and any
    # retained sensors keep their previous relative order.
    n=len(seq);dp=np.ones(n,np.int16);par=np.full(n,-1,np.int16);best=0
    for i in range(n):
        for j in range(i):
            if seq[j]<seq[i] and dp[j]+1>dp[i]:dp[i]=dp[j]+1;par[i]=j
        if dp[i]>dp[best]:best=i
    keep=[];q=best
    while q>=0:keep.append(q);q=int(par[q])
    return set(keep[::-1])

def move_records(P):
    records=[];counts=[];moved_fracs=[]
    for t in range(1,P.shape[1]):
        prev=P[:,t-1].astype(np.int16);cur=P[:,t].astype(np.int16)
        pos=np.empty(C,np.int16);pos[prev]=np.arange(C,dtype=np.int16)
        seq=pos[cur];keep=lis_keep(seq);moves=[(r,int(cur[r])) for r in range(C) if r not in keep]
        counts.append(len(moves));moved_fracs.append(len(moves)/C);records.append(moves)
    return records,counts,moved_fracs

def move_frame(P):
    rec,counts,mf=move_records(P)
    raw=bytearray(P[:,0].astype(np.uint8).tobytes())
    for moves in rec:
        raw.append(len(moves)&255)
        for pos,s in moves:raw.append(s&255);raw.append(pos&255)
    blob=ZC.compress(bytes(raw));dec=ZD.decompress(blob);off=0
    prev=np.frombuffer(dec[off:off+C],np.uint8).astype(np.int32).copy();off+=C
    PP=np.empty_like(P,dtype=np.int32);PP[:,0]=prev
    for t in range(1,P.shape[1]):
        n=int(dec[off]);off+=1;moves=[]
        for _ in range(n):
            s=int(dec[off]);p=int(dec[off+1]);off+=2;moves.append((p,s))
        moved={s for _,s in moves};base=[int(s) for s in prev if int(s) not in moved]
        cur=base
        for p,s in sorted(moves):cur.insert(p,s)
        if len(cur)!=C or len(set(cur))!=C:raise RuntimeError(('move decode permutation',t,len(cur),len(set(cur))))
        prev=np.asarray(cur,np.int32);PP[:,t]=prev
    if off!=len(dec):raise RuntimeError(('move decode trailing',off,len(dec)))
    if not np.array_equal(PP,P):raise RuntimeError('move stream roundtrip')
    return len(blob)+24,'braid_moves',float(np.mean(mf)),float(np.median(mf)),float(np.max(mf)),float(np.mean(counts))

def synthesize(X,eps):
    lo=np.ceil(X-eps-1e-12).astype(np.int32);hi=np.floor(X+eps+1e-12).astype(np.int32)
    S=np.empty((C,T),np.int64);P=np.empty((C,T),np.int32);R=np.empty((C,T),np.int64)
    prev=np.argsort(X[:,0],kind='stable').astype(np.int32);prevS=None
    full_same=0;motions=[];spears=[];plateau=[]
    for t in range(T):
        order=prev if t==0 else stable_interval_order(prev,lo[:,t],hi[:,t])
        y=choose_sorted_values(order,lo[:,t],hi[:,t],prevS)
        S[:,t]=y;P[:,t]=order;R[order,t]=y
        if t>0:
            full_same+=int(np.array_equal(order,prev))
            pos0=np.empty(C,np.int32);pos1=np.empty(C,np.int32);pos0[prev]=np.arange(C);pos1[order]=np.arange(C)
            motions.append(float(np.mean(np.abs(pos1-pos0))))
            a=pos0.astype(np.float64);bb=pos1.astype(np.float64);a-=a.mean();bb-=bb.mean();spears.append(float(np.dot(a,bb)/np.sqrt(np.dot(a,a)*np.dot(bb,bb))))
        plateau.append(float(np.mean(np.diff(y)==0)))
        prev=order;prevS=y
    me=float(np.max(np.abs(X-R)))
    if me>eps*(1+1e-10):raise RuntimeError(('hard error',me,eps))
    return S,P,R,{'maxerr':me,'unchanged_whole_order_fraction':full_same/max(1,T-1),'mean_abs_rank_motion':float(np.mean(motions)),
                  'median_consecutive_spearman':float(np.median(spears)),'mean_plateau_edge_fraction':float(np.mean(plateau))}

def physical_rebuild(S,P):
    R=np.empty_like(S)
    for t in range(T):R[P[:,t],t]=S[:,t]
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=b.stats(d);eps=.1*std;rows=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T
            sb,ori=b.szrun(X,eps)
            Q=np.rint(X/256.0).astype(np.int64);base_b,base_rep=b.encode_array(Q)
            S,P,R,st=synthesize(X,eps)
            sv_b,sv_rep=b.encode_array(S)
            rank=np.empty_like(P)
            for t in range(T):rank[P[:,t],t]=np.arange(C,dtype=np.int32)
            p_b,p_rep=b.encode_array(P);r_b,r_rep=b.encode_array(rank)
            mv_b,mv_rep,mv_mean,mv_med,mv_max,mv_count=move_frame(P)
            idx=min((p_b,p_rep,'perm_frame'),(r_b,r_rep,'rank_frame'),(mv_b,mv_rep,'braid_moves'),key=lambda z:z[0])
            RR=physical_rebuild(S,P)
            if not np.array_equal(RR,R):raise RuntimeError('physical decode mismatch')
            me=float(np.max(np.abs(X-RR)))
            if me>eps*(1+1e-10):raise RuntimeError(('decoded hard',name,me,eps))
            total=sv_b+idx[0]+64
            row={'tile':name,'bytes':total,'bps':8*total/(C*T),'sorted_value_bytes':sv_b,'sorted_value_bps':8*sv_b/(C*T),'sorted_value_rep':sv_rep,
                 'identity_bytes':idx[0],'identity_bps':8*idx[0]/(C*T),'identity_rep':idx[1],'identity_kind':idx[2],
                 'move_frame_bytes':mv_b,'move_mean_fraction':mv_mean,'move_median_fraction':mv_med,'move_max_fraction':mv_max,'mean_moved_sensors_per_time':mv_count,
                 'sz3_bytes':sb,'sz3_bps':8*sb/(C*T),'gain_vs_sz3':sb/total,'fixed256_bytes':base_b,'gain_vs_fixed256':base_b/total,'fixed256_rep':base_rep,'orientation':ori}
            row.update(st);rows.append(row);print(json.dumps(row,indent=2),flush=True)
    n=C*T*len(rows);tb=sum(x['bytes'] for x in rows);sz=sum(x['sz3_bytes'] for x in rows);fb=sum(x['fixed256_bytes'] for x in rows)
    out={'std':std,'eps':eps,'shape':[C,T],'rows':rows,'aggregate':{'bytes':tb,'bps':8*tb/n,'sz3_bytes':sz,'sz3_bps':8*sz/n,'gain_vs_sz3':sz/tb,
         'fixed256_bytes':fb,'gain_vs_fixed256':fb/tb,'sorted_value_bps':8*sum(x['sorted_value_bytes'] for x in rows)/n,'identity_bps':8*sum(x['identity_bytes'] for x in rows)/n,
         'median_move_fraction':float(np.median([x['move_median_fraction'] for x in rows]))},
         'scope':'Rank-braid hard-error gauge screen. The codec no longer preserves the nearest-grid sensor rank. Each source sample is only its exact integer +/-epsilon interval. At t=0 sensors are ordered by amplitude. Thereafter interval-disjoint pairs define only the mandatory precedence DAG; a stable topological sort prioritizes the previous decoded sensor order, suppressing every rank crossing not forced by non-overlapping error intervals. Sorted reconstruction values are then chosen inside those intervals with a bounded monotone temporal projection to preserve rank-amplitude continuity. Decoder receives the sorted value field plus the smallest exact identity representation among full permutation, physical-rank, or an actual braid move stream that keeps the LIS of the previous order and transmits only moved sensor IDs+target positions. Both sorted values and identity are byte-decoded; physical samples are rebuilt and the unchanged 10%-global-std hard error is verified. Matched SZ3 and fixed256 are rerun on hard/easy/medium/far 128x1024 tiles. No AI; screen only.'}
    print(json.dumps(out['aggregate'],indent=2),flush=True);json.dump(out,open('imperial_rank_braid_gauge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
