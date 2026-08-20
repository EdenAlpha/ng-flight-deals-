#!/usr/bin/env python3
"""Test whether the Kahu neural probability head collapses to a Gaussian scale law.

This is a distillation/interpretability diagnostic.  It reproduces the PR #735
model, causally adapts it through only the first 12 fixed Kahu positions, freezes
that neural teacher, and then asks two questions on a common fixed context pool:

1. Can each 19-class neural residual PMF be approximated by a zero-mean
   discretized Gaussian with one parameter sigma?
2. Can sigma itself be approximated by a sparse explicit equation of the 12
   causal scale/roughness summaries plus y/x/t, fitted on positions 0..11 and
   evaluated on unseen positions 12..15?

The 17 central classes are q=-8..8 and the two tail classes are q<-8 and q>8,
so the Gaussian PMF is integrated over half-integer bins and the two outer tails.
We report KL/excess coding cost relative to the frozen neural teacher and actual
sampled class code lengths on the last four held-out positions.

No future current-trace values or side bits are introduced.  This is not yet a
serialized codec or a claim that the sparse law replaces the causal predictor.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
import numpy as np

import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import boundary_waveform_probability_v1 as bw
import kahu_unseen_causal_scale_features_v1 as scale
import kahu_probability_head_dissection_v1 as hd

TARGET='marine_kahu_3d'
TARGET_FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))
DISTILL_POSITIONS=12
CAP_PER_POSITION=4096
SIGMA_GRID=np.geomspace(.18,6.0,128).astype(np.float64)
SPARSE_TERMS=12


def gaussian_pmfs_zero(sigmas):
    """Return [n,19] discretized zero-mean Gaussian class PMFs."""
    import torch
    s=torch.as_tensor(np.asarray(sigmas,np.float64),dtype=torch.float64).reshape(-1,1)
    # Central q=-8..8 bins use edges q +/- .5.
    qs=torch.arange(-8,9,dtype=torch.float64).reshape(1,-1)
    rt2=math.sqrt(2.0)
    def cdf(x): return 0.5*(1.0+torch.erf(x/(s*rt2)))
    lo=(qs-.5);hi=(qs+.5)
    central=cdf(hi)-cdf(lo)
    neg=0.5*(1.0+torch.erf(torch.tensor(-8.5,dtype=torch.float64)/(s*rt2)))
    pos=1.0-0.5*(1.0+torch.erf(torch.tensor(8.5,dtype=torch.float64)/(s*rt2)))
    P=torch.cat([central,neg,pos],1)
    P=P/torch.clamp(P.sum(1,keepdim=True),min=1e-300)
    return P.numpy()


def gaussian_pmfs_shifted(mu,sigma):
    import torch
    mu=torch.as_tensor(np.asarray(mu,np.float64),dtype=torch.float64).reshape(-1,1)
    s=torch.as_tensor(np.asarray(sigma,np.float64),dtype=torch.float64).reshape(-1,1).clamp_min(.08)
    qs=torch.arange(-8,9,dtype=torch.float64).reshape(1,-1);rt2=math.sqrt(2.)
    def cdf_edge(edge): return 0.5*(1.0+torch.erf((edge-mu)/(s*rt2)))
    central=cdf_edge(qs+.5)-cdf_edge(qs-.5)
    neg=cdf_edge(torch.tensor(-8.5,dtype=torch.float64))
    pos=1.0-cdf_edge(torch.tensor(8.5,dtype=torch.float64))
    P=torch.cat([central,neg,pos],1);P=P/torch.clamp(P.sum(1,keepdim=True),min=1e-300)
    return P.numpy()


def entropy_bits(P):
    P=np.asarray(P,np.float64);return -(P*np.log2(np.maximum(P,1e-300))).sum(1)


def best_zero_gaussian(P):
    G=gaussian_pmfs_zero(SIGMA_GRID);LG=-np.log2(np.maximum(G,1e-300))
    best_sigma=[];best_ce=[]
    for s in range(0,len(P),4096):
        Q=P[s:s+4096];CE=Q@LG.T;j=np.argmin(CE,1);best_sigma.append(SIGMA_GRID[j]);best_ce.append(CE[np.arange(len(Q)),j])
    return np.concatenate(best_sigma),np.concatenate(best_ce)


def sparse_sigma_equation(S,sigma,pos):
    from sklearn.preprocessing import PolynomialFeatures,StandardScaler
    from sklearn.linear_model import OrthogonalMatchingPursuit, Ridge
    S=np.asarray(S,np.float64);sigma=np.asarray(sigma,np.float64);pos=np.asarray(pos)
    tr=pos<DISTILL_POSITIONS;te=~tr
    poly=PolynomialFeatures(degree=2,include_bias=False)
    D=poly.fit_transform(S);names=np.asarray(poly.get_feature_names_out(hd.FEATURE_NAMES))
    sc=StandardScaler();Z=sc.fit_transform(D[tr]);Zall=sc.transform(D)
    y=np.log(np.maximum(sigma,.08))
    omp=OrthogonalMatchingPursuit(n_nonzero_coefs=SPARSE_TERMS,fit_intercept=True)
    omp.fit(Z,y[tr]);sel=np.flatnonzero(np.abs(omp.coef_)>1e-12)
    # Refit selected terms with small ridge for numerical stability.
    rr=Ridge(alpha=1e-4);rr.fit(Z[:,sel],y[tr]);pred=rr.predict(Zall[:,sel]);sp=np.exp(pred)
    def r2(mask):
        yy=y[mask];pp=pred[mask];return float(1.-np.sum((yy-pp)**2)/max(np.sum((yy-yy.mean())**2),1e-12))
    terms=[]
    # Coefficients are in standardized polynomial coordinates; still explicit
    # and the scaler metadata below makes the equation exactly reproducible.
    for j,c in zip(sel,rr.coef_):terms.append({'term':str(names[j]),'standardized_coef':float(c),'raw_term_mean':float(sc.mean_[j]),'raw_term_scale':float(sc.scale_[j])})
    return sp,{'target':'log(sigma)','form':'exp(intercept + sparse standardized quadratic terms)','intercept':float(rr.intercept_),'selected_term_count':int(len(sel)),'terms':terms,'train_log_sigma_r2':r2(tr),'heldout_last4_log_sigma_r2':r2(te)}


def main(a):
    import torch
    q.b.build=scale.build_with_scale_yxt;fr.CHUNK=512;bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in tuple(s for s in q.SURVEYS if s!=TARGET):
        for frac in base.SOURCE_FRACS:
            X,ep,_=q.b.extract(ds,m,e,frac);source.append((q.crop(X),ep));print('GD_SOURCE',ds,frac,flush=True)
    net,mu,sd,static=fr.fit_base(source,20261919);state,u1,u2=fr.new_adapter(99100);reservoir=[]
    # Causally adapt teacher through first 12 positions only.
    raw=[]
    for pi,frac in enumerate(TARGET_FRACS):
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);raw.append((X,ep,md))
        if pi<DISTILL_POSITIONS:
            if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
            meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode'),'shape':list(map(int,X.shape))}
            fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0)
            print('GD_ADAPTED',pi,flush=True)
    # Freeze one common teacher state. Distillation uses positions 0..11;
    # positions 12..15 are untouched by both neural adaptation and equation fit.
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    PP=[];SS=[];YY=[];POS=[]
    reprq=np.concatenate([np.arange(-8,9,dtype=np.float64),np.array([-9.,9.])])
    for pi,(X,ep,md) in enumerate(raw):
        A,T,I,R=q.b.build(X,ep);A=np.asarray(A,np.float32);sem=A[:,-len(hd.FEATURE_NAMES):].copy();An=(A-mu)/sd;Y=q.b.cls(T)
        n=min(CAP_PER_POSITION,len(An));ii=np.linspace(0,len(An)-1,n,dtype=np.int64)
        with torch.no_grad():P=torch.softmax(net(torch.from_numpy(An[ii])),1).cpu().numpy().astype(np.float64)
        PP.append(P);SS.append(sem[ii]);YY.append(Y[ii]);POS.append(np.full(n,pi,np.int16));print('GD_POOL',pi,n,flush=True)
    P=np.concatenate(PP);S=np.concatenate(SS);Y=np.concatenate(YY);pos=np.concatenate(POS);H=entropy_bits(P)
    sigma_best,ce_best=best_zero_gaussian(P)
    # Moment-matched shifted Gaussian to diagnose whether centering/sign is the
    # main deviation from a pure scale family.
    mu_m=P@reprq;second=P@(reprq*reprq);sig_m=np.sqrt(np.maximum(second-mu_m*mu_m,.08**2));Gshift=gaussian_pmfs_shifted(mu_m,sig_m);ce_shift=-(P*np.log2(np.maximum(Gshift,1e-300))).sum(1)
    sigma_law,eq=sparse_sigma_equation(S,sigma_best,pos);Glaw=gaussian_pmfs_zero(sigma_law);ce_law=-(P*np.log2(np.maximum(Glaw,1e-300))).sum(1)
    # Actual residual-class costs on sampled contexts.
    idx=np.arange(len(Y));neural_true=-np.log2(np.maximum(P[idx,Y],1e-300));best_true=-np.log2(np.maximum(gaussian_pmfs_zero(sigma_best)[idx,Y],1e-300));law_true=-np.log2(np.maximum(Glaw[idx,Y],1e-300));shift_true=-np.log2(np.maximum(Gshift[idx,Y],1e-300))
    def stats(mask):
        return {
          'samples':int(mask.sum()),'neural_mean_entropy_bits':float(H[mask].mean()),
          'best_zero_gaussian_KL_bits_to_neural':float((ce_best[mask]-H[mask]).mean()),
          'moment_shifted_gaussian_KL_bits_to_neural':float((ce_shift[mask]-H[mask]).mean()),
          'sparse_sigma_law_KL_bits_to_neural':float((ce_law[mask]-H[mask]).mean()),
          'true_class_neural_bps':float(neural_true[mask].mean()),
          'true_class_best_zero_gaussian_bps':float(best_true[mask].mean()),
          'true_class_shifted_gaussian_bps':float(shift_true[mask].mean()),
          'true_class_sparse_sigma_law_bps':float(law_true[mask].mean()),
          'sparse_law_true_class_penalty_vs_neural_bps':float((law_true[mask]-neural_true[mask]).mean()),
          'best_zero_gaussian_true_class_penalty_vs_neural_bps':float((best_true[mask]-neural_true[mask]).mean()),
        }
    tr=pos<DISTILL_POSITIONS;te=~tr
    out={'kind':'kahu-head-gaussian-distill-v1','status':'teacher_distillation_diagnostic_not_serialized_codec','teacher':'PR735 model causally adapted through Kahu positions 0..11 then frozen','distillation_positions':list(range(DISTILL_POSITIONS)),'heldout_positions':list(range(DISTILL_POSITIONS,len(TARGET_FRACS))),'heldout_positions_used_in_teacher_adaptation_or_equation_fit':False,'gaussian_family':'19-class discretized Gaussian: q=-8..8 half-integer bins plus two outer tails','sparse_sigma_equation':eq,'train_stats':stats(tr),'heldout_last4_stats':stats(te),'overall_stats':stats(np.ones(len(pos),bool)),'sigma_summary':{'train_median':float(np.median(sigma_best[tr])),'heldout_median':float(np.median(sigma_best[te])),'heldout_p10':float(np.quantile(sigma_best[te],.1)),'heldout_p90':float(np.quantile(sigma_best[te],.9))},'note':'If best-zero-Gaussian KL is small, the 19-way neural head is largely a one-dimensional scale family. The sparse-law penalty measures the additional difficulty of replacing the neural scale estimator by an explicit equation. Tail gamma costs, boundaries and serialized entropy-coder overhead are outside this diagnostic.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('GAUSSIAN_DISTILL_FINAL',json.dumps(out,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
