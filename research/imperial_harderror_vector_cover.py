import json,sys,math
import h5py,numpy as np

NCH=32;NS=(4,8,16);HFACTORS=(1.5,1.0,0.75,0.5);PHASES=8;SAFETY=1-1e-6
TERM=None;MAXK='M'

def stats(d):
 s=ss=0.;n=0
 for t0 in range(0,d.shape[0],2048):
  x=np.asarray(d[t0:min(d.shape[0],t0+2048)],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,math.sqrt(max(0.,ss/n-m*m))
def H(a):
 _,c=np.unique(np.asarray(a).ravel(),return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def nearest(x,h,phi):return np.rint((x-phi)/h).astype(np.int32)
def legal(x,bound,h,phi):
 lo=np.ceil((x-bound-phi)/h-1e-12).astype(np.int32);hi=np.floor((x+bound-phi)/h+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal set')
 return lo,hi
def choose_phase(prev,h):
 # Previous records only: phase is decoder-derived, never target-tuned.
 tt=np.linspace(0,prev[0].shape[0]-1,512,dtype=np.int32);cc=np.linspace(0,prev[0].shape[1]-1,128,dtype=np.int32);best=None
 for k in range(PHASES):
  phi=h*k/PHASES;hs=[]
  for d in prev:
   x=np.asarray(d[tt,:],np.float64)[:,cc].ravel();hs.append(H(nearest(x,h,phi)))
  v=float(np.mean(hs))
  if best is None or v<best[0]:best=(v,phi,k)
 return best
def blocks(a,n):
 m=a.shape[0]//n*n;return np.ascontiguousarray(a[:m].reshape(-1,n))
def build_trie(P):
 # P is integer phrase matrix. Shapes are translation-invariant q-q0.
 D=P-P[:,0:1];U,c=np.unique(D[:,1:],axis=0,return_counts=True);root={MAXK:int(c.max())}
 for row,cnt in zip(U,c):
  node=root
  for v in row:
   v=int(v);child=node.get(v)
   if child is None:child={MAXK:int(cnt)};node[v]=child
   elif cnt>child[MAXK]:child[MAXK]=int(cnt)
   node=child
  node[TERM]=int(cnt)
 return root,int(c.sum()),int(len(c))
def best_shape(node,los,his,pos=0,best_count=0,path=None):
 if path is None:path=[]
 if pos==len(los):
  c=node.get(TERM,0)
  return (c,tuple(path)) if c>best_count else (best_count,None)
 bestp=None
 for v in range(int(los[pos]),int(his[pos])+1):
  ch=node.get(v)
  if ch is None or ch.get(MAXK,0)<=best_count:continue
  c,p=best_shape(ch,los,his,pos+1,best_count,path+[v])
  if c>best_count:best_count=c;bestp=p
 return best_count,bestp
def scalar_model(P):
 vals,c=np.unique(P,return_counts=True);lo=int(vals.min());hi=int(vals.max());cnt=np.zeros(hi-lo+1,np.float64)+0.25;cnt[vals-lo]+=c;return lo,cnt/cnt.sum()
def scalar_bits(q,model):
 lo,p=model;idx=q-lo;ok=(idx>=0)&(idx<len(p));out=np.full(q.shape,16.0,np.float64);out[ok]=-np.log2(np.maximum(p[idx[ok]],1e-300));return out
def run_channel(prevq,targetx,n,bound,h,phi):
 PB=np.concatenate([blocks(prevq[0],n),blocks(prevq[1],n)],axis=0);trie,total,vocab=build_trie(PB);smodel=scalar_model(np.concatenate(prevq));m=targetx.shape[0]//n*n;XB=targetx[:m].reshape(-1,n);lo,hi=legal(XB,bound,h,phi);nearestq=np.minimum(np.maximum(nearest(XB,h,phi),lo),hi)
 literal_bits=scalar_bits(nearestq,smodel).sum(axis=1);totbits=0.0;matched=0;states=[];shape_bits=[];anchor_bits=[];maxerr=0.0
 for j in range(len(XB)):
  best=None
  for q0 in range(int(lo[j,0]),int(hi[j,0])+1):
   sl=lo[j,1:]-q0;sh=hi[j,1:]-q0;c,p=best_shape(trie,sl,sh)
   if c<=0 or p is None:continue
   ab=float(scalar_bits(np.asarray([q0],np.int32),smodel)[0]);sb=-math.log2(c/total);cost=1.0+ab+sb
   if best is None or cost<best[0]:best=(cost,q0,p,c,ab,sb)
  if best is None:
   totbits+=1.0+float(literal_bits[j]);states.append(0);continue
  cost,q0,p,c,ab,sb=best;q=np.empty(n,np.int32);q[0]=q0;q[1:]=q0+np.asarray(p,np.int32);R=phi+h*q;me=float(np.max(np.abs(XB[j]-R)))
  if me>bound*(1+3e-6):raise RuntimeError(('cover hard error',n,me,bound))
  maxerr=max(maxerr,me);totbits+=cost;matched+=1;states.append(int(np.prod(hi[j]-lo[j]+1)));shape_bits.append(sb);anchor_bits.append(ab)
 return {'bps':totbits/(len(XB)*n),'matched_fraction':matched/len(XB),'dictionary_vocab':vocab,'previous_phrases':total,'mean_legal_vector_count':float(np.mean(states)) if states else 0.0,'matched_shape_bits_per_phrase':float(np.mean(shape_bits)) if shape_bits else None,'matched_anchor_bits_per_phrase':float(np.mean(anchor_bits)) if anchor_bits else None,'maxerr_matched':maxerr}
def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;bound=eps*SAFETY;chs=np.linspace(0,6911,NCH,dtype=np.int32);rows=[]
  for hf in HFACTORS:
   h=hf*bound;_,phi,pidx=choose_phase(ds[:2],h)
   for n in NS:
    rr=[]
    for c in chs:
     prevq=[nearest(np.asarray(ds[k][:,int(c)],np.float64),h,phi) for k in (0,1)];x=np.asarray(ds[2][:,int(c)],np.float64);rr.append(run_channel(prevq,x,n,bound,h,phi))
    rows.append({'h_over_eps_approx':hf,'phrase_length':n,'phase_index':pidx,'phase':phi,'same_channel_vector_cover_bps':float(np.mean([r['bps'] for r in rr])),'matched_fraction':float(np.mean([r['matched_fraction'] for r in rr])),'mean_dictionary_vocab':float(np.mean([r['dictionary_vocab'] for r in rr])),'mean_previous_phrases':float(np.mean([r['previous_phrases'] for r in rr])),'mean_legal_vector_count':float(np.mean([r['mean_legal_vector_count'] for r in rr])),'mean_matched_shape_bits_per_phrase':float(np.mean([r['matched_shape_bits_per_phrase'] for r in rr if r['matched_shape_bits_per_phrase'] is not None])),'mean_matched_anchor_bits_per_phrase':float(np.mean([r['matched_anchor_bits_per_phrase'] for r in rr if r['matched_anchor_bits_per_phrase'] is not None])),'maxerr':max(r['maxerr_matched'] for r in rr)})
  rows.sort(key=lambda r:r['same_channel_vector_cover_bps']);out={'files':3,'channels':chs.tolist(),'std':std,'eps':eps,'bound':bound,'fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':(8*86361271/(30000*6912))/2,'rows':rows,'scope':'Hard-error vector-cover diagnostic. For each fine-lattice target phrase, every Cartesian combination of legal per-sample states is implicit. A trie built only from translation-invariant phrase shapes in the two preceding decoded-lattice minutes finds the highest-probability previous shape compatible with the entire target tolerance box, without enumerating the exponential legal set. A matched phrase transmits one mode bit, static shape symbol and scalar anchor; an unmatched phrase transmits one mode bit plus scalar literals under previous-record models. Dictionary/model are decoder-derived from previous minutes. Hard error is explicitly verified for every matched codeword. Ideal static arithmetic rate only; integrate a real coder only if rate headroom is material.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_harderror_vector_cover.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
