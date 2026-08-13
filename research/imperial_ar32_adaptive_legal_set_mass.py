import json,sys,math
from collections import defaultdict
import h5py,numpy as np
import imperial_ar32_exact_legal_path_mass as b
import imperial_decoder_phase_automaton as dm

OFFSET=-512;A=1024;ALPHA0=.5;ALPHA1=.25;BACKOFF=32.0

def idx(k):
 q=int(k)-OFFSET
 if q<0 or q>=A:raise RuntimeError(('symbol outside alphabet',k))
 return q

def init_model(K):
 c0=np.zeros(A,np.int64);pairs=defaultdict(int);ctot=defaultdict(int);tot=0
 for c in b.CH:
  prev=0
  for k in K[c]:
   q=idx(k);c0[q]+=1;tot+=1;pairs[(idx(prev),q)]+=1;ctot[idx(prev)]+=1;prev=int(k)
 return c0,pairs,ctot,tot

def prob(k,prev,c0,pairs,ctot,tot):
 q=idx(k);p=idx(prev);p0=(float(c0[q])+ALPHA0)/(float(tot)+ALPHA0*A);n=ctot[p];p1=(float(pairs[(p,q)])+ALPHA1)/(float(n)+ALPHA1*A);lam=float(n)/(float(n)+BACKOFF);return (1-lam)*p0+lam*p1

def enumerate_adaptive(src,state,prevk,co,eps,c0,pairs,ctot,tot):
 bestlog=-1e300;bestR=None;bestK=None;logmass=-np.inf;count=0;nodes=0
 def rec(q,s,pk,lp,ks,rs,curtot):
  nonlocal bestlog,bestR,bestK,logmass,count,nodes
  nodes+=1
  if q==b.L:
   count+=1;logmass=float(np.logaddexp2(logmass,lp))
   if lp>bestlog:bestlog=lp;bestR=np.asarray(rs,np.int64);bestK=np.asarray(ks,np.int32)
   return
  p=b.predict(s,co);lo=int(math.ceil((float(src[q])-eps-p)/b.FINE-1e-12));hi=int(math.floor((float(src[q])+eps-p)/b.FINE+1e-12))
  for k in range(lo,hi+1):
   rr=p+b.FINE*k
   if abs(float(src[q])-rr)>eps*(1+1e-10):continue
   pr=prob(k,pk,c0,pairs,ctot,curtot);ii=idx(k);jj=idx(pk);c0[ii]+=1;pairs[(jj,ii)]+=1;ctot[jj]+=1
   ns=s.copy();ns[:-1]=ns[1:];ns[-1]=rr
   rec(q+1,ns,int(k),lp+math.log2(pr),ks+[int(k)],rs+[int(rr)],curtot+1)
   c0[ii]-=1;pairs[(jj,ii)]-=1;ctot[jj]-=1
 rec(0,state.copy(),int(prevk),0.0,[],[],tot)
 if count==0:raise RuntimeError('no legal path')
 return {'count':count,'log2_mass':logmass,'best_log2_prob':bestlog,'bestR':bestR,'bestK':bestK,'nodes':nodes}

def commit_path(K,prev,c0,pairs,ctot,tot):
 for k in K:
  ii=idx(k);jj=idx(prev);c0[ii]+=1;pairs[(jj,ii)]+=1;ctot[jj]+=1;tot+=1;prev=int(k)
 return prev,tot

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=dm.stats(d);eps=.1*std;X=np.asarray(d[:b.END,b.C0:b.C0+b.C],np.float64).T
 model_bytes,co,R0,K0=b.fit_model_and_prefix(X,eps);c0,pairs,ctot,tot=init_model(K0);rows=[];allset=[];allmap=[];allcnt=[];allnodes=[]
 # Each channel gets its own reconstruction state/last symbol, while the adaptive probability model is pooled and decoder-known.
 states={int(c):R0[c,-b.P:].copy() for c in b.CH};prevs={int(c):int(K0[c,-1]) for c in b.CH}
 for t in range(b.TRAIN,b.END,b.L):
  for c in b.CH:
   cc=int(c);src=X[c,t:t+b.L];z=enumerate_adaptive(src,states[cc],prevs[cc],co,eps,c0,pairs,ctot,tot);setbps=-z['log2_mass']/b.L;mapbps=-z['best_log2_prob']/b.L;allset.append(setbps);allmap.append(mapbps);allcnt.append(z['count']);allnodes.append(z['nodes'])
   for rr in z['bestR']:states[cc][:-1]=states[cc][1:];states[cc][-1]=int(rr)
   prevs[cc],tot=commit_path(z['bestK'],prevs[cc],c0,pairs,ctot,tot)
   if float(np.max(np.abs(src-z['bestR'])))>eps*(1+1e-10):raise RuntimeError('MAP hard')
  if (t-b.TRAIN)//b.L%64==0:print(json.dumps({'t':t,'mean_set_so_far':float(np.mean(allset)),'mean_map_so_far':float(np.mean(allmap))}),flush=True)
 for c in b.CH:
  ix=[i for i in range(len(allset)) if i%len(b.CH)==list(b.CH).index(c)];rows.append({'channel':int(b.C0+c),'blocks':len(ix),'mean_set_mass_bps':float(np.mean(np.asarray(allset)[ix])),'mean_MAP_bps':float(np.mean(np.asarray(allmap)[ix]))})
 Atest=X[b.CH,b.TRAIN:b.END];szb=b.szrun(Atest,eps);target=4*szb[0]/Atest.size
 out={'global_std':std,'eps':eps,'ar_order':b.P,'fine_step':b.FINE,'block_length':b.L,'training_samples':b.TRAIN,'target_interval':[b.TRAIN,b.END],'channels':[int(b.C0+x) for x in b.CH],'adaptive_model':{'alphabet':[OFFSET,OFFSET+A-1],'zero_order_alpha':ALPHA0,'order1_alpha':ALPHA1,'context_backoff_strength':BACKOFF,'target_model_metadata_bytes':0},'matched_sz3':{'bytes':szb[0],'bps':8*szb[0]/Atest.size,'two_x_target_bps':target},'aggregate':{'mean_exact_adaptive_set_mass_bps':float(np.mean(allset)),'median_exact_adaptive_set_mass_bps':float(np.median(allset)),'p90_exact_adaptive_set_mass_bps':float(np.percentile(allset,90)),'mean_MAP_bps':float(np.mean(allmap)),'mean_legal_paths':float(np.mean(allcnt)),'mean_DFS_nodes':float(np.mean(allnodes)),'ratio_set_mass_to_2x_target':float(np.mean(allset))/target},'rows':rows,'scope':'Exact adaptive legal-set mass diagnostic, not yet a byte codec. Shared AR32 and step128 prefix reconstruction are decoder-known. A pooled finite-alphabet adaptive probability model is initialized only from decoded prefix K. It mixes a KT-smoothed zero-order K law with a KT-smoothed order-1 transition law using decoder-known count-based backoff. For every held-out 8-sample block, exhaustive DFS enumerates every recursively legal path. Probabilities are path-dependent: each candidate symbol temporarily updates the same adaptive counts that a decoder would update if that path were chosen. The exact probability mass of all legal paths and MAP path are computed with no pruning. The MAP legal path is then committed to both AR state and adaptive counts before the next block, so the chosen reconstruction literally teaches the future model without transmitting target probability tables. -log2 legal-set mass is still an ideal set/arithmetic-seed rate, not realized bytes. No AI.'}
 print(json.dumps(out['aggregate'],indent=2),flush=True);json.dump(out,open('imperial_ar32_adaptive_legal_set_mass.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
