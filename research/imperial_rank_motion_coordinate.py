import json,sys
import h5py,numpy as np
from pysz import sz,szConfig,szErrorBoundMode
import imperial_sparse_causal_annihilator as m

C=128;T=1024;STEP=256
GROUPS=(8,16,32,64,128)
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))

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
    # Exact decoder from sorted values plus either perm/rank representation.
    R=np.empty_like(Q)
    for t in range(Q.shape[1]):
        for g in range(0,Q.shape[0],G):
            p=perm[g:g+G,t]
            for r in range(G):R[g+int(p[r]),t]=S[g+r,t]
    if not np.array_equal(R,Q):raise RuntimeError('rank roundtrip')
    return S,perm,rank

def stability(rank,G):
    if rank.shape[1]<2:return {}
    d=rank[:,1:]-rank[:,:-1]
    unchanged=float(np.mean(d==0));mad=float(np.mean(np.abs(d)))
    # Spearman rank correlation of consecutive permutations, averaged over group/time.
    vals=[]
    for g in range(0,rank.shape[0],G):
        a=rank[g:g+G,:-1].astype(np.float64);b=rank[g:g+G,1:].astype(np.float64)
        aa=a-a.mean(axis=0,keepdims=True);bb=b-b.mean(axis=0,keepdims=True)
        den=np.sqrt((aa*aa).sum(axis=0)*(bb*bb).sum(axis=0));z=(aa*bb).sum(axis=0)/np.maximum(den,1e-12);vals.append(z)
    return {'rank_unchanged_fraction':unchanged,'mean_abs_rank_motion':mad,'median_consecutive_spearman':float(np.median(np.concatenate(vals)))}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;Q=np.rint(X/STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            sb,ori=szrun(X,eps);base_b,base_rep=m.encode_array(Q)
            tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/Q.size,'fixed256_bytes':base_b,'fixed256_bps':8*base_b/Q.size,'fixed256_rep':base_rep})
            for G in GROUPS:
                S,P,RK=rank_transform(Q,G);sv_b,sv_rep=m.encode_array(S);p_b,p_rep=m.encode_array(P);r_b,r_rep=m.encode_array(RK)
                if p_b<=r_b:ib,irep,kind=p_b,p_rep,'sorted_to_physical_perm'
                else:ib,irep,kind=r_b,r_rep,'physical_to_rank'
                total=sv_b+ib+64
                row={'tile':name,'group':G,'bytes':total,'bps':8*total/Q.size,'sorted_value_bytes':sv_b,'sorted_value_rep':sv_rep,
                     'index_bytes':ib,'index_rep':irep,'index_kind':kind,'sz3_bytes':sb,'gain_vs_sz3':sb/total,'gain_vs_fixed256':base_b/total,
                     'fixed256_bytes':base_b,'maxerr':me};row.update(stability(RK,G));rows.append(row)
                print(json.dumps(row),flush=True)
        combos=[];szb=sum(t['sz3_bytes'] for t in tiles);fb=sum(t['fixed256_bytes'] for t in tiles);n=C*T*len(tiles)
        for G in GROUPS:
            rr=[r for r in rows if r['group']==G];b=sum(r['bytes'] for r in rr)
            combos.append({'group':G,'bytes':b,'bps':8*b/n,'sz3_bytes':szb,'fixed256_bytes':fb,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,
                           'median_rank_unchanged':float(np.median([r['rank_unchanged_fraction'] for r in rr])),
                           'median_abs_rank_motion':float(np.median([r['mean_abs_rank_motion'] for r in rr])),
                           'median_spearman':float(np.median([r['median_consecutive_spearman'] for r in rr])),
                           'sorted_value_bps':8*sum(r['sorted_value_bytes'] for r in rr)/n,'index_bps':8*sum(r['index_bytes'] for r in rr)/n})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'groups':list(GROUPS),'tiles':tiles,'combos':combos,'rows':rows,
             'scope':'Order-statistic coordinate codec screen. Each source tile is first mapped to the legal fixed 256 grid (<=128 max error). Within fixed channel groups at every time sample, amplitudes are stably sorted. The decoder receives the sorted amplitude field plus whichever exact rank/permutation field is smaller under the same self-decoding integer frame menu, then reconstructs every physical channel exactly before the hard-error check. This tests whether DAS is simpler as evolving order statistics plus rank motion rather than fixed sensor coordinates. All index bytes and framing are charged; matched SZ3 and fixed-grid bytes are rerun. No AI; four-tile screen only.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_rank_motion_coordinate.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
