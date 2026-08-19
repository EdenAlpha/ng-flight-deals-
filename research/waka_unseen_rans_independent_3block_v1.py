#!/usr/bin/env python3
"""Three-block independent probability-regenerating rANS Waka gate.

Promotion of the successful single-block independent decoder. Encoder and decoder
begin from identical source-trained interior/boundary models but never share target
CDFs or original Waka samples. Each side independently regenerates finite 15-bit
CDFs from its own causal reconstructed state, updates the main model only after
1024 interior symbols have been charged/decoded, and performs identical replay
between the three held-out Waka blocks using only already-decoded target features.

Every block is an actual byte-oriented rANS payload. Required checks:
- exact residual-lattice recovery on each block,
- encoder/decoder model synchronization after each block and after replay,
- reconstruction max error <= epsilon,
- actual weighted bytes versus matched SZ3.
"""
from __future__ import annotations
import argparse,copy,json
from pathlib import Path
import numpy as np
import torch
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import waka_unseen_fast_boundary_mlp_v1 as bm
import waka_unseen_boundary_mlp_rans_v1 as rr
import waka_unseen_rans_independent_decoder_v1 as one

HEADER_BYTES=128
TARGET_FRACS=(.15,.50,.85)
REPLAY_PER_TILE=fr.REPLAY_PER_TILE
REPLAY_CAP=fr.REPLAY_CAP
REPLAY_STEPS=fr.REPLAY_STEPS_BETWEEN_TILES


def param_diff(a,b):
    return max(float((x-y).abs().max()) for x,y in zip(a.parameters(),b.parameters()))


def opt_diff(sa,sb):
    oa=sa.get('opt');ob=sb.get('opt')
    if oa is None or ob is None:return 0.0 if oa is ob else float('inf')
    vals=[]
    pa=list(oa.param_groups[0]['params']);pb=list(ob.param_groups[0]['params'])
    for a,b in zip(pa,pb):
        xa=oa.state.get(a,{});xb=ob.state.get(b,{})
        if xa.keys()!=xb.keys():return float('inf')
        for k in xa:
            va,vb=xa[k],xb[k]
            if torch.is_tensor(va):vals.append(float((va-vb).abs().max()))
            elif va!=vb:return float('inf')
    return max(vals) if vals else 0.0


def add_reservoir(reservoir,features,labels):
    if not features:return
    X=torch.from_numpy(np.stack(features).astype(np.float32));Y=torch.tensor(labels,dtype=torch.long)
    take=min(REPLAY_PER_TILE,len(X))
    if take:
        ii=torch.linspace(0,len(X)-1,take,dtype=torch.float64).round().long()
        reservoir.append((X[ii].clone(),Y[ii].clone()))
        while sum(len(z[0]) for z in reservoir)>REPLAY_CAP:reservoir.pop(0)


def replay(net,state,reservoir):
    if not reservoir:return
    X=torch.cat([z[0] for z in reservoir],0);Y=torch.cat([z[1] for z in reservoir],0)
    for _ in range(REPLAY_STEPS):
        for st in range(0,len(X),4096):fr._update(net,X[st:st+4096],Y[st:st+4096],state,1)


