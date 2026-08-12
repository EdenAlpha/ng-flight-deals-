import json, math, sys
import h5py, numpy as np

FULL_SZ3_BPS=3.331839158950617
TARGET_BPS=FULL_SZ3_BPS/2
SAFETY=1-1e-5
ALPHA=.5
TRAIN_COUNTS=(32,256)
LENS=(4,8)
TARGET_REGIONS=(0,2304,4606,6880)
TARGET_NCH=2
QOFF=512; QK=1024


def stats(d):
    s=ss=0.0; n=0
    for i in range(0,d.shape[0],2048):
        x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64)
        s+=float(x.sum()); ss+=float((x*x).sum()); n+=x.size
    m=s/n
    return m,float(np.sqrt(max(0.0,ss/n-m*m)))


def nearest_q(x,eps):
    return np.rint(np.asarray(x,np.float64)/eps).astype(np.int16)


def legal_bounds(x,eps):
    b=eps*SAFETY; h=eps
    x=np.asarray(x,np.float64)
    lo=np.ceil((x-b)/h-1e-12).astype(np.int16)
    hi=np.floor((x+b)/h+1e-12).astype(np.int16)
    if np.any(lo>hi): raise RuntimeError('empty legal set')
    if int(np.max(hi.astype(np.int32)-lo.astype(np.int32)))>1:
        raise RuntimeError(('more than two legal states',int(np.max(hi.astype(np.int32)-lo.astype(np.int32)))))
    return lo,hi,h


