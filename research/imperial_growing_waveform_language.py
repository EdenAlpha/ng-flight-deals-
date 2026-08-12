import json, math, sys
from collections import Counter
import numpy as np, h5py, s3fs, boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET='gdr-data-lake'
PREFIX='imperialvalleydas/v1.0.0/'
TARGET=PREFIX+'DF__UTC_20201113_235932.602.h5'
HIST=(2,8,32,128)
REGIONS=(0,2304,4606,6880)
W=8
N=16
POLS=(False,True)
# Frozen from PR238 on the identical canonical target; avoids target-trained retuning here.
STD=1336.977803780576
EPS=.1*STD
STEP=2*EPS
PHASE=196.36861493027212
SAFETY=1-1e-5
QOFF=1024; QBINS=2048; ALPHA=.25
FULL_SZ3_BPS=3.331839158950617
TARGET_BPS=FULL_SZ3_BPS/2

def qarr(x):
    q=np.floor((np.asarray(x,np.float64)+PHASE)/STEP).astype(np.int16)
    if int(q.min())<-QOFF or int(q.max())>=QOFF: raise RuntimeError(('q range',int(q.min()),int(q.max())))
    return q

def blocks(q):
    m=q.shape[0]//N*N
    # q is time x channels; return every channel's non-overlapping phrases.
    return np.concatenate([q[:m,j].reshape(-1,N) for j in range(q.shape[1])],axis=0)

def canon(A,pol):
    A=np.asarray(A,np.int16); D=A.astype(np.int32)-A[:,0:1].astype(np.int32)
    flag=np.zeros(len(A),np.uint8)
    if pol:
        sg=np.ones(len(A),np.int32); und=np.ones(len(A),bool)
        for j in range(1,N):
            take=und&(D[:,j]!=0)
            sg[take]=np.where(D[take,j]<0,-1,1); und[take]=False
        flag=(sg<0).astype(np.uint8); D*=sg[:,None]
    if int(D.min())<-32768 or int(D.max())>32767: raise RuntimeError('shape int16 overflow')
    B=np.ascontiguousarray(D.astype('<i2'))
    keys=B.view(np.dtype((np.void,2*N))).ravel()
    return keys,flag

def upd_counter(counter,keys):
    u,c=np.unique(keys,return_counts=True)
    for k,n in zip(u,c): counter[k.tobytes()]+=int(n)

def scalar_bits(counts,total,vals):
    vals=np.asarray(vals,np.int32).ravel(); idx=vals+QOFF
    if np.any((idx<0)|(idx>=QBINS)): raise RuntimeError('scalar range')
    den=total+ALPHA*QBINS
    return -np.log2((counts[idx]+ALPHA)/den)

def eval_target(shape_counts,shape_total,anchor_counts,anchor_total,scalar_counts,scalar_total,T,pol):
    keys,flags=canon(T,pol); anchors=T[:,0].astype(np.int32)
    sb=0.; known=np.zeros(len(T),bool); shape_bits=np.zeros(len(T),np.float64)
    for i,k in enumerate(keys):
        n=shape_counts.get(k.tobytes(),0)
        if n:
            known[i]=True; shape_bits[i]=-math.log2(n/shape_total)
    ab=scalar_bits(anchor_counts,anchor_total,anchors)
    # Fully decoder-known escape model: pooled previous-history scalar distribution, not target entropy.
    literal=scalar_bits(scalar_counts,scalar_total,T).reshape(len(T),N).sum(axis=1)
    bits=np.empty(len(T),np.float64)
    bits[known]=1.0+shape_bits[known]+ab[known]+(1.0 if pol else 0.0)
    bits[~known]=1.0+literal[~known]
    known_payload=(shape_bits[known]+ab[known]+(1.0 if pol else 0.0))/N if np.any(known) else np.array([],np.float64)
    return {
        'bps':float(bits.sum()/(len(T)*N)),
        'seen_fraction':float(known.mean()),
        'known_phrase_bps':float(known_payload.mean()) if known_payload.size else None,
        'escape_phrase_bps':float(np.mean((1.0+literal[~known])/N)) if np.any(~known) else None,
        'shape_vocab':len(shape_counts),
        'shape_occurrences':shape_total,
    }

def open_h5(fs,key):
    f=fs.open(f'{BUCKET}/{key}','rb',block_size=8<<20,cache_type='readahead')
    return f,h5py.File(f,'r')

def read_regions(d):
    return [qarr(d[:,c0:c0+W]) for c0 in REGIONS]

