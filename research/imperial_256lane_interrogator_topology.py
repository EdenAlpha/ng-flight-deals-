import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r
import imperial_persistent_ar32_full_array_jit as a

STEP=267;P=32;C128=128;C256=256;NT=8192;TB=1024
m.STEP=STEP;a.m.m.STEP=STEP
GROUPS=(('hard',512),('easy',2304),('medium',4608),('far',6656))
STRIDES=(2,4,8,16,32,64,128)
OFFSETS=(1,2,4,8,16,32,64,128)


def fit_half(X):
    co=r.fit_shared(X[:,:TB],P);mb,cd=r.model_frame(co)
    R,K=a.build(X,cd)
    return cd,int(mb),R,K


def enc(A):
    A=np.asarray(A,np.int32);total=0;reps={};D=np.empty_like(A)
    for t0 in range(0,A.shape[1],TB):
        fr=m.encode_k(A[:,t0:t0+TB]);n,rep,Q=int(fr[0]),fr[1],fr[2]
        total+=n+20;reps[rep]=reps.get(rep,0)+1;D[:,t0:t0+Q.shape[1]]=Q
        if not np.array_equal(Q,A[:,t0:t0+Q.shape[1]]):raise RuntimeError('frame decode')
    return total,reps,D


def permutation(stride):
    # Lane-major ordering: split 256 sequential channels into `stride` interleaved lanes.
    order=np.arange(C256,dtype=np.int32).reshape(-1,stride).T.ravel()
    inv=np.empty_like(order);inv[order]=np.arange(C256,dtype=np.int32)
    return order,inv


def entropy_int(x):
    _,cnt=np.unique(np.asarray(x).ravel(),return_counts=True);p=cnt.astype(np.float64)/cnt.sum()
    return float(-(p*np.log2(p)).sum())


def conditional_entropy(x,y):
    # H(Y|X) exact empirical discrete entropy. Values are typically small AR innovation integers.
    x=np.asarray(x,np.int32).ravel();y=np.asarray(y,np.int32).ravel()
    xy=np.stack([x,y],axis=1)
    _,cxy=np.unique(xy,axis=0,return_counts=True);p=cxy.astype(np.float64)/cxy.sum();hxy=float(-(p*np.log2(p)).sum())
    return hxy-entropy_int(x)


def bitplane_xor_entropy(x,y):
    # Zigzag low 8 planes: nonlinear/digital dependence diagnostic, not a byte claim.
    def zz(v):
        z=np.asarray(v,np.int64);return np.where(z>=0,2*z,-2*z-1).astype(np.uint64)
    a0=zz(x);b0=zz(y);rows=[]
    for bit in range(8):
        z=((a0>>bit)^(b0>>bit))&1;pf=float(np.mean(z));
        h=0.0 if pf in (0.0,1.0) else float(-pf*math.log2(pf)-(1-pf)*math.log2(1-pf))
        rows.append({'bit':bit,'xor_one_fraction':pf,'xor_entropy_bps':h})
    return rows


def split_transform(K):
    A=K[:128].copy();D=(K[128:].astype(np.int64)-K[:128].astype(np.int64)).astype(np.int32)
    ab,ar,Ad=enc(A);db,dr,Dd=enc(D)
    R=np.empty_like(K);R[:128]=Ad;R[128:]=Ad+Dd
    if not np.array_equal(R,K):raise RuntimeError('split-delta inverse')
    return {'bytes':ab+db,'a_bytes':ab,'d_bytes':db,'a_reps':ar,'d_reps':dr}


