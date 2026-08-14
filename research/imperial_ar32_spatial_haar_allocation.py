import json,math,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as h

C=128;NT=4096;TRAIN=1024;P=32;TB=1024;REGIONS=(('easy',2304),('medium',4608));GROUPS=(8,16,32)
CAND=np.asarray([32,48,64,80,96,112,128,144,160,176,192,208,224,240,256,266,288,320,352,384,448,512,640,768,896,1024,1280,1536,1792,2048,2560,3072,4096],np.int32)

def haar_mats(g):
 L=int(round(math.log2(g)));T=[];levels=[]
 T.append(np.ones(g,np.int64));levels.append(0)
 # Coarse to fine gives stable subband ordering; one row per localized detail.
 for l in range(L,0,-1):
  bs=1<<l;hh=bs>>1
  for b0 in range(0,g,bs):
   r=np.zeros(g,np.int64);r[b0:b0+hh]=1;r[b0+hh:b0+bs]=-1;T.append(r);levels.append(l)
 T=np.asarray(T,np.int64);W=np.rint(g*np.linalg.inv(T.astype(np.float64))).astype(np.int64)
 if not np.array_equal(W@T,g*np.eye(g,dtype=np.int64)):raise RuntimeError(('haar inverse',g))
 return T,W,np.asarray(levels,np.int32)

def level_steps(levels,params):
 return np.asarray([params[int(l)] for l in levels],np.int32)

