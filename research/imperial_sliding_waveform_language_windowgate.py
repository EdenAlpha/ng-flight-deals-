import os, sys, json
from collections import Counter
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import imperial_growing_waveform_language as g
import boto3, s3fs
from botocore import UNSIGNED
from botocore.config import Config

WINDOWS=(0,7500,15000,22500)
WLEN=1024
REGIONS=g.REGIONS
HIST=g.HIST
POLS=g.POLS
N=g.N

def target_blocks(d,c0,quantized=True):
    out=[]
    for t0 in WINDOWS:
        x=np.asarray(d[t0:t0+WLEN,c0:c0+1],np.float64)
        if quantized:x=g.qarr(x)
        out.append(g.blocks(x))
    return np.concatenate(out,axis=0)

def prior_samples_and_sliding(d,c0):
    samples=[]; phrases=[]
    for t0 in WINDOWS:
        q=g.qarr(np.asarray(d[t0:t0+WLEN,c0:c0+1],np.float64))[:,0]
        samples.append(q)
        # Every possible N-sample prior phrase is a decoder-known content token.
        phrases.append(np.lib.stride_tricks.sliding_window_view(q,N).copy())
    return np.concatenate(samples),np.concatenate(phrases,axis=0)

def main():
    s3=boto3.client('s3',config=Config(signature_version=UNSIGNED));objs=[]
    for pg in s3.get_paginator('list_objects_v2').paginate(Bucket=g.BUCKET,Prefix=g.PREFIX):
        objs.extend(o['Key'] for o in pg.get('Contents',[]) if o['Key'].endswith('.h5'))
    objs.sort();ti=objs.index(g.TARGET)
    if ti<max(HIST):raise RuntimeError(('not enough history',ti))
    history=objs[ti-max(HIST):ti]
    fs=s3fs.S3FileSystem(anon=True,default_fill_cache=False)

    rf,hf=g.open_h5(fs,g.TARGET)
    try:
        d=hf['Acoustic']
        tar=np.concatenate([target_blocks(d,c0,True) for c0 in REGIONS],axis=0)
        src=np.concatenate([target_blocks(d,c0,False) for c0 in REGIONS],axis=0)
    finally:
        hf.close();rf.close()
    centers=(tar.astype(np.float64)+0.5)*g.STEP-g.PHASE
    maxerr=float(np.max(np.abs(src-centers)))
    if maxerr>g.EPS*(1+5e-6):raise RuntimeError(('hard error',maxerr,g.EPS))

    shape_counts={p:Counter() for p in POLS};shape_total=0
    scalar_counts=np.zeros(g.QBINS,np.int64);scalar_total=0
    anchor_counts=np.zeros(g.QBINS,np.int64);anchor_total=0
    rows=[]
    # Nearest prior records first: checkpoints are exact 2/8/32/128-record suffixes.
    for hidx,key in enumerate(reversed(history),1):
        rf,hf=g.open_h5(fs,key)
        try:
            d=hf['Acoustic']
            for c0 in REGIONS:
                q,B=prior_samples_and_sliding(d,c0)
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
                r=g.eval_target(shape_counts[pol],shape_total,anchor_counts,anchor_total,
                                scalar_counts,scalar_total,tar,pol)
                r.update({'history_records':hidx,'polarity_canonical':pol,
                          'prior_phrase_alignment':'all_sliding_offsets',
                          'target_phrase_alignment':'fixed_nonoverlap',
                          'gain_vs_fullfile_sz3_ideal':g.FULL_SZ3_BPS/r['bps'],
                          'ratio_to_2x_target':r['bps']/g.TARGET_BPS})
                rows.append(r)
            print(json.dumps({'history':hidx,'rows':rows[-2:]},indent=2),flush=True)
    out={'target':g.TARGET,'windows':list(WINDOWS),'window_length':WLEN,
         'regions':list(REGIONS),'channels_total':len(REGIONS),'phrase_length':N,
         'history_checkpoints':list(HIST),'prior_phrase_alignment':'every_sample_offset',
         'target_phrase_alignment':'fixed_nonoverlap','std':g.STD,'eps':g.EPS,
         'step':g.STEP,'phase':g.PHASE,'maxerr':maxerr,
         'strict_2x_target_bps':g.TARGET_BPS,'fullfile_sz3_bps_reference':g.FULL_SZ3_BPS,
         'rows':rows,
         'scope':'Sliding-prior directional waveform-language gate. The target remains fixed nonoverlapping 16-sample phrases, but every possible 16-sample window from the decoder-history sample windows enters the content dictionary, removing arbitrary phrase-origin alignment. Four fixed 1024-sample windows and one channel per cable regime are used. History checkpoints are the immediately preceding 2/8/32/128 records. Target contributes no model counts; target hard-error lattice is verified. Ideal static arithmetic screen only and prior raw-history dictionary remains exploratory until rebuilt from decoder-reconstructable history.'}
    json.dump(out,open('imperial_sliding_waveform_language_windowgate.json','w'),indent=2)
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__':main()
