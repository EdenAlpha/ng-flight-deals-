import json,sys,math
import h5py,numpy as np
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;TB=1024
GROUPS=(8,16)
STEP_CAND=np.asarray([48,64,80,96,112,128,144,160,176,192,208,224,240,256,266,280,296,320,352,384,416,448,512,576,640,768],np.int32)
UNIFORM=266


def hadamard(n):
 H=np.array([[1]],np.int64)
 while H.shape[0]<n:H=np.block([[H,H],[H,-H]])
 return H


def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())


def max_budget(g,eps):
 # inverse error <= sum(step_s)/(2g) before final integer rounding; reserve 0.5 for that rounding.
 return int(math.floor(2.0*g*(float(eps)-0.5)-1e-12))


def run_codec(X,co,g,steps,collect_y=False):
 H=hadamard(g);steps=np.asarray(steps,np.int32);R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 Ystore=np.empty(X.shape,np.int64) if collect_y else None
 a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(NT):
  pred=np.zeros(C,np.int32)
  if t>=P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
  e=X[:,t].astype(np.int64)-pred.astype(np.int64)
  for c0 in range(0,C,g):
   y=H@e[c0:c0+g];q=np.rint(y.astype(np.float64)/steps.astype(np.float64)).astype(np.int32);yh=q.astype(np.int64)*steps.astype(np.int64)
   er=np.rint((H@yh).astype(np.float64)/g).astype(np.int32);K[c0:c0+g,t]=q;R[c0:c0+g,t]=pred[c0:c0+g]+er
   if collect_y:Ystore[c0:c0+g,t]=y
 return R,K,Ystore


def decode_codec(K,co,g,steps):
 H=hadamard(g);steps=np.asarray(steps,np.int32);R=np.zeros(K.shape,np.int32);a=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(K.shape[1]):
  pred=np.zeros(C,np.int32)
  if t>=P:
   for c in range(C):pred[c]=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
  for c0 in range(0,C,g):
   yh=K[c0:c0+g,t].astype(np.int64)*steps.astype(np.int64);er=np.rint((H@yh).astype(np.float64)/g).astype(np.int32);R[c0:c0+g,t]=pred[c0:c0+g]+er
 return R


def subband_major(K,g):
 ng=C//g;rows=np.asarray([q*g+s for s in range(g) for q in range(ng)],np.int32);return K[rows],rows

def undo_rows(A,rows):
 K=np.empty_like(A);K[rows]=A;return K


def entropy_table(Y,g):
 # All samples from the same Hadamard coordinate share a candidate step.
 out=np.empty((g,len(STEP_CAND)),np.float64)
 for s in range(g):
  z=Y[s::g].ravel().astype(np.float64)
  for j,d in enumerate(STEP_CAND):out[s,j]=h0(np.rint(z/float(d)).astype(np.int32))
 return out


def allocate(Y,g,eps):
 B=max_budget(g,eps);Htab=entropy_table(Y,g);inf=1e300
 dp=np.full((g+1,B+1),inf,np.float64);prevb=np.full((g+1,B+1),-1,np.int32);prevj=np.full((g+1,B+1),-1,np.int16);dp[0,0]=0.0
 for s in range(g):
  reachable=np.flatnonzero(np.isfinite(dp[s]))
  for b0 in reachable:
   v0=dp[s,b0]
   for j,d in enumerate(STEP_CAND):
    b1=int(b0+d)
    if b1>B:
     continue
    v=v0+Htab[s,j]
    if v<dp[s+1,b1]:dp[s+1,b1]=v;prevb[s+1,b1]=b0;prevj[s+1,b1]=j
 b=int(np.argmin(dp[g]));steps=np.empty(g,np.int32)
 for s in range(g,0,-1):
  j=int(prevj[s,b])
  if j<0:raise RuntimeError(('allocation failure',g,B,b))
  steps[s-1]=int(STEP_CAND[j]);b=int(prevb[s,b])
 return steps,{'budget':B,'used':int(steps.sum()),'predicted_sum_h0':float(np.min(dp[g])),'subband_h0_table_best_unconstrained':[float(Htab[s].min()) for s in range(g)]}