def encode_block(net,mu,sd,R,S,state,reservoir,first_global_chunk):
    starts=[];freqs=[];bufF=[];bufY=[];allF=[];allY=[];chunk_index=0;ny,nx,nt=R.shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                raw=int(R[y,x,t]);boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1)
                if boundary:
                    cdf=one.single_cdf(bm._BMODEL,one.boundary_feature(S,R,y,x,t),bm._BMU,bm._BSD)
                else:
                    f=one.main_feature(S,R,y,x,t);nf=((f-mu)/sd).astype(np.float32)
                    cdf=one.single_cdf(net,f,mu,sd);bufF.append(nf);bufY.append(one.class_of(raw));allF.append(nf);allY.append(one.class_of(raw))
                one.push_class_events(starts,freqs,cdf,raw)
                if not boundary and len(bufF)==fr.CHUNK:
                    X=torch.from_numpy(np.stack(bufF));Y=torch.tensor(bufY,dtype=torch.long)
                    steps=fr.FIRST_CHUNK_STEPS if first_global_chunk and chunk_index==0 else fr.LATER_CHUNK_STEPS
                    fr._update(net,X,Y,state,steps);bufF=[];bufY=[];chunk_index+=1
    if bufF:
        X=torch.from_numpy(np.stack(bufF));Y=torch.tensor(bufY,dtype=torch.long)
        steps=fr.FIRST_CHUNK_STEPS if first_global_chunk and chunk_index==0 else fr.LATER_CHUNK_STEPS
        fr._update(net,X,Y,state,steps)
    add_reservoir(reservoir,allF,allY)
    return rr.rans_encode(starts,freqs)


def decode_block(net,mu,sd,stream,shape,state,reservoir,first_global_chunk):
    dec=rr.RansDecoder(stream);R=np.zeros(shape,np.int32);S=np.zeros(shape,np.float64);bufF=[];bufY=[];allF=[];allY=[];chunk_index=0;ny,nx,nt=shape
    for y in range(ny):
        for x in range(nx):
            for t in range(nt):
                boundary=(x==0 or t<14 or t>=nt-q.b.RAD-1)
                if boundary:
                    f=one.boundary_feature(S,R,y,x,t);cdf=one.single_cdf(bm._BMODEL,f,bm._BMU,bm._BSD)
                else:
                    f=one.main_feature(S,R,y,x,t);nf=((f-mu)/sd).astype(np.float32);cdf=one.single_cdf(net,f,mu,sd)
                c=dec.decode(cdf);raw=one.decode_tail(dec,c);R[y,x,t]=raw;S[y,x,t]=one.predict_s(S,y,x,t)+raw
                if not boundary:
                    bufF.append(nf);bufY.append(c);allF.append(nf);allY.append(c)
                    if len(bufF)==fr.CHUNK:
                        X=torch.from_numpy(np.stack(bufF));Y=torch.tensor(bufY,dtype=torch.long)
                        steps=fr.FIRST_CHUNK_STEPS if first_global_chunk and chunk_index==0 else fr.LATER_CHUNK_STEPS
                        fr._update(net,X,Y,state,steps);bufF=[];bufY=[];chunk_index+=1
    if bufF:
        X=torch.from_numpy(np.stack(bufF));Y=torch.tensor(bufY,dtype=torch.long)
        steps=fr.FIRST_CHUNK_STEPS if first_global_chunk and chunk_index==0 else fr.LATER_CHUNK_STEPS
        fr._update(net,X,Y,state,steps)
    if dec.pos!=-1:raise RuntimeError(('unread rANS renormalization bytes',dec.pos))
    add_reservoir(reservoir,allF,allY)
    return R,S