def xor_transform(K):
    # Reversible zigzag XOR across the two 128-channel halves.
    def zz(v):
        v=np.asarray(v,np.int64);return np.where(v>=0,2*v,-2*v-1).astype(np.uint32)
    def unzz(z):
        z=np.asarray(z,np.uint32).astype(np.uint64);return np.where((z&1)==0,z>>1,-((z>>1)+1)).astype(np.int32)
    A=K[:128].copy();za=zz(A);zb=zz(K[128:]);X=(za^zb).astype(np.uint32)
    # reinterpret unsigned XOR values as int32 exactly for existing lossless backend.
    Xi=X.view(np.int32)
    ab,ar,Ad=enc(A);xb,xr,Xd=enc(Xi)
    recx=Xd.astype(np.int32).view(np.uint32);B=unzz(zz(Ad)^recx)
    R=np.vstack([Ad,B])
    if not np.array_equal(R,K):raise RuntimeError('xor inverse')
    return {'bytes':ab+xb,'a_bytes':ab,'xor_bytes':xb,'a_reps':ar,'xor_reps':xr}


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[]
        for name,c0 in GROUPS:
            X=np.asarray(d[:NT,c0:c0+C256],np.float64).T
            c0coef,m0,R0,K0=fit_half(X[:128]);c1coef,m1,R1,K1=fit_half(X[128:]);K=np.vstack([K0,K1])
            R=np.vstack([R0,R1]);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'hard',me,eps))
            # Current incumbent: two natural 128-channel AR32 innovation streams.
            b0,r0,D0=enc(K0);b1,r1,D1=enc(K1);base=b0+b1+m0+m1+64
            if not np.array_equal(np.vstack([D0,D1]),K):raise RuntimeError('baseline K')
            # Single 256 frame and fixed lane permutations; model cost remains identical.
            oneb,oner,oned=enc(K)
            if not np.array_equal(oned,K):raise RuntimeError('one256')
            layouts=[{'kind':'contiguous256','bytes':oneb+m0+m1+64,'payload_bytes':oneb,'reps':oner}]
            for s in STRIDES:
                order,inv=permutation(s);pb,pr,Pd=enc(K[order]);back=Pd[inv]
                if not np.array_equal(back,K):raise RuntimeError(('perm inverse',s))
                layouts.append({'kind':f'lane_stride_{s}','bytes':pb+m0+m1+64,'payload_bytes':pb,'reps':pr})
            sp=split_transform(K);layouts.append({'kind':'half_delta','bytes':sp['bytes']+m0+m1+72,'payload_bytes':sp['bytes'],'detail':sp})
            xo=xor_transform(K);layouts.append({'kind':'half_zigzag_xor','bytes':xo['bytes']+m0+m1+72,'payload_bytes':xo['bytes'],'detail':xo})
            # Diagnostics at possible digital-lane offsets.
            deps=[]
            for off in OFFSETS:
                x=K[:-off];y=K[off:]
                hx=entropy_int(x);hy=entropy_int(y);hygx=conditional_entropy(x,y)
                deps.append({'offset':off,'H_x':hx,'H_y':hy,'H_y_given_x':hygx,'mutual_information_bps':hy-hygx,
                             'linear_corr':float(np.corrcoef(x.ravel(),y.ravel())[0,1]),
                             'zigzag_xor_low8':bitplane_xor_entropy(x,y)})
            layouts.sort(key=lambda z:z['bytes']);best=layouts[0]
            row={'region':name,'c0':c0,'samples':int(X.size),'eps':eps,'maxerr':me,
                 'baseline_bytes':int(base),'baseline_bps':8*base/X.size,
                 'best':best,'best_gain_vs_two128':base/best['bytes'],'layouts':layouts,'offset_dependence':deps,
                 'model_bytes':[m0,m1]}
            rows.append(row);print(json.dumps({'region':name,'baseline_bps':row['baseline_bps'],'best':best,
                'best_gain_vs_two128':row['best_gain_vs_two128'],
                'offset_MI':[(q['offset'],q['mutual_information_bps'],q['linear_corr']) for q in deps]},indent=2),flush=True)
        # Freeze one common layout across all four groups to avoid per-region cherry-picking.
        kinds=sorted({x['kind'] for r0 in rows for x in r0['layouts']})
        combos=[]
        for kind in kinds:
            bb=sum(r0['baseline_bytes'] for r0 in rows);nn=sum(r0['samples'] for r0 in rows)
            vv=[next(x for x in r0['layouts'] if x['kind']==kind) for r0 in rows];b=sum(x['bytes'] for x in vv)
            combos.append({'kind':kind,'bytes':b,'baseline_bytes':bb,'bps':8*b/nn,'baseline_bps':8*bb/nn,'gain_vs_two128':bb/b})
        combos.sort(key=lambda x:x['bytes'])
        out={'global_std':std,'eps':eps,'analysis_nt':NT,'groups':[list(x) for x in GROUPS],
             'rows':rows,'frozen_layouts':combos,
             'scope':('Exact innovation-topology screen. Imperial has 6912=27*256 channels. This does not dispute that physical nearest-neighbor topology is offset1; it asks whether a secondary interrogator/DSP lane structure remains in the decoder-real AR32 innovation field. Each natural 256 group is still predicted by the incumbent two independently trained shared AR32 models on its two 128 halves, so source modeling and hard-error contract are unchanged. Exact K is then losslessly encoded as two128 incumbent frames, one contiguous256 frame, fixed lane-major permutations, half-delta, or reversible zigzag-XOR across halves. Every candidate is byte-decoded/inverted exactly; because K is exact the previously verified AR32 reconstruction remains identical and max error is rechecked. Fixed offsets 1..128 also report discrete conditional entropy, mutual information, linear correlation and low zigzag-bit XOR entropy as diagnostics. One common layout is aggregated across hard/easy/medium/far groups. No AI; screen only.')}
        json.dump(out,open('imperial_256lane_interrogator_topology.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