def evaluate(X,co,g,steps,eps,label):
 B=max_budget(g,eps)
 if int(np.sum(steps))>B:raise RuntimeError((label,'budget',int(np.sum(steps)),B))
 R,K,Y=run_codec(X,co,g,steps,collect_y=True);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError((label,'encoder hard',me,eps))
 # Test natural and subband-major coefficient layouts with exact arithmetic decode.
 an,bn,nbn,Kdn=h.arithmetic(K);Rdn=decode_codec(Kdn,co,g,steps);men=float(np.max(np.abs(X.astype(np.float64)-Rdn.astype(np.float64))))
 if not np.array_equal(Kdn,K) or not np.array_equal(Rdn,R) or men>eps*(1+1e-12):raise RuntimeError((label,'natural decode',men,eps))
 KS,rows=subband_major(K,g);asb,bsb,nbsb,KSD=h.arithmetic(KS);K2=undo_rows(KSD,rows);R2=decode_codec(K2,co,g,steps);mes=float(np.max(np.abs(X.astype(np.float64)-R2.astype(np.float64))))
 if not np.array_equal(KSD,KS) or not np.array_equal(K2,K) or not np.array_equal(R2,R) or mes>eps*(1+1e-12):raise RuntimeError((label,'subband decode',mes,eps))
 model=2*g+24
 nat={'order':'natural','bytes':int(an)+model,'bps':8*(int(an)+model)/X.size,'arithmetic_bits':int(bn),'symbol_bits':int(nbn),'maxerr':men}
 sub={'order':'subband_major','bytes':int(asb)+model,'bps':8*(int(asb)+model)/X.size,'arithmetic_bits':int(bsb),'symbol_bits':int(nbsb),'maxerr':mes}
 best=min((nat,sub),key=lambda z:z['bytes']);best=dict(best);best.update({'label':label,'g':g,'steps':[int(x) for x in steps],'step_sum':int(np.sum(steps)),'budget':B,'mean_step':float(np.mean(steps)),'min_step':int(np.min(steps)),'max_step':int(np.max(steps)),'model_bytes':model,'symbol_h0_bps':h0(K)})
 return best,Y


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
   for g in GROUPS:
    uni=np.full(g,UNIFORM,np.int32)
    ub,Y=evaluate(X,co,g,uni,eps,f'g{g}_uniform')
    # Two source-trained redesign rounds. The selected step vector is explicitly transmitted, so design on target data is legal.
    s1,diag1=allocate(Y,g,eps);b1,Y1=evaluate(X,co,g,s1,eps,f'g{g}_alloc1');b1['allocation_diag']=diag1
    s2,diag2=allocate(Y1,g,eps);b2,Y2=evaluate(X,co,g,s2,eps,f'g{g}_alloc2');b2['allocation_diag']=diag2
    for z in (ub,b1,b2):z.update({'gain_vs_step267':base/z['bytes'],'gain_vs_sz3':sz/z['bytes'],'ratio_to_2x_sz3_target':z['bytes']/(sz/2)})
    best=min((ub,b1,b2),key=lambda z:z['bytes']);variants.append({'g':g,'uniform':ub,'alloc1':b1,'alloc2':b2,'best':best});print(json.dumps({'region':region,'g':g,'best':best},indent=2),flush=True)
   best=min((v['best'] for v in variants),key=lambda z:z['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'step267_bytes':int(base),'step267_bps':8*base/X.size,'step267_maxerr':me0,'best':best,'variants':variants};rows.append(row)
   print(json.dumps({'summary':{'region':region,'step267_bps':row['step267_bps'],'sz3_bps':row['sz3_bps'],'best':best}},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'groups':list(GROUPS),'step_candidates':[int(x) for x in STEP_CAND],'rows':rows,'scope':'Executable source-trained rate allocation for spatial Hadamard transforms of decoder-real Huber AR32 innovations. For group sizes 8 and 16, each Hadamard coordinate receives its own integer quantizer step. The exact hard-error condition is enforced analytically: inverse Hadamard sample error before integer rounding is bounded by sum_s(step_s)/(2g), and 0.5 source unit is reserved for final integer rounding, so sum_s(step_s) <= floor(2g(epsilon-0.5)). Starting from uniform step266, the actual decoder-real transformed innovation field is measured; a dynamic program chooses one candidate step per subband minimizing summed empirical scalar entropy under that L-infinity budget. The chosen g uint16 step values are explicitly transmitted and charged. A second redesign round uses the actual reconstruction induced by the first allocation. Every candidate is then encoded/decoded through the same incumbent cold-start arithmetic backend under both natural and subband-major layouts, the full recursive source is regenerated, and max error is verified. Exact step267 Huber AR32 and matched SZ3 are rerun on identical hard/easy/medium/far regions. This tests transform bit allocation under the real hard-error geometry, not MSE waterfilling. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_hadamard_rate_allocation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
