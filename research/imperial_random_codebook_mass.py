import json,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import Counter
import h5py,numpy as np
from research.imperial_harderror_vector_cover import stats,choose_phase,nearest,legal

HFACTORS=(1.5,1.0,0.75);NS=(8,16,32);NPAIR=16;ALPHA=8.0;SAFETY=1-1e-6

def lse(vals):
 vals=[v for v in vals if math.isfinite(v)]
 if not vals:return -math.inf
 m=max(vals);return m+math.log(sum(math.exp(v-m) for v in vals))

def build_model(seqs):
 marg=Counter();tr=Counter();out=Counter();N=0
 for seq in seqs:
  ss=[tuple(x) if isinstance(x,(tuple,list,np.ndarray)) else int(x) for x in seq]
  marg.update(ss);N+=len(ss)
  for a,b in zip(ss[:-1],ss[1:]):tr[(a,b)]+=1;out[a]+=1
 p0={s:c/N for s,c in marg.items()}
 return p0,tr,out

def logtrans(model,a,b):
 p0,tr,out=model;pb=p0.get(b,0.0)
 if pb<=0:return -math.inf
 return math.log((tr.get((a,b),0)+ALPHA*pb)/(out.get(a,0)+ALPHA))

def mass_single(x,model,bound,h,phi):
 lo,hi=legal(x,bound,h,phi);p0,_,_=model;dp={q:math.log(p0[q]) for q in range(int(lo[0]),int(hi[0])+1) if q in p0}
 for t in range(1,len(x)):
  nd={}
  for b in range(int(lo[t]),int(hi[t])+1):
   if b not in p0:continue
   nd[b]=lse([la+logtrans(model,a,b) for a,la in dp.items()])
  dp=nd
  if not dp:return -math.inf
 return lse(dp.values())

def mass_pair(x,model,bound,h,phi):
 lo,hi=legal(x,bound,h,phi);p0,_,_=model
 def states(t):
  return [(a,b) for a in range(int(lo[t,0]),int(hi[t,0])+1) for b in range(int(lo[t,1]),int(hi[t,1])+1) if (a,b) in p0]
 st=states(0);dp={s:math.log(p0[s]) for s in st}
 for t in range(1,len(x)):
  nd={}
  for b in states(t):nd[b]=lse([la+logtrans(model,a,b) for a,la in dp.items()])
  dp=nd
  if not dp:return -math.inf
 return lse(dp.values())

def summarize(rates,target):
 a=np.asarray(rates,np.float64);fin=a[np.isfinite(a)]
 return {'blocks':int(len(a)),'finite_fraction':float(len(fin)/len(a)),'mean_bps':float(np.mean(fin)) if len(fin) else None,'median_bps':float(np.median(fin)) if len(fin) else None,'p10_bps':float(np.percentile(fin,10)) if len(fin) else None,'p90_bps':float(np.percentile(fin,90)) if len(fin) else None,'fraction_at_or_below_2x_target':float(np.mean(a<=target)),'fraction_at_or_below_sz3':float(np.mean(a<=2*target))}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;bound=eps*SAFETY;target=(8*86361271/(30000*6912))/2;pstarts=np.linspace(0,6910,NPAIR,dtype=np.int32);rows=[]
  for hf in HFACTORS:
   h=hf*bound;_,phi,pidx=choose_phase(ds[:2],h)
   for n in NS:
    sr=[];pr=[]
    for c0 in pstarts:
     c=int(c0)
     # single-channel model and target blocks
     pseq=[nearest(np.asarray(ds[k][:,c],np.float64),h,phi) for k in (0,1)];sm=build_model(pseq);tx=np.asarray(ds[2][:,c],np.float64);m=len(tx)//n*n
     for b in tx[:m].reshape(-1,n):
      lm=mass_single(b,sm,bound,h,phi);sr.append((-lm/math.log(2)/n) if math.isfinite(lm) else math.inf)
     # adjacent-channel pair process: one codeword emits both channels jointly
     pq=[]
     for k in (0,1):
      a=nearest(np.asarray(ds[k][:,c:c+2],np.float64),h,phi);pq.append([tuple(map(int,r)) for r in a])
     pm=build_model(pq);X=np.asarray(ds[2][:,c:c+2],np.float64);m=len(X)//n*n
     for B in X[:m].reshape(-1,n,2):
      lm=mass_pair(B,pm,bound,h,phi);pr.append((-lm/math.log(2)/(2*n)) if math.isfinite(lm) else math.inf)
    rows.append({'h_over_eps_approx':hf,'block_time':n,'phase_index':pidx,'single_channel_seed_rate':summarize(sr,target),'adjacent_pair_seed_rate':summarize(pr,target)})
  out={'files':3,'adjacent_pairs':pstarts.tolist(),'std':std,'eps':eps,'alpha_markov_backoff':ALPHA,'fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':target,'rows':rows,'scope':'Random-codebook existence diagnostic. Previous two decoded-lattice minutes define a channel-specific first-order Markov generator; adjacent-pair mode treats each two-channel state as one symbol, so its generator is genuinely spatiotemporal. For each target hard-error block the dynamic program sums the full model probability mass of every generated state sequence whose reconstruction lies inside every sample interval. If that mass is p, an iid decoder-known random codebook needs about -log2(p) seed bits for one legal hit. Reported rate is that seed-length threshold per sample, not yet an executable seed-search compressor. State support is conservatively restricted to states observed previously; no target-trained probabilities.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_random_codebook_mass.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
