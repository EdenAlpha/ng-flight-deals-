#!/usr/bin/env python3
"""Fixed zero-bit trace-time regime heads on the unseen-Kahu y/x/t leader.

The current Kahu leader shows strong nonstationarity along trace time. This
experiment keeps the successful y/x/t structural coordinates and the entire
predictor/residual/boundary/replay stack, but replaces the single final 19-class
interior output layer with four equal-width deterministic trace-time heads.

Regime boundaries are fixed a priori at normalized trace-time quartiles
[0,.25,.50,.75,1], not tuned on Kahu. The decoder knows t and nt, so routing
costs zero transmitted bits. A shared 320/240/160 trunk is retained; only the
final class head is regime-specific. Kahu remains absent from source fitting and
normalization. Every target chunk is charged before adaptation. Diagnostic ideal
probability rate only; not yet a serialized codec claim.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import migrated_volume_multisource15_replay_loso_v1 as base
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_quick_adapter_loso_v1 as q
import kahu_unseen_longstream_fast_boundary_wave_v1 as k
import kahu_unseen_yxt_coordinate_v1 as yxt

REFERENCE_512=1.9023606738716896
REFERENCE_TIME=1.9255376298482818
REFERENCE_YXT=1.9321423201209738
QUARTILES=(0.25,0.50,0.75)


def quartile_fit(train_tiles,seed):
    AA=[];TT=[];RR=[]
    for X,eps in train_tiles:
        A,T,_,R=q.b.build(q.crop(X),eps);AA.append(A);TT.append(T);RR.append(R.reshape(-1))
    A=np.concatenate(AA);T=np.concatenate(TT);fullR=np.concatenate(RR)
    A,T=q.deterministic_subsample(A,T,base.MAX_TRAIN)
    mu=A.mean(0);sd=A.std(0);sd[sd<.1]=1.;A=(A-mu)/sd;Y=q.b.cls(T)
    sh=np.bincount(q.b.cls(fullR),minlength=q.b.NCLASS).astype(np.float64)+1.;sh/=sh.sum();static=-np.log2(sh)
    h1,h2,h3=base.HIDDEN
    # y/x/t build appends normalized t as the final feature. Convert fixed raw
    # tau quartiles into normalized-feature thresholds used by the network.
    tau_mu=float(mu[-1]);tau_sd=float(sd[-1]);cuts=torch.tensor([(z-tau_mu)/tau_sd for z in QUARTILES],dtype=torch.float32)
    class M(nn.Module):
        def __init__(self,d):
            super().__init__();self.trunk=nn.Sequential(nn.Linear(d,h1),nn.SiLU(),nn.LayerNorm(h1),nn.Linear(h1,h2),nn.SiLU(),nn.Linear(h2,h3),nn.SiLU());self.heads=nn.ModuleList([nn.Linear(h3,q.b.NCLASS) for _ in range(4)]);self.register_buffer('tau_cuts',cuts.clone())
        def latent(self,x):return self.trunk(x)
        def forward(self,x):
            z=self.latent(x);reg=torch.bucketize(x[:,-1].contiguous(),self.tau_cuts)
            out=torch.empty((len(x),q.b.NCLASS),dtype=z.dtype,device=z.device)
            for r,h in enumerate(self.heads):
                m=(reg==r)
                if torch.any(m):out[m]=h(z[m])
            return out
    torch.manual_seed(seed);np.random.seed(seed);torch.set_num_threads(min(8,torch.get_num_threads()))
    net=M(A.shape[1]);opt=torch.optim.AdamW(net.parameters(),lr=1.5e-3,weight_decay=3e-4);Xt=torch.from_numpy(A);Yt=torch.from_numpy(Y);idx=torch.arange(len(Xt));bs=8192
    for ep in range(base.EPOCHS):
        net.train();perm=idx[torch.randperm(len(idx))];tot=0.
        for i in range(0,len(perm),bs):
            j=perm[i:i+bs];loss=F.cross_entropy(net(Xt[j]),Yt[j]);opt.zero_grad();loss.backward();opt.step();tot+=float(loss.detach())*len(j)
        print('KAHU_QUARTILE_FIT',seed,ep,tot/len(Xt),flush=True)
    net.eval()
    for p in net.parameters():p.requires_grad_(False)
    print('KAHU_QUARTILE_PARAMS',sum(p.numel() for p in net.parameters()),'tau_mu',tau_mu,'tau_sd',tau_sd,'normalized_cuts',cuts.tolist(),flush=True)
    return net,mu,sd,static


def main(a):
    # Install the exact positive y/x/t feature map first. Boundary waveform
    # features use only R from q.b.build and are otherwise unchanged.
    q.b.build=yxt.build_with_yxt
    base.wide_fit=quartile_fit
    fr.CHUNK=512
    k.main(a)
    out=json.load(open(a.out));out['kind']='unseen-kahu-yxt-quartile-heads-v1';out['main_feature_change']='y/x/t coordinates plus four fixed equal trace-time output heads sharing one 320/240/160 trunk';out['time_regime_boundaries_normalized_trace_time']=list(QUARTILES);out['regime_selector_transmitted_bits']=0;out['regime_boundaries_tuned_on_kahu']=False;out['reference_512_gain_vs_sz3']=REFERENCE_512;out['reference_time_gain_vs_sz3']=REFERENCE_TIME;out['reference_yxt_gain_vs_sz3']=REFERENCE_YXT;out['gain_ratio_vs_yxt']=float(out['full_replay_weighted_gain_vs_sz3']/REFERENCE_YXT);out['note']='Fixed quartile routing is decoder-known and survey-independent. Predictor, quantizer, boundary waveform model, source surveys, replay and 512-symbol post-charge adaptation remain frozen. Ideal probability rate only.'
    Path(a.out).write_text(json.dumps(out,indent=2));print('KAHU_QUARTILE_FINAL',json.dumps({x:y for x,y in out.items() if x not in ('base_rows','adapt_rows','source_meta')},indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
