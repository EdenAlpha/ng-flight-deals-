import json, math, sys
import h5py
import numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_decoder_phase_automaton as m

C=128; NT=30000; C0=512; CURRENT_BYTES=2468803; MATCHED_SZ3=2767977


def h0(a):
    a=np.asarray(a).reshape(-1); _,cnt=np.unique(a,return_counts=True)
    p=cnt.astype(np.float64)/cnt.sum(); return float(-(p*np.log2(p)).sum())


def tile_entropy(K,cg,tb):
    bits=0.0; hs=[]
    for c0 in range(0,C,cg):
        for t0 in range(0,NT,tb):
            a=K[c0:min(C,c0+cg),t0:min(NT,t0+tb)]
            hh=h0(a); bits+=hh*a.size; hs.append(hh)
    return {'channel_group':cg,'time_block':tb,'oracle_h0_bps':bits/K.size,
            'min_tile_h0':float(np.min(hs)),'median_tile_h0':float(np.median(hs)),
            'max_tile_h0':float(np.max(hs)),'tiles':len(hs)}


def binary_mi(a,b):
    a=np.asarray(a,dtype=np.uint8).reshape(-1); b=np.asarray(b,dtype=np.uint8).reshape(-1)
    n=len(a); joint=np.bincount((a<<1)|b,minlength=4).astype(np.float64).reshape(2,2)/n
    pa=joint.sum(1); pb=joint.sum(0); mi=0.0
    for i in range(2):
        for j in range(2):
            p=joint[i,j]
            if p>0: mi+=p*math.log2(p/(pa[i]*pb[j]))
    return float(mi)


def corr(a,b):
    a=np.asarray(a,dtype=np.float64).reshape(-1); b=np.asarray(b,dtype=np.float64).reshape(-1)
    a-=a.mean(); b-=b.mean(); den=math.sqrt(float(a@a)*float(b@b))
    return float((a@b)/den) if den else 0.0


def spectral_flatness(K,axis):
    A=K.astype(np.float64); A-=A.mean(axis=axis,keepdims=True)
    F=np.fft.rfft(A,axis=axis) if axis==1 else np.fft.fft(A,axis=axis)
    P=np.abs(F)**2; P=np.mean(P,axis=1-axis); P=np.maximum(P,1e-18)
    return float(np.exp(np.mean(np.log(P)))/np.mean(P))


def main(path):
    with h5py.File(path,'r') as hf:
        d=hf['Acoustic']; _,std=m.stats(d); eps=.1*std; X=np.asarray(d[:,C0:C0+C],np.float64).T
    _,co=ah.fits(X); R,K=ah.run_ar(X,co)
    me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+5e-6): raise RuntimeError(('hard',me,eps))
    global_h=h0(K)
    configs=[(128,30000),(128,4096),(128,1024),(128,256),(64,30000),(32,30000),(16,30000),(4,30000),(1,30000),(32,4096),(16,2048),(8,1024),(4,512),(1,256)]
    tiles=[]
    for cg,tb in configs:
        r=tile_entropy(K,cg,tb); r['gain_vs_global_h0_bps']=global_h-r['oracle_h0_bps']; tiles.append(r); print(json.dumps({'tile':r}),flush=True)
    Z=(K==0)
    temporal=[]
    for lag in (1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192):
        if lag>=NT: continue
        r={'lag':lag,'zero_mi_bits':binary_mi(Z[:,lag:],Z[:,:-lag]),'k_corr':corr(K[:,lag:],K[:,:-lag])}
        temporal.append(r); print(json.dumps({'temporal':r}),flush=True)
    spatial=[]
    for off in (1,2,4,8,16,32,64):
        r={'offset':off,'zero_mi_bits':binary_mi(Z[off:],Z[:-off]),'k_corr':corr(K[off:],K[:-off])}
        spatial.append(r); print(json.dumps({'spatial':r}),flush=True)
    ridge=[]
    for off in (1,2,4,8,16,32):
        for lag in (0,1,2,4,8,16,32,64):
            if lag==0:
                a=Z[off:,:]; b=Z[:-off,:]; ka=K[off:,:]; kb=K[:-off,:]
            else:
                a=Z[off:,lag:]; b=Z[:-off,:-lag]; ka=K[off:,lag:]; kb=K[:-off,:-lag]
            r={'offset':off,'lag':lag,'zero_mi_bits':binary_mi(a,b),'k_corr':corr(ka,kb)}; ridge.append(r)
    ridge_sorted=sorted(ridge,key=lambda r:r['zero_mi_bits'],reverse=True)
    out={'meta':{'shape':[C,NT],'samples':K.size,'eps':eps,'maxerr':me,'current_bps':8*CURRENT_BYTES/K.size,'target_2x_bps':8*(MATCHED_SZ3/2)/K.size},
         'global_k_h0_bps':global_h,'tile_oracle_entropy':tiles,'temporal_dependence':temporal,'spatial_dependence':spatial,
         'spacetime_ridge_top20':ridge_sorted[:20],
         'spectral_flatness':{'temporal':spectral_flatness(K,1),'spatial':spectral_flatness(K,0)},
         'summary':{'best_tile_oracle':min(tiles,key=lambda r:r['oracle_h0_bps']),
                    'strongest_temporal_zero_mi':max(temporal,key=lambda r:r['zero_mi_bits']),
                    'strongest_spatial_zero_mi':max(spatial,key=lambda r:r['zero_mi_bits']),
                    'strongest_spacetime_zero_mi':ridge_sorted[0]},
         'note':'Tile entropies are encoder-side oracle order-0 entropies with distribution-table cost deliberately omitted; their gain vs global H0 is therefore an upper diagnostic on simple nonstationarity, not an achievable codec gain. MI/correlation measures dependence left in the exact audited AR32 K field.'}
    json.dump(out,open('imperial_innovation_dependency_atlas.json','w'),indent=2)
    print(json.dumps({'summary':out['summary'],'spectral_flatness':out['spectral_flatness']},indent=2),flush=True)
if __name__=='__main__': main(sys.argv[1])
