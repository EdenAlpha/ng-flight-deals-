import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

ORDERS=(1,2,4,8,16)
KINDS=('shared','per_channel')
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def fit_shared(X,p):
 Y=X[:,p:].reshape(-1).astype(np.float64)
 A=np.empty((Y.size,p+1),np.float64)
 for j in range(p):A[:,j]=X[:,p-1-j:-1-j if j>=0 else None].reshape(-1) if j<p-1 else X[:,:-p].reshape(-1)
 # Simpler explicit slicing to avoid endpoint ambiguity.
 for j in range(p):A[:,j]=X[:,p-1-j:X.shape[1]-1-j].reshape(-1)
 A[:,-1]=1.0
 coef=np.linalg.lstsq(A,Y,rcond=1e-8)[0].astype(np.float32)
 return coef

def fit_per_channel(X,p):
 C=X.shape[0];co=np.empty((C,p+1),np.float32)
 for c in range(C):
  Y=X[c,p:].astype(np.float64);A=np.empty((Y.size,p+1),np.float64)
  for j in range(p):A[:,j]=X[c,p-1-j:X.shape[1]-1-j]
  A[:,-1]=1.0;co[c]=np.linalg.lstsq(A,Y,rcond=1e-8)[0].astype(np.float32)
 return co

def model_frame(co):
 a=np.asarray(co,np.float32);bb=Z.compress(a.tobytes());r=np.frombuffer(D.decompress(bb),np.float32,count=a.size).reshape(a.shape).copy()
 if not np.array_equal(r.view(np.uint32),a.view(np.uint32)):raise RuntimeError('model rt')
 return len(bb)+36,r

def predict_hist(R,c,t,coef,p,kind):
 if t<p:return 0
 co=coef if kind=='shared' else coef[c]
 v=float(co[-1])
 for j in range(p):v+=float(co[j])*float(R[c,t-1-j])
 if not math.isfinite(v):raise RuntimeError(('nonfinite pred',c,t,p,kind))
 return int(np.rint(v))

def encode(X,eps,p,kind):
 co=fit_shared(X,p) if kind=='shared' else fit_per_channel(X,p);mb,cd=model_frame(co)
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);P=np.zeros(X.shape,np.int32)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   pred=predict_hist(R,c,t,cd,p,kind);k=int(np.rint((float(X[c,t])-pred)/m.STEP));r=pred+m.STEP*k
   if abs(float(X[c,t])-r)>128+1e-9:raise RuntimeError(('round',c,t,p,kind))
   P[c,t]=pred;K[c,t]=k;R[c,t]=r
 frame=m.encode_k(K);Kd=frame[2];Rd=np.zeros_like(R)
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):Rd[c,t]=predict_hist(Rd,c,t,cd,p,kind)+m.STEP*int(Kd[c,t])
 if not np.array_equal(Rd,R):raise RuntimeError(('decode',p,kind))
 me=float(np.max(np.abs(X-Rd.astype(float))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',me,eps))
 return {'bytes':mb+frame[0]+20,'model_bytes':mb,'k_bytes':frame[0],'rep':frame[1],'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_abs1_fraction':float(np.mean(np.abs(K)==1)),'k_std':float(K.std()),'phase_entropy':m.entropy(np.mod(P,256)),'coefficients':cd.tolist() if kind=='shared' else None,'median_ar1':float(np.median(cd[:,0])) if kind=='per_channel' else None}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=m.stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in m.SPECS:
   X=np.asarray(d[t0:t0+m.T,c0:c0+m.C],np.float64).T;sb,ori=m.szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'local_std':float(X.std())})
   base=m.encode_source(X,eps,'fixed0');base.update({'tile':name,'kind':'fixed0','order':0,'sz3_bytes':sb,'gain_vs_sz3':sb/base['bytes'],'bps':8*base['bytes']/X.size});rows.append(base)
   for p in ORDERS:
    for kind in KINDS:
     r=encode(X,eps,p,kind);r.update({'tile':name,'kind':kind,'order':p,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size,'gain_vs_fixed0':base['bytes']/r['bytes']});rows.append(r);print(json.dumps(r),flush=True)
  combos=[];sz=sum(t['sz3_bytes'] for t in tiles);n=m.C*m.T*len(tiles);fixed=sum(r['bytes'] for r in rows if r['kind']=='fixed0')
  combos.append({'kind':'fixed0','order':0,'bytes':fixed,'sz3_bytes':sz,'bps':8*fixed/n,'gain_vs_sz3':sz/fixed,'gain_vs_fixed0':1.0})
  for p in ORDERS:
   for kind in KINDS:
    rr=[r for r in rows if r['kind']==kind and r['order']==p];b=sum(r['bytes'] for r in rr)
    combos.append({'kind':kind,'order':p,'bytes':b,'sz3_bytes':sz,'bps':8*b/n,'gain_vs_sz3':sz/b,'gain_vs_fixed0':fixed/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'mean_model_bps':8*sum(r['model_bytes'] for r in rr)/n,'median_k_zero_fraction':float(np.median([r['k_zero_fraction'] for r in rr]))})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':m.STEP,'orders':list(ORDERS),'kinds':list(KINDS),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Dyadic dynamical-state / resonator codec screen. A tiny AR(p)+intercept state equation is least-squares fitted to the source tile, explicitly float32 serialized and byte-decoded, then used recursively by the decoder to generate an integer predictor P. Only k=round((X-P)/256) is transmitted; P mod256 is therefore a free low-byte phase and reconstruction error is always <=128 under unchanged Imperial 10%-global-std epsilon. Tests one shared recurrence for all 128 channels and per-channel recurrences at p=1/2/4/8/16. Complete innovation fields use the same decoder-real Zstd menu as PR #298, recursive decode is verified, model bytes fully counted, matched SZ3 on identical hard/easy/medium/far 128x1024 tiles. Linear system identification only; no AI.'};print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_dyadic_shared_resonator.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
