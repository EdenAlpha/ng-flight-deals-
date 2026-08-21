#!/usr/bin/env python3
from __future__ import annotations
import json,math,sys
import h5py,numpy as np,torch
import torch.nn as nn
import torch.nn.functional as F
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
CURRENT_BYTES=22382;STEP=267;MAXK=128;NCLASS=2*MAXK+2;TAIL=NCLASS-1;SEED=20260821
WARMS=(128,256,512);HIDDENS=(128,256);EPOCHS=100
KOFF=((1,0),(2,0),(4,0),(8,0),(16,0),(0,-1),(0,-2),(0,-4),(1,-1),(1,1),(2,-1),(2,1),(4,-1),(4,1),(8,-1),(8,1))
ROFF=((1,0),(2,0),(4,0),(8,0),(16,0),(0,-1),(0,-2),(1,-1),(1,1),(2,-1),(2,1))
class Net(nn.Module):
 def __init__(self,nin,h):super().__init__();self.net=nn.Sequential(nn.Linear(nin,h),nn.GELU(),nn.Linear(h,h),nn.GELU(),nn.Linear(h,NCLASS))
 def forward(self,x):return self.net(x)
def oval(A,c,t,dt,dc):
 tt=t-dt;cc=c+dc
 if tt<0 or cc<0 or cc>=A.shape[0] or (dt==0 and dc>=0):return 0.0
 return float(A[cc,tt])
def make_data(K,R,cod,offs):
 xs=[];ys=[];ts=[]
 for t in range(16,K.shape[1]):
  for c in range(K.shape[0]):
   z=[]
   for dt,dc in KOFF:z.append(oval(K,c,t,dt,dc)/16.0)
   for dt,dc in ROFF:z.append((oval(R,c,t,dt,dc)-oval(R,c,t,1,0))/STEP)
   p=u.sample_pred(R,c,t,cod,offs);z.extend([float(p%STEP)/STEP,float(c)/(K.shape[0]-1),float(t)/K.shape[1],abs(oval(K,c,t,1,0))/16.0])
   k=int(K[c,t]);y=k+MAXK if -MAXK<=k<=MAXK else TAIL;xs.append(z);ys.append(y);ts.append(t)
 return np.asarray(xs,np.float32),np.asarray(ys,np.int64),np.asarray(ts,np.int32)
def tail_extra_bits(K,mask):
 vals=np.abs(K[mask]).astype(np.int64)-MAXK
 vals=np.maximum(vals,1);return 1.0+2.0*np.floor(np.log2(vals)).astype(np.float64)
def empirical_cross_bits(train_y,test_y):
 cnt=np.bincount(train_y,minlength=NCLASS).astype(np.float64)+0.5;p=cnt/cnt.sum();return float((-np.log2(p[test_y])).mean())
def eval_cfg(Xf,Y,T,Kflat,warm,h,szb):
 tr=T<warm;te=T>=warm;mu=Xf[tr].mean(0);sd=Xf[tr].std(0);sd=np.where(sd>1e-4,sd,1.0);A=((Xf-mu)/sd).astype(np.float32)
 torch.manual_seed(SEED+warm+h);model=Net(A.shape[1],h);opt=torch.optim.AdamW(model.parameters(),lr=2e-3,weight_decay=1e-4)
 xt=torch.from_numpy(A[tr]);yt=torch.from_numpy(Y[tr]);model.train()
 for ep in range(EPOCHS):
  opt.zero_grad();loss=F.cross_entropy(model(xt),yt);loss.backward();opt.step()
 with torch.no_grad():
  logits=model(torch.from_numpy(A[te]));lp=F.log_softmax(logits,dim=1)/math.log(2.0);yb=torch.from_numpy(Y[te]);bits=(-lp[torch.arange(len(yb)),yb]).cpu().numpy().astype(np.float64)
 testK=Kflat[te];tail=(Y[te]==TAIL)
 if tail.any():bits[tail]+=tail_extra_bits(testK,tail)
 test_bps=float(bits.mean());base_bps=8.0*CURRENT_BYTES/Kflat.size;warm_frac=float(np.sum(T<warm)/len(T));projected=warm_frac*base_bps+(1-warm_frac)*test_bps;target_bps=8.0*(szb/2.0)/Kflat.size
 return {'warm_t':warm,'hidden':h,'train_samples':int(tr.sum()),'test_samples':int(te.sum()),'train_tail_fraction':float(np.mean(Y[tr]==TAIL)),'test_tail_fraction':float(np.mean(tail)),'test_bps':test_bps,'empirical_trainhist_test_bps':empirical_cross_bits(Y[tr],Y[te]),'projected_full_bps_with_warmup_at_current_rate':projected,'target_2x_bps':target_bps,'ceiling_crosses_2x':bool(projected<=target_bps)}
def main(path):
 torch.set_num_threads(2)
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);offs,co,sbest,_=u.search_sample(X);_,R,K,mb,ob,cod=sbest;Xf,Y,T=make_data(K,R,cod,offs);Kflat=[]
 for t in range(16,K.shape[1]):
  for c in range(K.shape[0]):Kflat.append(int(K[c,t]))
 Kflat=np.asarray(Kflat,np.int32);rows=[]
 for w in WARMS:
  for h in HIDDENS:
   r=eval_cfg(Xf,Y,T,Kflat,w,h,szb);rows.append(r);print('ROW',json.dumps(r),flush=True)
 rows.sort(key=lambda r:r['projected_full_bps_with_warmup_at_current_rate']);best=rows[0];scalar=float(-(lambda p: np.sum(p*np.log2(p)))(np.unique(Kflat,return_counts=True)[1]/Kflat.size))
 out={'kind':'imperial-heldout-conditional-entropy-v20','shape':list(X.shape),'eps':eps,'step':STEP,'current_bytes':CURRENT_BYTES,'current_bps':8*CURRENT_BYTES/K.size,'sz3_bytes':int(szb),'strict_2x_target_bytes':szb/2.0,'strict_2x_target_bps':8*(szb/2.0)/K.size,'scalar_k_entropy_bps':scalar,'best':best,'rows':rows,'scope':'HELD-OUT CONDITIONAL-ENTROPY CEILING, not a codec claim. The current exact SZ-style K field is fixed. A probability MLP trains only on earlier time samples and predicts later unseen K symbols from decoder-known causal K/R history, predictor phase, and coordinates. No later labels enter training. Model bytes and arithmetic-coder overhead are intentionally free in this diagnostic; warmup samples are conservatively charged at the current actual bps. If projected bps cannot approach the 2x target even here, the remaining Imperial field is close to an information-floor problem for this representation. If it can, nonlinear causal structure remains exploitable.'}
 json.dump(out,open('imperial_heldout_conditional_entropy_v20.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
