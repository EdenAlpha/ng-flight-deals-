import json,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as codec
import imperial_dyadic_shared_resonator as ar

C=128;T=30000;TB=1024;P=32;STEP=256
SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
MODES=('identity','pairsplit','haar1','haar2','haar3','haar4','haar7','cdf53_1','cdf53_2','cdf53_3','cdf53_4','cdf53_7')

@njit(cache=True)
def recur(X,co,p,step):
    nc,nt=X.shape;R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
    for c in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            pred=int(np.rint(v));k=int(np.rint((X[c,t]-pred)/step));R[c,t]=pred+step*k;K[c,t]=k
    return R,K

@njit(cache=True)
def decode_k(K,co,p,step):
    nc,nt=K.shape;R=np.zeros((nc,nt),np.int32)
    for c in range(nc):
        for t in range(nt):
            v=0.0
            if t>=p:
                v=float(co[p])
                for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
            R[c,t]=int(np.rint(v))+step*int(K[c,t])
    return R

def haar_fwd(A):
    A=np.asarray(A,np.int64);e=A[0::2];o=A[1::2];d=o-e;s=e+np.floor_divide(d,2);return s,d

def haar_inv(s,d):
    s=np.asarray(s,np.int64);d=np.asarray(d,np.int64);e=s-np.floor_divide(d,2);o=d+e;A=np.empty((e.shape[0]*2,e.shape[1]),np.int64);A[0::2]=e;A[1::2]=o;return A

def cdf53_fwd(A):
    A=np.asarray(A,np.int64);e=A[0::2].copy();o=A[1::2].copy();en=np.vstack((e[1:],e[-1:]));d=o-np.floor_divide(e+en,2);dp=np.vstack((d[:1],d[:-1]));s=e+np.floor_divide(dp+d+2,4);return s,d

def cdf53_inv(s,d):
    s=np.asarray(s,np.int64);d=np.asarray(d,np.int64);dp=np.vstack((d[:1],d[:-1]));e=s-np.floor_divide(dp+d+2,4);en=np.vstack((e[1:],e[-1:]));o=d+np.floor_divide(e+en,2);A=np.empty((e.shape[0]*2,e.shape[1]),np.int64);A[0::2]=e;A[1::2]=o;return A

def multilevel_fwd(A,levels,kind):
    cur=np.asarray(A,np.int64);details=[]
    for _ in range(levels):
        cur,d=(haar_fwd(cur) if kind=='haar' else cdf53_fwd(cur));details.append(d)
    return cur,details

def multilevel_inv(coarse,details,kind):
    cur=np.asarray(coarse,np.int64)
    for d in reversed(details):cur=haar_inv(cur,d) if kind=='haar' else cdf53_inv(cur,d)
    return cur

def encode_component(A):
    fr=codec.encode_k(np.asarray(A,np.int32));return int(fr[0])+20,fr[1],np.asarray(fr[2],np.int64)

def encode_mode(K,mode):
    K=np.asarray(K,np.int64)
    if mode=='identity':
        b,rep,D=encode_component(K)
        if not np.array_equal(D,K):raise RuntimeError('identity decode')
        return b,{'components':[{'shape':list(K.shape),'bytes':b,'rep':rep}]},D
    if mode=='pairsplit':
        even=K[0::2];detail=K[1::2]-K[0::2];b0,r0,E=encode_component(even);b1,r1,D=encode_component(detail);R=np.empty_like(K);R[0::2]=E;R[1::2]=E+D
        if not np.array_equal(R,K):raise RuntimeError('pairsplit decode')
        return b0+b1+1,{'components':[{'shape':list(even.shape),'bytes':b0,'rep':r0},{'shape':list(detail.shape),'bytes':b1,'rep':r1}]},R
    kind='haar' if mode.startswith('haar') else 'cdf53';levels=int(mode.split('haar')[-1] if kind=='haar' else mode.split('_')[-1]);coarse,details=multilevel_fwd(K,levels,kind);comps=[];cb,cr,Cd=encode_component(coarse);comps.append({'band':'coarse','shape':list(coarse.shape),'bytes':cb,'rep':cr});dd=[];total=cb
    for lev,d in enumerate(details,1):
        b,r,z=encode_component(d);total+=b;dd.append(z);comps.append({'band':f'd{lev}','shape':list(d.shape),'bytes':b,'rep':r})
    R=multilevel_inv(Cd,dd,kind)
    if not np.array_equal(R,K):raise RuntimeError(('lifting decode',mode))
    return total+1,{'components':comps},R