def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in s.SOURCE_IDS:
        for frac in s.SOURCE_FRACS:
            X,ep,md=q.b.extract(ds,m,e,frac);source.append((s.central24(X),ep));print('MULTI_INDEP_SOURCE',ds,frac,source[-1][0].shape,flush=True)
    q.crop=lambda X:np.ascontiguousarray(X);fr.CHUNK=1024
    net0,mu,sd,static=bm.patched_fit(source,20261319)
    enet=copy.deepcopy(net0);dnet=copy.deepcopy(net0)
    estate,_,_=fr.new_adapter(120001);dstate,_,_=fr.new_adapter(120001)
    eres=[];dres=[];rows=[]
    for pi,frac in enumerate(TARGET_FRACS):
        if pi>0:
            replay(enet,estate,eres);replay(dnet,dstate,dres)
            pd=param_diff(enet,dnet);od=opt_diff(estate,dstate)
            if pd!=0.0 or od!=0.0:raise RuntimeError(('encoder/decoder replay divergence',pi,pd,od))
        X,eps,md=s.extract_waka16(m,e,frac);_,_,_,R0=q.b.build(X,eps);S0=one.state_from_residuals(R0)
        stream=encode_block(enet,mu,sd,R0,S0,estate,eres,pi==0)
        R1,S1=decode_block(dnet,mu,sd,stream,R0.shape,dstate,dres,pi==0)
        if not np.array_equal(R0,R1):
            at=np.argwhere(R0!=R1)[0];idx=tuple(map(int,at));raise RuntimeError(('independent residual mismatch',pi,idx,int(R0[idx]),int(R1[idx])))
        pd=param_diff(enet,dnet);od=opt_diff(estate,dstate)
        if pd!=0.0 or od!=0.0:raise RuntimeError(('encoder/decoder model divergence',pi,pd,od))
        if len(eres)!=len(dres):raise RuntimeError(('reservoir length divergence',pi,len(eres),len(dres)))
        for j,(ea,da) in enumerate(zip(eres,dres)):
            if not torch.equal(ea[0],da[0]) or not torch.equal(ea[1],da[1]):raise RuntimeError(('reservoir content divergence',pi,j))
        step=2*float(eps)*.9999;Y=S1*step;maxerr=float(np.max(np.abs(np.asarray(X,np.float64)-Y)))
        if maxerr>float(eps)*(1+3e-6):raise RuntimeError(('reconstruction error',pi,maxerr,eps))
        sb,sme=q.matched_sz3(X,eps);total=len(stream)+HEADER_BYTES
        row={'position':pi,'fraction':float(frac),'shape':list(map(int,X.shape)),'samples':int(X.size),'rans_payload_bytes':len(stream),'header_bytes':HEADER_BYTES,'actual_total_bytes':total,'actual_bps':float(8*total/X.size),'sz3_bytes':int(sb),'gain_vs_sz3_actual_bytes':float(sb/total),'residual_roundtrip_exact':True,'max_reconstruction_error':maxerr,'epsilon':float(eps),'error_bound_valid':True,'encoder_decoder_model_max_parameter_difference':pd,'encoder_decoder_optimizer_max_difference':od,'sz3_maxerr':float(sme)}
        rows.append(row);print('MULTI_INDEPENDENT_WAKA',json.dumps(row),flush=True)
    actual=sum(z['actual_total_bytes'] for z in rows);sz=sum(z['sz3_bytes'] for z in rows);samples=sum(z['samples'] for z in rows);gain=float(sz/actual)
    out={'kind':'unseen-waka-independent-probability-regenerating-rans-decoder-3block-v1','status':'three_block_end_to_end_actual_stream','training_datasets':list(s.SOURCE_IDS),'source_training_tiles':len(source),'waka_used_in_probability_training':False,'decoder_reuses_encoder_cdfs':False,'decoder_receives_original_samples':False,'decoder_regenerates_main_and_boundary_probabilities':True,'target_positions_all_charged':True,'target_fractions':list(TARGET_FRACS),'adaptation_chunk':fr.CHUNK,'replay_between_blocks_uses_only_already_decoded_target_features':True,'replay_cap':REPLAY_CAP,'replay_steps_between_blocks':REPLAY_STEPS,'cdf_precision_bits':rr.SCALE_BITS,'rows':rows,'actual_total_bytes':int(actual),'sz3_total_bytes':int(sz),'actual_weighted_gain_vs_sz3':gain,'actual_weighted_gap_to_2x_bps':float((actual-.5*sz)*8/samples),'crosses_weighted_2x_actual':bool(gain>=2.0),'all_residual_roundtrips_exact':True,'all_error_bounds_valid':True,'final_encoder_decoder_model_max_parameter_difference':param_diff(enet,dnet),'final_encoder_decoder_optimizer_max_difference':opt_diff(estate,dstate),'important':'Encoder and decoder independently regenerate every target CDF and preserve identical adaptation/replay state across all three unseen Waka blocks. Actual byte-oriented rANS payloads are counted.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('MULTI_INDEPENDENT_FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
