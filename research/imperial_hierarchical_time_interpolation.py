import json,sys
import h5py,numpy as np
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_decoder_phase_automaton as m

C=128;NT=8192;STEP=267;TB=1024
SPECS=(('easy',2304),('medium',4608))
STRIDES=(8,16,32,64,128)

def schedule(stride):
 anchors=list(range(0,NT,stride))
 if anchors[-1]!=NT-1:anchors.append(NT-1)
 ops=[];prev=None
 for t in anchors:
  ops.append((t,-1 if prev is None else prev,-1));prev=t
 intervals=[(anchors[i],anchors[i+1]) for i in range(len(anchors)-1)]
 while intervals:
  new=[]
  for l,r in intervals:
   if r-l<=1:continue
   q=(l+r)//2;ops.append((q,l,r));new.append((l,q));new.append((q,r))
  intervals=new
 if len(ops)!=NT or len({x[0] for x in ops})!=NT:raise RuntimeError(('schedule',stride,len(ops)))
 return ops

def encode_source(X,ops):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for t,l,r in ops:
  if r<0:
   p=np.zeros(C,np.int32) if l<0 else R[:,l]
  else:
   p=np.rint((R[:,l].astype(np.float64)+R[:,r].astype(np.float64))*0.5).astype(np.int32)
  k=np.rint((X[:,t].astype(np.float64)-p.astype(np.float64))/STEP).astype(np.int32);K[:,t]=k;R[:,t]=p+STEP*k
 return R,K

def decode_source(K,ops):
 R=np.zeros(K.shape,np.int32)
 for t,l,r in ops:
  if r<0:p=np.zeros(C,np.int32) if l<0 else R[:,l]
  else:p=np.rint((R[:,l].astype(np.float64)+R[:,r].astype(np.float64))*0.5).astype(np.int32)
  R[:,t]=p+STEP*K[:,t]
 return R

def reorder(K,ops):
 order=np.asarray([x[0] for x in ops],np.int32);return K[:,order],order

def undo(A,order):
 K=np.empty_like(A);K[:,order]=A;return K

def main(path):
 h.C=C;h.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=m.stats(d);eps=.1*gs;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,ar=h.fits(XF);R0,K0=h.run_ar(XF,ar);base,_,_,D0=h.arithmetic(K0)
   if not np.array_equal(h.decode_source(D0,ar),R0):raise RuntimeError('base decode')
   sz=sum(int(m.szrun(XF[:,t:t+TB],eps)[0]) for t in range(0,NT,TB));screen=[];keep={}
   for s in STRIDES:
    ops=schedule(s);R,K=encode_source(X,ops);me=float(np.max(np.abs(XF-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,s,'hard',me,eps))
    KS,order=reorder(K,ops);n,reps=h.backend_bytes(KS);n=n-h.MODEL_BYTES+32;z={'stride':s,'backend_bytes':int(n),'backend_bps':8*n/X.size,'gain_backend_vs_step267':None,'gain_backend_vs_sz3':sz/n,'k_std':float(KS.std()),'k_zero':float(np.mean(KS==0)),'maxerr':me,'reps':reps};screen.append(z);keep[s]=(ops,R,K,KS,order);print(json.dumps({'region':region,**{k:v for k,v in z.items() if k!='reps'}},indent=2),flush=True)
   b=min(screen,key=lambda z:z['backend_bytes']);ops,R,K,KS,order=keep[b['stride']];an,bits,nb,SD=h.arithmetic(KS);an=an-h.MODEL_BYTES+32;K2=undo(SD,order);Rd=decode_source(K2,ops);me=float(np.max(np.abs(XF-Rd.astype(np.float64))))
   if not np.array_equal(SD,KS) or not np.array_equal(K2,K) or not np.array_equal(Rd,R) or me>eps*(1+1e-12):raise RuntimeError((region,'decode',me,eps))
   best={'stride':b['stride'],'bytes':int(an),'bps':8*an/X.size,'gain_vs_step267':base/an,'gain_vs_sz3':sz/an,'ratio_to_2x_sz3_target':an/(sz/2),'arithmetic_bits':int(bits),'symbol_bits':int(nb),'maxerr':me};rows.append({'region':region,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'screen':screen});print(json.dumps({'summary':region,'best':best},indent=2),flush=True)
  json.dump({'eps':eps,'strides':list(STRIDES),'rows':rows,'scope':'Executable source-coordinate hierarchical temporal interpolation. Sparse anchors are decoded first using previous-anchor prediction; every interval is then recursively bisected and each midpoint is predicted from its two already-decoded endpoint reconstructions. Exact 267-step correction symbols guarantee <=133.5 error at every decoded sample. Symbols are reordered in the actual coarse-to-fine decode schedule and exactly coded/decoded; no future source value is free side information. Huber AR32 arithmetic and matched SZ3 are rerun on identical easy/medium regions.'},open('imperial_hierarchical_time_interpolation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
