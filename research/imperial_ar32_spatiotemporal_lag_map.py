import json,sys,math
import h5py,numpy as np
from scipy.signal import fftconvolve
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267
MAX_DC=64;MAX_DT=128


def fit_shared_ar(X):
    rows=[];ys=[]
    for c in range(X.shape[0]):
        x=np.asarray(X[c,:TRAIN],np.float64)
        for t in range(P,TRAIN):
            rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
    return np.linalg.lstsq(np.asarray(rows,np.float64),np.asarray(ys,np.float64),rcond=None)[0].astype(np.float32)


def run_ar(X,coef):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
    for c in range(X.shape[0]):
        for t in range(X.shape[1]):
            p=0 if t<P else int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
            k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
    return R,K


def zig(a):
    a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)


def rect(pref,c0,c1,t0,t1):
    return int(pref[c1,t1]-pref[c0,t1]-pref[c1,t0]+pref[c0,t0])


def binary_mi(n00,n01,n10,n11):
    n=float(n00+n01+n10+n11)
    if n<=0:return 0.0
    ns=np.asarray([[n00,n01],[n10,n11]],np.float64)
    p=ns/n;pa=p.sum(axis=1);pb=p.sum(axis=0);z=0.0
    for i in range(2):
        for j in range(2):
            if p[i,j]>0:z+=p[i,j]*math.log2(p[i,j]/(pa[i]*pb[j]))
    return float(z)


def feature_lag_map(B):
    B=np.asarray(B,np.uint8);c,t=B.shape
    # linear 2-D autocorrelation. For an autocorrelation the +/- lag pair is symmetric.
    corr=np.rint(fftconvolve(B.astype(np.float32),B[::-1,::-1].astype(np.float32),mode='full')).astype(np.int64)
    pref=np.pad(B.astype(np.int64).cumsum(0).cumsum(1),((1,0),(1,0)))
    out=[]
    for dc in range(0,min(MAX_DC,c-1)+1):
        for dt in range(-MAX_DT,MAX_DT+1):
            if dc==0 and dt<=0:continue
            if dt>=0:
                at0,at1=0,t-dt;bt0,bt1=dt,t
            else:
                at0,at1=-dt,t;bt0,bt1=0,t+dt
            if at1<=at0:continue
            ca0,ca1=0,c-dc;cb0,cb1=dc,c
            n=(c-dc)*(at1-at0)
            n1a=rect(pref,ca0,ca1,at0,at1);n1b=rect(pref,cb0,cb1,bt0,bt1)
            n11=int(corr[c-1+dc,t-1+dt])
            # roundoff guard for FFT correlation
            n11=max(0,min(n11,n1a,n1b));n10=n1a-n11;n01=n1b-n11;n00=n-n11-n10-n01
            mi=binary_mi(n00,n01,n10,n11)
            out.append({'dc':dc,'dt':dt,'mi_bps':mi,'pairs':int(n),'p11':n11/n})
    return out


def direct_check(B,dc,dt,corrval):
    if dt>=0:a=B[:B.shape[0]-dc,:B.shape[1]-dt];b=B[dc:,dt:]
    else:a=B[:B.shape[0]-dc,-dt:];b=B[dc:,:B.shape[1]+dt]
    return int(np.sum(a.astype(np.int64)*b.astype(np.int64)))==int(corrval)