def canonical_scale(P):
    P=np.asarray(P,np.int32)
    d=P-P[:,0:1]
    aa=np.abs(d)
    g=np.gcd.reduce(aa,axis=1)
    nz=aa!=0
    first=np.argmax(nz,axis=1)
    s=np.sign(d[np.arange(len(P)),first]).astype(np.int32)
    s[g==0]=1
    den=np.where(g==0,1,g)
    prim=(d//den[:,None])*s[:,None]
    gain=(g*s).astype(np.int16)
    return prim.astype(np.int16),gain,P[:,0].astype(np.int16)


def phrases(Q,N):
    T=(Q.shape[0]//N)*N
    return np.ascontiguousarray(Q[:T].T).reshape(-1,N)


def void_keys(P,N):
    return np.ascontiguousarray(P.astype('<i2')).view(np.dtype((np.void,2*N))).ravel()


def hist_cost(vals,offset=QOFF,K=QK):
    v=np.asarray(vals,np.int32).ravel()+offset
    if v.min()<0 or v.max()>=K: raise RuntimeError(('hist range',int(v.min()-offset),int(v.max()-offset)))
    cnt=np.bincount(v,minlength=K).astype(np.float64)
    den=cnt.sum()+ALPHA*K
    return -np.log2((cnt+ALPHA)/den),cnt


def build_model(Q0,Q1,N):
    P=np.concatenate([phrases(Q0,N),phrases(Q1,N)],axis=0)
    prim,gain,anchor=canonical_scale(P)
    keys=void_keys(prim,N)
    uniq,counts=np.unique(keys,return_counts=True)
    qcost,qcnt=hist_cost(np.concatenate([Q0.ravel(),Q1.ravel()]))
    gcost,gcnt=hist_cost(gain)
    acost,acnt=hist_cost(anchor)
    return {'N':N,'uniq':uniq,'counts':counts.astype(np.int64),'total_shapes':int(len(keys)),
            'qcost':qcost,'gcost':gcost,'acost':acost,'unique_shapes':int(len(uniq)),
            'shape_reuse':float(1-len(uniq)/len(keys)),'mean_shape_count':float(len(keys)/len(uniq))}


def lookup_counts(model,prim):
    keys=void_keys(prim,model['N']); u=model['uniq']; idx=np.searchsorted(u,keys)
    ok=idx<len(u)
    safe=np.minimum(idx,len(u)-1)
    ok &= (u[safe]==keys)
    out=np.zeros(len(keys),np.int64); out[ok]=model['counts'][safe[ok]]
    return out


def cost_from_table(tab,v):
    z=np.asarray(v,np.int32)+QOFF
    bad=(z<0)|(z>=QK)
    z=np.clip(z,0,QK-1)
    out=tab[z].astype(np.float64)
    out[bad]=50.0
    return out


def pattern_matrix(N):
    x=np.arange(1<<N,dtype=np.uint32)[:,None]
    b=((x>>np.arange(N,dtype=np.uint32))&1).astype(np.int16)
    return b


def score_target(X,eps,model):
    N=model['N']; lo,hi,h=legal_bounds(X,eps); T=(len(X)//N)*N
    lo=lo[:T].reshape(-1,N); hi=hi[:T].reshape(-1,N); pats=pattern_matrix(N)
    total=0.0; matched=0; chosen_match_bits=0.0; escape_bits_total=0.0; hardmax=0.0
    chosen=[]
    for a,b in zip(lo,hi):
        esc_per=np.minimum(cost_from_table(model['qcost'],a),cost_from_table(model['qcost'],b))
        esc=1.0+float(esc_per.sum()); escape_bits_total+=esc
        P=a[None,:]+pats*(b-a)[None,:]
        prim,gain,anchor=canonical_scale(P)
        cnt=lookup_counts(model,prim); valid=cnt>0
        best_bits=1e300; best_idx=-1
        if np.any(valid):
            shape=np.full(len(P),1e300,np.float64)
            shape[valid]=-np.log2(cnt[valid].astype(np.float64)/model['total_shapes'])
            bits=1.0+shape+cost_from_table(model['gcost'],gain)+cost_from_table(model['acost'],anchor)
            j=int(np.argmin(bits)); best_bits=float(bits[j]); best_idx=j
        if best_bits<esc:
            q=P[best_idx]; bits=best_bits; matched+=1; chosen_match_bits+=bits
        else:
            # Decoder-honest ideal scalar escape: independently choose the cheaper legal state.
            ca=cost_from_table(model['qcost'],a); cb=cost_from_table(model['qcost'],b)
            q=np.where(ca<=cb,a,b).astype(np.int16); bits=esc
        R=q.astype(np.float64)*h; src=X[len(chosen)*N:len(chosen)*N+N]
        me=float(np.max(np.abs(src-R))); hardmax=max(hardmax,me)
        if me>eps*(1+5e-6): raise RuntimeError(('hard error',me,eps))
        chosen.append(q); total+=bits
    n=T
    return {'samples':n,'phrases':len(lo),'ideal_bits':total,'ideal_bps':total/n,
            'match_fraction':matched/len(lo),'matched_phrases':matched,
            'mean_bits_per_matched_phrase':chosen_match_bits/max(1,matched),
            'escape_only_bps':escape_bits_total/n,'maxerr':hardmax}


def main(paths):
    fs=[h5py.File(p,'r') for p in paths]
    try:
        ds=[f['Acoustic'] for f in fs]
        if any(tuple(d.shape)!=(30000,6912) for d in ds): raise RuntimeError('shape drift')
        stds=[stats(d)[1] for d in ds]; eps=[.1*s for s in stds]
        maxch=256
        allch=np.linspace(0,6911,maxch,dtype=np.int32)
        Xprev=[np.asarray(d[:,allch],np.float64) for d in ds[:2]]
        Qprev=[nearest_q(x,e) for x,e in zip(Xprev,eps[:2])]
        target_channels=[]
        for c0 in TARGET_REGIONS:
            target_channels.extend(range(c0,min(c0+TARGET_NCH,6912)))
        Xt=np.asarray(ds[2][:,target_channels],np.float64)
        rows=[]; models=[]
        for M in TRAIN_COUNTS:
            # Nested, cable-spanning subsets: 32 = every 8th channel of the 256-channel grid.
            step=maxch//M; idx=np.arange(0,maxch,step,dtype=np.int32)[:M]
            q0=Qprev[0][:,idx]; q1=Qprev[1][:,idx]
            for N in LENS:
                model=build_model(q0,q1,N)
                meta={'train_channels':M,'phrase_len':N,'unique_shapes':model['unique_shapes'],
                      'training_phrases':model['total_shapes'],'shape_reuse':model['shape_reuse'],
                      'mean_shape_count':model['mean_shape_count']}
                models.append(meta)
                for j,c in enumerate(target_channels):
                    r=score_target(Xt[:,j],eps[2],model); r.update(meta); r['target_channel']=int(c); rows.append(r)
                    print(json.dumps({'model':meta,'channel':int(c),'score':r}),flush=True)
        combos=[]
        for M in TRAIN_COUNTS:
            for N in LENS:
                rr=[r for r in rows if r['train_channels']==M and r['phrase_len']==N]
                bits=sum(r['ideal_bits'] for r in rr); ns=sum(r['samples'] for r in rr); bps=bits/ns
                combos.append({'train_channels':M,'phrase_len':N,'ideal_bps':bps,
                               'gain_vs_verified_fullfile_sz3_bps':FULL_SZ3_BPS/bps,
                               'ratio_to_strict_2x_target':bps/TARGET_BPS,
                               'mean_match_fraction':float(np.mean([r['match_fraction'] for r in rr])),
                               'min_channel_match_fraction':min(r['match_fraction'] for r in rr),
                               'max_channel_match_fraction':max(r['match_fraction'] for r in rr),
                               'escape_only_bps':sum(r['escape_only_bps']*r['samples'] for r in rr)/ns,
                               'unique_shapes':rr[0]['unique_shapes'],'training_phrases':rr[0]['training_phrases'],
                               'shape_reuse':rr[0]['shape_reuse']})
        combos.sort(key=lambda x:x['ideal_bps'])
        out={'shape':[30000,6912],'stds':stds,'eps':eps,'training_channel_grid':allch.tolist(),
             'target_channels':target_channels,'train_counts':list(TRAIN_COUNTS),'phrase_lengths':list(LENS),
             'verified_fullfile_sz3_bps':FULL_SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,
             'combos':combos,'models':models,'rows':rows,
             'scope':'Sequential global seismic-shape language screen. Two already-decoded previous Imperial minutes define a dictionary pooled across fixed cable-spanning training channels. Each phrase is quotiented by absolute offset, integer amplitude scale (GCD of differences), and polarity, producing a primitive waveform symbol. For each target phrase, every legal h=epsilon reconstruction in its unchanged +/-10%-target-std box is enumerated exactly (<=2^N vectors) and the lowest-cost historical primitive shape+signed gain+anchor is selected. Escapes use decoder-known scalar probabilities from prior minutes. All probabilities are prior-only; target contributes no counts. Reported rate is ideal arithmetic codelength, not yet a byte container. Every chosen target reconstruction is explicitly hard-error verified. No AI.'}
        print(json.dumps({'combos':combos},indent=2),flush=True); json.dump(out,open('imperial_global_scale_quotient_language.json','w'),indent=2)
    finally:
        for f in fs:f.close()

if __name__=='__main__': main(sys.argv[1:])
