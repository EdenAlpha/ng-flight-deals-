import os, sys, json
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import imperial_growing_waveform_language as g
import boto3, s3fs
from botocore import UNSIGNED
from botocore.config import Config

# Directional gate only: one channel in each precommitted cable regime and
# four fixed 1024-sample windows spread through every minute. All phrase,
# lattice, probability, target, and history definitions remain PR269's.
WINDOWS=(0,7500,15000,22500)
WLEN=1024
REGIONS=g.REGIONS
HIST=g.HIST
POLS=g.POLS

def phrase_blocks(d,c0,quantized=True):
    out=[]
    for t0 in WINDOWS:
        x=np.asarray(d[t0:t0+WLEN,c0:c0+1],np.float64)
        if quantized:x=g.qarr(x)
        out.append(g.blocks(x))
    return np.concatenate(out,axis=0)

def main():
    s3=boto3.client('s3',config=Config(signature_version=UNSIGNED))
    objs=[]
    for pg in s3.get_paginator('list_objects_v2').paginate(Bucket=g.BUCKET,Prefix=g.PREFIX):
        objs.extend(o['Key'] for o in pg.get('Contents',[]) if o['Key'].endswith('.h5'))
    objs.sort(); ti=objs.index(g.TARGET)
    if ti<max(HIST): raise RuntimeError(('not enough history',ti))
    history=objs[ti-max(HIST):ti]
    fs=s3fs.S3FileSystem(anon=True,default_fill_cache=False)

    rf,hf=g.open_h5(fs,g.TARGET)
    try:
        d=hf['Acoustic']
        tar=np.concatenate([phrase_blocks(d,c0,True) for c0 in REGIONS],axis=0)
        src=np.concatenate([phrase_blocks(d,c0,False) for c0 in REGIONS],axis=0)
    finally:
        hf.close();rf.close()
    centers=(tar.astype(np.float64)+0.5)*g.STEP-g.PHASE
    maxerr=float(np.max(np.abs(src-centers)))
    if maxerr>g.EPS*(1+5e-6):raise RuntimeError(('hard error',maxerr,g.EPS))

    shape_counts={p:Counter() for p in POLS}; shape_total=0
    scalar_counts=np.zeros(g.QBINS,np.int64);scalar_total=0
    anchor_counts=np.zeros(g.QBINS,np.int64);anchor_total=0
    rows=[]
    # Accumulate the nearest prior record first so 2/8/32/128 mean exact
    # nested suffixes immediately preceding the target, not increasingly old
    # prefixes of a 128-record window.
    for hidx,key in enumerate(reversed(history),1):
        rf,hf=g.open_h5(fs,key)
        try:
            d=hf['Acoustic']
            for c0 in REGIONS:
                B=phrase_blocks(d,c0,True)
                q=B.reshape(-1)
                idx=q.astype(np.int32)+g.QOFF
                scalar_counts+=np.bincount(idx,minlength=g.QBINS);scalar_total+=idx.size
                a=B[:,0].astype(np.int32)+g.QOFF
                anchor_counts+=np.bincount(a,minlength=g.QBINS);anchor_total+=a.size
                for pol in POLS:
                    keys,_=g.canon(B,pol);g.upd_counter(shape_counts[pol],keys)
                shape_total+=len(B)
        finally:
            hf.close();rf.close()
        if hidx in HIST:
            for pol in POLS:
                r=g.eval_target(shape_counts[pol],shape_total,anchor_counts,anchor_total,scalar_counts,scalar_total,tar,pol)
                r.update({'history_records':hidx,'polarity_canonical':pol,
                          'gain_vs_fullfile_sz3_ideal':g.FULL_SZ3_BPS/r['bps'],
                          'ratio_to_2x_target':r['bps']/g.TARGET_BPS})
                rows.append(r)
            print(json.dumps({'history':hidx,'rows':rows[-2:]},indent=2),flush=True)
    out={'target':g.TARGET,'windows':list(WINDOWS),'window_length':WLEN,
         'regions':list(REGIONS),'channels_total':len(REGIONS),'phrase_length':g.N,
         'history_checkpoints':list(HIST),'std':g.STD,'eps':g.EPS,'step':g.STEP,
         'phase':g.PHASE,'maxerr':maxerr,'strict_2x_target_bps':g.TARGET_BPS,
         'fullfile_sz3_bps_reference':g.FULL_SZ3_BPS,'rows':rows,
         'scope':'Distributed-window directional gate for PR269. One fixed channel per cable regime and four fixed 1024-sample windows per minute are used solely to measure the exact nearest-history 2/8/32/128-record phrase-recurrence/rate curve faster. The target contributes no model counts and the exact PR269 hard-error lattice is verified. Ideal static arithmetic screen only, not a whole-file codec claim.'}
    json.dump(out,open('imperial_growing_waveform_language_windowgate.json','w'),indent=2)
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
