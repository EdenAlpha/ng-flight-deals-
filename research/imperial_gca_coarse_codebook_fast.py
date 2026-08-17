import json,math,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
import imperial_huber_ar32_component_zsm_gps as cg
C=128;NT=30000;C0=512;P=32;RAD=133;FINE=267;TRAIN=4096
STEPS=(320,384,448,512,640,768,1024)
@njit(cache=True)
def pred(co,R,c,t):
 if t<P:return 0
 s=np.float32(co[0])
 for j in range(P):s=np.float32(s+np.float32(co[j+1])*np.float32(R[c,t-1-j]))
 return int(np.rint(s))
@njit(cache=True)
def runN(X,co,S,d,T):
 R=np.zeros((C,T),np.int32);M=np.zeros((C,T),np.uint8);V=np.zeros((C,T),np.int32)
 for c in range(C):
  for t in range(T):
   p=pred(co,R,c,t);x=int(X[c,t]);q=int(np.rint((x-p-d)/S));r=p+d+S*q
   if abs(x-r)<=RAD:M[c,t]=0;V[c,t]=q;R[c,t]=r
   else:
    k=int(np.rint((x-p)/FINE));r=p+FINE*k;M[c,t]=1;V[c,t]=k;R[c,t]=r
 return R,M,V
def H(a):
 _,n=np.unique(np.asarray(a).reshape(-1),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())
def rate(M,V):
 p=float(np.mean(M));hm=0. if p in (0,1) else -(p*math.log2(p)+(1-p)*math.log2(1-p));z=M==0;o=~z
 return hm+(1-p)*(H(V[z]) if np.any(z) else 0)+p*(H(V[o]) if np.any(o) else 0)
def main(path):
 with h5py.File(path,'r') as hf:
  ds=hf['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.rint(np.asarray(ds[:,C0:C0+C],np.float64).T).astype(np.int64)
 _,co=ah.fits(X.astype(np.float64));_,cod=cg.model_frame(co);rows=[]
 for S in STEPS:
  scr=[]
  for d in range(0,S,max(1,S//16)):
   _,M,V=runN(X,cod,S,d,TRAIN);scr.append((rate(M,V),d))
  _,d=min(scr);R,M,V=runN(X,cod,S,d,NT);row={'step':S,'phase':int(d),'fallback_fraction':float(np.mean(M)),'conditional_h0_bps':rate(M,V),'maxerr':float(np.max(np.abs(X-R.astype(np.int64))))};rows.append(row);print(json.dumps(row),flush=True)
 out={'rows':rows,'best':min(rows,key=lambda r:r['conditional_h0_bps']),'baseline_K_h0_bps':5.42790583731344,'target_bps':8*(2767977/2)/(C*NT),'note':'Prefix-screened entropy diagnostic only; not serialized codec bytes.'};json.dump(out,open('imperial_gca_coarse_codebook_fast.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])