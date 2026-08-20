#!/usr/bin/env python3
from __future__ import annotations
import io,json,math,struct,sys
import h5py,numpy as np,torch
import torch.nn as nn
import universal_rate_searched_predictor_v1 as u
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

FINAL_STEP=u.STEP
BASE_BYTES=22390
CONFIGS=((2,4),(2,8),(3,4),(3,8),(4,4),(4,8))
EPOCHS=120
PATCH=256
SEED=20260820

class TinyRefiner(nn.Module):
    def __init__(self,h):
        super().__init__();self.c1=nn.Conv2d(5,h,3,padding=1);self.c2=nn.Conv2d(h,h,3,padding=1);self.c3=nn.Conv2d(h,1,3,padding=1)
    def forward(self,x):
        z=torch.tanh(self.c1(x));z=torch.tanh(self.c2(z));return 0.5*torch.tanh(self.c3(z))

def build_step(X,co,offs,step,Kgiven=None):
    R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
    for t in range(X.shape[1]):
        for c in range(X.shape[0]):
            p=u.sample_pred(R,c,t,co,offs);k=int(Kgiven[c,t]) if Kgiven is not None else int(np.rint((float(X[c,t])-p)/step));K[c,t]=k;R[c,t]=p+step*k
    return R,K

def features(R):
    A=R.astype(np.float32);mu=float(A.mean());sd=max(float(A.std()),1.0);x=(A-mu)/sd
    dt=np.zeros_like(x);dt[:,1:]=A[:,1:]-A[:,:-1];dt/=sd
    dc=np.zeros_like(x);dc[1:,:]=A[1:,:]-A[:-1,:];dc/=sd
    cc=np.linspace(-1,1,A.shape[0],dtype=np.float32)[:,None]*np.ones((1,A.shape[1]),np.float32)
    tt=np.ones((A.shape[0],1),np.float32)*np.linspace(-1,1,A.shape[1],dtype=np.float32)[None,:]
    F=np.stack([x,dt,dc,cc,tt],axis=0)[None]
    return F,mu,sd

def pack_model(model,h,mu,sd):
    parts=[struct.pack('<Bff',h,np.float32(mu),np.float32(sd))]
    shapes=[]
    for p in model.parameters():
        a=p.detach().cpu().numpy().astype('<f2');shapes.append(a.shape);parts.append(a.tobytes())
    blob=b''.join(parts)
    return blob,shapes

def unpack_model(blob,h,shapes):
    hh,mu,sd=struct.unpack_from('<Bff',blob,0);assert hh==h;off=9;model=TinyRefiner(h)
    with torch.no_grad():
        for p,shape in zip(model.parameters(),shapes):
            n=int(np.prod(shape));a=np.frombuffer(blob,dtype='<f2',count=n,offset=off).astype(np.float32).reshape(shape).copy();off+=2*n;p.copy_(torch.from_numpy(a))
    assert off==len(blob);model.eval();return model,float(mu),float(sd)

def feature_with_norm(R,mu,sd):
    A=R.astype(np.float32);x=(A-mu)/sd;dt=np.zeros_like(x);dt[:,1:]=A[:,1:]-A[:,:-1];dt/=sd;dc=np.zeros_like(x);dc[1:,:]=A[1:,:]-A[:-1,:];dc/=sd
    cc=np.linspace(-1,1,A.shape[0],dtype=np.float32)[:,None]*np.ones((1,A.shape[1]),np.float32);tt=np.ones((A.shape[0],1),np.float32)*np.linspace(-1,1,A.shape[1],dtype=np.float32)[None,:]
    return np.stack([x,dt,dc,cc,tt],axis=0)[None]

