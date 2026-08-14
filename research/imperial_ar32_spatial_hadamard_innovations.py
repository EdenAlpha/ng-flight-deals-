import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;QSTEP=266;TB=1024;GROUPS=(2,4,8,16)

def hadamard(n):
 H=np.array([[1]],np.int32)
 while H.shape[0]<n:H=np.block([[H,H],[H,-H]])
 return H

def quant_round(y):return np.rint(np.asarray(y,np.float64)/QSTEP).astype(np.int32)

def run_transform(X,co,g):
 H=hadamard(g);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(NT):
  pred=np.zeros(C,np.int32)
  if t>=P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
  e=np.asarray(X[:,t],np.int32)-pred
  for c0 in range(0,C,g):
   y=H@e[c0:c0+g];k=quant_round(y);yh=QSTEP*k;er=np.rint((H@yh).astype(np.float64)/g).astype(np.int32)
   K[c0:c0+g,t]=k;R[c0:c0+g,t]=pred[c0:c0+g]+er
 return R,K

def decode_transform(K,co,g):
 H=hadamard(g);R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(K.shape[1]):
  pred=np.zeros(C,np.int32)
  if t>=P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
  for c0 in range(0,C,g):
   yh=QSTEP*K[c0:c0+g,t].astype(np.int32);er=np.rint((H@yh).astype(np.float64)/g).astype(np.int32);R[c0:c0+g,t]=pred[c0:c0+g]+er
 return R

def subband_major(K,g):
 # Reorder transformed coordinates so arithmetic 'left' context sees same Hadamard subband across neighboring groups.
 ng=C//g;out=np.empty_like(K);j=0
 for s in range(g):
  for q in range(ng):out[j]=K[q*g+s];j+=1
 return out

def undo_subband_major(A,g):
 ng=C//g;K=np.empty_like(A);j=0
 for s in range(g):
  for q in range(ng):K[q*g+s]=A[j];j+=1
 return K

def h0(K):
 _,n=np.unique(np.asarray(K).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,co=h.fits(XF)
   # Incumbent exact step267 Huber AR32 + arithmetic on identical samples.
   R0,K0=h.run_ar(XF,co);base,nbit0,nb0,Kd0=h.arithmetic(K0);Rd0=h.decode_source(Kd0,co);me0=float(np.max(np.abs(XF-Rd0.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',me0,eps))
   sz=0
   for t0 in range(0,NT,TB):bb,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(bb)
   variants=[]
   for g in GROUPS:
    R,K=run_transform(X,co,g);me=float(np.max(np.abs(XF-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,g,'encoder hard',me,eps))
    # Natural transformed-coordinate order.
    ab,nbit,nb,Kd=h.arithmetic(K);Rd=decode_transform(Kd,co,g);dme=float(np.max(np.abs(XF-Rd.astype(np.float64))))
    if not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((region,g,'natural decode',dme,eps))
    nat={'order':'natural','bytes':int(ab)+8,'bps':8*(int(ab)+8)/X.size,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'h0_bps':h0(K),'maxerr':dme}
    # Subband-major stream order; mapping is deterministic and costs no model bytes beyond explicit framing.
    KS=subband_major(K,g);sb,nbit2,nb2,KSD=h.arithmetic(KS);K2=undo_subband_major(KSD,g);R2=decode_transform(K2,co,g);dme2=float(np.max(np.abs(XF-R2.astype(np.float64))))
    if not np.array_equal(KSD,KS) or not np.array_equal(K2,K) or not np.array_equal(R2,R) or dme2>eps*(1+1e-12):raise RuntimeError((region,g,'subband decode',dme2,eps))
    sub={'order':'subband_major','bytes':int(sb)+8,'bps':8*(int(sb)+8)/X.size,'arithmetic_bits':int(nbit2),'symbol_bits':int(nb2),'h0_bps':h0(KS),'maxerr':dme2}
    best=min((nat,sub),key=lambda z:z['bytes']);best=dict(best);best.update({'group':g,'qstep':QSTEP,'gain_vs_step267':base/best['bytes'],'gain_vs_sz3':sz/best['bytes'],'ratio_to_2x_sz3_target':best['bytes']/(sz/2)})
    variants.append({'group':g,'natural':nat,'subband_major':sub,'best':best});print(json.dumps({'region':region,'variant':best},indent=2),flush=True)
   best=min((v['best'] for v in variants),key=lambda z:z['bytes'])
   row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_bytes':int(base),'step267_bps':8*base/X.size,'step267_arithmetic_bits':int(nbit0),'step267_symbol_bits':int(nb0),'step267_maxerr':me0,'best':best,'variants':variants};rows.append(row)
   print(json.dumps({'summary':{'region':region,'step267_bps':row['step267_bps'],'sz3_bps':row['sz3_bps'],'best':best}},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'qstep':QSTEP,'groups':list(GROUPS),'rows':rows,'scope':'Executable decoder-real spatial Hadamard transform of Huber AR32 innovations. At each time t all 128 temporal AR32 predictions are computed solely from already reconstructed same-channel history. The current 128-dimensional source residual vector is then split into contiguous power-of-two channel groups, transformed with an unnormalized integer Hadamard matrix H, each transform coefficient is uniformly quantized with step266, and the residual vector is reconstructed by round(H*yhat/g). Since every coefficient quantization error is <=133 and each inverse Hadamard row has g entries of magnitude 1/g, pre-rounding source residual error is <=133; final integer rounding adds at most 0.5, giving a deterministic <=133.5 bound below epsilon~133.698. The decoded residual vector becomes the exact future AR state. Group sizes 2/4/8/16 are tested with both natural transformed-coordinate ordering and a deterministic subband-major reordering designed to make the incumbent left-neighbor arithmetic context compare like subbands. The same cold-start contextual arithmetic engine exactly decodes all transform symbols, the full recursive source trajectory is regenerated and hard-error checked, framing is charged, and exact step267 AR32 plus matched SZ3 are rerun on identical hard/easy/medium/far regions. This differs from earlier raw-signal DCT/Hadamard tests: decorrelation is applied only to decoder-real innovations after the strongest temporal predictor. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_spatial_hadamard_innovations.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
