import json,math,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h
import imperial_ar32_openloop_2d_hadamard_innovations as b

C=128;NT=4096;P=32;TB=1024;REGIONS=(('easy',2304),('medium',4608));CONFIGS=((4,4),(8,4))
CAND=np.asarray([48,64,80,96,112,128,144,160,176,192,208,224,240,256,266,280,296,320,352,384,416,448,512,576,640,768],np.int32)

def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def run(X,co,bt,gs,steps,collect=False):
 Hs=b.hadamard(gs);Ht=b.hadamard(bt);S=np.asarray(steps,np.int32).reshape(gs,bt);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);ys=[[] for _ in range(gs*bt)] if collect else None
 for t0 in range(0,NT,bt):
  pred=b.forecast_block(R,co,t0,bt);E=X[:,t0:t0+bt].astype(np.int64)-pred.astype(np.int64)
  for c0 in range(0,C,gs):
   Y=Hs@E[c0:c0+gs]@Ht.T;Q=np.rint(Y.astype(np.float64)/S.astype(np.float64)).astype(np.int32);Yh=Q.astype(np.int64)*S.astype(np.int64);Er=np.rint((Hs@Yh@Ht.T).astype(np.float64)/(gs*bt)).astype(np.int32)
   K[c0:c0+gs,t0:t0+bt]=Q;R[c0:c0+gs,t0:t0+bt]=pred[c0:c0+gs]+Er
   if collect:
    for i,v in enumerate(Y.ravel()):ys[i].append(int(v))
 return R,K,ys

def decode(K,co,bt,gs,steps):
 Hs=b.hadamard(gs);Ht=b.hadamard(bt);S=np.asarray(steps,np.int32).reshape(gs,bt);R=np.zeros(K.shape,np.int32)
 for t0 in range(0,NT,bt):
  pred=b.forecast_block(R,co,t0,bt)
  for c0 in range(0,C,gs):
   Yh=K[c0:c0+gs,t0:t0+bt].astype(np.int64)*S.astype(np.int64);Er=np.rint((Hs@Yh@Ht.T).astype(np.float64)/(gs*bt)).astype(np.int32);R[c0:c0+gs,t0:t0+bt]=pred[c0:c0+gs]+Er
 return R

@njit(cache=True)
def alloc_dp(cost,steps,budget):
 n,m=cost.shape;inf=1e300;dp=np.full((n+1,budget+1),inf);pb=np.full((n+1,budget+1),-1,np.int32);pj=np.full((n+1,budget+1),-1,np.int16);dp[0,0]=0.
 for i in range(n):
  for z in range(budget+1):
   if dp[i,z]>=inf/2:continue
   for j in range(m):
    q=z+steps[j]
    if q<=budget:
     v=dp[i,z]+cost[i,j]
     if v<dp[i+1,q]:dp[i+1,q]=v;pb[i+1,q]=z;pj[i+1,q]=j
 z=0;best=inf
 for q in range(budget+1):
  if dp[n,q]<best:best=dp[n,q];z=q
 out=np.empty(n,np.int32)
 for i in range(n,0,-1):j=pj[i,z];out[i-1]=steps[j];z=pb[i,z]
 return out,best

def allocate(ys,bt,gs,eps):
 n=bt*gs;cost=np.empty((n,len(CAND)),np.float64)
 for i,z in enumerate(ys):
  z=np.asarray(z,np.float64)
  for j,s in enumerate(CAND):cost[i,j]=h0(np.rint(z/float(s)).astype(np.int32))
 budget=int(math.floor(2*n*(float(eps)-0.5)-1e-12));steps,pred=alloc_dp(cost,CAND,budget);return steps.reshape(gs,bt),budget,float(pred)

def encode_variant(X,co,bt,gs,steps,eps,label):
 R,K,_=run(X,co,bt,gs,steps,False);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError((label,'hard',me,eps))
 KS,ro,coo=b.reorder_2d(K,bt,gs);ab,nbit,nb,KSD=h.arithmetic(KS);Kd=b.undo_2d(KSD,ro,coo);Rd=decode(Kd,co,bt,gs,steps);dme=float(np.max(np.abs(X.astype(np.float64)-Rd.astype(np.float64))))
 if not np.array_equal(KSD,KS) or not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((label,'decode',dme,eps))
 model=2*bt*gs+24;return {'label':label,'bt':bt,'gs':gs,'steps':[int(x) for x in np.asarray(steps).ravel()],'step_sum':int(np.sum(steps)),'min_step':int(np.min(steps)),'max_step':int(np.max(steps)),'mean_step':float(np.mean(steps)),'bytes':int(ab)+model,'bps':8*(int(ab)+model)/X.size,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'h0_bps':h0(K),'model_bytes':model,'maxerr':dme}

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=1024;b.C=C;b.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,coef=h.fits(XF);R0,K0=h.run_ar(XF,coef);base,_,_,D0=h.arithmetic(K0);RR=h.decode_source(D0,coef);me0=float(np.max(np.abs(XF-RR.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard'))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(q)
   vv=[]
   for bt,gs in CONFIGS:
    uni=np.full((gs,bt),266,np.int32);Ru,Ku,ys=run(X,coef,bt,gs,uni,True);ume=float(np.max(np.abs(XF-Ru.astype(np.float64))))
    if ume>eps*(1+1e-12):raise RuntimeError((region,bt,gs,'uniform hard'))
    steps,budget,pred=allocate(ys,bt,gs,eps);a=encode_variant(X,coef,bt,gs,steps,eps,'allocated');a.update({'budget':budget,'predicted_sum_h0':pred,'gain_vs_step267':base/a['bytes'],'gain_vs_sz3':sz/a['bytes'],'ratio_to_2x_target':a['bytes']/(sz/2)})
    u=encode_variant(X,coef,bt,gs,uni,eps,'uniform');u.update({'budget':budget,'gain_vs_step267':base/u['bytes'],'gain_vs_sz3':sz/u['bytes'],'ratio_to_2x_target':u['bytes']/(sz/2)})
    best=min((a,u),key=lambda z:z['bytes']);vv.append({'bt':bt,'gs':gs,'uniform':u,'allocated':a,'best':best});print(json.dumps({'region':region,'config':[bt,gs],'best':best},indent=2),flush=True)
   best=min((x['best'] for x in vv),key=lambda z:z['bytes']);rows.append({'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'variants':vv});print(json.dumps({'summary':rows[-1]},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'configs':[list(x) for x in CONFIGS],'rows':rows,'scope':'Fast constructive pilot for hard-error-constrained 2-D Hadamard subband allocation after decoder-real short-block open-loop Huber AR32 forecasting. Only easy and medium 128x4096 regions are used to decide whether the direction merits a full-array gate. For each 4x4 or 4-channel x8-time transform tile, the fixed-step266 reconstruction is first executed and its actual transform coefficients collected. A dynamic program chooses one quantizer step per 2-D subband from a fixed candidate set to minimize summed empirical scalar entropy under the exact L-infinity budget sum(step_j)<=floor(2*N*(epsilon-0.5)), where N=gs*bt; this guarantees pre-rounding source error <=sum(step)/(2N) and final integer rounding remains below epsilon. The complete step vector is explicitly transmitted/charged, transform symbols are exactly decoded using the incumbent arithmetic backend in deterministic 2-D subband-major order, and the full recursive source is regenerated and hard-error checked. Uniform-step, closed-loop step267 AR32 and matched SZ3 controls are rerun. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_openloop_2d_hadamard_allocation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
