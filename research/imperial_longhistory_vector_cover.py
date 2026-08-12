import json,math
from collections import Counter
import numpy as np,h5py,s3fs,boto3
from botocore import UNSIGNED
from botocore.config import Config

BUCKET='gdr-data-lake';PREFIX='imperialvalleydas/v1.0.0/';TARGET=PREFIX+'DF__UTC_20201113_235932.602.h5'
HISTS=(2,8,32);REGIONS=(0,2304,4606,6880);W=2;N=16
STD=1336.977803780576;EPS=.1*STD;BOUND=EPS*(1-1e-6);HF=1.5;H=HF*BOUND;PHASES=8
ALPHA=.25;QOFF=1024;QBINS=2048;FULL_SZ3_BPS=3.331839158950617;TARGET_BPS=FULL_SZ3_BPS/2
TERM=None;MAXK='M'

def nearest(x,phi):return np.rint((np.asarray(x,np.float64)-phi)/H).astype(np.int32)
def legal(x,phi):
 x=np.asarray(x,np.float64);lo=np.ceil((x-BOUND-phi)/H-1e-12).astype(np.int32);hi=np.floor((x+BOUND-phi)/H+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal set')
 return lo,hi

def entropy(a):
 _,c=np.unique(np.asarray(a).ravel(),return_counts=True);p=c/c.sum();return float(-(p*np.log2(p)).sum())
def choose_phase(prev):
 best=None
 for k in range(PHASES):
  phi=H*k/PHASES;v=np.mean([entropy(nearest(x,phi)) for x in prev])
  if best is None or v<best[0]:best=(v,phi,k)
 return best

def blocks(a):
 m=a.shape[0]//N*N;return np.ascontiguousarray(a[:m].reshape(-1,N))
def build_trie(P):
 D=P-P[:,0:1];U,c=np.unique(D[:,1:],axis=0,return_counts=True);root={MAXK:int(c.max())}
 for row,cnt in zip(U,c):
  node=root
  for vv in row:
   v=int(vv);ch=node.get(v)
   if ch is None:ch={MAXK:int(cnt)};node[v]=ch
   elif int(cnt)>ch[MAXK]:ch[MAXK]=int(cnt)
   node=ch
  node[TERM]=int(cnt)
 return root,int(c.sum()),int(len(c))
def best_shape(node,los,his,pos=0,best_count=0,path=None):
 if path is None:path=[]
 if pos==len(los):
  c=node.get(TERM,0);return (c,tuple(path)) if c>best_count else (best_count,None)
 bestp=None
 for v in range(int(los[pos]),int(his[pos])+1):
  ch=node.get(v)
  if ch is None or ch.get(MAXK,0)<=best_count:continue
  c,p=best_shape(ch,los,his,pos+1,best_count,path+[v])
  if c>best_count:best_count=c;bestp=p
 return best_count,bestp
def scalar_model(Q):
 vals,c=np.unique(Q,return_counts=True);lo=int(vals.min());hi=int(vals.max());cnt=np.zeros(hi-lo+1,np.float64)+ALPHA;cnt[vals-lo]+=c;return lo,cnt/cnt.sum()
def scalar_bits(q,model):
 lo,p=model;idx=np.asarray(q,np.int32)-lo;ok=(idx>=0)&(idx<len(p));out=np.full(idx.shape,16.0,np.float64);out[ok]=-np.log2(np.maximum(p[idx[ok]],1e-300));return out

def evaluate(hist_q,target_x,phi):
 PB=np.concatenate([blocks(q) for q in hist_q],axis=0);trie,total,vocab=build_trie(PB);smodel=scalar_model(np.concatenate(hist_q));XB=blocks(target_x);lo,hi=legal(XB,phi);nq=np.minimum(np.maximum(nearest(XB,phi),lo),hi);literal=scalar_bits(nq,smodel).sum(axis=1)
 bits=0.;matched=0;maxerr=0.;known_cost=[];esc_cost=[]
 for j in range(len(XB)):
  best=None
  for q0 in range(int(lo[j,0]),int(hi[j,0])+1):
   c,p=best_shape(trie,lo[j,1:]-q0,hi[j,1:]-q0)
   if c<=0 or p is None:continue
   ab=float(scalar_bits(np.array([q0]),smodel)[0]);sb=-math.log2(c/total);cost=1.0+ab+sb
   if best is None or cost<best[0]:best=(cost,q0,p,c,ab,sb)
  if best is None:
   c=1.0+float(literal[j]);bits+=c;esc_cost.append(c/N);continue
  cost,q0,p,c,ab,sb=best;q=np.empty(N,np.int32);q[0]=q0;q[1:]=q0+np.asarray(p,np.int32);R=phi+H*q;me=float(np.max(np.abs(XB[j]-R)))
  if me>EPS*(1+5e-6):raise RuntimeError(('hard error',me,EPS))
  bits+=cost;matched+=1;maxerr=max(maxerr,me);known_cost.append(cost/N)
 return {'bps':bits/(len(XB)*N),'matched_fraction':matched/len(XB),'known_phrase_bps':float(np.mean(known_cost)) if known_cost else None,'escape_phrase_bps':float(np.mean(esc_cost)) if esc_cost else None,'vocab':vocab,'history_phrases':total,'maxerr':maxerr}

def open_h5(fs,key):
 rf=fs.open(f'{BUCKET}/{key}','rb',block_size=8<<20,cache_type='readahead');return rf,h5py.File(rf,'r')
def read_selected(d):return np.concatenate([np.asarray(d[:,c0:c0+W],np.float64) for c0 in REGIONS],axis=1)

def main():
 s=boto3.client('s3',config=Config(signature_version=UNSIGNED));objs=[]
 for pg in s.get_paginator('list_objects_v2').paginate(Bucket=BUCKET,Prefix=PREFIX):objs.extend(o['Key'] for o in pg.get('Contents',[]) if o['Key'].endswith('.h5'))
 objs.sort();ti=objs.index(TARGET);history=objs[ti-max(HISTS):ti];fs=s3fs.S3FileSystem(anon=True,default_fill_cache=False)
 # Target and immediate two prior records determine the decoder-known phase.
 rf,hf=open_h5(fs,TARGET)
 try:T=read_selected(hf['Acoustic'])
 finally:hf.close();rf.close()
 prev=[]
 for key in history[-2:]:
  rf,hf=open_h5(fs,key)
  try:prev.append(read_selected(hf['Acoustic']))
  finally:hf.close();rf.close()
 _,phi,pidx=choose_phase(prev)
 # Read max history once into compact selected-channel arrays.
 Hraw=[]
 for i,key in enumerate(history,1):
  rf,hf=open_h5(fs,key)
  try:Hraw.append(read_selected(hf['Acoustic']))
  finally:hf.close();rf.close()
  if i in (2,8,16,24,32):print(json.dumps({'history_loaded':i}),flush=True)
 rows=[]
 for nh in HISTS:
  start=len(Hraw)-nh
  for j,c in enumerate([c for c0 in REGIONS for c in range(c0,c0+W)]):
   histq=[nearest(a[:,j],phi) for a in Hraw[start:]];r=evaluate(histq,T[:,j],phi);r.update({'history_records':nh,'channel':c,'region_c0':next(c0 for c0 in REGIONS if c0<=c<c0+W),'gain_vs_fullfile_sz3_ideal':FULL_SZ3_BPS/r['bps'],'ratio_to_2x_target':r['bps']/TARGET_BPS});rows.append(r)
  rr=[r for r in rows if r['history_records']==nh];print(json.dumps({'history':nh,'mean_bps':float(np.mean([r['bps'] for r in rr])),'mean_match':float(np.mean([r['matched_fraction'] for r in rr])),'min_bps':min(r['bps'] for r in rr),'max_bps':max(r['bps'] for r in rr)},indent=2),flush=True)
 agg=[]
 for nh in HISTS:
  rr=[r for r in rows if r['history_records']==nh];agg.append({'history_records':nh,'mean_bps':float(np.mean([r['bps'] for r in rr])),'mean_matched_fraction':float(np.mean([r['matched_fraction'] for r in rr])),'mean_known_phrase_bps':float(np.mean([r['known_phrase_bps'] for r in rr if r['known_phrase_bps'] is not None])),'mean_escape_phrase_bps':float(np.mean([r['escape_phrase_bps'] for r in rr if r['escape_phrase_bps'] is not None])),'gain_vs_fullfile_sz3_ideal':FULL_SZ3_BPS/float(np.mean([r['bps'] for r in rr])),'ratio_to_2x_target':float(np.mean([r['bps'] for r in rr]))/TARGET_BPS})
 out={'target':TARGET,'history_max':max(HISTS),'history_checkpoints':list(HISTS),'channels':[c for c0 in REGIONS for c in range(c0,c0+W)],'phrase_length':N,'h_over_eps':HF,'phase':phi,'phase_index':pidx,'eps':EPS,'fullfile_sz3_bps_reference':FULL_SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,'aggregate':agg,'rows':rows,'scope':'Long-history hard-error vector-cover rate audit. Up to 32 previous decoder-history minutes provide same-channel translation-invariant 16-sample waveform shapes. For every target phrase, interval/trie search asks whether any vector in the full Cartesian product of per-sample +/-10%-global-std legal states equals a historical shape plus a legal scalar anchor. Matched phrases pay mode+frequency-coded shape+anchor; unmatched phrases pay previous-history scalar literals. History and phase are decoder-reproducible under the fixed lattice; target contributes no model counts. Ideal arithmetic rate only, not yet a byte container.'}
 print(json.dumps({'aggregate':agg},indent=2),flush=True);json.dump(out,open('imperial_longhistory_vector_cover.json','w'),indent=2)
if __name__=='__main__':main()
