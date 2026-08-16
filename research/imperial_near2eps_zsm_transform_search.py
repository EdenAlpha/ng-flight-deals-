import json,sys
import h5py,numpy as np
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

q.f.q_decode=sc.q_decode
TRANSFORMS=('raw','time_delta','space_delta','lorenzo','med','paeth','avg')

def pred(a,l,u,d,mode):
    if mode=='med':
        if d>=max(l,u):return min(l,u)
        if d<=min(l,u):return max(l,u)
        return l+u-d
    if mode=='paeth':
        p=l+u-d;pl=abs(p-l);pu=abs(p-u);pd=abs(p-d)
        return l if pl<=pu and pl<=pd else (u if pu<=pd else d)
    if mode=='avg':return (l+u)//2
    raise ValueError(mode)

def transform(D,mode):
    D=np.asarray(D,np.int32)
    if mode=='raw':return D.copy()
    E=np.empty_like(D)
    if mode=='time_delta':
        E[:,0]=D[:,0];E[:,1:]=D[:,1:]-D[:,:-1];return E
    if mode=='space_delta':
        E[0,:]=D[0,:];E[1:,:]=D[1:,:]-D[:-1,:];return E
    if mode=='lorenzo':
        E[0,0]=D[0,0]
        E[0,1:]=D[0,1:]-D[0,:-1]
        E[1:,0]=D[1:,0]-D[:-1,0]
        E[1:,1:]=D[1:,1:]-D[1:,:-1]-D[:-1,1:]+D[:-1,:-1]
        return E
    for t in range(D.shape[1]):
        for c in range(D.shape[0]):
            l=int(D[c-1,t]) if c else 0;u=int(D[c,t-1]) if t else 0;d=int(D[c-1,t-1]) if c and t else 0
            E[c,t]=int(D[c,t])-pred(D,l,u,d,mode)
    return E

def inverse(E,mode):
    E=np.asarray(E,np.int32)
    if mode=='raw':return E.copy()
    D=np.empty_like(E)
    if mode=='time_delta':
        D[:,0]=E[:,0]
        for t in range(1,E.shape[1]):D[:,t]=D[:,t-1]+E[:,t]
        return D
    if mode=='space_delta':
        D[0,:]=E[0,:]
        for c in range(1,E.shape[0]):D[c,:]=D[c-1,:]+E[c,:]
        return D
    if mode=='lorenzo':
        for t in range(E.shape[1]):
            for c in range(E.shape[0]):
                l=int(D[c-1,t]) if c else 0;u=int(D[c,t-1]) if t else 0;d=int(D[c-1,t-1]) if c and t else 0
                if c and t:p=l+u-d
                elif c:p=l
                elif t:p=u
                else:p=0
                D[c,t]=p+int(E[c,t])
        return D
    for t in range(E.shape[1]):
        for c in range(E.shape[0]):
            l=int(D[c-1,t]) if c else 0;u=int(D[c,t-1]) if t else 0;d=int(D[c-1,t-1]) if c and t else 0
            D[c,t]=pred(D,l,u,d,mode)+int(E[c,t])
    return D

def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+q.C],np.float64).T
    h,Q,D,dts,dcs,co,intercept,changes,meanlegal=q.build_full(X,eps)
    mb,mrep,ddt,ddc,dco,dinter=g.model_frame(dts,dcs,co,intercept)
    screens=[];cache={}
    for mode in TRANSFORMS:
        E=transform(D,mode);cache[mode]=E
        if not np.array_equal(inverse(E,mode),D):raise RuntimeError(('transform replay',mode))
        for W in q.WINDOWS:
            bb,nb=q.encode_zsm(E,W,q.SCREEN);screens.append({'payload':len(bb),'bits':int(nb),'mode':mode,'W':int(W)})
            print(json.dumps({'screen':screens[-1]}),flush=True)
    screens.sort(key=lambda r:r['payload']);best_screen=screens[0];mode=best_screen['mode'];W=best_screen['W'];E=cache[mode]
    bb,nbit=q.encode_zsm(E,W,q.NT);Ed=q.decode_zsm(bb,nbit,W,E.shape);Dd=inverse(Ed,mode)
    if not np.array_equal(Ed,E):raise RuntimeError('ZSM transformed decode')
    if not np.array_equal(Dd,D):raise RuntimeError('inverse transformed defect')
    Qd=q.f.q_decode(Dd,ddt,ddc,dco,dinter,q.f.SCALE)
    if not np.array_equal(Qd,Q):raise RuntimeError('Q replay')
    me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
    if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
    total=int(mb)+len(bb)+q.HEADER+2
    hist=2478995;sz3=2767977
    out={'region':'hard','shape':[q.C,q.NT],'samples':int(X.size),'eps':eps,'hfac':q.FAC,'model_bytes':int(mb),'selected_transform':mode,'selected_window':int(W),'payload_bytes':len(bb),'arithmetic_bits':int(nbit),'total_bytes':total,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/total,'matched_sz3_bytes':sz3,'gain_vs_sz3':sz3/total,'maxerr':me,'screens':screens,'scope':'Exact reversible pre-language search on the full canonical 128x30000 hard block. The near-2epsilon learned Q/model/defect field is unchanged from PR551. Encoder screens a fixed public menu of reversible causal defect transforms (raw, temporal/spatial delta, 2-D Lorenzo, MED, Paeth, average) crossed with historical ZSM W=4/8/64 using only the first 4096 time samples. One byte charges the transform selector and one byte charges the ZSM window selector. Exactly one full transformed ZSM stream is materialized, independently decoded, inverse-transformed to the identical learned defect field, used to causally regenerate identical Q from the charged model, and hard-error validated. No ideal entropy or uncharged selector is counted.'}
    json.dump(out,open('imperial_near2eps_zsm_transform_search.json','w'),indent=2)
    print(json.dumps({'summary':{k:out[k] for k in ('selected_transform','selected_window','total_bytes','historical_ar32_zsm_bytes','gain_vs_historical_ar32_zsm','matched_sz3_bytes','gain_vs_sz3','maxerr')}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
