import json,sys
import h5py,numpy as np
import imperial_rank_motion_coordinate as m

C=m.C;T=m.T;STEP=m.STEP
MODES=('walsh','shift_walsh')

def hadamard(n):
    H=np.ones((1,1),np.int64)
    while H.shape[0]<n:H=np.block([[H,H],[H,-H]])
    return H
H=hadamard(C)

def choose_walsh(Q):
    Y=np.empty_like(Q);ids=np.zeros(Q.shape[1],np.int64);Y[:,0]=Q[:,0];prev=Y[:,0].copy()
    for t in range(1,Q.shape[1]):
        cand=H*Q[:,t][None,:];cost=np.abs(cand-prev[None,:]).sum(axis=1);j=int(np.argmin(cost));ids[t]=j;Y[:,t]=cand[j];prev=Y[:,t]
    return Y,np.zeros(Q.shape[1],np.int64),ids

def choose_shift_walsh(Q):
    Y=np.empty_like(Q);sh=np.zeros(Q.shape[1],np.int64);ids=np.zeros(Q.shape[1],np.int64);Y[:,0]=Q[:,0];prev=Y[:,0].copy();ps=0;pm=0
    for t in range(1,Q.shape[1]):
        x=Q[:,t]
        # First search cyclic shift under previous Walsh mask.
        mask=H[pm];best=None
        for s in range(C):
            z=mask*np.roll(x,s);cost=int(np.abs(z-prev).sum());ds=min((s-ps)%C,(ps-s)%C);key=(cost,ds,s)
            if best is None or key<best[0]:best=(key,s,z.copy())
        _,s,z=best
        # Then choose Walsh mask for that shifted slice. One additional shift refinement follows.
        xr=np.roll(x,s);cand=H*xr[None,:];cost=np.abs(cand-prev[None,:]).sum(axis=1);j=int(np.argmin(cost))
        mask=H[j];best=None
        for s2 in range(C):
            zz=mask*np.roll(x,s2);cost2=int(np.abs(zz-prev).sum());ds=min((s2-s)%C,(s-s2)%C);key=(cost2,ds,s2)
            if best is None or key<best[0]:best=(key,s2,zz.copy())
        _,s,z=best;sh[t]=s;ids[t]=j;Y[:,t]=z;prev=z;ps=s;pm=j
    return Y,sh,ids

def inverse(Y,sh,ids):
    R=np.empty_like(Y)
    for t in range(Y.shape[1]):R[:,t]=np.roll(Y[:,t]*H[int(ids[t])],-int(sh[t]))
    return R

def side_bytes(sh,ids):
    sb,sr=m.encode_array(sh.reshape(1,-1));ib,ir=m.encode_array(ids.reshape(1,-1));return sb+ib+32,{'shift_bytes':sb,'shift_rep':sr,'mask_bytes':ib,'mask_rep':ir,'median_shift_change':float(np.median(np.minimum(np.diff(sh)%C,(-np.diff(sh))%C))) if len(sh)>1 else 0.0,'mask_unchanged_fraction':float(np.mean(ids[1:]==ids[:-1])) if len(ids)>1 else 1.0}

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;Q=np.rint(X/STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            szb,ori=m.szrun(X,eps);fb,fr=m.encode_array(Q);tiles.append({'tile':name,'sz3_bytes':szb,'fixed256_bytes':fb,'fixed256_rep':fr})
            for mode in MODES:
                Y,sh,ids=choose_walsh(Q) if mode=='walsh' else choose_shift_walsh(Q);yb,yr=m.encode_array(Y);side,ss=side_bytes(sh,ids);R=inverse(Y,sh,ids)
                if not np.array_equal(R,Q):raise RuntimeError(('inverse',name,mode))
                maxerr=float(np.max(np.abs(X-R*STEP)))
                if maxerr>128.000001 or maxerr>eps:raise RuntimeError(('hard',name,mode,maxerr,eps))
                total=yb+side;row={'tile':name,'mode':mode,'bytes':total,'bps':8*total/Q.size,'payload_bytes':yb,'payload_bps':8*yb/Q.size,'payload_rep':yr,'side_bytes':side,'side_bps':8*side/Q.size,'sz3_bytes':szb,'fixed256_bytes':fb,'gain_vs_sz3':szb/total,'gain_vs_fixed256':fb/total,'maxerr':maxerr};row.update(ss);rows.append(row);print(json.dumps(row),flush=True)
        n=C*T*len(tiles);szb=sum(x['sz3_bytes'] for x in tiles);fb=sum(x['fixed256_bytes'] for x in tiles);combos=[]
        for mode in MODES:
            rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr)
            combos.append({'mode':mode,'bytes':b,'bps':8*b/n,'payload_bps':8*sum(r['payload_bytes'] for r in rr)/n,'side_bps':8*sum(r['side_bytes'] for r in rr)/n,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,'min_tile_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr),'median_mask_unchanged':float(np.median([r['mask_unchanged_fraction'] for r in rr])),'median_shift_change':float(np.median([r['median_shift_change'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'modes':list(MODES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Exact signed-permutation gauge screen. Each legal fixed256 time slice may be multiplied by one decoder-transmitted Walsh/Hadamard +/-1 spatial mask; shift_walsh also uses a transmitted cyclic channel shift. Mask and shift IDs are tiny per-slice side streams and fully charged. The transformed integer field is self-decoding through the same frame menu; decoder reapplies the same Walsh mask (self-inverse) and inverse shift to reproduce Q exactly before the <=128 hard-error check. Greedy gauge selection minimizes L1 change from the previous transformed slice. This tests whether apparent sensor-identity entropy is actually high-wavenumber phase/translation complexity. Matched SZ3/fixed256 rerun; no AI; four-tile screen.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_walsh_signed_permutation_gauge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
