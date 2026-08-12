import json,sys,math
import h5py
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

NS=(4,8,16,32,64)
NCH=32
PHASES=64
BASE=np.uint64(11400714819323198485)

def stats(d):
    s=ss=0.0;n=0
    for t0 in range(0,d.shape[0],2048):
        x=np.asarray(d[t0:min(d.shape[0],t0+2048)],dtype=np.float64)
        s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
    mu=s/n;return mu,math.sqrt(max(0.0,ss/n-mu*mu))

def H(a):
    _,c=np.unique(a,return_counts=True);p=c.astype(np.float64)/c.sum();return float(-(p*np.log2(p)).sum())

def choose_phase(d,eps):
    step=2*eps
    tt=np.linspace(0,d.shape[0]-1,1024,dtype=np.int32)
    cc=np.linspace(0,d.shape[1]-1,256,dtype=np.int32)
    # h5py allows one fancy axis at a time, so materialize the selected rows first.
    rows=np.asarray(d[tt,:],dtype=np.float64)
    x=rows[:,cc].ravel()
    best=None
    for k in range(PHASES):
        ph=step*k/PHASES;q=np.floor((x+ph)/step).astype(np.int32);h=H(q)
        if best is None or h<best[0]:best=(h,ph,k)
    return best

def quant_col(d,c,step,phase):
    x=np.asarray(d[:,c],dtype=np.float64);return np.floor((x+phase)/step).astype(np.int32)

def hash_windows(a,n):
    a=np.asarray(a,dtype=np.int64)
    if len(a)<n:return np.empty(0,np.uint64)
    w=sliding_window_view(a,n);vals=(w.astype(np.int64)+2147483648).astype(np.uint64)
    pw=np.empty(n,np.uint64);pw[-1]=np.uint64(1)
    for i in range(n-2,-1,-1):pw[i]=pw[i+1]*BASE
    return np.sum(vals*pw,axis=1,dtype=np.uint64)

def phrase_hashes(q,n,shape=False,polarity=False):
    if shape:
        a=np.diff(q).astype(np.int32);h=hash_windows(a,n-1)
        if polarity:h=np.minimum(h,hash_windows(-a,n-1))
        return h
    return hash_windows(q,n)

def main(paths):
    fs=[h5py.File(p,'r') for p in paths]
    try:
        ds=[f['Acoustic'] for f in fs]
        if any(tuple(d.shape)!=(30000,6912) for d in ds):raise RuntimeError('shape drift')
        mu,std=stats(ds[-1]);eps=.1*std;step=2*eps;h0,phase,pidx=choose_phase(ds[-1],eps)
        channels=np.linspace(0,ds[-1].shape[1]-1,NCH,dtype=np.int32)
        Q=[[quant_col(d,int(c),step,phase) for c in channels] for d in ds]
        target_scalar_H=float(np.mean([H(q) for q in Q[-1]]));rows=[]
        for n in NS:
            for shape,pol in [(False,False),(True,False),(True,True)]:
                mode='exact' if not shape else ('shape_offset_polarity' if pol else 'shape_offset')
                # Compute each stream fingerprint once for this mode/length.
                HH=[[phrase_hashes(q,n,shape,pol) for q in qq] for qq in Q]
                pool=np.unique(np.concatenate([h for fi in range(len(HH)-1) for h in HH[fi]]))
                same_num=same_den=cross_num=cross_den=0
                for ci,ht in enumerate(HH[-1]):
                    idx=np.arange(0,len(ht),n,dtype=np.int32);hs=ht[idx]
                    same=np.unique(np.concatenate([HH[fi][ci] for fi in range(len(HH)-1)]))
                    same_num+=int(np.isin(hs,same,assume_unique=False).sum());same_den+=len(hs)
                    cross_num+=int(np.isin(hs,pool,assume_unique=False).sum());cross_den+=len(hs)
                sf=same_num/same_den;cf=cross_num/cross_den
                ref_positions=(len(Q)-1)*NCH*30000
                refbits=math.ceil(math.log2(ref_positions))+1+(10 if shape else 0)+(1 if pol else 0)
                unmatched=target_scalar_H*n;optimistic=(cf*refbits+(1-cf)*unmatched)/n
                rows.append({'n':n,'mode':mode,'same_channel_match_fraction':sf,'cross_channel_corpus_match_fraction':cf,'reference_bits_per_match':refbits,'optimistic_phrase_bps_if_unmatched_scalar':optimistic,'dictionary_unique_hashes':int(pool.size)})
        rows.sort(key=lambda r:r['optimistic_phrase_bps_if_unmatched_scalar'])
        out={'files':len(paths),'shape':list(ds[-1].shape),'channels_tested':NCH,'global_std_target':std,'eps':eps,'step':step,'chosen_phase':phase,'phase_index':pidx,'sample_phase_H0':h0,'mean_selected_channel_H0':target_scalar_H,'two_x_sz3_target_bps':1.8859028760018859,'best_phrase_modes':rows[:30],'all_rows':rows,'interpretation':'Exact mode reuses an identical hard-error quantized phrase. shape_offset reuses an identical delta waveform at a different integer baseline; polarity additionally canonicalizes sign inversion. This is a recurrence/codebook diagnostic, not yet a compressed container.'}
        print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_corpus_self_dictionary.json','w'),indent=2)
    finally:
        for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
