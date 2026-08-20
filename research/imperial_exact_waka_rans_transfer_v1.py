#!/usr/bin/env python3
from __future__ import annotations
import argparse,copy,json
from pathlib import Path
import h5py,numpy as np,torch
from pysz import sz,szConfig,szErrorBoundMode
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import waka_unseen_fast_boundary_mlp_v1 as bm
import waka_unseen_rans_independent_decoder_v1 as one
import waka_unseen_rans_independent_3block_v1 as three
import waka_unseen_boundary_mlp_rans_v1 as rr

# Exact PR718 system: historical independent-decoder result = 2.0283285781744156x.
WAKA_HEAD='0ce6631316c1843df1de9dd0e097ec59940a7cd2'
WAKA_GAIN=2.0283285781744156
T0=14488;C0=512;C=32;T=1024;EPS=133.69778037805762
HEADER=128;CURRENT=22527;SZ3_EXPECT=26751

def sz3_both(X):
    best=None
    for tr in (False,True):
        A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=EPS
        bb,_=sz.compress(A,cfg);R,_=sz.decompress(bb,np.float32,A.shape);me=float(np.max(np.abs(A.astype(float)-R.astype(float))))
        if me>EPS*(1+5e-6):raise RuntimeError(('sz3 error',me))
        z=(int(bb.size),'T' if tr else 'CT',me)
        if best is None or z[0]<best[0]:best=z
    return best

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    # This is exactly PR718's source set: 15 Kahu/Opunake/Tui tiles, no Waka/Imperial.
    for ds in s.SOURCE_IDS:
        for frac in s.SOURCE_FRACS:
            X,ep,_=q.b.extract(ds,m,e,frac);source.append((s.central24(X),ep));print('SOURCE',ds,frac,source[-1][0].shape,flush=True)
    q.crop=lambda X:np.ascontiguousarray(X);fr.CHUNK=1024
    net0,mu,sd,_=bm.patched_fit(source,20261319)
    enet=copy.deepcopy(net0);dnet=copy.deepcopy(net0)
    estate,_,_=fr.new_adapter(120001);dstate,_,_=fr.new_adapter(120001);eres=[];dres=[]
    with h5py.File(a.imperial,'r') as f:X2=np.asarray(f['Acoustic'][T0:T0+T,C0:C0+C],np.float64).T
    if X2.shape!=(C,T):raise RuntimeError(X2.shape)
    # ONLY transfer change: DAS channel axis -> existing x axis; y is singleton/absent.
    X=np.ascontiguousarray(X2[None,:,:]);A,Tv,I,R0=q.b.build(X,EPS)
    if A.shape[1]!=len(mu):raise RuntimeError(('feature drift',A.shape[1],len(mu)))
    S0=one.state_from_residuals(R0)
    stream=three.encode_block(enet,mu,sd,R0,S0,estate,eres,True)
    R1,S1=three.decode_block(dnet,mu,sd,stream,R0.shape,dstate,dres,True)
    if not np.array_equal(R0,R1):raise RuntimeError('residual mismatch')
    pd=three.param_diff(enet,dnet);od=three.opt_diff(estate,dstate)
    if pd!=0 or od!=0:raise RuntimeError(('state divergence',pd,od))
    if len(eres)!=len(dres):raise RuntimeError('reservoir length')
    for x,y in zip(eres,dres):
        if not torch.equal(x[0],y[0]) or not torch.equal(x[1],y[1]):raise RuntimeError('reservoir content')
    Y=S1[0]*(2*EPS*.9999);me=float(np.max(np.abs(X2-Y)))
    if me>EPS*(1+3e-6):raise RuntimeError(('hard error',me))
    szb,ori,szme=sz3_both(X2)
    if szb!=SZ3_EXPECT:raise RuntimeError(('SZ3 drift',szb,SZ3_EXPECT))
    total=len(stream)+HEADER
    out={'kind':'imperial-exact-waka-rans-transfer-v1','source_pr':718,'source_head':WAKA_HEAD,'verified_waka_actual_gain_vs_sz3':WAKA_GAIN,
         'exact_waka_model_used':True,'later_kahu_scale_yxt_model_used':False,'imperial_used_in_training_or_normalization':False,
         'geometry_adapter':'[channel,time] -> [y=1,x=channel,time]; no fitted adapter parameters','model_or_feature_stack_changed':False,
         'adaptation_chunk':1024,'cdf_precision_bits':rr.SCALE_BITS,'actual_rans_stream':True,'independent_decoder_cdfs':True,
         'imperial':{'shape':[C,T],'epsilon':EPS,'payload_bytes':len(stream),'header_bytes':HEADER,'actual_total_bytes':total,
         'actual_bps':8*total/(C*T),'sz3_bytes':szb,'sz3_orientation':ori,'gain_vs_sz3':szb/total,
         'current_imperial_bytes':CURRENT,'gain_vs_current_imperial':CURRENT/total,'maxerr':me,'sz3_maxerr':szme,
         'residual_roundtrip_exact':True,'model_sync':True,'residual_zero_fraction':float(np.mean(R0==0)),
         'residual_std':float(R0.std()),'tail_fraction_abs_gt_8':float(np.mean(np.abs(R0)>q.b.LIM))}}
    Path(a.out).write_text(json.dumps(out,indent=2));print('FINAL',json.dumps(out['imperial'],indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--imperial',required=True);p.add_argument('--out',required=True);main(p.parse_args())
