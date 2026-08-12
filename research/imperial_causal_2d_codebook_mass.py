import json,sys,os,math,itertools
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collections import Counter
import h5py,numpy as np
from research.imperial_harderror_vector_cover import stats,choose_phase,nearest,legal

WIDTHS=(3,4);HFACTORS=(1.5,1.0);N=16;STARTS=(0,2304,4606,6908);BLOCK_STRIDE=16;ALPHA=8.0;BETA=.1;SAFETY=1-1e-6

def lse(vals):
 vals=[v for v in vals if math.isfinite(v)]
 if not vals:return -math.inf
 m=max(vals);return m+math.log(sum(math.exp(v-m) for v in vals))
class Mesh:
 def __init__(self,seqs,qmin,qmax):
  self.root=Counter();self.spat=Counter();self.so=Counter();self.temp=Counter();self.to=Counter();self.mesh=Counter();self.mo=Counter();self.n=0;self.qmin=qmin;self.qmax=qmax;self.K=qmax-qmin+1
  for Q in seqs:
   Q=np.asarray(Q,np.int32);self.root.update(map(int,Q.ravel()));self.n+=Q.size
   for j in range(1,Q.shape[1]):
    for a,b in zip(Q[:,j-1],Q[:,j]):self.spat[(int(a),int(b))]+=1;self.so[int(a)]+=1
   for a,b in zip(Q[:-1,0],Q[1:,0]):self.temp[(int(a),int(b))]+=1;self.to[int(a)]+=1
   for t in range(1,Q.shape[0]):
    for j in range(1,Q.shape[1]):
     ctx=(int(Q[t-1,j]),int(Q[t,j-1]),int(Q[t-1,j-1]));q=int(Q[t,j]);self.mesh[(ctx,q)]+=1;self.mo[ctx]+=1
  self.den=self.n+BETA*self.K;self.cache={}
 def p0(self,q):return (self.root.get(int(q),0)+BETA)/self.den if self.qmin<=q<=self.qmax else 0.0
 def lp0(self,q):return math.log(self.p0(q))
 def cond(self,kind,ctx,q):
  key=(kind,ctx,int(q));v=self.cache.get(key)
  if v is not None:return v
  p=self.p0(q)
  if kind=='s':num=self.spat.get((int(ctx),int(q)),0);den=self.so.get(int(ctx),0)
  elif kind=='t':num=self.temp.get((int(ctx),int(q)),0);den=self.to.get(int(ctx),0)
  else:num=self.mesh.get((ctx,int(q)),0);den=self.mo.get(ctx,0)
  v=math.log((num+ALPHA*p)/(den+ALPHA));self.cache[key]=v;return v

def states_at(lo,hi,t):
 return list(itertools.product(*[range(int(lo[t,j]),int(hi[t,j])+1) for j in range(lo.shape[1])]))
def mass_patch(X,M,bound,h,phi):
 lo,hi=legal(X,bound,h,phi);st=states_at(lo,hi,0);dp={}
 for v in st:
  lp=M.lp0(v[0])
  for j in range(1,len(v)):lp+=M.cond('s',v[j-1],v[j])
  dp[v]=lp
 for t in range(1,len(X)):
  cur=states_at(lo,hi,t);nd={}
  for b in cur:
   vals=[]
   for a,la in dp.items():
    lp=la+M.cond('t',a[0],b[0])
    for j in range(1,len(b)):lp+=M.cond('m',(a[j],b[j-1],a[j-1]),b[j])
    vals.append(lp)
   nd[b]=lse(vals)
  dp=nd
  if not dp:return -math.inf
 return lse(dp.values())
def summarize(a,target):
 a=np.asarray(a,np.float64);f=a[np.isfinite(a)];return {'blocks':int(len(a)),'finite_fraction':float(len(f)/len(a)),'mean_bps':float(np.mean(f)) if len(f) else None,'median_bps':float(np.median(f)) if len(f) else None,'p10_bps':float(np.percentile(f,10)) if len(f) else None,'p90_bps':float(np.percentile(f,90)) if len(f) else None,'fraction_at_or_below_2x_target':float(np.mean(a<=target)),'fraction_at_or_below_sz3':float(np.mean(a<=2*target))}
def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;bound=eps*SAFETY;target=(8*86361271/(30000*6912))/2;rows=[]
  for hf in HFACTORS:
   h=hf*bound;_,phi,pidx=choose_phase(ds[:2],h);qmin=math.floor((-32768-phi)/h)-2;qmax=math.ceil((32767-phi)/h)+2
   for W in WIDTHS:
    rates=[];group_rates=[]
    for c0 in STARTS:
     c=min(int(c0),6912-W);prev=[nearest(np.asarray(ds[k][:,c:c+W],np.float64),h,phi) for k in (0,1)];M=Mesh(prev,qmin,qmax);X=np.asarray(ds[2][:,c:c+W],np.float64);m=len(X)//N*N;B=X[:m].reshape(-1,N,W)[::BLOCK_STRIDE];gr=[]
     for patch in B:
      lm=mass_patch(patch,M,bound,h,phi);r=(-lm/math.log(2)/(N*W)) if math.isfinite(lm) else math.inf;rates.append(r);gr.append(r)
     group_rates.append({'c0':c,'summary':summarize(gr,target)})
    rows.append({'h_over_eps_approx':hf,'width_channels':W,'block_time':N,'block_stride':BLOCK_STRIDE,'phase_index':pidx,'seed_rate':summarize(rates,target),'groups':group_rates})
  out={'files':3,'starts':list(STARTS),'std':std,'eps':eps,'alpha_context_backoff':ALPHA,'beta_root':BETA,'fullfile_sz3_bps':2*target,'strict_2x_target_bps':target,'rows':rows,'scope':'Causal 2-D random-codebook existence diagnostic. Previous two decoded-lattice minutes define a normalized mesh generator: q(c,t) is conditioned on q(c,t-1), already-generated q(c-1,t), and q(c-1,t-1), with root-distribution backoff. For each target W x 16 hard-error patch, dynamic programming sums the probability mass of every generated 2-D state field lying inside all sample intervals. -log2(mass)/(W*16) is the seed-rate threshold for a decoder-known random codebook, not yet an executable compressor. Four deterministic cable regions, every 16th block, no target-trained probabilities.'};print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_causal_2d_codebook_mass.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