def main(path):
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
        for name,c0 in SPECS:
            X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K=run_ar(X,coef)
            me=float(np.max(np.abs(X-R.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((name,'hard',me,eps))
            H=K[:,TRAIN:];u=zig(H)
            feats={
                'zero':(H==0),
                'positive':(H>0),
                'abs_ge2':(np.abs(H)>=2),
                'abs_ge4':(np.abs(H)>=4),
                'zig_bit0':((u&1)!=0),
                'zig_bit1':(((u>>1)&1)!=0),
                'zig_bit2':(((u>>2)&1)!=0),
            }
            feature_rows={}
            aggregate={}
            for fn,B in feats.items():
                rr=feature_lag_map(B)
                # Validate FFT indexing on representative axis/off-axis shifts.
                for dc,dt in ((0,1),(1,0),(1,1),(2,-3),(16,7)):
                    q=next(x for x in rr if x['dc']==dc and x['dt']==dt)
                    if dt>=0:a=B[:B.shape[0]-dc,:B.shape[1]-dt];bb=B[dc:,dt:]
                    else:a=B[:B.shape[0]-dc,-dt:];bb=B[dc:,:B.shape[1]+dt]
                    n11=int(np.sum(a.astype(np.int64)*bb.astype(np.int64)))
                    if abs(q['p11']*q['pairs']-n11)>.5:raise RuntimeError(('fft lag mismatch',fn,dc,dt,q,n11))
                axis={(x['dc'],x['dt']):x['mi_bps'] for x in rr if x['dc']==0 or x['dt']==0}
                off=[x for x in rr if x['dc']>0 and x['dt']!=0]
                for x in off:
                    sx=axis.get((x['dc'],0),0.0);tx=axis.get((0,abs(x['dt'])),0.0)
                    x['axis_max_mi']=max(sx,tx);x['excess_over_axis']=x['mi_bps']-x['axis_max_mi']
                top=sorted(rr,key=lambda x:x['mi_bps'],reverse=True)[:30]
                topoff=sorted(off,key=lambda x:x['mi_bps'],reverse=True)[:30]
                topex=sorted(off,key=lambda x:x['excess_over_axis'],reverse=True)[:30]
                feature_rows[fn]={'top30_all':top,'top30_offaxis':topoff,'top30_excess':topex,
                                  'best_axis_temporal':max((x for x in rr if x['dc']==0),key=lambda x:x['mi_bps']),
                                  'best_axis_spatial':max((x for x in rr if x['dt']==0),key=lambda x:x['mi_bps']),
                                  'best_offaxis':topoff[0],'best_excess':topex[0]}
                for x in off:
                    key=(x['dc'],x['dt']);aggregate.setdefault(key,[]).append(x['mi_bps'])
            consensus=[]
            for (dc,dt),vals in aggregate.items():
                consensus.append({'dc':dc,'dt':dt,'sum_mi_bps':float(sum(vals)),'mean_mi_bps':float(np.mean(vals)),'max_feature_mi_bps':float(max(vals))})
            consensus.sort(key=lambda x:x['sum_mi_bps'],reverse=True)
            row={'region':name,'c0':c0,'samples':int(H.size),'feature_results':feature_rows,'consensus_top50_offaxis':consensus[:50],'maxerr':me}
            rows.append(row);print(json.dumps({'region':name,'top_consensus':consensus[:10],
                'feature_best_offaxis':{k:v['best_offaxis'] for k,v in feature_rows.items()},
                'feature_best_excess':{k:v['best_excess'] for k,v in feature_rows.items()}},indent=2),flush=True)
    out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'heldout':[TRAIN,NT],'max_dc':MAX_DC,'max_abs_dt':MAX_DT,'rows':rows,
         'scope':'Exhaustive slanted-spacetime dependency audit on the current decoder-real shared AR32 + step267 innovation field. PR #376 searched spatial lags at zero time offset and PR #383 searched temporal lags at zero channel offset; this branch searches their missing cross-product: channel offsets 1..64 and time offsets -128..128 on hard/easy/medium/far held-out innovations. Seven nonlinear binary views of exact K are analyzed with linear 2-D FFT autocorrelation and exact overlap marginals, with direct-slice checks validating representative shifts. Off-axis mutual information is ranked both absolutely and by excess over the stronger corresponding pure-spatial/pure-temporal axis lag. A sharp excess ridge would indicate propagating/slanted dependence invisible to the separate axis audits and justify a reversible characteristic/context codec. This is a diagnostic, not a compression claim. No AI. Draft/do not merge.'}
    json.dump(out,open('imperial_ar32_spatiotemporal_lag_map.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
