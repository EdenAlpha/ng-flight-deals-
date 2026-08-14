import json,sys
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;QSTEP=266;TB=1024
CONFIGS=((4,4),(8,4),(8,8),(16,8))

def hadamard(n):
 H=np.array([[1]],np.int64)
 while H.shape[0]<n:H=np.block([[H,H],[H,-H]])
 return H

def forecast_block(R,co,t0,bt):
 a=float(co[0]);b=np.asarray(co[1:],np.float32);PRED=np.zeros((C,bt),np.int32)
 for c in range(C):
  for j in range(bt):
   t=t0+j
   if t<P:p=0
   else:
    if t0>=P:
     pre=R[c,t-P:t0].astype(np.int32)
     if j:hist=np.concatenate((pre,PRED[c,:j]))[-P:]
     else:hist=pre[-P:]
    else:
     # With bt<=16 and P=32, any block beginning before P contains only t<P.
     raise RuntimeError(('unexpected warmup geometry',t0,t))
    p=int(np.rint(a+float(np.dot(b,hist[::-1].astype(np.float32)))))
   PRED[c,j]=p
 return PRED

def run_codec(X,co,bt,gs):
 Hs=hadamard(gs);Ht=hadamard(bt);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 for t0 in range(0,NT,bt):
  pred=forecast_block(R,co,t0,bt);E=X[:,t0:t0+bt].astype(np.int64)-pred.astype(np.int64)
  for c0 in range(0,C,gs):
   Y=Hs@E[c0:c0+gs]@Ht.T;Q=np.rint(Y.astype(np.float64)/QSTEP).astype(np.int32);Yh=Q.astype(np.int64)*QSTEP
   Er=np.rint((Hs@Yh@Ht.T).astype(np.float64)/(gs*bt)).astype(np.int32)
   K[c0:c0+gs,t0:t0+bt]=Q;R[c0:c0+gs,t0:t0+bt]=pred[c0:c0+gs]+Er
 return R,K

def decode_codec(K,co,bt,gs):
 Hs=hadamard(gs);Ht=hadamard(bt);R=np.zeros(K.shape,np.int32)
 for t0 in range(0,K.shape[1],bt):
  pred=forecast_block(R,co,t0,bt)
  for c0 in range(0,C,gs):
   Yh=K[c0:c0+gs,t0:t0+bt].astype(np.int64)*QSTEP;Er=np.rint((Hs@Yh@Ht.T).astype(np.float64)/(gs*bt)).astype(np.int32)
   R[c0:c0+gs,t0:t0+bt]=pred[c0:c0+gs]+Er
 return R

def reorder_2d(K,bt,gs):
 ng=C//gs;nb=NT//bt
 rows=np.asarray([q*gs+s for s in range(gs) for q in range(ng)],np.int32)
 cols=np.asarray([b*bt+j for j in range(bt) for b in range(nb)],np.int32)
 return K[rows][:,cols],rows,cols

def undo_2d(A,rows,cols):
 K=np.empty_like(A);tmp=np.empty_like(A);tmp[rows]=A;K[:,cols]=tmp;return K

def h0(K):
 _,n=np.unique(np.asarray(K).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,co=h.fits(XF)
   R0,K0=h.run_ar(XF,co);base,n0,nb0,Kd0=h.arithmetic(K0);Rd0=h.decode_source(Kd0,co);me0=float(np.max(np.abs(XF-Rd0.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'baseline hard',me0,eps))
   sz=0
   for t0 in range(0,NT,TB):bb,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(bb)
   variants=[]
   for bt,gs in CONFIGS:
    R,K=run_codec(X,co,bt,gs);me=float(np.max(np.abs(XF-R.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,bt,gs,'encoder hard',me,eps))
    # Natural coefficient-grid stream.
    an,bn,nbn,Kdn=h.arithmetic(K);Rdn=decode_codec(Kdn,co,bt,gs);men=float(np.max(np.abs(XF-Rdn.astype(np.float64))))
    if not np.array_equal(Kdn,K) or not np.array_equal(Rdn,R) or men>eps*(1+1e-12):raise RuntimeError((region,bt,gs,'natural decode',men,eps))
    nat={'order':'natural','bytes':int(an)+16,'bps':8*(int(an)+16)/X.size,'arithmetic_bits':int(bn),'symbol_bits':int(nbn),'h0_bps':h0(K),'maxerr':men}
    # Spatial+temporal subband-major stream: identical subbands become contiguous for online contexts.
    KS,rord,cord=reorder_2d(K,bt,gs);asb,bsb,nbsb,KSD=h.arithmetic(KS);K2=undo_2d(KSD,rord,cord);R2=decode_codec(K2,co,bt,gs);mes=float(np.max(np.abs(XF-R2.astype(np.float64))))
    if not np.array_equal(KSD,KS) or not np.array_equal(K2,K) or not np.array_equal(R2,R) or mes>eps*(1+1e-12):raise RuntimeError((region,bt,gs,'subband decode',mes,eps))
    sub={'order':'subband_major_2d','bytes':int(asb)+16,'bps':8*(int(asb)+16)/X.size,'arithmetic_bits':int(bsb),'symbol_bits':int(nbsb),'h0_bps':h0(KS),'maxerr':mes}
    best=min((nat,sub),key=lambda z:z['bytes']);best=dict(best);best.update({'bt':bt,'gs':gs,'qstep':QSTEP,'gain_vs_step267':base/best['bytes'],'gain_vs_sz3':sz/best['bytes'],'ratio_to_2x_sz3_target':best['bytes']/(sz/2)})
    variants.append({'bt':bt,'gs':gs,'natural':nat,'subband':sub,'best':best});print(json.dumps({'region':region,'variant':best},indent=2),flush=True)
   best=min((v['best'] for v in variants),key=lambda z:z['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_bytes':int(base),'step267_bps':8*base/X.size,'step267_maxerr':me0,'best':best,'variants':variants};rows.append(row)
   print(json.dumps({'summary':{'region':region,'step267_bps':row['step267_bps'],'sz3_bps':row['sz3_bps'],'best':best}},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'qstep':QSTEP,'configs':[list(x) for x in CONFIGS],'rows':rows,'scope':'Executable short-block open-loop Huber-AR32 plus 2-D Hadamard innovation codec. At each time-block boundary, the decoder has the exact prior reconstructed state. It forecasts the next bt=4/8/16 samples recursively using only that state and its own forecasts, never current unknown corrections. The complete source-minus-forecast innovation block is therefore decoder-coordinate-known once transform symbols arrive. Each gs x bt innovation tile (gs=4/8 channels) is transformed by unnormalized spatial and temporal Hadamards, coefficients are quantized with step266, and inverse reconstruction is round(Hs*Yhat*Ht^T/(gs*bt)). Every transform coefficient error is <=133; each inverse 2-D Hadamard row has absolute weights summing to one, so pre-rounding sample error is <=133 and final integer rounding adds <=0.5, giving <=133.5 below epsilon~133.698 regardless of forecast error. The decoded block becomes the exact state for the next forecast block. Natural and deterministic 2-D subband-major coefficient layouts are both exactly arithmetic-decoded; the entire recursive source is regenerated and hard-error checked. Exact closed-loop step267 Huber AR32 and matched SZ3 are rerun on identical hard/easy/medium/far regions. This is a true block-vector representation after prediction, not a raw-signal transform and not an entropy oracle. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_openloop_2d_hadamard_innovations.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