def train_refiner(X,R1,step1,h):
    torch.manual_seed(SEED+h+step1);np.random.seed(SEED+h+step1)
    F,mu,sd=features(R1);Y=((X.astype(np.float32)-R1.astype(np.float32))/float(step1))[None,None]
    model=TinyRefiner(h);opt=torch.optim.Adam(model.parameters(),lr=0.015,weight_decay=1e-5);lossfn=nn.MSELoss()
    FT=torch.from_numpy(F);YT=torch.from_numpy(Y);nt=X.shape[1]
    model.train()
    for ep in range(EPOCHS):
        t0=(ep*137)%(max(1,nt-PATCH+1));xb=FT[:,:,:,t0:t0+PATCH];yb=YT[:,:,:,t0:t0+PATCH]
        opt.zero_grad();pred=model(xb);loss=lossfn(pred,yb);loss.backward();opt.step()
        if ep%30==0:print('TRAIN',step1,h,ep,float(loss.detach()),flush=True)
    blob,shapes=pack_model(model,h,mu,sd);dec,mu2,sd2=unpack_model(blob,h,shapes)
    with torch.no_grad():pred=dec(torch.from_numpy(feature_with_norm(R1,mu2,sd2))).numpy()[0,0]
    corr=np.rint(pred*float(step1)).astype(np.int32)
    return blob,shapes,corr,float(np.mean((X-R1-corr)**2))

def final_correct(X,R1,corr,Kgiven=None):
    P=R1.astype(np.int64)+corr.astype(np.int64)
    K=np.asarray(Kgiven,np.int32) if Kgiven is not None else np.rint((X-P)/FINAL_STEP).astype(np.int32)
    R=(P+FINAL_STEP*K.astype(np.int64)).astype(np.int32);return R,K

def main(path):
    torch.set_num_threads(2)
    with h5py.File(path,'r') as f:
        ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
    szb,ori=m.szrun(X,eps);offs,co,sbest,shist=u.search_sample(X);_,_,_,mb,ob,cod=sbest
    rows=[]
    for factor,h in CONFIGS:
        step1=FINAL_STEP*factor;R1,K1=build_step(X,cod,offs,step1);b1,K1d,d1=u.exact_field(K1);R1d,K1x=build_step(X,cod,offs,step1,Kgiven=K1d)
        if not np.array_equal(K1x,K1) or not np.array_equal(R1d,R1):raise RuntimeError('coarse replay')
        blob,shapes,corr,mse=train_refiner(X,R1d,step1,h);R2,K2=final_correct(X,R1d,corr);b2,K2d,d2=u.exact_field(K2);R2d,K2x=final_correct(X,R1d,corr,Kgiven=K2d)
        if not np.array_equal(K2x,K2) or not np.array_equal(R2d,R2):raise RuntimeError('final replay')
        me=float(np.max(np.abs(X-R2d.astype(np.float64))))
        if me>eps*(1+5e-6):raise RuntimeError(('hard',factor,h,me,eps))
        # fixed header + base predictor metadata + coarse factor byte + model blob + both exact K streams
        total=fair.COMMON_HEADER+1+len(ob)+len(mb)+1+len(blob)+b1+b2
        row={'factor':factor,'hidden':h,'bytes':int(total),'coarse_field_bytes':int(b1),'final_field_bytes':int(b2),'model_bytes':len(blob),'model_mse':mse,'final_k_zero_fraction':float(np.mean(K2==0)),'maxerr':me,'gain_vs_sz3':float(szb/total),'gain_vs_base':float(BASE_BYTES/total)}
        rows.append(row);print('ROW',json.dumps(row),flush=True)
    rows.sort(key=lambda r:r['bytes']);best=rows[0]
    out={'kind':'universal-coarse-neural-refinement-v11','shape':list(X.shape),'eps':eps,'final_step':FINAL_STEP,'base_offsets':[list(x) for x in offs],'base_bytes':BASE_BYTES,'sz3_bytes':int(szb),'sz3_orientation':ori,'best':best,'rows':rows,'principle':'First encode a deliberately coarser error-bounded-style reconstruction. Train a tiny per-block convolutional residual model from that reconstruction to the original, serialize the compact float16 model, then encode a second correction lattice at the original strict step so final max error is unchanged. This tests whether learned residual structure can buy enough coarse-stage savings to pay for model+correction overhead.'}
    json.dump(out,open('universal_coarse_neural_refinement_v11.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
