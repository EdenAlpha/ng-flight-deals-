import json,sys,os,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import h5py,numpy as np
from research.imperial_harderror_vector_cover import stats,nearest,legal,choose_phase,blocks,scalar_model,scalar_bits,best_shape,MAXK,TERM

NCH=32;NS=(4,8,16);HFACTORS=(1.0,0.75,0.5);BINS=(1,2,3,4,6);SAFETY=1-1e-6

def build_prototypes(P,B):
 D=(P-P[:,0:1])[:,1:];K=np.floor_divide(D,B).astype(np.int32);_,inv,c=np.unique(K,axis=0,return_inverse=True,return_counts=True);m=len(c);sums=np.zeros((m,D.shape[1]),np.int64)
 for j in range(D.shape[1]):np.add.at(sums[:,j],inv,D[:,j].astype(np.int64))
 proto=np.rint(sums/c[:,None]).astype(np.int32);U,inv2=np.unique(proto,axis=0,return_inverse=True);w=np.bincount(inv2,weights=c).astype(np.int64)
 root={MAXK:int(w.max())}
 for row,wt in zip(U,w):
  node=root
  for v in row:
   v=int(v);ch=node.get(v)
   if ch is None:ch={MAXK:int(wt)};node[v]=ch
   elif wt>ch[MAXK]:ch[MAXK]=int(wt)
   node=ch
  node[TERM]=int(wt)
 return root,int(w.sum()),int(len(w))

def run_channel(prevq,targetx,n,bound,h,phi,B):
 PB=np.concatenate([blocks(prevq[0],n),blocks(prevq[1],n)],axis=0);trie,total,vocab=build_prototypes(PB,B);smodel=scalar_model(np.concatenate(prevq));m=targetx.shape[0]//n*n;XB=targetx[:m].reshape(-1,n);lo,hi=legal(XB,bound,h,phi);nearestq=np.minimum(np.maximum(nearest(XB,h,phi),lo),hi);literal=scalar_bits(nearestq,smodel).sum(axis=1)
 tot=0.;match=0;shape_bits=[];anchor_bits=[];mx=0.
 for j in range(len(XB)):
  best=None
  for q0 in range(int(lo[j,0]),int(hi[j,0])+1):
   c,p=best_shape(trie,lo[j,1:]-q0,hi[j,1:]-q0)
   if c<=0 or p is None:continue
   ab=float(scalar_bits(np.asarray([q0],np.int32),smodel)[0]);sb=-math.log2(c/total);cost=1+ab+sb
   if best is None or cost<best[0]:best=(cost,q0,p,ab,sb)
  if best is None:tot+=1+float(literal[j]);continue
  cost,q0,p,ab,sb=best;q=np.empty(n,np.int32);q[0]=q0;q[1:]=q0+np.asarray(p,np.int32);R=phi+h*q;me=float(np.max(np.abs(XB[j]-R)))
  if me>bound*(1+3e-6):raise RuntimeError(('hard',n,B,me,bound))
  mx=max(mx,me);tot+=cost;match+=1;shape_bits.append(sb);anchor_bits.append(ab)
 return {'bps':tot/(len(XB)*n),'matched_fraction':match/len(XB),'prototype_vocab':vocab,'matched_shape_bits':float(np.mean(shape_bits)) if shape_bits else None,'matched_anchor_bits':float(np.mean(anchor_bits)) if anchor_bits else None,'maxerr':mx}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];_,std=stats(ds[-1]);eps=.1*std;bound=eps*SAFETY;chs=np.linspace(0,6911,NCH,dtype=np.int32);rows=[]
  for hf in HFACTORS:
   h=hf*bound;_,phi,pidx=choose_phase(ds[:2],h);PQ=[[nearest(np.asarray(ds[k][:,int(c)],np.float64),h,phi) for k in (0,1)] for c in chs];TX=[np.asarray(ds[2][:,int(c)],np.float64) for c in chs]
   for n in NS:
    for B in BINS:
     rr=[run_channel(PQ[i],TX[i],n,bound,h,phi,B) for i in range(NCH)]
     rows.append({'h_over_eps_approx':hf,'phrase_length':n,'shape_cluster_bin_q':B,'phase_index':pidx,'constructed_cover_bps':float(np.mean([r['bps'] for r in rr])),'matched_fraction':float(np.mean([r['matched_fraction'] for r in rr])),'mean_prototype_vocab':float(np.mean([r['prototype_vocab'] for r in rr])),'mean_matched_shape_bits_per_phrase':float(np.mean([r['matched_shape_bits'] for r in rr if r['matched_shape_bits'] is not None])),'mean_matched_anchor_bits_per_phrase':float(np.mean([r['matched_anchor_bits'] for r in rr if r['matched_anchor_bits'] is not None])),'maxerr':max(r['maxerr'] for r in rr)})
  rows.sort(key=lambda r:r['constructed_cover_bps']);out={'files':3,'channels':chs.tolist(),'std':std,'eps':eps,'bound':bound,'fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':(8*86361271/(30000*6912))/2,'rows':rows,'scope':'Constructed hard-error vector-cover audit. Previous decoded-lattice phrase shapes are deterministically partitioned into coarse cells in translation-invariant shape space; each cell is replaced by a synthetic rounded-mean prototype that need never have occurred in the data, and its weight is the cluster population. A trie of those decoder-derived prototypes is searched through each target block hard-error box exactly. Matched blocks pay one mode bit + prototype static code + scalar anchor; escapes pay previous-record scalar literals. Prototype metadata is free only because it is deterministically reconstructed from the already-decoded previous minutes. Ideal static arithmetic screen; hard error explicitly checked for every match.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_constructed_vector_cover.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
