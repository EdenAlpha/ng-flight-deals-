import json,sys,math,heapq
import h5py,numpy as np
from numba import njit
import imperial_huber_ar32_coldstart_arithmetic_regions as a

C=128;NT=4096;TRAIN=1024;P=32;TB=1024;MODEL_BYTES=177
SELECT=np.arange(0,128,16,dtype=np.int32)  # 8 sensors spread across each 128-channel region
REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
STEPS=(267,256,240,224,208,192)
BEAM=32

@njit(cache=True)
def greedy_all(X,co,step):
 nc,nt=X.shape;R=np.zeros((nc,nt),np.int32);K=np.zeros((nc,nt),np.int32)
 a0=float(co[0]);b=co[1:]
 for c in range(nc):
  for t in range(nt):
   if t<P: pred=0
   else:
    z=a0
    for j in range(P): z+=float(b[j])*float(R[c,t-1-j])
    pred=int(np.rint(z))
   k=int(np.rint((X[c,t]-pred)/step));K[c,t]=k;R[c,t]=pred+step*k
 return R,K

@njit(cache=True)
def decode_step(K,co,step):
 nc,nt=K.shape;R=np.zeros((nc,nt),np.int32);a0=float(co[0]);b=co[1:]
 for c in range(nc):
  for t in range(nt):
   if t<P: pred=0
   else:
    z=a0
    for j in range(P):z+=float(b[j])*float(R[c,t-1-j])
    pred=int(np.rint(z))
   R[c,t]=pred+step*int(K[c,t])
 return R

def clip4(k): return max(-4,min(4,int(k)))

def make_cost_model(K):
 # Prefix-only conditional law P(K_t | clipped K_{t-1}). This model is encoder-side only;
 # the decoder never needs it because the chosen exact K stream is transmitted.
 counts=[{} for _ in range(9)];tot=np.zeros(9,np.int64)
 vals=[]
 for c in range(K.shape[0]):
  for t in range(TRAIN):
   prev=int(K[c,t-1]) if t else 0;ctx=clip4(prev)+4;k=int(K[c,t]);vals.append(k)
   counts[ctx][k]=counts[ctx].get(k,0)+1;tot[ctx]+=1
 lo=min(vals);hi=max(vals);A=max(32,hi-lo+21);alpha=.5
 def nll(prev,k):
  ctx=clip4(prev)+4;n=counts[ctx].get(int(k),0)
  return -math.log2((n+alpha)/(float(tot[ctx])+alpha*A))
 return nll,{'prefix_k_min':int(lo),'prefix_k_max':int(hi),'alphabet_smoothing':int(A)}

def legal_range(x,pred,step,eps):
 lo=int(math.ceil((float(x)-float(pred)-eps)/step-1e-12))
 hi=int(math.floor((float(x)-float(pred)+eps)/step+1e-12))
 return lo,hi

def beam_channel(x,co,step,eps,Rpre,Kpre,nll):
 # State is exactly what the decoder carries: last P reconstructions + previous K.
 # We preserve the greedy prefix and optimize only held-out t>=TRAIN.
 H=np.asarray(Rpre[TRAIN-P:TRAIN],np.int32)[None,:]
 costs=np.zeros(1,np.float64);prev=np.asarray([int(Kpre[TRAIN-1])],np.int32)
 parents=[];choices=[];multi_count=[];a0=float(co[0]);b=np.asarray(co[1:],np.float32)
 for t in range(TRAIN,NT):
  preds=np.rint(a0+H[:,::-1].astype(np.float32)@b).astype(np.int64)
  cand=[];had_multi=0
  for bi in range(H.shape[0]):
   kmn,kmx=legal_range(int(x[t]),int(preds[bi]),step,eps)
   if kmx<kmn: raise RuntimeError(('no legal k',t,step,int(x[t]),int(preds[bi]),kmn,kmx))
   if kmx>kmn:had_multi+=1
   for k in range(kmn,kmx+1):
    r=int(preds[bi])+step*k
    err=abs(float(x[t])-r)
    if err>eps*(1+1e-12):raise RuntimeError(('illegal branch',t,step,k,err,eps))
    cc=float(costs[bi])+float(nll(int(prev[bi]),k))
    # deterministic tiny tie breaker only; does not materially affect objective
    cc2=cc+1e-12*(abs(k)+0.001*(k+1000))
    cand.append((cc2,cc,bi,k,r))
  cand.sort(key=lambda q:(q[0],q[3],q[2]));keep=cand[:BEAM]
  newH=np.empty((len(keep),P),np.int32);newc=np.empty(len(keep),np.float64);newp=np.empty(len(keep),np.int32)
  par=np.empty(len(keep),np.int16);cho=np.empty(len(keep),np.int32)
  for j,q in enumerate(keep):
   _,cc,bi,k,r=q;newH[j,:-1]=H[bi,1:];newH[j,-1]=r;newc[j]=cc;newp[j]=k;par[j]=bi;cho[j]=k
  H,costs,prev=newH,newc,newp;parents.append(par);choices.append(cho);multi_count.append(had_multi)
 best=int(np.argmin(costs));ks=np.empty(NT-TRAIN,np.int32)
 for q in range(NT-TRAIN-1,-1,-1):
  ks[q]=choices[q][best];best=int(parents[q][best])
 return ks,float(np.min(costs)),{'beam_width':BEAM,'mean_states_with_multiple_legal_choices':float(np.mean(multi_count)),'max_states_with_multiple_legal_choices':int(max(multi_count))}