def h0(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def run(X,coef,g,params,collect=False):
 T,W,levels=haar_mats(g);sv=level_steps(levels,params).astype(np.int64);ng=C//g;R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);ys={int(l):[] for l in np.unique(levels)} if collect else None;a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for t in range(NT):
  if t<P:pred=np.zeros(C,np.int32)
  else:pred=np.rint(a+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
  E=(X[:,t]-pred).astype(np.int64).reshape(ng,g);Y=E@T.T;Q=np.rint(Y.astype(np.float64)/sv[None,:].astype(np.float64)).astype(np.int32);Yh=Q.astype(np.int64)*sv[None,:];Er=np.rint((Yh@W.T).astype(np.float64)/g).astype(np.int32);R[:,t]=pred+Er.reshape(C);K[:,t]=Q.reshape(C)
  if collect:
   for j,l in enumerate(levels):ys[int(l)].extend(int(v) for v in Y[:,j])
 return R,K,ys

def decode(K,coef,g,params):
 T,W,levels=haar_mats(g);sv=level_steps(levels,params).astype(np.int64);ng=C//g;R=np.zeros(K.shape,np.int32);a=float(coef[0]);b=np.asarray(coef[1:],np.float32)
 for t in range(NT):
  if t<P:pred=np.zeros(C,np.int32)
  else:pred=np.rint(a+R[:,t-P:t][:,::-1].astype(np.float32)@b).astype(np.int32)
  Q=K[:,t].reshape(ng,g);Yh=Q.astype(np.int64)*sv[None,:];Er=np.rint((Yh@W.T).astype(np.float64)/g).astype(np.int32);R[:,t]=pred+Er.reshape(C)
 return R

def subband_major(K,g):
 ng=C//g;rows=np.asarray([q*g+j for j in range(g) for q in range(ng)],np.int32);return K[rows],rows

def undo_rows(A,rows):
 K=np.empty_like(A);K[rows]=A;return K

def budget_weights(g):
 L=int(round(math.log2(g)));return [1]+[g//(1<<l) for l in range(1,L+1)]

def params_to_steps_list(g,params):
 L=int(round(math.log2(g)));return [int(params[0])]+[int(params[l]) for l in range(1,L+1)]

@njit(cache=True)
def dp_alloc(cost,weights,cand,budget):
 n,m=cost.shape;inf=1e300;dp=np.full((n+1,budget+1),inf);pb=np.full((n+1,budget+1),-1,np.int32);pj=np.full((n+1,budget+1),-1,np.int16);dp[0,0]=0.
 for i in range(n):
  w=weights[i]
  for z in range(budget+1):
   if dp[i,z]>=inf/2:continue
   for j in range(m):
    q=z+w*cand[j]
    if q<=budget:
     v=dp[i,z]+cost[i,j]
     if v<dp[i+1,q]:dp[i+1,q]=v;pb[i+1,q]=z;pj[i+1,q]=j
 zz=0;best=inf
 for z in range(budget+1):
  if dp[n,z]<best:best=dp[n,z];zz=z
 out=np.empty(n,np.int32)
 for i in range(n,0,-1):j=pj[i,zz];out[i-1]=cand[j];zz=pb[i,zz]
 return out,best

def allocate(ys,g,eps):
 L=int(round(math.log2(g)));lev=[0]+list(range(1,L+1));weights=np.asarray(budget_weights(g),np.int32);cost=np.empty((len(lev),len(CAND)),np.float64)
 # Rate per original sample: root fraction 1/g; level-l detail fraction 1/2^l.
 for i,l in enumerate(lev):
  z=np.asarray(ys[l],np.float64);frac=(1.0/g if l==0 else 1.0/(1<<l))
  for j,s in enumerate(CAND):cost[i,j]=frac*h0(np.rint(z/float(s)).astype(np.int32))
 budget=int(math.floor(2*g*(float(eps)-0.5)-1e-12));v,pred=dp_alloc(cost,weights,CAND,budget);params={0:int(v[0])}
 for i,l in enumerate(range(1,L+1),start=1):params[l]=int(v[i])
 used=int(v[0]+sum((g//(1<<l))*v[l] for l in range(1,L+1)));return params,budget,used,float(pred)

def encode_variant(X,coef,g,params,eps,label,collect=False):
 R,K,ys=run(X,coef,g,params,collect);me=float(np.max(np.abs(X.astype(np.float64)-R.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError((label,g,'hard',me,eps,params))
 KS,rows=subband_major(K,g);ab,nbit,nb,D=h.arithmetic(KS);Kd=undo_rows(D,rows);Rd=decode(Kd,coef,g,params);dme=float(np.max(np.abs(X.astype(np.float64)-Rd.astype(np.float64))))
 if not np.array_equal(D,KS) or not np.array_equal(Kd,K) or not np.array_equal(Rd,R) or dme>eps*(1+1e-12):raise RuntimeError((label,g,'decode',dme,eps))
 L=int(round(math.log2(g)));model=2*(L+1)+24;steps=params_to_steps_list(g,params)
 return {'label':label,'g':g,'params':{str(k):int(v) for k,v in params.items()},'level_steps_root_then_fine_to_coarse':steps,'min_step':min(steps),'max_step':max(steps),'bytes':int(ab)+model,'bps':8*(int(ab)+model)/X.size,'arithmetic_bits':int(nbit),'symbol_bits':int(nb),'symbol_h0_bps':h0(K),'model_bytes':model,'maxerr':dme},ys

def main(path):
 h.C=C;h.NT=NT;h.TRAIN=TRAIN
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.int16).T.astype(np.int32);XF=X.astype(np.float64);_,coef=h.fits(XF);R0,K0=h.run_ar(XF,coef);base,_,_,D0=h.arithmetic(K0);RR=h.decode_source(D0,coef);me0=float(np.max(np.abs(XF-RR.astype(np.float64))))
   if me0>eps*(1+1e-12):raise RuntimeError((region,'base hard'))
   sz=0
   for t0 in range(0,NT,TB):q,_=m.szrun(XF[:,t0:t0+TB],eps);sz+=int(q)
   variants=[]
   for g in GROUPS:
    L=int(round(math.log2(g)));uni={l:266 for l in range(L+1)};u,ys=encode_variant(X,coef,g,uni,eps,'uniform',True);p1,budget,used1,pred1=allocate(ys,g,eps);a1,ys1=encode_variant(X,coef,g,p1,eps,'alloc1',True);p2,_,used2,pred2=allocate(ys1,g,eps);a2,_=encode_variant(X,coef,g,p2,eps,'alloc2',False)
    for z in (u,a1,a2):z.update({'gain_vs_step267':base/z['bytes'],'gain_vs_sz3':sz/z['bytes'],'ratio_to_2x_target':z['bytes']/(sz/2),'budget':budget})
    a1.update({'budget_used':used1,'predicted_rate_bps':pred1});a2.update({'budget_used':used2,'predicted_rate_bps':pred2});best=min((u,a1,a2),key=lambda z:z['bytes']);variants.append({'g':g,'uniform':u,'alloc1':a1,'alloc2':a2,'best':best});print(json.dumps({'region':region,'g':g,'best':best},indent=2),flush=True)
   best=min((x['best'] for x in variants),key=lambda z:z['bytes']);row={'region':region,'c0':c0,'samples':int(X.size),'eps':eps,'step267_bytes':int(base),'step267_bps':8*base/X.size,'sz3_bytes':sz,'sz3_bps':8*sz/X.size,'best':best,'variants':variants};rows.append(row);print(json.dumps({'summary':row},indent=2),flush=True)
  out={'global_std':gstd,'eps':eps,'shape':[C,NT],'groups':list(GROUPS),'rows':rows,'scope':'Fast decoder-real multiscale spatial Haar innovation pilot on easy and medium Imperial. After each Huber AR32 temporal prediction, contiguous channel groups are transformed by an exact unnormalized hierarchical Haar basis: one group sum plus localized difference coefficients at every dyadic scale. Inverse reconstruction uses an exact integer numerator with denominator g. A source sample depends only on the root coefficient and one detail coefficient per scale; therefore with root step d0 and level-l detail step dl, pre-rounding max error is bounded by d0/(2g)+sum_l dl/(2*2^l). The encoded allocation enforces the equivalent integer budget d0+sum_l(g/2^l)dl <= floor(2g(epsilon-0.5)), reserving 0.5 for final integer rounding. Uniform step266 is executable control. A dynamic program then selects one transmitted uint16 step per scale from a fixed dictionary to minimize empirical subband entropy under the exact hard-error budget, followed by one decoder-real redesign round. Coefficients are serialized subband-major across channel groups and exactly decoded with the incumbent contextual arithmetic backend; the recursive source is regenerated and hard-error checked. Closed-loop step267 Huber AR32 and matched SZ3 are rerun. This tests a local multiscale transform whose inverse error support is logarithmic in group size rather than a raw-signal transform. No AI. Draft/do not merge.'};json.dump(out,open('imperial_ar32_spatial_haar_allocation.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
