import json,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as c
import imperial_dyadic_shared_resonator as ar

C=128;P=32;STEP=256;TRAIN=1024;T0=14488;NS=1024;END=T0+NS
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))

@njit(cache=True)
def recur(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    for cc in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[cc,t-1-j])
            pred=int(np.rint(v));k=int(np.rint((X[cc,t]-pred)/step));R[cc,t]=pred+step*k;K[cc,t]=k
    return R,K

def bp_blob(U,transpose):
    U=np.asarray(U,np.uint64);z=U.T if transpose else U;flat=z.ravel();mx=int(flat.max()) if flat.size else 0;nb=max(1,mx.bit_length());bl=[]
    for bit in range(nb):bl.append(c.Z.compress(np.packbits(((flat>>bit)&1).astype(np.uint8),bitorder='little').tobytes()))
    raw=[]
    for bb in bl:raw.append(c.D.decompress(bb))
    out=np.zeros(flat.size,np.uint64)
    for bit,bb in enumerate(raw):out|=np.unpackbits(np.frombuffer(bb,np.uint8),bitorder='little')[:flat.size].astype(np.uint64)<<bit
    out=out.reshape(z.shape)
    if transpose:out=out.T
    return sum(map(len,bl))+4*nb+40,out,nb

def variant(K,name):
    K=np.asarray(K,np.int32)
    if name=='bp_spacefast':
        U=c.zig(K);n,back,nb=bp_blob(U,True);Q=c.unzig(back).reshape(K.shape)
    elif name=='bp_gray_spacefast':
        U=c.gray(c.zig(K));n,back,nb=bp_blob(U,True);Q=c.unzig(c.ungray(back)).reshape(K.shape)
    elif name=='bp_xors_spacefast':
        U=c.zig(K);A=U.copy();A[1:]=U[1:]^U[:-1];n,back,nb=bp_blob(A,True);UU=back.copy()
        for i in range(1,UU.shape[0]):UU[i]^=UU[i-1]
        Q=c.unzig(UU).reshape(K.shape)
    elif name=='bp_delta_spacefast':
        A=K.astype(np.int64).copy();A[1:]=K[1:].astype(np.int64)-K[:-1].astype(np.int64);U=c.zig(A);n,back,nb=bp_blob(U,True);D=c.unzig(back).astype(np.int64);Q=np.cumsum(D,axis=0,dtype=np.int64).astype(np.int32)
    elif name=='bp_lorenzo_spacefast':
        A=K.astype(np.int64).copy();A[1:,1:]=K[1:,1:].astype(np.int64)-K[:-1,1:].astype(np.int64)-K[1:,:-1].astype(np.int64)+K[:-1,:-1].astype(np.int64);A[0,1:]=K[0,1:].astype(np.int64)-K[0,:-1].astype(np.int64);A[1:,0]=K[1:,0].astype(np.int64)-K[:-1,0].astype(np.int64);U=c.zig(A);n,back,nb=bp_blob(U,True);D=c.unzig(back).astype(np.int64);Q=np.cumsum(np.cumsum(D,axis=0,dtype=np.int64),axis=1,dtype=np.int64).astype(np.int32)
    else:raise ValueError(name)
    if not np.array_equal(Q,K):raise RuntimeError(('variant roundtrip',name))
    return int(n),int(nb)

def main(path):
    names=('bp_spacefast','bp_gray_spacefast','bp_xors_spacefast','bp_delta_spacefast','bp_lorenzo_spacefast')
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=c.stats(d);eps=.1*std;rows=[]
        for label,c0 in SPECS:
            X=np.asarray(d[:END,c0:c0+C],np.float64).T;co=ar.fit_shared(X[:,:TRAIN],P);mb,cd=ar.model_frame(co);R,K=recur(X,np.asarray(cd,np.float32),P,STEP);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>128.000001 or me>eps:raise RuntimeError(('hard',label,me,eps))
            Q=K[:,T0:END];base=c.encode_k(Q);base_bytes=int(base[0])+20
            row={'region':label,'c0':c0,'baseline_bytes':base_bytes,'baseline_bps':8*base_bytes/Q.size,'baseline_rep':base[1],'maxerr':me,'variants':[]}
            for name in names:
                n,nb=variant(Q,name);b=n+20+1;row['variants'].append({'name':name,'bytes':b,'bps':8*b/Q.size,'gain_vs_baseline':base_bytes/b,'nbits':nb})
            row['variants'].sort(key=lambda z:z['bytes']);rows.append(row);print(json.dumps(row,indent=2),flush=True)
    agg=[];base=sum(r['baseline_bytes'] for r in rows);n=C*NS*len(rows)
    for name in names:
        b=sum(next(z['bytes'] for z in r['variants'] if z['name']==name) for r in rows);agg.append({'name':name,'bytes':b,'bps':8*b/n,'baseline_bytes':base,'gain_vs_baseline':base/b,'min_region_gain':min(r['baseline_bytes']/next(z['bytes'] for z in r['variants'] if z['name']==name) for r in rows)})
    agg.sort(key=lambda z:z['bytes']);out={'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'frame_t0':T0,'frame_ns':NS,'regions':[x[0] for x in SPECS],'aggregate':agg,'rows':rows,
    'scope':'Exact bitplane-layout gate on one held-out 128x1024 persistent-AR32 innovation frame from each hard/easy/medium/far region. The current encode_k baseline already tests channel-major zigzag bitplanes plus raw/dt/ds/Lorenzo/zigzag/XOR/Gray. New variants preserve the exact K field but pack each bitplane after transposing K so channel is the fast axis and same-time neighboring sensors become adjacent bits. Additional variants apply reversible Gray, spatial XOR, signed spatial delta, or full Lorenzo before spatially contiguous bitplane packing. Every candidate bitplane payload is Zstd-compressed, byte-decoded, inverse transformed and exact-K checked. One variant byte is charged. This is a backend screen only; sample reconstruction/error is unchanged. No AI.'}
    print(json.dumps({'aggregate':agg},indent=2),flush=True);json.dump(out,open('imperial_ar32_spatial_bitplane_orientation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
