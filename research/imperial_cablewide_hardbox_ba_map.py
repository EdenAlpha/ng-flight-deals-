import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r
import imperial_persistent_ar32_full_array_jit as a

C=128;NT=8192;TB=1024;P=32;STEP=267;NCB=54;NPARTS=3
m.STEP=STEP;a.m.m.STEP=STEP


def hard_ba(values,rad,maxiter=300,tol=1e-10):
    v=np.asarray(values,np.int64).ravel();xmin=int(v.min());xmax=int(v.max())
    ylo=xmin-rad;yhi=xmax+rad;n=yhi-ylo+1
    cnt=np.bincount((v-xmin).astype(np.int64),minlength=xmax-xmin+1).astype(np.float64)
    p=cnt/cnt.sum();xidx=np.arange(rad,rad+len(p),dtype=np.int64)
    q=np.full(n,1.0/n,np.float64);prev=None;delta=None
    yy=np.arange(n,dtype=np.int64)
    lo=np.maximum(yy-rad,0);hi=np.minimum(yy+rad+1,n)
    for it in range(maxiter):
        cs=np.empty(n+1,np.float64);cs[0]=0.0;np.cumsum(q,out=cs[1:])
        Z=cs[xidx+rad+1]-cs[xidx-rad]
        if np.any((p>0)&(Z<=0)):raise RuntimeError('zero legal mass')
        rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])))
        w=np.zeros(n,np.float64);w[xidx]=np.divide(p,Z,out=np.zeros_like(p),where=Z>0)
        ws=np.empty(n+1,np.float64);ws[0]=0.0;np.cumsum(w,out=ws[1:])
        qn=q*(ws[hi]-ws[lo]);sm=float(qn.sum())
        if not np.isfinite(sm) or sm<=0:raise RuntimeError('BA normalization')
        qn/=sm
        delta=None if prev is None else abs(rate-prev)
        q=qn
        if delta is not None and delta<tol:break
        prev=rate
    cs=np.r_[0.0,np.cumsum(q)];Z=cs[xidx+rad+1]-cs[xidx-rad]
    rate=float(-np.sum(p[p>0]*np.log2(Z[p>0])))
    keep=q>max(1e-15,q.max()*1e-12)
    return {'rate_bps':rate,'iterations':it+1,'last_rate_delta':delta,
            'residual_min':xmin,'residual_max':xmax,'reproduction_span':[ylo,yhi],
            'support_size':int(np.count_nonzero(keep)),'q_entropy_bps':float(-np.sum(q[q>0]*np.log2(q[q>0])))}


def main(path,part):
    part=int(part);per=(NCB+NPARTS-1)//NPARTS;lo_cb=part*per;hi_cb=min(NCB,(part+1)*per)
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rad=int(math.floor(eps));rows=[]
        for cb in range(lo_cb,hi_cb):
            c0=cb*C;X=np.asarray(d[:NT,c0:c0+C],np.float64).T
            co=r.fit_shared(X[:,:TB],P);mb,cd=r.model_frame(co)
            R,K=a.build(X,cd)
            E=np.rint(X-R.astype(np.float64)+STEP*K.astype(np.float64)).astype(np.int32)
            ba=hard_ba(E,rad)
            sz=0
            for t0 in range(0,NT,TB):b,_=m.szrun(X[:,t0:t0+TB],eps);sz+=int(b)
            n=int(X.size);target_bps=4*sz/n
            row={'cb':cb,'c0':c0,'samples':n,'model_bytes':int(mb),'eps':eps,'integer_radius':rad,
                 'local_std':float(X.std()),'eps_over_local_std':float(eps/X.std()),
                 'ar32_residual_std':float(E.std()),'ar32_k_std':float(K.std()),'ar32_k_zero_fraction':float(np.mean(K==0)),
                 'hardbox_ba':ba,'matched_sz3_bytes':int(sz),'matched_sz3_bps':float(8*sz/n),
                 'two_x_sz3_target_bps':float(target_bps),'ba_over_2x_target':float(ba['rate_bps']/target_bps)}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
    nsum=sum(x['samples'] for x in rows);ba_bits=sum(x['hardbox_ba']['rate_bps']*x['samples'] for x in rows);szsum=sum(x['matched_sz3_bytes'] for x in rows)
    summary={'samples':int(nsum),'ba_model_bytes':float(ba_bits/8),'ba_model_bps':float(ba_bits/nsum),
             'matched_sz3_bytes':int(szsum),'matched_sz3_bps':float(8*szsum/nsum),
             'two_x_target_bytes':float(szsum/2),'two_x_target_bps':float(4*szsum/nsum),
             'ba_over_2x_target':float((ba_bits/8)/(szsum/2)),
             'blocks_below_2x_target':int(sum(x['ba_over_2x_target']<1 for x in rows))}
    out={'part':part,'block_range':[lo_cb,hi_cb],'global_std':std,'eps':eps,'integer_radius':rad,'analysis_nt':NT,
         'rows':rows,'part_summary':summary,
         'scope':('Cable-wide hard-error information diagnostic, not a compression claim and not a rigorous process-level lower bound. Each fixed 128-channel block fits the current shared AR32 model only on its first 1024 samples and replays the verified recursive step267 state through the first 8192 samples. The exact integer source residual E=X-P is recovered from that decoder-real trajectory. A target-adaptive zero-distortion Blahut-Arimoto iteration then minimizes memoryless mutual information under the exact integer relation |E-Y|<=floor(global 10%-std epsilon). This is the hard-box-optimal marginal reproduction law for the empirical residual distribution, but it deliberately ignores remaining temporal/spatial dependence and does not charge transmission of the reproduction law. Matched SZ3 is rerun on the identical eight 128x1024 tiles. Three workers cover all 54 cable blocks. No AI.')}
    print(json.dumps({'part_summary':summary},indent=2),flush=True)
    json.dump(out,open(f'imperial_cablewide_hardbox_ba_{part}.json','w'),indent=2)

if __name__=='__main__':main(sys.argv[1],sys.argv[2])
