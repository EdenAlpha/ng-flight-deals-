import json,sys,math
import h5py,numpy as np

NS=(1,2,4,8,16,32)
NCH=32
PHASES=64


def stats(d):
 s=ss=0.;n=0
 for t0 in range(0,d.shape[0],2048):
  x=np.asarray(d[t0:min(d.shape[0],t0+2048)],dtype=np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 mu=s/n;return mu,math.sqrt(max(0.0,ss/n-mu*mu))

def entropy_counts(c):
 c=np.asarray(c,dtype=np.float64);p=c[c>0]/c.sum();return float(-(p*np.log2(p)).sum())

def H_values(a):
 _,c=np.unique(a,return_counts=True);return entropy_counts(c)

def choose_phase(d,eps):
 step=2*eps;tt=np.linspace(0,d.shape[0]-1,1024,dtype=np.int32);cc=np.linspace(0,d.shape[1]-1,256,dtype=np.int32)
 rows=np.asarray(d[tt,:],dtype=np.float64);x=rows[:,cc].ravel();best=None
 for k in range(PHASES):
  ph=step*k/PHASES;q=np.floor((x+ph)/step).astype(np.int32);h=H_values(q)
  if best is None or h<best[0]:best=(h,ph,k)
 return best

def quant_col(d,c,step,phase):
 x=np.asarray(d[:,c],dtype=np.float64);return np.floor((x+phase)/step).astype(np.int32)

def rows(q,n):
 m=(len(q)//n)*n
 return np.ascontiguousarray(q[:m].reshape(-1,n),dtype=np.int32)

def row_entropy(A):
 if A.shape[0]==0:return 0.0,0,0.0
 _,c=np.unique(A,axis=0,return_counts=True);return entropy_counts(c),int(c.size),float(np.mean(c==1))

def channel_markov_phrase_entropy(A):
 # Empirical first-order entropy rate over nonoverlapping phrase identities within one channel.
 # This is diagnostic only; singleton contexts expose finite-sample overfitting risk.
 if A.shape[0]<2:return None
 u,inv,c=np.unique(A,axis=0,return_inverse=True,return_counts=True)
 prev=inv[:-1];nxt=inv[1:]
 pairs=np.stack([prev,nxt],axis=1);_,pc=np.unique(pairs,axis=0,return_counts=True)
 _,prevc=np.unique(prev,return_counts=True)
 hp=entropy_counts(pc);hprev=entropy_counts(prevc);cond=max(0.0,hp-hprev)
 return {'conditional_phrase_bits':cond,'phrase_entropy_bits':entropy_counts(c),'phrase_vocab':int(len(c)),'singleton_phrase_fraction':float(np.mean(c==1))}

def keys(A):
 # Collision-free fixed-width row key for searchsorted. np.void compares the raw int32 tuple bytes.
 B=np.ascontiguousarray(A,dtype='<i4');return B.view(np.dtype((np.void,B.dtype.itemsize*B.shape[1]))).ravel()

def cross_entropy(prevA,targetA,literal_bps,n):
 pk=keys(prevA);tk=keys(targetA);u,c=np.unique(pk,return_counts=True)
 pos=np.searchsorted(u,tk);seen=(pos<len(u));seen &= np.where(seen,u[np.minimum(pos,len(u)-1)]==tk,False)
 N=len(tk);unseen=int((~seen).sum());pe=max(unseen/max(1,N),1/(N+1))
 bits=0.0
 if np.any(seen):
  cc=c[pos[seen]].astype(np.float64);p=(1-pe)*cc/c.sum();bits+=float(np.sum(-np.log2(np.maximum(p,1e-300))))
 if unseen:bits+=unseen*(-math.log2(pe)+n*literal_bps)
 return {'bps':bits/(N*n) if N else 0.0,'unseen_fraction':unseen/max(1,N),'dictionary_vocab':int(len(u)),'previous_phrases':int(len(pk)),'target_phrases':int(N),'escape_probability':pe}

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs]
  if len(ds)!=3 or any(tuple(d.shape)!=(30000,6912) for d in ds):raise RuntimeError('identity')
  _,std=stats(ds[-1]);eps=.1*std;step=2*eps;h0s,phase,pidx=choose_phase(ds[-1],eps);channels=np.linspace(0,6911,NCH,dtype=np.int32)
  Q=[[quant_col(d,int(c),step,phase) for c in channels] for d in ds]
  literal_bps=float(np.mean([H_values(q) for q in Q[-1]]));outrows=[]
  for n in NS:
   tar=[rows(q,n) for q in Q[-1]];prev=[[rows(q,n) for q in QQ] for QQ in Q[:-1]]
   pooled_tar=np.concatenate(tar,axis=0);pooled_prev=np.concatenate([a for pp in prev for a in pp],axis=0)
   hg,vocab,sing=row_entropy(pooled_tar)
   ch=[];mark=[]
   for A in tar:
    h,v,s=row_entropy(A);ch.append((A.shape[0],h,v,s));m=channel_markov_phrase_entropy(A)
    if m:mark.append((A.shape[0]-1,m))
   chbps=sum(nn*h for nn,h,_,_ in ch)/sum(nn for nn,_,_,_ in ch)/n
   pooled_bps=hg/n
   # Same-channel prior model: previous two minutes for the same cable position.
   ce=[]
   for ci,A in enumerate(tar):
    P=np.concatenate([prev[0][ci],prev[1][ci]],axis=0);r=cross_entropy(P,A,literal_bps,n);ce.append((A.shape[0],r))
   same_ce=sum(nn*r['bps'] for nn,r in ce)/sum(nn for nn,_ in ce)
   same_unseen=sum(nn*r['unseen_fraction'] for nn,r in ce)/sum(nn for nn,_ in ce)
   corpus_ce=cross_entropy(pooled_prev,pooled_tar,literal_bps,n)
   if mark:
    markov_bps=sum(nn*m['conditional_phrase_bits'] for nn,m in mark)/sum(nn for nn,_ in mark)/n
    mark_single=float(np.mean([m['singleton_phrase_fraction'] for _,m in mark]))
   else:markov_bps=None;mark_single=None
   outrows.append({'phrase_length':n,'pooled_empirical_block_entropy_bps':pooled_bps,'channel_conditioned_block_entropy_bps':chbps,'channel_first_order_phrase_entropy_bps':markov_bps,'channel_markov_singleton_phrase_fraction':mark_single,'target_pooled_vocab':vocab,'target_pooled_singleton_fraction':sing,'same_channel_previous_two_record_cross_entropy_bps':same_ce,'same_channel_unseen_fraction':same_unseen,'pooled_previous_corpus_cross_entropy':corpus_ce})
  out={'files':3,'shape':[30000,6912],'channels_tested':channels.tolist(),'global_std_target':std,'eps':eps,'step':step,'phase':phase,'phase_index':pidx,'sample_phase_H0_probe_bps':h0s,'mean_selected_channel_scalar_entropy_bps':literal_bps,'correct_fullfile_sz3_bps':8*86361271/(30000*6912),'strict_2x_target_bps':(8*86361271/(30000*6912))/2,'rows':outrows,'scope':'Higher-order language diagnostic on 32 deterministic channels from three consecutive full Imperial records. Nonoverlapping n-sample quantized phrases are exact int32 tuples. Reports block entropy, decoder-known channel-conditioned block entropy, empirical within-channel phrase Markov entropy (with singleton warning), and true cross-entropy of the target minute under phrase-frequency models learned only from the two preceding decoded minutes. Previous-record models are available only in sequential corpus compression, not standalone-file coding.'}
  print(json.dumps(out,indent=2),flush=True);json.dump(out,open('imperial_corpus_phrase_language.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