def matched_sz3(X,eps):
    total=0
    for t0 in range(0,T,TB):
        t1=min(T,t0+TB);b,_=codec.szrun(X[:,t0:t1],eps);total+=b
    return int(total)

def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=codec.stats(d);eps=.1*std;rows=[];regions=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:,c0:c0+C],np.float64).T;co=ar.fit_shared(X[:,:TB],P);mb,cd=ar.model_frame(co);R,K=recur(X,np.asarray(cd,np.float32),P,STEP);me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>128.000001 or me>eps:raise RuntimeError(('source hard',name,me,eps))
            szb=matched_sz3(X,eps);reg={'region':name,'c0':c0,'samples':int(X.size),'model_bytes':int(mb),'sz3_bytes':szb,'sz3_bps':8*szb/X.size};regions.append(reg)
            # Each transform is frozen across all 1024-sample innovation frames; one transform ID byte per original frame is charged by encode_mode.
            for mode in MODES:
                total=int(mb)+32;reps={};component_bytes=0
                Kd=np.empty_like(K,np.int64)
                for fi,t0 in enumerate(range(0,T,TB)):
                    t1=min(T,t0+TB);b,meta,back=encode_mode(K[:,t0:t1],mode);total+=b;component_bytes+=b;Kd[:,t0:t1]=back
                    for z in meta['components']:reps[z['rep']]=reps.get(z['rep'],0)+1
                if not np.array_equal(Kd,K):raise RuntimeError(('K roundtrip',name,mode))
                Rd=decode_k(Kd.astype(np.int32),np.asarray(cd,np.float32),P,STEP);fme=float(np.max(np.abs(X-Rd.astype(np.float64))))
                if fme>eps*(1+1e-12) or fme>128.000001:raise RuntimeError(('final hard',name,mode,fme,eps))
                row={'region':name,'c0':c0,'mode':mode,'bytes':total,'innovation_bytes':component_bytes,'model_bytes':int(mb),'bps':8*total/X.size,'innovation_bps':8*component_bytes/X.size,'sz3_bytes':szb,'gain_vs_sz3':szb/total,'maxerr':fme,'reps':reps};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='reps'}),flush=True)
        n=sum(r['samples'] for r in regions);sz=sum(r['sz3_bytes'] for r in regions);combos=[]
        for mode in MODES:
            rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr);ib=sum(r['innovation_bytes'] for r in rr)
            combos.append({'mode':mode,'bytes':b,'innovation_bytes':ib,'bps':8*b/n,'innovation_bps':8*ib/n,'sz3_bytes':sz,'gain_vs_sz3':sz/b,'min_region_gain_vs_sz3':min(r['gain_vs_sz3'] for r in rr),'median_region_gain_vs_sz3':float(np.median([r['gain_vs_sz3'] for r in rr]))})
        combos.sort(key=lambda x:x['bytes']);base=next(x for x in combos if x['mode']=='identity')
        for x in combos:x['gain_vs_identity']=base['bytes']/x['bytes'];x['innovation_gain_vs_identity']=base['innovation_bytes']/x['innovation_bytes']
        out={'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'regions':[x[0] for x in SPECS],'time_samples':T,'width':C,'modes':list(MODES),'aggregate':combos,'region_metadata':regions,'rows':rows,
             'scope':'Exact reversible spatial-subband screen on persistent shared AR32 innovations. Each 128-channel region fits one shared float32 AR32 model only from the first 1024 source samples and keeps state continuous over all 30000 samples. For every 1024-sample K frame, identity uses the existing encode_k menu (which already includes raw, temporal delta, spatial first delta, full Lorenzo, zigzag XOR, Gray and bitplanes). New modes split adjacent-channel structure into independently entropy-coded reversible subbands: pair split, integer Haar lifting, and reversible CDF 5/3 lifting at 1/2/3/4/7 levels. Every subband uses the exact existing self-decoding encode_k backend and pays its own frame overhead plus one transform-ID byte per original frame. Subbands are byte-decoded, inverse lifted to exact K, persistent AR32 reconstruction is rerun, and <=128 hard error verified. Matched SZ3 is rerun on the identical 128x1024 tiling. No AI; four full-minute region screen, not whole-array.'}
        print(json.dumps({'aggregate':combos},indent=2),flush=True);json.dump(out,open('imperial_ar32_spatial_lifting_innovations.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
