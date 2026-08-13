import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_ar32_innovation_gaussian_rd as g

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;L=8;COVER_BLOCKS=256
MARGINS=(0.25,0.5,1.0)


def hard_ba(values,rad,maxiter=600,tol=1e-11):
    v=np.asarray(values,np.int64).ravel()
    xmin=int(v.min());xmax=int(v.max())
    ylo=xmin-rad;yhi=xmax+rad;n=yhi-ylo+1
    # Exact empirical source histogram on every integer residual value.
    cnt=np.bincount((v-xmin).astype(np.int64),minlength=xmax-xmin+1).astype(np.float64)
    p=cnt/cnt.sum();xidx=np.arange(rad,rad+len(p),dtype=np.int64)
    q=np.full(n,1.0/n,np.float64)
    prev=None
    for it in range(maxiter):
        cs=np.empty(n+1,np.float64);cs[0]=0.0;np.cumsum(q,out=cs[1:])
        Z=cs[xidx+rad+1]-cs[xidx-rad]
        if np.any((p>0)&(Z<=0)):raise RuntimeError('zero legal mass during BA')
        rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])))
        w=np.zeros(n,np.float64);w[xidx]=np.divide(p,Z,out=np.zeros_like(p),where=Z>0)
        ws=np.empty(n+1,np.float64);ws[0]=0.0;np.cumsum(w,out=ws[1:])
        lo=np.maximum(np.arange(n)-rad,0);hi=np.minimum(np.arange(n)+rad+1,n)
        s=ws[hi]-ws[lo]
        qn=q*s
        sm=float(qn.sum())
        if not np.isfinite(sm) or sm<=0:raise RuntimeError('BA normalization')
        qn/=sm
        if prev is not None and abs(rate-prev)<tol:
            q=qn;break
        q=qn;prev=rate
    # Recompute final legal mass and rate.
    cs=np.r_[0.0,np.cumsum(q)]
    Z=cs[xidx+rad+1]-cs[xidx-rad]
    rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])))
    yvals=np.arange(ylo,yhi+1,dtype=np.int32)
    keep=q>max(1e-15,q.max()*1e-12)
    return {'rate_bps':rate,'iterations':it+1,'xmin':xmin,'xmax':xmax,'ylo':ylo,'yhi':yhi,
            'support_size':int(np.count_nonzero(keep)),'q_entropy_bps':float(-np.sum(q[q>0]*np.log2(q[q>0]))),
            'max_q':float(q.max()),'min_positive_q':float(q[q>0].min())},yvals,q


def make_blocks(E):
    E=np.rint(np.asarray(E,np.float64)).astype(np.int32)
    bb=[]
    for c in range(E.shape[0]):
        z=E[c]
        n=(len(z)//L)*L
        if n:bb.append(z[:n].reshape(-1,L))
    return np.concatenate(bb,axis=0) if bb else np.empty((0,L),np.int32)


def cover_screen(blocks,yvals,q,rate,rad,seed):
    blocks=blocks[:COVER_BLOCKS]
    rng=np.random.default_rng(seed)
    out=[]
    for margin in MARGINS:
        requested=float(rate+margin)
        bits=int(math.ceil(requested*L))
        if bits>16:
            out.append({'margin_bps':margin,'requested_rate_bps':requested,'codebook_bits':bits,
                        'codebook_size':2**bits,'tested':False,'reason':'codebook exceeds 2^16 fast-gate cap'})
            continue
        M=1<<bits
        code=rng.choice(yvals,size=(M,L),replace=True,p=q).astype(np.int32)
        hits=0;first_ids=[];candidate_counts=[]
        # Exact static residual-box membership. This is a proposal/coverage gate, not yet recursive AR decoding.
        for b in blocks:
            ok=np.ones(M,dtype=bool)
            for j in range(L):
                ok &= np.abs(code[:,j].astype(np.int64)-int(b[j]))<=rad
                if not np.any(ok):break
            ids=np.flatnonzero(ok)
            candidate_counts.append(int(len(ids)))
            if len(ids):hits+=1;first_ids.append(int(ids[0]))
        out.append({'margin_bps':margin,'requested_rate_bps':requested,'actual_id_rate_bps':bits/L,
                    'codebook_bits':bits,'codebook_size':M,'tested':True,'blocks_tested':int(len(blocks)),
                    'hit_fraction':hits/max(1,len(blocks)),'hits':hits,
                    'median_legal_codewords':float(np.median(candidate_counts)) if candidate_counts else 0.0,
                    'max_legal_codewords':max(candidate_counts) if candidate_counts else 0,
                    'mean_first_hit_id':float(np.mean(first_ids)) if first_ids else None})
    return out


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rad=int(math.floor(eps));rows=[]
        for ri,(name,c0) in enumerate(SPECS):
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            coef=g.fit_shared_ar(X);R,K,E=g.run_ar(X,coef)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'AR hard',me,eps))
            held=np.rint(E[:,TRAIN:]).astype(np.int32)
            ba,yvals,q=hard_ba(held,rad)
            sz=0
            for t0 in range(TRAIN,NT,1024):b,_=m.szrun(X[:,t0:t0+1024],eps);sz+=int(b)
            ns=C*(NT-TRAIN);szbps=8*sz/ns;target=szbps/2
            blocks=make_blocks(held)
            screen=cover_screen(blocks,yvals,q,ba['rate_bps'],rad,0xBADC0DE+ri)
            row={'region':name,'c0':c0,'samples':ns,'eps':eps,'integer_radius':rad,
                 'source_residual_std':float(held.std()),'source_residual_min':int(held.min()),'source_residual_max':int(held.max()),
                 'hardbox_ba':ba,'matched_sz3_bps':szbps,'two_x_sz3_target_bps':target,
                 'ba_over_2x_target':ba['rate_bps']/target if target>0 else None,
                 'random_product_cover_L8':screen,'ar32_maxerr':me}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'integer_radius':rad,'block_length':L,'rows':rows,
         'scope':('Hard-error rate/coverage diagnostic, not yet a compression claim. The current decoder-real shared AR32 model is fit on t<1024 and replayed through t<8192. On held-out integer source residuals E=X-P, zero-distortion Blahut-Arimoto is solved directly for the relation |E-Y|<=floor(epsilon): p(y|x) may have support only on legally reconstructing residuals. The resulting target-adaptive reproduction law q(y) minimizes the memoryless mutual-information rate for that exact hard interval relation; this is not a process-level lower bound and q-model transmission is not yet charged. For L=8, a deterministic random product codebook drawn from q is then fast-gated on 256 nonoverlapping residual blocks at BA rate plus fixed margins, capped at 2^16 codewords. That coverage test is static in the incumbent residual coordinate and is not yet a recursive AR codec. Purpose: test whether previous random codebooks failed because they sampled source-like rather than hard-box-optimal reproduction distributions. No AI.')}
    json.dump(out,open('imperial_hardbox_ba_random_cover.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1])
