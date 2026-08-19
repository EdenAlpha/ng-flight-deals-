#!/usr/bin/env python3
"""Measurement-only time/depth profile of the frozen unseen-Kahu 512 engine.

Compression behavior is unchanged. Every probability bit is charged exactly as
in the frozen 1.90236x control; this wrapper only accumulates the already-paid
main-model class bits by the modeled sample's absolute t coordinate. The purpose
is to locate the remaining Kahu gap before designing another probability model.
"""
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import numpy as np
import torch
import torch.nn.functional as F
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q

REFERENCE_GAIN=1.9023606738716896
CHUNK=512
fr.CHUNK=CHUNK
# Boundaries cover the modeled interior t=14..nt-RAD-2. These bands are fixed
# structural coordinates and use no target values.
EDGES=(14,64,128,256,384,512,768,1024,1280,1493)


def _band_index(t):
    # Last edge is exclusive for normal nt=1500/RAD=6 modeled samples.
    return max(0,min(len(EDGES)-2,int(np.searchsorted(EDGES,int(t),side='right')-1)))


def profiled_score_and_adapt(net,mu,sd,static,X,eps,meta,state,_u1,_u2,reservoir,first_tile):
    X=q.crop(X);A,T,I,R=q.b.build(X,eps);A=(A-mu)/sd;Y=q.b.cls(T)
    XE=torch.from_numpy(A);YY=torch.from_numpy(Y);bits=q.boundary_bits(static,R,I);chunk_bits=[]
    bbits=np.zeros(len(EDGES)-1,np.float64);bn=np.zeros(len(EDGES)-1,np.int64)
    for ci,s in enumerate(range(0,len(XE),CHUNK)):
        e=min(len(XE),s+CHUNK);xx=XE[s:e];yy=YY[s:e];net.eval()
        with torch.no_grad():
            lp=F.log_softmax(net(xx),1)/math.log(2);idx=torch.arange(len(yy));per=(-lp[idx,yy]).cpu().numpy();cb=float(per.sum())
        bits+=cb;chunk_bits.append(cb/max(1,len(yy)))
        for off,v in enumerate(per):
            bi=_band_index(int(I[s+off,2]));bbits[bi]+=float(v);bn[bi]+=1
        fr._update(net,xx,yy,state,fr.FIRST_CHUNK_STEPS if (first_tile and ci==0) else fr.LATER_CHUNK_STEPS)
    bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
    take=min(fr.REPLAY_PER_TILE,len(XE))
    if take:
        ii=torch.linspace(0,len(XE)-1,take,dtype=torch.float64).round().long();reservoir.append((XE[ii].clone(),YY[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>fr.REPLAY_CAP:reservoir.pop(0)
    sb,sme=q.matched_sz3(X,eps);ours=int(math.ceil(bits/8))+q.HEADER_BYTES
    bands=[]
    for i in range(len(bn)):
        bands.append({'t0':int(EDGES[i]),'t1_exclusive':int(EDGES[i+1]),'modeled_samples':int(bn[i]),'class_bits':float(bbits[i]),'class_bps':float(bbits[i]/bn[i]) if bn[i] else None,'all_tile_sample_contribution_bps':float(bbits[i]/X.size)})
    return {**meta,'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bits[0]) if chunk_bits else None,'modeled_chunk_bps_last':float(chunk_bits[-1]) if chunk_bits else None,'time_band_profile':bands}


def main(a):
    fr.CHUNK=CHUNK;fr.score_and_adapt=profiled_score_and_adapt
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-512-timeband-profile-v1';out['measurement_only']=True;out['time_band_edges']=list(EDGES);out['reference_512_gain_vs_sz3']=REFERENCE_GAIN;out['gain_delta_vs_reference']=float(out['full_replay_weighted_gain_vs_sz3']-REFERENCE_GAIN)
    agg=[]
    for i in range(len(EDGES)-1):
        bits=sum(float(r['time_band_profile'][i]['class_bits']) for r in out['adapt_rows']);n=sum(int(r['time_band_profile'][i]['modeled_samples']) for r in out['adapt_rows']);samples=sum(int(r['samples']) for r in out['adapt_rows'])
        agg.append({'t0':EDGES[i],'t1_exclusive':EDGES[i+1],'modeled_samples':n,'class_bits':bits,'class_bps':bits/n if n else None,'all_target_sample_contribution_bps':bits/samples})
    out['aggregate_time_band_profile']=agg;out['note']='Measurement-only decomposition of class-probability bits. Predictor, residuals, probability model, source training and adaptation are unchanged; ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_TIMEBAND_FINAL',json.dumps({'gain':out['full_replay_weighted_gain_vs_sz3'],'delta_vs_reference':out['gain_delta_vs_reference'],'bands':agg},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