def main():
    s3=boto3.client('s3',config=Config(signature_version=UNSIGNED)); rows=[]
    objs=[]
    for pg in s3.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=PREFIX):
        objs.extend(o['Key'] for o in pg.get('Contents',[]) if o['Key'].endswith('.h5'))
    objs.sort(); ti=objs.index(TARGET)
    if ti<max(HIST): raise RuntimeError(('not enough history',ti))
    history=objs[ti-max(HIST):ti]
    fs=s3fs.S3FileSystem(anon=True,default_fill_cache=False)
    # Target is read once; all later model statistics come only from prior records.
    rf,hf=open_h5(fs,TARGET)
    try:
        d=hf['Acoustic'];
        if tuple(d.shape)!=(30000,6912): raise RuntimeError(('target shape',d.shape))
        tar_blocks=np.concatenate([blocks(q) for q in read_regions(d)],axis=0)
    finally:
        hf.close(); rf.close()
    # Hard-error audit for the exact lattice represented by every phrase.
    centers=(tar_blocks.astype(np.float64)+0.5)*STEP-PHASE
    # Re-read corresponding source phrase values compactly for max-error audit.
    rf,hf=open_h5(fs,TARGET)
    try:
        src_blocks=np.concatenate([blocks(np.asarray(hf['Acoustic'][:,c0:c0+W],np.float64)) for c0 in REGIONS],axis=0)
    finally:
        hf.close(); rf.close()
    maxerr=float(np.max(np.abs(src_blocks-centers)))
    if maxerr>EPS*(1+5e-6): raise RuntimeError(('hard error',maxerr,EPS))

    shape_counts={p:Counter() for p in POLS}; shape_total=0
    scalar_counts=np.zeros(QBINS,np.int64); scalar_total=0
    anchor_counts=np.zeros(QBINS,np.int64); anchor_total=0
    # Process from oldest to newest so every checkpoint is a genuine prefix of decoder history.
    for hidx,key in enumerate(history,1):
        rf,hf=open_h5(fs,key)
        try:
            d=hf['Acoustic'];
            if tuple(d.shape)!=(30000,6912): raise RuntimeError(('history shape',key,d.shape))
            for q in read_regions(d):
                B=blocks(q)
                idx=q.astype(np.int32).ravel()+QOFF
                scalar_counts+=np.bincount(idx,minlength=QBINS); scalar_total+=idx.size
                a=B[:,0].astype(np.int32)+QOFF
                anchor_counts+=np.bincount(a,minlength=QBINS); anchor_total+=a.size
                for pol in POLS:
                    keys,_=canon(B,pol); upd_counter(shape_counts[pol],keys)
                shape_total+=len(B)
        finally:
            hf.close(); rf.close()
        if hidx in HIST:
            for pol in POLS:
                r=eval_target(shape_counts[pol],shape_total,anchor_counts,anchor_total,scalar_counts,scalar_total,tar_blocks,pol)
                r.update({'history_records':hidx,'polarity_canonical':pol,'gain_vs_fullfile_sz3_ideal':FULL_SZ3_BPS/r['bps'],'ratio_to_2x_target':r['bps']/TARGET_BPS})
                rows.append(r)
            print(json.dumps({'history':hidx,'rows':rows[-2:]},indent=2),flush=True)
    out={
        'target':TARGET,'history_max':max(HIST),'history_checkpoints':list(HIST),
        'regions':list(REGIONS),'channels_per_region':W,'channels_total':W*len(REGIONS),'phrase_length':N,
        'std':STD,'eps':EPS,'step':STEP,'phase':PHASE,'maxerr':maxerr,
        'fullfile_sz3_bps_reference':FULL_SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,
        'rows':rows,
        'scope':'Long-history sequential waveform-language rate audit. A fixed 16-sample translation-invariant phrase language is learned only from prior Imperial records, with history prefixes 2/8/32/128. Target contributes no model counts. Shape IDs are content IDs/frequencies, not location pointers; anchors and escapes use previous-history scalar probabilities. Target lattice reconstruction is explicitly hard-error checked. Rates are ideal static arithmetic codelengths, not yet a byte-container claim. Prior records are read as the decoder-known language state under this screen; a production sequential codec must reproduce the same dictionary state from its own decoded history.'
    }
    json.dump(out,open('imperial_growing_waveform_language.json','w'),indent=2)
    print(json.dumps(out,indent=2),flush=True)
if __name__=='__main__': main()
