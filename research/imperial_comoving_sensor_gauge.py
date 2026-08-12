import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_rank_motion_coordinate as m

C=m.C;T=m.T;STEP=m.STEP
MODES=('shift','shift_sign','shift_parity_sign')

def choose_frame(Q,mode):
    Q=np.asarray(Q,np.int64);Y=np.empty_like(Q);sh=np.zeros(Q.shape[1],np.int64);sg=np.ones(Q.shape[1],np.int64)
    Y[:,0]=Q[:,0];prev=Y[:,0].copy();prev_shift=0
    for t in range(1,Q.shape[1]):
        x=Q[:,t];best=None
        # Full cyclic search; propagation speed is represented by the temporal evolution of the chosen shift.
        for s in range(C):
            z=np.roll(x,s)
            if mode=='shift_parity_sign':
                signs=(-1 if (t&1) else 1,)
            elif mode=='shift_sign': signs=(1,-1)
            else: signs=(1,)
            for sign in signs:
                zz=z*sign;cost=int(np.abs(zz-prev).sum())
                # Secondary tie break prefers smaller cyclic change in coordinate gauge.
                ds=min((s-prev_shift)%C,(prev_shift-s)%C)
                key=(cost,ds,s,0 if sign==1 else 1)
                if best is None or key<best[0]:best=(key,s,sign,zz.copy())
        _,s,sign,z=best;sh[t]=s;sg[t]=sign;Y[:,t]=z;prev=z;prev_shift=s
    return Y,sh,sg

def side_bytes(sh,sg,mode):
    sb,srep=m.encode_array(sh.reshape(1,-1));raw_delta=np.diff(sh,prepend=sh[0]);delta=np.minimum(raw_delta%C,(-raw_delta)%C)
    if mode=='shift_sign':
        bits=(sg<0).astype(np.uint8);packed=np.packbits(bits,bitorder='little').tobytes();blob=m.ZC.compress(packed);un=np.unpackbits(np.frombuffer(m.ZD.decompress(blob),np.uint8),bitorder='little')[:len(bits)]
        if not np.array_equal(un.astype(bool),bits.astype(bool)):raise RuntimeError('sign roundtrip')
        signb=len(blob)+16
    else:signb=0
    return sb+signb+32,{'shift_bytes':sb,'shift_rep':srep,'sign_bytes':signb,'median_abs_cyclic_shift_change':float(np.median(delta[1:])),'mean_abs_cyclic_shift_change':float(np.mean(delta[1:])),'sign_negative_fraction':float(np.mean(sg<0))}

def inverse_frame(Y,sh,sg):
    R=np.empty_like(Y)
    for t in range(Y.shape[1]):R[:,t]=np.roll(Y[:,t]*sg[t],-int(sh[t]))
    return R

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
        for name,t0,c0 in m.SPECS:
            X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;Q=np.rint(X/STEP).astype(np.int64);me=float(np.max(np.abs(X-Q*STEP)))
            if me>128.000001 or me>eps:raise RuntimeError(('grid',name,me,eps))
            szb,ori=m.szrun(X,eps);fb,fr=m.encode_array(Q);tiles.append({'tile':name,'sz3_bytes':szb,'fixed256_bytes':fb,'fixed256_rep':fr})
            for mode in MODES:
                Y,sh,sg=choose_frame(Q,mode);yb,yrep=m.encode_array(Y);side,ss=side_bytes(sh,sg,mode);R=inverse_frame(Y,sh,sg)
                if not np.array_equal(R,Q):raise RuntimeError(('inverse',name,mode))
                maxerr=float(np.max(np.abs(X-R*STEP)))
                if maxerr>128.000001 or maxerr>eps:raise RuntimeError(('hard',name,mode,maxerr,eps))
                total=yb+side;row={'tile':name,'mode':mode,'bytes':total,'bps':8*total/Q.size,'payload_bytes':yb,'payload_bps':8*yb/Q.size,'payload_rep':yrep,'side_bytes':side,'side_bps':8*side/Q.size,'sz3_bytes':szb,'fixed256_bytes':fb,'gain_vs_sz3':szb/total,'gain_vs_fixed256':fb/total,'maxerr':maxerr};row.update(ss);rows.append(row);print(json.dumps(row),flush=True)
        n=C*T*len(tiles);szb=sum(x['sz3_bytes'] for x in tiles);fb=sum(x['fixed256_bytes'] for x in tiles);combos=[]
        for mode in MODES:
            rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr)
            combos.append({'mode':mode,'bytes':b,'bps':8*b/n,'payload_bps':8*sum(r['payload_bytes'] for r in rr)/n,'side_bps':8*sum(r['side_bytes'] for r in rr)/n,'gain_vs_sz3':szb/b,'gain_vs_fixed256':fb/b,'min_tile_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr),'median_shift_change':float(np.median([r['median_abs_cyclic_shift_change'] for r in rr])),'median_negative_sign_fraction':float(np.median([r['sign_negative_fraction'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'modes':list(MODES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Exact co-moving sensor-coordinate gauge screen. The source is first mapped to the legal fixed 256 grid. At each time slice the encoder chooses a global cyclic channel shift minimizing L1 distance to the previously transformed slice; shift_sign also chooses a global polarity, while shift_parity_sign uses the decoder-known (-1)^t polarity. Shift sequence and any sign bits are fully charged and self-decoded. The transformed integer field is encoded through the same self-decoding frame menu, then inverse gauge transforms reproduce Q exactly before the <=128 hard-error check. This tests whether a cheap moving channel coordinate can turn propagating sensor-assignment complexity into stationary dynamics. Matched SZ3 and fixed256 rerun; no AI; four-tile screen.'}
        print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_comoving_sensor_gauge.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
