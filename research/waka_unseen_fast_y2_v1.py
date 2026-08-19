#!/usr/bin/env python3
"""Add already-decoded y-2 waveform context to the strongest unseen-Waka stack.

The successful direct residual representation is unchanged.  The probability
model gains only information from row y-2, which is fully decoded before the
current row.  Source training remains the proven 15 Kahu/Opunake/Tui 4x24 tiles,
so Waka remains completely absent from fitting and normalization.  Held-out
adaptation uses the independently positive 1024-symbol cadence, always scoring
before update.  Ideal probability rate only; not a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q

FROZEN_FAST_GAIN=1.9455818821962128
ORIG_BUILD=q.b.build
fr.CHUNK=1024

def reconstructed_state(R,eps):
    step=2*float(eps)*.9999;R=np.asarray(R);ny,nx,nt=R.shape;Y=np.empty(R.shape,np.float64)
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                if x>0:
                    if y>0:
                        sp=q.b.W*Y[y,x-1,t]+(1-q.b.W)*Y[y-1,x,t];ps=q.b.W*Y[y,x-1,t-1]+(1-q.b.W)*Y[y-1,x,t-1] if t else 0.
                    else:sp=Y[y,x-1,t];ps=Y[y,x-1,t-1] if t else 0.
                    p=q.b.A*sp+(Y[y,x,t-1]-q.b.A*ps if t else 0.)
                elif y>0:p=q.b.A*Y[y-1,x,t]+(Y[y,x,t-1]-q.b.A*Y[y-1,x,t-1] if t else 0.)
                elif t:p=Y[y,x,t-1]
                else:p=0.
                Y[y,x,t]=p+int(R[y,x,t])*step
    return Y/step

def build_y2(X,eps):
    A,T,I,R=ORIG_BUILD(X,eps);S=reconstructed_state(R,eps);rad=q.b.RAD;extra=[]
    for y,x,t in I:
        y=int(y);x=int(x);t=int(t)
        if y>=2:
            z=S[y-2,x];zr=R[y-2,x];u=S[y-1,x,t]
            row=(z[t-rad:t+rad+1]-z[t]).tolist()+np.asarray(zr[t-rad:t+rad+1],dtype=np.float64).tolist()+[float(z[t]),float(z[t]-u),1.0]
        else:row=[0.0]*(2*(2*rad+1)+3)
        extra.append(row)
    return np.concatenate([A,np.asarray(extra,np.float32)],axis=1),T,I,R

def main(a):
    q.b.build=build_y2
    s.main(a)
    out=json.load(open(a.out));out['kind']='unseen-waka-16x32-stacked-fast-adapt-yminus2-v1';out['extra_probability_context']='already-decoded row y-2 waveform window, residual window, center/difference, presence flag';out['residual_representation_changed']=False;out['waka_used_in_source_training']=False;out['adaptation_chunk']=fr.CHUNK;out['fast_adapt_reference_gain']=FROZEN_FAST_GAIN
    sz=sum(z['sz3_bytes'] for z in out['adapt_rows']);ours=sum(z['ideal_bytes_plus_header'] for z in out['adapt_rows']);samples=sum(z['samples'] for z in out['adapt_rows']);out['weighted_gap_to_2x_bps']=float((ours-.5*sz)*8/samples);out['gain_vs_fast_reference_ratio']=float(out['full_replay_weighted_gain_vs_sz3']/FROZEN_FAST_GAIN);out['positions_crossing_2x']=int(sum(z['gain_vs_sz3_ideal']>=2 for z in out['adapt_rows']));out['note']='Source-trained y-2 context plus proven 1024-symbol causal adaptation. No Waka sample enters fitting/normalization; every Waka chunk is charged before update. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('FAST_Y2_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('source_meta','base_rows','adapt_rows')},indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
