import json,math,sys
import h5py
import numpy as np
from scipy.spatial import cKDTree
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=30000;HALF=15000;RAD=133
BS=(8,16); STEPS=(1,67,134,267); KS=(16,64,256,1024,4096); KNN=16

def h2(p):
    if p<=0 or p>=1:return 0.0
    return -p*math.log2(p)-(1-p)*math.log2(1-p)

def H0(v):
    if len(v)==0:return 0.0
    _,c=np.unique(v,return_counts=True);p=c.astype(np.float64)/c.sum();return float(-(p*np.log2(p)).sum())

def blocks(A,B,t0,t1):
    n=(t1-t0)//B
    return np.ascontiguousarray(A[:,t0:t0+n*B].reshape(A.shape[0],n,B).reshape(-1,B)),n

def build_vocab(P,step,K):
    S=P-P[:,:1]
    if step>1:S=np.rint(S/step).astype(np.int32)*step
    else:S=S.astype(np.int32)
    U,c=np.unique(S,axis=0,return_counts=True)
    order=np.lexsort((np.arange(len(c)),-c))
    return U[order[:min(K,len(U))]].astype(np.float64),int(len(U))

def eval_vocab(Y,nper,V,B):
    F=Y-Y[:,:1]
    tree=cKDTree(V,compact_nodes=True,balanced_tree=True)
    kk=min(KNN,len(V))
    dist,idx=tree.query(F,k=kk,p=np.inf,distance_upper_bound=2*RAD,workers=-1)
    if kk==1:dist=dist[:,None];idx=idx[:,None]
    hit=np.zeros(len(Y),bool);chosen=np.full(len(Y),-1,np.int32);offs=np.zeros(len(Y),np.int32)
    for j in range(kk):
        todo=np.where((~hit)&np.isfinite(dist[:,j]))[0]
        if not len(todo):continue
        ids=idx[todo,j]
        D=Y[todo]-V[ids]
        lo=D.min(axis=1);hi=D.max(axis=1);ok=(hi-lo)<=2*RAD
        ii=todo[ok]
        if len(ii):
            ids2=ids[ok];lo2=lo[ok];hi2=hi[ok]
            o=np.rint((lo2+hi2)/2.0).astype(np.int32)
            hit[ii]=True;chosen[ii]=ids2;offs[ii]=o
    cov=float(hit.mean())
    ids=chosen[hit];ov=offs[hit]
    hid=H0(ids);hoff=H0(ov)
    # Decoder can predict level from the previous referenced level in the same channel;
    # measure only as a diagnostic, resetting at channel boundaries.
    ds=[]
    for c in range(C):
        z=offs[c*nper:(c+1)*nper];m=hit[c*nper:(c+1)*nper]
        prev=None
        for x,yes in zip(z,m):
            if yes:
                if prev is not None:ds.append(int(x)-prev)
                prev=int(x)
            else:prev=None
    hdo=H0(np.asarray(ds,np.int32)) if ds else 0.0
    return {'coverage':cov,'id_H0_bits_per_hit':hid,'offset_H0_bits_per_hit':hoff,'offset_delta_H0_bits_per_linked_hit':hdo,'flag_H0_bps':h2(cov)/B,'id_H0_bps':cov*hid/B,'offset_H0_bps':cov*hoff/B,'hit_payload_H0_bps_using_absolute_offset':h2(cov)/B+cov*(hid+hoff)/B,'hits':int(hit.sum())}

def main(path,cb):
    cb=int(cb);a.C=C;a.NT=NT
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;c0=cb*C
        X=np.asarray(d[:,c0:c0+C],np.float64).T;_,hu=a.fits(X);R,K=a.run_ar(X,hu)
        me=float(np.max(np.abs(X-R.astype(np.float64))))
        if me>eps*(1+1e-12):raise RuntimeError(('hard',cb,me,eps))
        rows=[]
        for B in BS:
            P,ntr=blocks(R,B,0,HALF);Y,nte=blocks(X,B,HALF,NT);P=P.astype(np.float64);Y=Y.astype(np.float64)
            for step in STEPS:
                for Ksz in KS:
                    V,nu=build_vocab(P,step,Ksz);q=eval_vocab(Y,nte,V,B);q.update({'B':B,'shape_quant_step':step,'K_requested':Ksz,'K_actual':len(V),'unique_training_shapes':nu});rows.append(q)
                    print(json.dumps(q),flush=True)
        out={'cb':cb,'c0':c0,'eps':eps,'ar_maxerr':me,'rows':rows,'scope':'Decoder-built translation-invariant shape vocabulary. Codewords are derived solely from already reconstructed first-half AR32 blocks: subtract each block first value, optionally quantize the shape with a fixed public step, count exact shape frequencies, and take the most frequent K. Test blocks are source samples only from the held-out second half. A hit is accepted only if there exists one scalar integer offset making every reconstructed sample stay within +/-133. No future data selects the vocabulary and no dictionary bytes are hidden. Entropy figures are diagnostics, not serialized codec bytes.'}
        json.dump(out,open(f'imperial_legal_shape_vocab_cb{cb}.json','w'),indent=2);print(json.dumps({'cb':cb,'done':True}),flush=True)
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
