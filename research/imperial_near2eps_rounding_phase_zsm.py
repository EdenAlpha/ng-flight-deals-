import json,sys
import h5py,numpy as np
from numba import njit
import imperial_near2eps_learned_zsm_fullhard as q
import imperial_near2eps_scale_128x4096 as sc
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
q.f.q_decode=sc.q_decode
RBS=tuple(range(0,g.SCALE,256))
@njit(cache=True)
def pred(Q,c,t,dt,dc,co,it,scale,rb):
 acc=it
 for j in range(dt.size):
  tt=t-int(dt[j]);cc=c+int(dc[j])
  if tt>=0 and cc>=0 and cc<Q.shape[0]:acc+=int(co[j])*int(Q[cc,tt])
 return (acc+rb)//scale
@njit(cache=True)
def defects(Q,dt,dc,co,it,scale,rb):
 D=np.empty_like(Q)
 for t in range(Q.shape[1]):
  for c in range(Q.shape[0]):D[c,t]=int(Q[c,t])-pred(Q,c,t,dt,dc,co,it,scale,rb)
 return D
@njit(cache=True)
def decodeD(D,dt,dc,co,it,scale,rb):
 Q=np.empty_like(D)
 for t in range(D.shape[1]):
  for c in range(D.shape[0]):Q[c,t]=pred(Q,c,t,dt,dc,co,it,scale,rb)+int(D[c,t])
 return Q

def main(path):
 with h5py.File(path,'r') as hf:
  d=hf['Acoustic'];_,std=m.stats(d);eps=.1*std;X=np.asarray(d[:,q.f.C0:q.f.C0+q.C],np.float64).T
 h,Q,D0,dt,dc,co,it,changes,meanlegal=q.build_full(X,eps);mb,mrep,_,_,_,_=g.model_frame(dt,dc,co,it);screens=[];states={}
 for rb in RBS:
  D=defects(Q[:,:q.SCREEN],dt,dc,co,it,g.SCALE,int(rb));best=None
  for W in q.WINDOWS:
   bb,nb=q.encode_zsm(D,W,q.SCREEN);score=int(mb)+len(bb);rec={'round_bias':int(rb),'W':int(W),'screen_total':score,'payload':len(bb),'bits':int(nb),'zero_fraction':float(np.mean(D==0)),'std':float(D.astype(np.float64).std())};screens.append(rec);print(json.dumps({'screen':rec}),flush=True)
   if best is None or score<best[0]:best=(score,int(W))
  states[int(rb)]=best[1]
 screens.sort(key=lambda r:r['screen_total']);finalists=[]
 for r in screens:
  rb=int(r['round_bias'])
  if rb not in finalists:finalists.append(rb)
  if len(finalists)>=3:break
 full=[]
 for rb in finalists:
  W=states[rb];D=defects(Q,dt,dc,co,it,g.SCALE,rb);bb,nb=q.encode_zsm(D,W,q.NT);Dd=q.decode_zsm(bb,nb,W,D.shape)
  if not np.array_equal(Dd,D):raise RuntimeError(('D decode',rb))
  Qd=decodeD(Dd,dt,dc,co,it,g.SCALE,rb)
  if not np.array_equal(Qd,Q):raise RuntimeError(('Q replay',rb))
  me=float(np.max(np.abs(X-Qd.astype(np.float64)*h)))
  if me>eps*(1+5e-6):raise RuntimeError(('hard',rb,me,eps))
  total=int(mb)+len(bb)+q.HEADER+3;rec={'round_bias':rb,'W':W,'bytes':total,'payload':len(bb),'bits':int(nb),'zero_fraction':float(np.mean(D==0)),'std':float(D.astype(np.float64).std()),'maxerr':me};full.append(rec);print(json.dumps({'full':rec}),flush=True)
 full.sort(key=lambda r:r['bytes']);best=full[0];old=2486110;hist=2478995;bestbytes=min(old,best['bytes']);out={'round_biases':list(RBS),'screens':screens,'finalists':finalists,'full':full,'best_new':best,'best_learned_bytes':bestbytes,'historical_learned_bytes':old,'historical_ar32_zsm_bytes':hist,'gain_vs_historical_ar32_zsm':hist/bestbytes,'scope':'Learned-generator fixed-point rounding-phase search on the complete 128x30000 hard block. Q, tap coordinates and Q12 coefficients are fixed from PR551. Only the decoder-shared integer rounding offset in pred=(acc+round_bias)//4096 is searched over a fixed public 16-value grid. W and round bias are prefix-screened, and the new stream charges one W selector byte plus a 2-byte round-bias field. Top three prefix candidates are fully ZSM materialized, exact decoded through the same rounding rule to identical Q, and hard-error validated. Final learned result is min(new stream, PR551 baseline). AR32 does not use this learned fixed-point generator, so this is representation-specific rather than a generic entropy advantage.'};json.dump(out,open('imperial_near2eps_rounding_phase_zsm.json','w'),indent=2);print(json.dumps({'summary':{'learned':bestbytes,'ar32_zsm':hist,'gain':hist/bestbytes,'best_new':best}},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
