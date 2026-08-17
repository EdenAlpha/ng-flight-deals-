import json,math,struct,sys
import h5py,numpy as np
from numba import njit
import imperial_decoder_phase_automaton as m
import imperial_huber_ar32_component_zsm_gps as cg
import imperial_huber_ar32_coldstart_arithmetic_regions as ah
C=128;NT=30000;C0=512;P=32;TRAIN=1024;STEP=267;INC=2468803;SZ3=2767977
WIDTHS=(128,64,32,16,8,4,2,1)
CONFIG={'zero':('base',64),'sign':('richall',4),'pref':('richmag',4),'suff':('richmag',4)}
def fit_group(X,a,b):
 rows=(b-a)*(TRAIN-P);A=np.empty((rows,P+1),np.float64);y=np.empty(rows,np.float64);q=0
 for c in range(a,b):
  x=X[c]
  for t in range(P,TRAIN):A[q,0]=1.;A[q,1:]=x[t-P:t][::-1];y[q]=x[t];q+=1
 co=np.linalg.lstsq(A,y,rcond=None)[0]
 for _ in range(3):
  r=y-A@co;w=np.minimum(1.,267./np.maximum(np.abs(r),1e-9));s=np.sqrt(w);co=np.linalg.lstsq(A*s[:,None],y*s,rcond=None)[0]
 return np.asarray(co,np.float32)
def fit_models(X,w):return np.stack([fit_group(X,a,min(C,a+w)) for a in range(0,C,w)])
@njit(cache=True)
def run(X,models,w):
 R=np.zeros((C,NT),np.int32);K=np.zeros((C,NT),np.int32)
 for c in range(C):
  co=models[c//w]
  for t in range(NT):
   if t<P:p=0
   else:
    s=np.float32(co[0])
    for j in range(P):s=np.float32(s+np.float32(co[j+1])*np.float32(R[c,t-1-j]))
    p=int(np.rint(s))
   k=int(np.rint((X[c,t]-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K
@njit(cache=True)
def replay(K,models,w):
 R=np.zeros(K.shape,np.int32)
 for c in range(C):
  co=models[c//w]
  for t in range(NT):
   if t<P:p=0
   else:
    s=np.float32(co[0])
    for j in range(P):s=np.float32(s+np.float32(co[j+1])*np.float32(R[c,t-1-j]))
    p=int(np.rint(s))
   R[c,t]=p+STEP*int(K[c,t])
 return R
def H(a):
 _,n=np.unique(a.reshape(-1),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())
def encode_fixed(K):
 stream=bytearray();entries={}
 for comp in cg.COMPONENTS:
  gr,W=CONFIG[comp];bb,nb=cg.encode_component(K,comp,W,NT,gr);sid=cg.config_id(gr,W);stream.extend(struct.pack('<BQI',sid,int(nb),len(bb)));stream.extend(bb);entries[comp]=(sid,int(nb),bb)
 return bytes(stream),entries
def main(path):
 with h5py.File(path,'r') as hf:
  ds=hf['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[:,C0:C0+C],np.float64).T
 rows=[];cands=[]
 for w in WIDTHS:
  models=fit_models(X,w);R,K=run(X,models,w);me=float(np.max(np.abs(X-R.astype(np.float64))));mb=models.nbytes;score=H(K)+8*mb/(C*NT);r={'group_width':w,'models':len(models),'model_bytes':mb,'K_h0_bps':H(K),'charged_h0_bps':score,'maxerr':me};rows.append(r);cands.append((score,w,models,R,K));print(json.dumps({'screen':r}),flush=True)
 cands.sort(key=lambda z:z[0]);score,w,models,R,K=cands[0];stream,entries=encode_fixed(K);Kd=cg.decode_components(entries,K.shape)
 if not np.array_equal(Kd,K):raise RuntimeError('K replay')
 Rd=replay(Kd,models,w)
 if not np.array_equal(Rd,R):raise RuntimeError('R replay')
 me=float(np.max(np.abs(X-Rd.astype(np.float64))));total=34+models.nbytes+len(stream)
 if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
 out={'winner_group_width':w,'bytes':int(total),'bps':8*total/(C*NT),'incumbent_bytes':INC,'delta_vs_incumbent':int(total-INC),'gain_vs_incumbent':INC/total,'matched_sz3_bytes':SZ3,'gain_vs_sz3':SZ3/total,'model_bytes':models.nbytes,'component_stream_bytes':len(stream),'maxerr':me,'screens':rows,'scope':'Channel-group AR32 generator search. Contiguous channel groups receive separately fitted Huber AR32 coefficient vectors trained on the same public 1024-sample prefix. Every float32 model byte is charged. Full step267 K is physically encoded with the incumbent component address, exact K is decoded, group models replay all samples, and unchanged hard error is enforced.'};json.dump(out,open('imperial_channelwise_ar32_generator.json','w'),indent=2);print(json.dumps({'summary':out},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])