def backend(K):
 total=MODEL_BYTES+1;reps={};frames=[]
 for t0 in range(0,NT,TB):
  t1=min(NT,t0+TB);n,rep,D=a.m.encode_k(K[:,t0:t1])
  if not np.array_equal(D,K[:,t0:t1]):raise RuntimeError(('backend decode',t0))
  n=int(n)+20;total+=n;reps[rep]=reps.get(rep,0)+1;frames.append({'t0':t0,'bytes':n,'rep':rep})
 return total,reps,frames

def main(path):
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=a.m.stats(d);eps=.1*gstd;rows=[]
  for region,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);hu=np.asarray(hu,np.float32)
   outsteps=[];sz=0
   Xsel=X[SELECT]
   for t0 in range(0,NT,TB):sb,_=a.m.szrun(Xsel[:,t0:min(t0+TB,NT)],eps);sz+=sb
   base267=None
   for step in STEPS:
    Rg,Kg=greedy_all(X,hu,step);nll,cmeta=make_cost_model(Kg)
    Ksel=Kg[SELECT].copy();beam_meta=[];beam_cost=0.0
    for j,ch in enumerate(SELECT):
     ks,cost,bm=beam_channel(X[ch],hu,step,eps,Rg[ch],Kg[ch],nll);Ksel[j,TRAIN:]=ks;beam_cost+=cost;beam_meta.append({'local_channel':int(ch),**bm})
    Rd=decode_step(Ksel,hu,step);me=float(np.max(np.abs(Xsel-Rd.astype(np.float64))))
    if me>eps*(1+1e-12):raise RuntimeError((region,step,'hard',me,eps))
    gb,grep,gframes=backend(Kg[SELECT]);tb,trep,tframes=backend(Ksel)
    rr={'step':step,'samples':int(Ksel.size),'greedy_bytes':gb,'greedy_bps':8*gb/Ksel.size,
        'trellis_bytes':tb,'trellis_bps':8*tb/Ksel.size,'gain_trellis_vs_same_step_greedy':gb/tb,
        'sz3_bytes':sz,'gain_trellis_vs_sz3':sz/tb,'maxerr':me,'prefix_cost_model':cmeta,
        'trellis_objective_cost_bits':beam_cost,'greedy_reps':grep,'trellis_reps':trep,
        'branching':{'mean_beam_states_with_multiple_legal_choices':float(np.mean([x['mean_states_with_multiple_legal_choices'] for x in beam_meta])),'max_beam_states_with_multiple_legal_choices':int(max(x['max_states_with_multiple_legal_choices'] for x in beam_meta))},
        'greedy_zero_fraction':float(np.mean(Kg[SELECT]==0)),'trellis_zero_fraction':float(np.mean(Ksel==0))}
    if step==267:base267=tb
    outsteps.append(rr);print(json.dumps({'region':region,**{k:v for k,v in rr.items() if k not in ('greedy_reps','trellis_reps','prefix_cost_model')}},indent=2),flush=True)
   for rr in outsteps:rr['gain_vs_trellis_step267']=base267/rr['trellis_bytes']
   best=min(outsteps,key=lambda q:q['trellis_bytes'])
   rows.append({'region':region,'c0':c0,'selected_channels':SELECT.tolist(),'sz3_bytes':sz,'baseline_step267_bytes':base267,'best':best,'steps':outsteps})
  out={'global_std':gstd,'eps':eps,'ar_order':P,'train':TRAIN,'end':NT,'beam_width':BEAM,'steps':list(STEPS),'selected_channels':SELECT.tolist(),'rows':rows,
       'scope':'Encoder-side trellis/noise-shaping gate on the real Huber-AR32 decoder state. Unlike prior phase/codebook experiments, this does not impose a procedural residue pattern. It deliberately uses slightly denser integer reconstruction lattices (steps 256..192) so some samples have multiple independently legal K choices under the unchanged max-error bound. The first 1024 samples stay on the ordinary greedy path. A prefix-only P(K|clipped previous K) law supplies a beam-search cost; on held-out samples a width-32 beam chooses among every legal K while carrying the exact last-32 reconstructed AR state. No beam model or decisions are needed by the decoder: only the chosen K stream and one step selector are transmitted. Exact K frames are byte-decoded through the incumbent backend, the source is recursively reconstructed, all model/frame/selector bytes are charged, and hard error is verified. Greedy decoding at each identical step, step267, and matched SZ3 on the same eight spatially spread sensors are controls. A real gain here would demonstrate distortion-choice shaping unavailable to the unique-choice step267 greedy quantizer and justify a full arithmetic-coded implementation. No AI. Draft/do not merge.'}
  json.dump(out,open('imperial_huber_ar32_trellis_quantizer.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
