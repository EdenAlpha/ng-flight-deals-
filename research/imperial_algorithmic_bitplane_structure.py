import json,math,sys
import h5py,numpy as np

REGIONS=(0,2304,4606,6880);NCH=4;MAXBITS=12;SAFETY=1-1e-5
LAGS=tuple(range(1,257))+(512,1000)
TARGET_BPS=1.6659195794753086;SZ3_BPS=3.331839158950617

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def qstate(d,c,eps):
 step=2*eps*SAFETY;x=np.asarray(d[:,c],np.float64);q=np.rint(x/step).astype(np.int32)
 if float(np.max(np.abs(x-q.astype(np.float64)*step)))>eps*(1+5e-6):raise RuntimeError('quant bound')
 # signed zigzag; bitplanes of exactly the legal reconstruction state
 u=((q.astype(np.int64)<<1)^(q.astype(np.int64)>>63)).astype(np.uint64)
 return q,u

def bits(u,b):return ((u>>np.uint64(b))&np.uint64(1)).astype(np.uint8)
def h2err(e):
 p=float(np.mean(e)) if len(e) else 0.0
 if p<=0 or p>=1:return 0.0
 return float(-p*math.log2(p)-(1-p)*math.log2(1-p))
def hbit(x):return h2err(x)

def best_lag_model(v):
 best=(hbit(v),0,float(np.mean(v)))
 for lag in LAGS:
  if lag>=len(v):continue
  e=np.bitwise_xor(v[lag:],v[:-lag]);h=h2err(e)
  if h<best[0]:best=(h,lag,float(np.mean(e)))
 return best

def xor_mask_pred(cur,left):
 # Features are decoder-causal in raster channel order.
 # f0=self t-1, f1=self t-2, f2=left same-t, f3=left t-1.
 n=len(cur);start=2
 F=np.stack([cur[start-1:n-1],cur[start-2:n-2],left[start:n],left[start-1:n-1]],axis=1).astype(np.uint8)
 y=cur[start:]
 best=None
 for mask in range(1,16):
  pred=np.zeros(len(y),np.uint8)
  for j in range(4):
   if (mask>>j)&1:pred^=F[:,j]
  e=pred^y;h=h2err(e)
  row=(h,mask,float(np.mean(e)))
  if best is None or row<best:best=row
 return best

def apply_xor_mask(cur,left,mask):
 n=len(cur);start=2;F=np.stack([cur[start-1:n-1],cur[start-2:n-2],left[start:n],left[start-1:n-1]],axis=1).astype(np.uint8);pred=np.zeros(n-start,np.uint8)
 for j in range(4):
  if (mask>>j)&1:pred^=F[:,j]
 return pred^cur[start:]

def bm_capped(s,cap=64,train=4096):
 # Exact Berlekamp-Massey over GF(2), but stop once complexity exceeds a useful cap.
 a=np.asarray(s[:train],np.uint8);n=len(a);C=np.zeros(cap+2,np.uint8);B=np.zeros(cap+2,np.uint8);C[0]=B[0]=1;L=0;m=1
 for N in range(n):
  d=int(a[N])
  for i in range(1,L+1):d^=int(C[i]&a[N-i])
  if d==0:m+=1;continue
  T=C.copy()
  if m>cap+1:return None
  for j in range(0,cap+2-m):
   if B[j]:C[j+m]^=1
  if 2*L<=N:
   L=N+1-L
   if L>cap:return None
   B=T;m=1
  else:m+=1
 return (L,C[:L+1].copy())
def apply_bm(s,model):
 if model is None:return None
 L,C=model
 if L==0:return np.asarray(s,np.uint8).copy()
 a=np.asarray(s,np.uint8);e=np.empty(max(0,len(a)-L),np.uint8)
 for n in range(L,len(a)):
  p=0
  for i in range(1,L+1):p^=int(C[i]&a[n-i])
  e[n-L]=p^int(a[n])
 return e

def choose_model(prev_bits,prev_left):
 # Model selection uses only already-decoded previous minute r1.
 raw=(hbit(prev_bits),'raw',None,float(np.mean(prev_bits)))
 lh,lag,le=best_lag_model(prev_bits);lagrow=(lh,'lag',int(lag),le)
 mh,mask,me=xor_mask_pred(prev_bits,prev_left);maskrow=(mh,'xor4',int(mask),me)
 bm=bm_capped(prev_bits,64,4096);be=apply_bm(prev_bits,bm)
 bmrow=(h2err(be),'bm',{'L':int(bm[0]),'C':bm[1].astype(int).tolist()} if bm is not None else None,float(np.mean(be)) if be is not None and len(be) else 0.5) if bm is not None else (99.0,'bm',None,1.0)
 return min((raw,lagrow,maskrow,bmrow),key=lambda r:r[0])
