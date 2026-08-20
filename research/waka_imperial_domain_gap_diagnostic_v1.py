#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,math
from pathlib import Path
import h5py,numpy as np,torch
import torch.nn.functional as F
import migrated_volume_multisource_replay_loso_v1 as s
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import waka_unseen_fast_boundary_mlp_v1 as bm

T0=14488; C0=512; C=32; T=1024; IMP_EPS=133.69778037805762
GROUPS={
    'current_wave_history':(0,10),
    'neighbor_wave_windows':(10,62),
    'neighbor_residual_windows':(62,114),
    'current_residual_history':(114,126),
    'scalar_geometry_relations':(126,134),
}

def entropy(v,n):
    c=np.bincount(np.asarray(v,np.int64),minlength=n).astype(np.float64)
    p=c[c>0]/max(1,c.sum())
    return float(-(p*np.log2(p)).sum())

def corr(a,b):
    a=np.asarray(a,np.float64);b=np.asarray(b,np.float64)
    if len(a)<2 or a.std()==0 or b.std()==0:return 0.0
    return float(np.corrcoef(a,b)[0,1])

def diagnose(name,X,eps,net,mu,sd):
    X=np.ascontiguousarray(np.asarray(X,np.float64))
    A,Tv,I,R=q.b.build(X,eps)
    Z=(A-mu)/sd
    Y=q.b.cls(Tv)
    ce=0.0
    net.eval()
    Xt=torch.from_numpy(Z.astype(np.float32));Yt=torch.from_numpy(Y)
    with torch.no_grad():
        for st in range(0,len(Xt),16384):
            yy=Yt[st:st+16384]
            lp=F.log_softmax(net(Xt[st:st+16384]),1)/math.log(2)
            ce+=float((-lp[torch.arange(len(yy)),yy]).sum())
    tail=np.maximum(np.abs(Tv)-q.b.LIM,0)
    tail_bits=float(q.b.gamma_bits(tail).sum())
    cls_h=entropy(Y,q.b.NCLASS)
    all_cls=q.b.cls(R.reshape(-1))
    all_tail=np.maximum(np.abs(R.reshape(-1))-q.b.LIM,0)
    groups={}
    for g,(a,b) in GROUPS.items():
        z=Z[:,a:b]
        groups[g]={
            'mean_abs_z':float(np.mean(np.abs(z))),
            'fraction_abs_z_gt_5':float(np.mean(np.abs(z)>5)),
            'fraction_abs_z_gt_10':float(np.mean(np.abs(z)>10)),
        }
    at=np.abs(Tv.astype(np.float64)); left=[]; up=[]
    for y,x,t in I:
        y=int(y);x=int(x);t=int(t)
        left.append(abs(float(R[y,x-1,t])))
        up.append(abs(float(R[y-1,x,t])) if y>0 else 0.0)
    out={
        'name':name,'shape':list(map(int,X.shape)),'samples':int(X.size),'epsilon':float(eps),
        'interior_symbols':int(len(Tv)),
        'residual_zero_fraction':float(np.mean(R==0)),
        'residual_tail_fraction_abs_gt_8':float(np.mean(np.abs(R)>q.b.LIM)),
        'residual_std':float(R.std()),
        'whole_residual_class_entropy_bps':entropy(all_cls,q.b.NCLASS),
        'whole_residual_tail_gamma_bps':float(q.b.gamma_bits(all_tail).sum()/R.size),
        'interior_empirical_class_entropy_bps':cls_h,
        'interior_model_zero_shot_class_ce_bps':float(ce/max(1,len(Tv))),
        'interior_model_zero_shot_plus_tail_bps':float((ce+tail_bits)/max(1,len(Tv))),
        'model_mismatch_penalty_over_empirical_class_bps':float(ce/max(1,len(Tv))-cls_h),
        'feature_fraction_abs_z_gt_5':float(np.mean(np.abs(Z)>5)),
        'feature_fraction_abs_z_gt_10':float(np.mean(np.abs(Z)>10)),
        'feature_mean_abs_z':float(np.mean(np.abs(Z))),
        'feature_groups':groups,
        'corr_abs_target_residual_vs_left_same_time':corr(at,left),
        'corr_abs_target_residual_vs_up_same_time':corr(at,up),
    }
    print('DIAG',json.dumps(out),flush=True)
    return out

def main(a):
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in s.SOURCE_IDS:
        for frac in s.SOURCE_FRACS:
            X,ep,_=q.b.extract(ds,m,e,frac);source.append((s.central24(X),ep));print('SOURCE',ds,frac,source[-1][0].shape,flush=True)
    q.crop=lambda X:np.ascontiguousarray(X);fr.CHUNK=1024
    net,mu,sd,_=bm.patched_fit(source,20261319)

    W,weps,_=s.extract_waka16(m,e,.15)
    normal=diagnose('waka_native_16x32',W,weps,net,mu,sd)
    # Same Waka samples, same ordering inside each row, but remove the second spatial axis.
    flat=np.ascontiguousarray(W.reshape(1,W.shape[0]*W.shape[1],W.shape[2]))
    flatd=diagnose('waka_same_samples_flattened_to_one_spatial_axis',flat,weps,net,mu,sd)

    with h5py.File(a.imperial,'r') as f:
        X2=np.asarray(f['Acoustic'][T0:T0+T,C0:C0+C],np.float64).T
    imp=diagnose('imperial_native_one_spatial_axis',X2[None,:,:],IMP_EPS,net,mu,sd)

    out={
      'kind':'waka-imperial-domain-gap-diagnostic-v1',
      'exact_pr718_source_model':True,
      'imperial_used_in_training_or_normalization':False,
      'waka_native':normal,'waka_flattened':flatd,'imperial':imp,
      'controlled_geometry_effect':{
        'tail_fraction_ratio_flat_over_native':float(flatd['residual_tail_fraction_abs_gt_8']/max(1e-12,normal['residual_tail_fraction_abs_gt_8'])),
        'residual_std_ratio_flat_over_native':float(flatd['residual_std']/max(1e-12,normal['residual_std'])),
        'zero_shot_model_bps_ratio_flat_over_native':float(flatd['interior_model_zero_shot_plus_tail_bps']/max(1e-12,normal['interior_model_zero_shot_plus_tail_bps'])),
      },
      'imperial_vs_waka_native':{
        'tail_fraction_ratio':float(imp['residual_tail_fraction_abs_gt_8']/max(1e-12,normal['residual_tail_fraction_abs_gt_8'])),
        'residual_std_ratio':float(imp['residual_std']/max(1e-12,normal['residual_std'])),
        'zero_shot_model_bps_ratio':float(imp['interior_model_zero_shot_plus_tail_bps']/max(1e-12,normal['interior_model_zero_shot_plus_tail_bps'])),
      },
      'note':'Mechanism diagnostic only. Waka-flat keeps the same samples but removes the second spatial axis to isolate how much the PR718 representation depends on 2-D migrated-volume geometry.'
    }
    Path(a.out).write_text(json.dumps(out,indent=2));print('FINAL',json.dumps(out['controlled_geometry_effect']),json.dumps(out['imperial_vs_waka_native']),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--imperial',required=True);p.add_argument('--out',required=True);main(p.parse_args())
