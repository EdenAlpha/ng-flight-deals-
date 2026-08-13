import json,sys,os,math
import boto3,h5py,numpy as np
from botocore import UNSIGNED
from botocore.config import Config
from scipy.spatial import cKDTree
import imperial_decoder_phase_automaton as m
import imperial_dyadic_shared_resonator as r

BUCKET='gdr-data-lake';PREFIX='imperialvalleydas/v1.0.0/';TARGET=PREFIX+'DF__UTC_20201113_235932.602.h5'
P=32;TRAIN=1024;L=8;STEP=267;H0=320;HC=512;T0=512;TC=128
TARGET_LOCAL=np.arange(0,TC,4,dtype=np.int64);HISTORY_WIDTHS=(128,256,512)

def download_pair():
    s=boto3.client('s3',config=Config(signature_version=UNSIGNED));objs=[]
    for pg in s.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=PREFIX):objs.extend(o['Key'] for o in pg.get('Contents',[]) if o['Key'].endswith('.h5'))
    objs.sort();i=objs.index(TARGET);prev=objs[i-1]
    s.download_file(BUCKET,TARGET,'target.h5');s.download_file(BUCKET,prev,'previous.h5')
    return prev

def reconstruct_block(X,eps):
    co=r.fit_shared(X[:,:TRAIN],P);R=np.zeros(X.shape,np.int64);K=np.zeros(X.shape,np.int32);E=np.zeros(X.shape,np.float32)
    for t in range(X.shape[1]):
        if t<P:pred=np.zeros(X.shape[0],np.int64)
        else:
            v=np.full(X.shape[0],float(co[-1]),np.float64)
            for j in range(P):v+=float(co[j])*R[:,t-1-j]
            pred=np.rint(v).astype(np.int64)
        e=X[:,t]-pred;kk=np.rint(e/STEP).astype(np.int64);rr=pred+STEP*kk
        if float(np.max(np.abs(X[:,t]-rr)))>eps*(1+1e-10):raise RuntimeError(('hard',t,float(np.max(np.abs(X[:,t]-rr)))))
        E[:,t]=e.astype(np.float32);K[:,t]=kk.astype(np.int32);R[:,t]=rr
    return co,R,K,E

def as_blocks(A,start=TRAIN):
    n=(A.shape[1]-start)//L;B=A[:,start:start+n*L].reshape(A.shape[0],n,L);return B.reshape(-1,L)

def pd(a):return {str(p):float(np.percentile(a,p)) for p in (10,25,50,75,90,95,99)}

def query(tree,H,eps):
    d,_=tree.query(H,k=1,p=np.inf,workers=1);ce=np.asarray(tree.query_ball_point(H,r=eps,p=np.inf,return_length=True),np.int64);c2=np.asarray(tree.query_ball_point(H,r=2*eps,p=np.inf,return_length=True),np.int64)
    return {'nearest_linf_percentiles':pd(d),'fraction_within_eps':float(np.mean(ce>0)),'fraction_within_2eps':float(np.mean(c2>0)),'mean_hits_within_eps':float(np.mean(ce)),'p90_hits_within_eps':float(np.percentile(ce,90))}

def main():
    prevkey=download_pair()
    with h5py.File('target.h5','r') as ft:
        dt=ft['Acoustic'];_,std=m.stats(dt);eps=.1*std;Xt=np.asarray(dt[:,T0:T0+TC],np.float64).T
    # Decoder-real current incumbent state and its source residual sequence.
    cot,Rt,Kt,Et=reconstruct_block(Xt,eps);Ht=as_blocks(Et[TARGET_LOCAL])
    # Previous minute: four 128-channel blocks, each with its own persistent AR32 model.
    dec_parts=[];src_parts=[];chan_parts=[]
    with h5py.File('previous.h5','r') as fp:
        dp=fp['Acoustic']
        for c0 in range(H0,H0+HC,128):
            X=np.asarray(dp[:,c0:c0+128],np.float64).T;co,R,K,E=reconstruct_block(X,eps)
            D=as_blocks((STEP*K).astype(np.float32));S=as_blocks(E);nper=(X.shape[1]-TRAIN)//L
            chans=np.repeat(np.arange(c0,c0+128,dtype=np.int32),nper)
            dec_parts.append(D);src_parts.append(S);chan_parts.append(chans)
    D=np.concatenate(dec_parts);S=np.concatenate(src_parts);CH=np.concatenate(chan_parts)
    # Query nested history widths centered on the target block.
    rows=[]
    centers={128:(T0,T0+128),256:(T0-64,T0+192),512:(H0,H0+HC)}
    for w in HISTORY_WIDTHS:
        lo,hi=centers[w];mask=(CH>=lo)&(CH<hi);Dc=D[mask];Sc=S[mask];td=cKDTree(Dc,compact_nodes=True,balanced_tree=True);ts=cKDTree(Sc,compact_nodes=True,balanced_tree=True)
        rd=query(td,Ht,eps);rs=query(ts,Ht,eps);bits=float(math.log2(len(Dc)));row={'history_channels':w,'history_channel_range':[lo,hi-1],'decoder_known_codewords':int(len(Dc)),'raw_location_index_bits':bits,'raw_location_index_bps':bits/L,'decoder_real_previous_reconstruction':rd,'oracle_previous_source_residual':rs};rows.append(row);print(json.dumps(row,indent=2),flush=True)
    A=Xt[TARGET_LOCAL,TRAIN:];szb,_=m.szrun(A,eps);szbps=8*szb/A.size;target=szbps/2
    out={'target_key':TARGET,'previous_key':prevkey,'global_std':std,'eps':eps,'ar_order':P,'step':STEP,'block_length':L,'target_channels':[int(T0+x) for x in TARGET_LOCAL],'target_samples':int(A.size),'matched_sz3_bytes':int(szb),'matched_sz3_bps':szbps,'two_x_target_bps':target,'rows':rows,'scope':'Previous-minute approximate residual-reference coverage gate, not yet a sequential codec. Both target and previous records use persistent shared AR32 per 128-channel block and legal step267 reconstruction. The decoder-real history codebook consists of every non-overlapping 8-sample innovation-residual vector STEP*K from the reconstructed immediately preceding minute; these vectors are available to a sequential decoder without transmitting a dictionary. Target query vectors are source residuals relative to the incumbent target decoder trajectory, so this first gate holds target state fixed. Exact Chebyshev queries report whether a previous decoded residual vector itself lies inside each target +/-epsilon residual box. A second oracle uses previous SOURCE residual vectors, which the decoder would not know, solely to quantify loss caused by prior bounded reconstruction. Nested 128/256/512-channel history windows expose codebook-size/coverage scaling; raw location-index bps is reported without claiming an entropy-coded implementation. If decoder-real coverage is material, the next branch must implement sequential state updates, location coding and escapes. No AI.'}
    print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_previous_minute_approx_residual_cover.json','w'),indent=2)
if __name__=='__main__':main()