def target_rate(cur,left,model):
 _,kind,param,_=model
 if kind=='raw':e=cur
 elif kind=='lag':
  lag=int(param);e=np.bitwise_xor(cur[lag:],cur[:-lag]) if lag else cur
 elif kind=='xor4':e=apply_xor_mask(cur,left,int(param))
 elif kind=='bm':
  p=param;bm=(int(p['L']),np.asarray(p['C'],np.uint8));e=apply_bm(cur,bm)
 else:raise ValueError(kind)
 # Ideal static arithmetic residual rate. Initial-condition cost is explicitly charged.
 init=0
 if kind=='lag':init=int(param)
 elif kind=='xor4':init=2
 elif kind=='bm':init=int(param['L']) if param else 0
 return h2err(e)*(len(e)/len(cur))+init/len(cur),float(np.mean(e)),len(e),init

def main(paths):
 fs=[h5py.File(p,'r') for p in paths]
 try:
  ds=[f['Acoustic'] for f in fs];stds=[stats(d)[1] for d in ds];eps=[.1*s for s in stds]
  rows=[];channel_rows=[]
  for c0 in REGIONS:
   for c in range(c0,c0+NCH):
    states=[];us=[];leftus=[]
    for fi,d in enumerate(ds):
     q,u=qstate(d,c,eps[fi]);states.append(q);us.append(u)
     _,lu=qstate(d,max(0,c-1),eps[fi]);leftus.append(lu)
    # Number of relevant zigzag planes determined only from previous decoded states.
    maxu=max(int(us[0].max()),int(us[1].max()),int(us[2].max()));nb=min(MAXBITS,max(1,maxu.bit_length()))
    total=0.0;detail=[]
    for b in range(nb):
     p=bits(us[1],b);pl=bits(leftus[1],b);model=choose_model(p,pl)
     t=bits(us[2],b);tl=bits(leftus[2],b);rate,err,nres,init=target_rate(t,tl,model);total+=rate
     detail.append({'bit':b,'model':model[1],'param':model[2],'validation_bps':model[0],'target_bps':rate,'target_error_fraction':err,'initial_bits':init,'target_one_fraction':float(np.mean(t))})
    channel_rows.append({'region_c0':c0,'channel':c,'bitplanes':nb,'ideal_algorithmic_bps':total,'gain_vs_fullfile_sz3_bps':SZ3_BPS/total if total>0 else float('inf'),'ratio_to_2x_target':total/TARGET_BPS,'details':detail})
  agg=float(np.mean([r['ideal_algorithmic_bps'] for r in channel_rows]));regions=[]
  for c0 in REGIONS:
   rr=[r for r in channel_rows if r['region_c0']==c0];regions.append({'region_c0':c0,'mean_bps':float(np.mean([r['ideal_algorithmic_bps'] for r in rr])),'min_bps':min(r['ideal_algorithmic_bps'] for r in rr),'max_bps':max(r['ideal_algorithmic_bps'] for r in rr),'models':{k:sum(d['model']==k for r in rr for d in r['details']) for k in ('raw','lag','xor4','bm')}})
  out={'shape':list(ds[-1].shape),'stds':stds,'eps':eps,'regions':list(REGIONS),'channels_per_region':NCH,'verified_fullfile_sz3_bps':SZ3_BPS,'strict_2x_target_bps':TARGET_BPS,'aggregate_mean_bps':agg,'aggregate_gain_vs_sz3_rate':SZ3_BPS/agg,'region_summary':regions,'channels':channel_rows,
   'scope':'Decoder-honest algorithmic bitplane diagnostic on nearest legal 10%-std reconstruction states. For each zigzag state bitplane, the previous decoded minute selects among raw entropy, GF(2) lag recurrence, a causal four-feature XOR cellular predictor, or an exact Berlekamp-Massey recurrence capped at linear complexity 64. The selected prior-defined model is then scored on the target minute; no target statistics select the model. Rates are ideal static residual-bit entropy plus initial-condition bits, not yet compressed-container bytes. Purpose: detect deterministic digital/interrogator algebra invisible to numerical correlation.'}
  print(json.dumps({'aggregate_mean_bps':agg,'regions':regions,'best_channels':sorted(channel_rows,key=lambda r:r['ideal_algorithmic_bps'])[:8]},indent=2),flush=True);json.dump(out,open('imperial_algorithmic_bitplane_structure.json','w'),indent=2)
 finally:
  for f in fs:f.close()
if __name__=='__main__':main(sys.argv[1:])
