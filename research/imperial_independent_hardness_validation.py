import json,sys,os
import boto3,h5py,numpy as np
from botocore import UNSIGNED
from botocore.config import Config
import imperial_huber_ar32_coldstart_arithmetic_regions as a
import imperial_activity6_full_array as fa

CANON='imperialvalleydas/v1.0.0/DF__UTC_20201113_235932.602.h5'
PREFIX='imperialvalleydas/v1.0.0/'
SELECTED=(0,4,10,14,20,28,35,42,48,50,52,53)
SLOTS=3


def choose_independent(s3):
    keys=[]
    token=None
    while len(keys)<200:
        kw={'Bucket':'gdr-data-lake','Prefix':PREFIX,'MaxKeys':1000}
        if token:kw['ContinuationToken']=token
        z=s3.list_objects_v2(**kw)
        for o in z.get('Contents',[]):
            k=o['Key']
            if k.endswith('.h5') and k!=CANON: keys.append((k,int(o.get('Size',0))))
        if not z.get('IsTruncated'):break
        token=z.get('NextContinuationToken')
    if not keys:raise RuntimeError('no independent Imperial HDF5 key visible from public prefix listing')
    # Prefer a same-sized neighboring minute when available; otherwise first HDF5.
    same=[x for x in keys if x[1]==415030456]
    pool=same or keys
    pool=sorted(pool)
    # Prefer a lexicographically nearby record after the canonical timestamp.
    after=[x for x in pool if x[0]>CANON]
    chosen=(after or pool)[0]
    return chosen, pool[:20]


def predict_bps(X,eps):
    dt=np.diff(X,axis=1)
    med=float(np.median(np.std(dt,axis=1)))
    r=med/eps
    return med,float(0.84566559+0.84579218*np.log2(r))


def main(slot):
    slot=int(slot);assert 0<=slot<SLOTS
    s3=boto3.client('s3',config=Config(signature_version=UNSIGNED))
    (key,size),candidates=choose_independent(s3)
    path='independent_imperial.h5'
    s3.download_file('gdr-data-lake',key,path)
    if size and os.path.getsize(path)!=size:raise RuntimeError(('size',size,os.path.getsize(path)))
    fa.NT=30000;fa.C=128;a.NT=30000;a.C=128
    with h5py.File(path,'r') as f:
        d=f['Acoustic'];shape=tuple(d.shape)
        if shape!=(30000,6912):raise RuntimeError(('shape',shape,key))
        _,gstd=a.m.stats(d);eps=.1*gstd
        blocks=SELECTED[slot::SLOTS]
        rows=[]
        for cb in blocks:
            c0=128*cb;X=np.asarray(d[:,c0:c0+128],np.float64).T
            med,pred=predict_bps(X,eps)
            _,hu=a.fits(X);R,K=a.run_ar(X,hu)
            act,_,_,Kd=fa.arithmetic_activity6(K);Rd=a.decode_source(Kd,hu)
            if not np.array_equal(Kd,K) or not np.array_equal(Rd,R):raise RuntimeError((cb,'decode'))
            me=float(np.max(np.abs(X-Rd.astype(np.float64))))
            if me>eps*(1+1e-12):raise RuntimeError((cb,'hard',me,eps))
            actual=8*act/X.size
            row={'cb':cb,'c0':c0,'median_channel_dt_std':med,'dt_scale_over_eps':med/eps,
                 'frozen_predicted_activity6_bps':pred,'actual_activity6_bps':actual,
                 'prediction_error_bps':pred-actual,'abs_error_bps':abs(pred-actual),
                 'k_zero_fraction':float(np.mean(K==0)),'k_std':float(np.std(K)),'maxerr':me}
            rows.append(row);print(json.dumps(row),flush=True)
    out={'slot':slot,'record_key':key,'record_size':size,'shape':shape,'global_std':float(gstd),'eps':float(eps),
         'candidate_keys_preview':candidates,'blocks':list(blocks),'rows':rows,
         'mae_bps':float(np.mean([r['abs_error_bps'] for r in rows])),
         'scope':'Independent-minute validation of the frozen one-feature Imperial hardness formula from PR475. Formula coefficients are not refit. Twelve cable blocks spanning the canonical easy/hard range are partitioned across three CI slots. Actual full-30,000-sample activity6 rates are recomputed under the same exact hard-error codec. No AI. Draft/do not merge.'}
    json.dump(out,open(f'imperial_independent_hardness_validation_{slot}.json','w'),indent=2)
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','candidate_keys_preview')},indent=2),flush=True)

if __name__=='__main__':main(sys.argv[1])
