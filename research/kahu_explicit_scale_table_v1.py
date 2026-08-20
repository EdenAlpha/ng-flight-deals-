#!/usr/bin/env python3
"""Compile the Kahu scale/roughness discovery into an explicit probability law.

PR #735 showed that decoder-known causal scale/roughness summaries improve the
strict unseen-Kahu neural probability model. This gate asks a stronger question:
can those summaries drive compression *without a neural interior model at all*?

The interior coder is a deterministic conditional class histogram. Context is
formed only from normalized y/x/t position and one source-defined causal scale
statistic. Context thresholds are quantiles learned from Waka/Opunake/Tui only.
For Kahu, each 512-symbol chunk is charged before its decoded classes update the
same table, so encoder and decoder can reproduce the adaptation exactly with no
side bits. The predictor, residual lattice, universal gamma tails, target
locations and source-trained boundary waveform coder are unchanged.

This is still an ideal-probability diagnostic: the fixed source tables and the
boundary model are not serialized/charged. The interior probability mechanism,
however, is fully non-neural and explicit.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np

import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_quick_adapter_loso_v1 as q
import boundary_waveform_probability_v1 as bw

TARGET='marine_kahu_3d'
TARGET_FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))
SOURCE_FRACS=base.SOURCE_FRACS
CHUNK=512
YBINS=4
XBINS=4
TBINS=8
SBINS=8
ALPHA=0.5
HEADER_BYTES=128
REFERENCE_NEURAL_SCALE=1.9473577357821565
REFERENCE_NEURAL_YXT=1.9321423201209738
VARIANTS=('position_only','current_wave_rms','neighbor_wave_rms','neighbor_resid_meanabs','current_resid_rms','composite_scale')


def _meanabs(z):return np.mean(np.abs(z),axis=1)
def _rms(z):return np.sqrt(np.mean(np.asarray(z,np.float64)**2,axis=1))
def _lg(z):return np.log1p(np.asarray(z,np.float64))


def causal_scalars(A):
    """Four explicit scalars extracted from the established decoder-known feature layout."""
    A=np.asarray(A,np.float32);w=2*q.b.RAD+1
    expected=10+8*w+q.b.HIST+8
    if A.shape[1]!=expected:raise RuntimeError(('base feature layout drift',A.shape[1],expected))
    p=0;cur=A[:,p:p+10];p+=10
    waves=[A[:,p+i*w:p+(i+1)*w] for i in range(4)];p+=4*w
    res=[A[:,p+i*w:p+(i+1)*w] for i in range(4)];p+=4*w
    crh=A[:,p:p+q.b.HIST]
    cw=_lg(_rms(cur))
    nw=_lg(np.mean(np.stack([_rms(z) for z in waves],1),1))
    nr=_lg(np.mean(np.stack([_meanabs(z) for z in res],1),1))
    cr=_lg(_rms(crh))
    return np.stack([cw,nw,nr,cr],axis=1)


def pos_bins(I,shape):
    ny,nx,nt=map(int,shape);I=np.asarray(I)
    y=np.minimum(YBINS-1,(I[:,0].astype(np.int64)*YBINS)//max(1,ny))
    x=np.minimum(XBINS-1,(I[:,1].astype(np.int64)*XBINS)//max(1,nx))
    t=np.minimum(TBINS-1,(I[:,2].astype(np.int64)*TBINS)//max(1,nt))
    return y,x,t


def cuts_for(z,n=SBINS):
    z=np.asarray(z,np.float64)
    return np.quantile(z,np.arange(1,n,dtype=np.float64)/float(n))


def sbin(z,cuts):return np.searchsorted(cuts,np.asarray(z,np.float64),side='right').astype(np.int64)


def ctx_index(I,shape,sv=None,cuts=None):
    y,x,t=pos_bins(I,shape)
    if sv is None:
        return ((y*XBINS+x)*TBINS+t).astype(np.int64),YBINS*XBINS*TBINS
    s=sbin(sv,cuts)
    return (((y*XBINS+x)*TBINS+t)*SBINS+s).astype(np.int64),YBINS*XBINS*TBINS*SBINS


def add_counts(counts,ctx,y):
    np.add.at(counts,(ctx,np.asarray(y,np.int64)),1.0)


def score_counts(counts,ctx,y):
    y=np.asarray(y,np.int64)
    p=counts[ctx,y]/counts[ctx].sum(axis=1)
    return float((-np.log2(np.maximum(p,1e-300))).sum())


def train_boundary_only(source,seed):
    # boundary_waveform_probability_v1.install() normally wraps the expensive
    # neural interior fit. Replace that interior fit with a cheap stub first;
    # the boundary model itself remains exactly the established source-trained
    # boundary MLP used by the current Kahu leader.
    def stub(train_tiles,_seed):
        rr=[]
        for X,eps in train_tiles:
            _,_,_,R=q.b.build(q.crop(X),eps);rr.append(R.reshape(-1))
        r=np.concatenate(rr);c=np.bincount(q.b.cls(r),minlength=q.b.NCLASS).astype(np.float64)+1.;c/=c.sum()
        return None,None,None,-np.log2(c)
    base.wide_fit=stub
    bw.install(base)
    _,_,_,static=base.wide_fit(source,seed)
    return static


def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));train_ids=tuple(s for s in q.SURVEYS if s!=TARGET)
    source=[];source_records=[]
    for ds in train_ids:
        for frac in SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);X=q.crop(X);A,T,I,R=q.b.build(X,ep);S=causal_scalars(A)
            source.append((X,ep));source_records.append((S,T,I,X.shape));print('EXPLICIT_SOURCE',ds,frac,X.shape,flush=True)
    # Train only the unchanged boundary probability model. No neural interior fit.
    static=train_boundary_only(source,20262020)

    allS=np.concatenate([z[0] for z in source_records],0)
    mu=allS.mean(0);sd=allS.std(0);sd[sd<1e-8]=1.
    composite=((allS-mu)/sd).mean(1)
    cuts={
      'current_wave_rms':cuts_for(allS[:,0]),
      'neighbor_wave_rms':cuts_for(allS[:,1]),
      'neighbor_resid_meanabs':cuts_for(allS[:,2]),
      'current_resid_rms':cuts_for(allS[:,3]),
      'composite_scale':cuts_for(composite),
    }
    source_tables={}
    for v in VARIANTS:
        nctx=YBINS*XBINS*TBINS if v=='position_only' else YBINS*XBINS*TBINS*SBINS
        C=np.full((nctx,q.b.NCLASS),ALPHA,np.float64)
        for S,T,I,shape in source_records:
            if v=='position_only':ctx,_=ctx_index(I,shape)
            else:
                if v=='current_wave_rms':sv=S[:,0]
                elif v=='neighbor_wave_rms':sv=S[:,1]
                elif v=='neighbor_resid_meanabs':sv=S[:,2]
                elif v=='current_resid_rms':sv=S[:,3]
                else:sv=((S-mu)/sd).mean(1)
                ctx,_=ctx_index(I,shape,sv,cuts[v])
            add_counts(C,ctx,q.b.cls(T))
        source_tables[v]=C
        print('EXPLICIT_TABLE',v,nctx,int(np.count_nonzero(C>ALPHA)),flush=True)

    targets=[]
    for frac in TARGET_FRACS:
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);A,T,I,R=q.b.build(X,ep);S=causal_scalars(A)
        targets.append((X,ep,md,S,T,I,R));print('EXPLICIT_TARGET',frac,X.shape,md.get('trace_first'),flush=True)

    results={}
    for v in VARIANTS:
        C=source_tables[v].copy();rows=[]
        for pi,(frac,z) in enumerate(zip(TARGET_FRACS,targets)):
            X,ep,md,S,T,I,R=z
            if v=='position_only':ctx,_=ctx_index(I,X.shape)
            else:
                if v=='current_wave_rms':sv=S[:,0]
                elif v=='neighbor_wave_rms':sv=S[:,1]
                elif v=='neighbor_resid_meanabs':sv=S[:,2]
                elif v=='current_resid_rms':sv=S[:,3]
                else:sv=((S-mu)/sd).mean(1)
                ctx,_=ctx_index(I,X.shape,sv,cuts[v])
            Y=q.b.cls(T);bits=float(q.boundary_bits(static,R,I));chunk_bps=[]
            for s0 in range(0,len(Y),CHUNK):
                ee=min(len(Y),s0+CHUNK);cb=score_counts(C,ctx[s0:ee],Y[s0:ee]);bits+=cb;chunk_bps.append(cb/max(1,ee-s0))
                # Legal target adaptation: update only after this chunk was charged.
                add_counts(C,ctx[s0:ee],Y[s0:ee])
            bits+=float(q.b.gamma_bits(np.maximum(np.abs(T)-q.b.LIM,0)).sum())
            sb,sme=q.matched_sz3(X,ep);ours=int(math.ceil(bits/8))+HEADER_BYTES
            row={'position':pi,'fraction':float(frac),'samples':int(X.size),'ideal_bytes_plus_header':ours,'ideal_bps':float(8*ours/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_ideal':float(sb/ours),'sz3_maxerr':float(sme),'modeled_chunk_bps_first':float(chunk_bps[0]),'modeled_chunk_bps_last':float(chunk_bps[-1])}
            rows.append(row);print('EXPLICIT_ROW',v,json.dumps(row),flush=True)
        gain=float(sum(r['sz3_bytes'] for r in rows)/sum(r['ideal_bytes_plus_header'] for r in rows));samples=sum(r['samples'] for r in rows);sz=sum(r['sz3_bytes'] for r in rows);ours=sum(r['ideal_bytes_plus_header'] for r in rows)
        results[v]={'weighted_gain_vs_sz3':gain,'weighted_gap_to_2x_bps':float((ours-.5*sz)*8/samples),'positions_crossing_2x':int(sum(r['gain_vs_sz3_ideal']>=2 for r in rows)),'rows':rows}
        print('EXPLICIT_FINAL',v,gain,flush=True)

    best=max(VARIANTS,key=lambda v:results[v]['weighted_gain_vs_sz3'])
    out={'kind':'unseen-kahu-explicit-causal-scale-table-v1','status':'diagnostic_ideal_probability_rate_not_serialized_codec','test_dataset':TARGET,'training_datasets':list(train_ids),'source_training_tiles':len(source),'target_position_count':len(targets),'kahu_used_in_source_tables_or_thresholds':False,'all_target_positions_charged':True,'interior_probability_model':'non-neural source-trained conditional histogram with post-charge causal count updates','interior_probability_model_non_neural':True,'boundary_probability_model':'unchanged source-trained causal boundary waveform MLP','boundary_model_non_neural':False,'context_position_bins':{'y':YBINS,'x':XBINS,'t':TBINS},'scale_bins':SBINS,'scale_threshold_rule':'equal-mass quantiles from non-Kahu source surveys only','dirichlet_alpha_per_class':ALPHA,'adaptation_chunk':CHUNK,'target_table_updates_only_after_scoring_decoded_symbols':True,'extra_transmitted_selector_bits':0,'fixed_source_tables_serialized_or_charged':False,'reference_neural_yxt_gain_vs_sz3':REFERENCE_NEURAL_YXT,'reference_neural_all12_scale_gain_vs_sz3':REFERENCE_NEURAL_SCALE,'variants':results,'best_variant':best,'best_weighted_gain_vs_sz3':float(results[best]['weighted_gain_vs_sz3']),'note':'Tests whether the neural scale/roughness discovery can be compiled into an explicit deterministic interior probability law. No neural network is used for interior probabilities; the established boundary MLP is intentionally held fixed for attribution.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('EXPLICIT_SCALE_TABLE_FINAL',json.dumps({k:v for k,v in out.items() if k!='variants'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
