#!/usr/bin/env python3
"""Dissect the trained Kahu residual-probability MLP head into interpretable laws.

This is an interpretability experiment, not a new codec result.  It reproduces
the PR #735 source-trained model (15 non-Kahu source tiles, 320/240/160 MLP,
12 causal scale/roughness summaries + y/x/t) and analyzes the *actual linear
19-class output head* before and after causal Kahu replay.

We extract four semantic directions from the head:
  zero    : q=0 logit versus the mean nonzero logit
  sign    : positive-residual logits versus negative-residual logits
  tail    : overflow logits versus in-range logits
  magnitude: least-squares slope of head weights against residual magnitude

For charged Kahu states we then:
  * rank last-hidden neurons by each semantic head direction;
  * correlate those neurons with the 12 explicit causal scale/roughness features
    and y/x/t;
  * intervene on each interpretable feature across empirical quantiles while
    holding the rest of each real seismic context fixed;
  * fit small linear/quadratic surrogate equations from the 15 interpretable
    variables to the neural head's zero-margin, expected-|q|, sign-margin and
    tail-margin outputs.

No future current-trace samples, Kahu training/normalization or side information
is introduced.  The purpose is to read out what the neural head has learned so
that a later deterministic codec can attempt to compile it into explicit rules.
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

TARGET='marine_kahu_3d'
TARGET_FRACS=tuple(float(x) for x in np.linspace(.04,.96,16))
FEATURE_NAMES=(
    'current_wave_meanabs','current_wave_rms',
    'left_wave_rms','left2_wave_rms','up_wave_rms','upleft_wave_rms',
    'left_resid_meanabs','left2_resid_meanabs','up_resid_meanabs','upleft_resid_meanabs',
    'current_resid_meanabs','current_resid_rms',
    'y_coord','x_coord','time_coord',
)
ANALYSIS_CAP_PER_POSITION=4096
SURROGATE_TRAIN_POSITIONS=12
RIDGE=1e-4


def _semantic_head(net):
    W=net.head.weight.detach().cpu().numpy().astype(np.float64)
    b=net.head.bias.detach().cpu().numpy().astype(np.float64)
    z=q.b.LIM
    center=np.arange(0,2*z+1)
    zero=z
    neg=np.arange(0,z)
    pos=np.arange(z+1,2*z+1)
    tails=np.array([2*z+1,2*z+2])
    nonzero=np.array([i for i in range(q.b.NCLASS) if i!=zero])
    magnitude=np.concatenate([np.abs(np.arange(-z,z+1)),np.array([z+1,z+1])]).astype(np.float64)
    mag0=magnitude-magnitude.mean();den=float((mag0**2).sum())
    dirs={
        'zero':W[zero]-W[nonzero].mean(0),
        'sign':W[pos].mean(0)-W[neg].mean(0),
        'tail':W[tails].mean(0)-W[center].mean(0),
        'magnitude':(mag0[:,None]*W).sum(0)/den,
    }
    biases={
        'zero':float(b[zero]-b[nonzero].mean()),
        'sign':float(b[pos].mean()-b[neg].mean()),
        'tail':float(b[tails].mean()-b[center].mean()),
        'magnitude':float((mag0*b).sum()/den),
    }
    top={k:[{'unit':int(i),'loading':float(v[i])} for i in np.argsort(-np.abs(v))[:16]] for k,v in dirs.items()}
    return W,b,dirs,biases,top


def _outputs(logits):
    import torch
    P=torch.softmax(logits,1).detach().cpu().numpy().astype(np.float64)
    L=logits.detach().cpu().numpy().astype(np.float64)
    z=q.b.LIM
    mags=np.concatenate([np.abs(np.arange(-z,z+1)),np.array([z+1,z+1])]).astype(np.float64)
    pos=np.arange(z+1,2*z+1);neg=np.arange(0,z);tails=np.array([2*z+1,2*z+2]);center=np.arange(0,2*z+1)
    def lse(a,axis=1):
        m=np.max(a,axis=axis,keepdims=True);return (m+np.log(np.exp(a-m).sum(axis=axis,keepdims=True))).squeeze(axis)
    zero_margin=L[:,z]-lse(np.delete(L,z,axis=1),1)
    sign_margin=lse(L[:,pos],1)-lse(L[:,neg],1)
    tail_margin=lse(L[:,tails],1)-lse(L[:,center],1)
    exp_abs=P@mags
    entropy=-(P*np.log2(np.maximum(P,1e-12))).sum(1)
    return np.stack([zero_margin,exp_abs,sign_margin,tail_margin,entropy],1)


def _r2(y,p):
    y=np.asarray(y);p=np.asarray(p);ss=float(((y-p)**2).sum());tot=float(((y-y.mean(0))**2).sum());return 1.0-ss/max(tot,1e-12)


def _fit_surrogate(X,Y,trainmask):
    # Interpretable low-order model: constant + 15 main effects + squares.
    X=np.asarray(X,np.float64);Y=np.asarray(Y,np.float64);tr=np.asarray(trainmask,bool)
    mu=X[tr].mean(0);sd=X[tr].std(0);sd[sd<1e-8]=1.;Z=(X-mu)/sd
    D=np.concatenate([np.ones((len(Z),1)),Z,Z*Z],1)
    Dt=D[tr];Yt=Y[tr]
    A=Dt.T@Dt+RIDGE*np.eye(Dt.shape[1]);A[0,0]-=RIDGE
    B=np.linalg.solve(A,Dt.T@Yt);P=D@B
    names=['intercept']+list(FEATURE_NAMES)+[f'{n}^2' for n in FEATURE_NAMES]
    coef=[]
    for oi,oname in enumerate(('zero_margin','expected_abs_q','sign_margin','tail_margin','entropy_bits')):
        order=np.argsort(-np.abs(B[1:,oi]))[:12]+1
        coef.append({'output':oname,'train_r2':_r2(Y[tr,oi],P[tr,oi]),'heldout_last4_r2':_r2(Y[~tr,oi],P[~tr,oi]),
                     'top_terms':[{'term':names[int(j)],'coef':float(B[j,oi])} for j in order]})
    return {'model':'ridge quadratic: intercept + 15 main effects + 15 squares','train_positions':SURROGATE_TRAIN_POSITIONS,
            'test_positions':len(TARGET_FRACS)-SURROGATE_TRAIN_POSITIONS,'fits':coef}


def _correlations(H,S,dirs):
    H=np.asarray(H,np.float64);S=np.asarray(S,np.float64)
    Hc=H-H.mean(0);Sc=S-S.mean(0);hs=np.sqrt((Hc*Hc).sum(0));ss=np.sqrt((Sc*Sc).sum(0));den=hs[:,None]*ss[None,:]
    C=(Hc.T@Sc)/np.maximum(den,1e-12)
    out={}
    for key,v in dirs.items():
        units=np.argsort(-np.abs(v))[:16];rows=[]
        for u in units[:10]:
            f=int(np.argmax(np.abs(C[u])));rows.append({'unit':int(u),'head_loading':float(v[u]),'best_feature':FEATURE_NAMES[f],'pearson_r':float(C[u,f])})
        out[key]=rows
    return out


def _interventions(net,Xnorm,Sraw,mu,sd):
    import torch
    X=np.asarray(Xnorm,np.float32);S=np.asarray(Sraw,np.float32)
    cap=min(4096,len(X));ii=np.linspace(0,len(X)-1,cap,dtype=np.int64);B=X[ii].copy();Sb=S[ii]
    res={}
    # interpretable variables occupy the last 15 network inputs by construction.
    start=X.shape[1]-len(FEATURE_NAMES)
    with torch.no_grad():
        baseout=_outputs(net(torch.from_numpy(B))).mean(0)
        for j,n in enumerate(FEATURE_NAMES):
            qs=np.quantile(Sb[:,j],[.1,.3,.5,.7,.9]);curve=[]
            for val in qs:
                C=B.copy();C[:,start+j]=(float(val)-float(mu[start+j]))/float(sd[start+j])
                o=_outputs(net(torch.from_numpy(C))).mean(0)
                curve.append({'feature_value':float(val),'zero_margin':float(o[0]),'expected_abs_q':float(o[1]),'sign_margin':float(o[2]),'tail_margin':float(o[3]),'entropy_bits':float(o[4])})
            res[n]={'curve':curve,'delta_low_to_high':{k:float(curve[-1][k]-curve[0][k]) for k in ('zero_margin','expected_abs_q','sign_margin','tail_margin','entropy_bits')}}
    return {'baseline_mean':{'zero_margin':float(baseout[0]),'expected_abs_q':float(baseout[1]),'sign_margin':float(baseout[2]),'tail_margin':float(baseout[3]),'entropy_bits':float(baseout[4])},'features':res}


def main(a):
    import torch
    q.b.build=scale.build_with_scale_yxt;fr.CHUNK=512;bw.install(base);fr._orig_fit=base.wide_fit
    m=json.load(open(a.manifest));e=json.load(open(a.eps));source=[]
    for ds in tuple(s for s in q.SURVEYS if s!=TARGET):
        for frac in base.SOURCE_FRACS:
            X,ep,_=q.b.extract(ds,m,e,frac);source.append((q.crop(X),ep));print('HEAD_SOURCE',ds,frac,flush=True)
    net,mu,sd,static=fr.fit_base(source,20261919)
    W0,b0,dirs0,bias0,top0=_semantic_head(net)
    state,u1,u2=fr.new_adapter(99100);reservoir=[]
    H=[];S=[];O=[];P=[];position_rows=[];Xpool=[];Spool=[]
    for pi,frac in enumerate(TARGET_FRACS):
        X,ep,md=q.b.extract(TARGET,m,e,frac);X=q.crop(X);A,T,I,R=q.b.build(X,ep);A=np.asarray(A,np.float32);sem=A[:,-len(FEATURE_NAMES):].copy();An=(A-mu)/sd
        n=min(ANALYSIS_CAP_PER_POSITION,len(An));ii=np.linspace(0,len(An)-1,n,dtype=np.int64);xx=torch.from_numpy(An[ii])
        net.eval()
        with torch.no_grad():
            h=net.latent(xx).cpu().numpy();logits=net.head(torch.from_numpy(h));out=_outputs(logits)
        H.append(h);S.append(sem[ii]);O.append(out);P.append(np.full(n,pi,np.int16));Xpool.append(An[ii]);Spool.append(sem[ii])
        position_rows.append({'position':pi,'fraction':float(frac),'samples_analyzed':n,'mean_zero_margin':float(out[:,0].mean()),'mean_expected_abs_q':float(out[:,1].mean()),'mean_entropy_bits':float(out[:,4].mean())})
        meta={'dataset':TARGET,'position':pi,'fraction':float(frac),'trace_first':md.get('trace_first'),'geometry_mode':md.get('geometry_mode'),'shape':list(map(int,X.shape))}
        if pi>0:fr.replay_adapter(net,state,u1,u2,reservoir)
        fr.score_and_adapt(net,mu,sd,static,X,ep,meta,state,u1,u2,reservoir,pi==0)
        print('HEAD_POSITION',pi,position_rows[-1],flush=True)
    H=np.concatenate(H);S=np.concatenate(S);O=np.concatenate(O);P=np.concatenate(P);Xpool=np.concatenate(Xpool);Spool=np.concatenate(Spool)
    W1,b1,dirs1,bias1,top1=_semantic_head(net)
    trainmask=P<SURROGATE_TRAIN_POSITIONS
    head_change={k:{'cosine_base_to_adapted':float(np.dot(dirs0[k],dirs1[k])/(np.linalg.norm(dirs0[k])*np.linalg.norm(dirs1[k])+1e-12)),'relative_l2_change':float(np.linalg.norm(dirs1[k]-dirs0[k])/(np.linalg.norm(dirs0[k])+1e-12))} for k in dirs0}
    # Intervention uses final causally-adapted model on real contexts accumulated across Kahu.
    intervention=_interventions(net,Xpool,Spool,mu,sd)
    out={
      'kind':'kahu-probability-head-dissection-v1','status':'interpretability_diagnostic_not_codec',
      'model':'same 15-source, 320/240/160, 19-class residual probability MLP as PR735',
      'heldout_kahu_used_in_source_training_or_normalization':False,'kahu_adaptation_only_after_charged_decoding':True,
      'feature_names':list(FEATURE_NAMES),'semantic_head_definitions':{
        'zero':'q=0 head row minus mean of all nonzero rows','sign':'mean positive in-range rows minus mean negative in-range rows',
        'tail':'mean overflow rows minus mean in-range rows','magnitude':'least-squares slope of each hidden-unit head weight against class |q|'},
      'base_head_top_units':top0,'adapted_head_top_units':top1,'head_direction_change_after_kahu':head_change,
      'adapted_head_unit_feature_correlations':_correlations(H,S,dirs1),
      'quadratic_surrogate_from_15_interpretable_features':_fit_surrogate(S,O,trainmask),
      'causal_feature_interventions_on_adapted_model':intervention,'position_summary':position_rows,
      'note':'Directly dissects the final linear probability head and then intervenes on the 15 explicit decoder-known variables. Correlations are descriptive; intervention curves are the stronger causal readout. A later gate must turn any stable law into a deterministic coder and measure actual bytes.'}
    Path(a.out).write_text(json.dumps(out,indent=2));print('HEAD_DISSECTION_FINAL',json.dumps({k:v for k,v in out.items() if k not in ('base_head_top_units','adapted_head_top_units','adapted_head_unit_feature_correlations','causal_feature_interventions_on_adapted_model')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
