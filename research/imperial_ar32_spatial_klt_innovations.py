import json,math,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_decoder_phase_automaton as m

SPECS=(('easy',2304),('medium',4608))
C=128;NT=8192;TRAIN=1024;TB=1024;GROUPS=(8,16)

def baseline_residual(X,co):
 R,K=h.run_ar(X.astype(np.float64),co);P=R.astype(np.float64)-267.0*K.astype(np.float64);return R,K,X.astype(np.float64)-P

def canon(U):
 U=np.asarray(U,np.float64).copy()
 for j in range(U.shape[1]):
  i=int(np.argmax(np.abs(U[:,j])))
  if U[i,j]<0:U[:,j]*=-1
 return U

def eigbasis(A):
 S=A@A.T/max(1,A.shape[1]);w,U=np.linalg.eigh(S);U=U[:,np.argsort(w)[::-1]];return canon(U)

def make_bases(E,g,mode,eps):
 ng=C//g;bases=[];steps=[]
 if mode=='shared':
  S=np.zeros((g,g),np.float64)
  for q in range(ng):
   A=E[q*g:(q+1)*g,:TRAIN];S+=A@A.T
  w,U=np.linalg.eigh(S);U=canon(U[:,np.argsort(w)[::-1]])
  raw=np.asarray(U,'<f8').tobytes();Ud=np.frombuffer(raw,'<f8').reshape(g,g).copy()
  for q in range(ng):bases.append(Ud)
  model=len(raw)
 else:
  model=0
  for q in range(ng):
   U=eigbasis(E[q*g:(q+1)*g,:TRAIN]);raw=np.asarray(U,'<f8').tobytes();U=np.frombuffer(raw,'<f8').reshape(g,g).copy();bases.append(U);model+=len(raw)
 for U in bases:
  l=float(np.max(np.sum(np.abs(U),axis=1)));d=max(1,int(math.floor(2.0*(eps-1.0)/l)));steps.append(d)
 model+=2*ng+32
 return bases,np.asarray(steps,np.int32),model

def run(X,co,g,bases,steps):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32);ng=C//g
 for t in range(NT):
  pred=np.zeros(C,np.int32)
  if t>=h.P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-h.P:t][::-1].astype(np.float32)))))
  e=X[:,t].astype(np.float64)-pred.astype(np.float64)
  for q in range(ng):
   c0=q*g;U=bases[q];d=float(steps[q]);y=U.T@e[c0:c0+g];z=np.rint(y/d).astype(np.int32);er=np.rint(U@(z.astype(np.float64)*d)).astype(np.int32);K[c0:c0+g,t]=z;R[c0:c0+g,t]=pred[c0:c0+g]+er
 return R,K

def decode(K,co,g,bases,steps):
 R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32);ng=C//g
 for t in range(K.shape[1]):
  pred=np.zeros(C,np.int32)
  if t>=h.P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-h.P:t][::-1].astype(np.float32)))))
  for q in range(ng):
   c0=q*g;U=bases[q];d=float(steps[q]);er=np.rint(U@(K[c0:c0+g,t].astype(np.float64)*d)).astype(np.int32);R[c0:c0+g,t]=pred[c0:c0+g]+er
 return R

def reorder(K,g):
 ng=C//g;rows=np.asarray([q*g+s for s in range(g) for q in range(ng)],np.int32);return K[rows],rows

def undo(A,rows):
 K=np.empty_like(A);K[rows]=A;return K

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,co=h.fits(XF);R0,K0,E=baseline_residual(X,co);base,_,_,D0=h.arithmetic(K0)
   if not np.array_equal(h.decode_source(D0,co),R0):raise RuntimeError('base decode')
   sz=sum(int(m.szrun(XF[:,t:t+TB],eps)[0]) for t in range(0,NT,TB));cand=[]
   for g in GROUPS:
    for mode in ('shared','per_group'):
     B,S,model=make_bases(E,g,mode,eps);R,K=run(X,co,g,B,S);me=float(np.max(np.abs(XF-R.astype(np.float64))))
     if me>eps*(1+1e-12):raise RuntimeError((region,g,mode,'hard',me,eps,S.tolist()))
     an,_,_,Kd=h.arithmetic(K);Rd=decode(Kd,co,g,B,S)
     if not np.array_equal(Kd,K) or not np.array_equal(Rd,R):raise RuntimeError((region,g,mode,'decode'))
     KS,ordr=reorder(K,g);sb,_,_,SD=h.arithmetic(KS);K2=undo(SD,ordr);R2=decode(K2,co,g,B,S)
     if not np.array_equal(K2,K) or not np.array_equal(R2,R):raise RuntimeError((region,g,mode,'subdecode'))
     n=min(int(an),int(sb))+model;z={'g':g,'basis':mode,'bytes':n,'bps':8*n/X.size,'model_bytes':model,'mean_step':float(S.mean()),'min_step':int(S.min()),'max_step':int(S.max()),'gain267':base/n,'gain_sz3':sz/n,'maxerr':me};cand.append(z);print(json.dumps({'region':region,**z}),flush=True)
   best=min(cand,key=lambda z:z['bytes']);rows.append({'region':region,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'candidates':cand})
  json.dump({'eps':eps,'groups':list(GROUPS),'rows':rows},open('imperial_ar32_spatial_klt_innovations.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
