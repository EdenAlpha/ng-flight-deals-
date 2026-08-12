import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=128;T=1024;STEP=256
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
MODES=('fixed0','time1','time15','time2','left','avg_t_l','frac_lorenzo','frac_accel','frac_both','median3')
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  b,_=sz.compress(A,cfg);R,_=sz.decompress(b,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
  row=(int(b.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def sdtype(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  z=np.iinfo(dt)
  if mn>=z.min and mx<=z.max:return dt
 raise RuntimeError((mn,mx))
def udtype(a):
 a=np.asarray(a);mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('u1'),np.dtype('<u2'),np.dtype('<u4')):
  if mx<=np.iinfo(dt).max:return dt
 raise RuntimeError(mx)
def zig(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzig(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)
def gray(u):return np.asarray(u,np.uint64)^(np.asarray(u,np.uint64)>>1)
def ungray(g):
 x=np.asarray(g,np.uint64).copy();s=1
 while s<64:x^=x>>s;s*=2
 return x

def signed_blob(a):
 a=np.asarray(a,np.int32);dt=sdtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.int32).reshape(a.shape);return len(bb)+30,r,dt.str
def unsigned_blob(a):
 a=np.asarray(a,np.uint64);dt=udtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.uint64).reshape(a.shape);return len(bb)+30,r,dt.str

def encode_k(K):
 K=np.asarray(K,np.int32);c=[]
 arr={'raw':K.copy()}
 a=K.copy();a[:,1:]=K[:,1:]-K[:,:-1];arr['dt']=a
 a=K.copy();a[1:]=K[1:]-K[:-1];arr['ds']=a
 a=K.copy();a[1:,1:]=K[1:,1:]-K[:-1,1:]-K[1:,:-1]+K[:-1,:-1];a[0,1:]=K[0,1:]-K[0,:-1];a[1:,0]=K[1:,0]-K[:-1,0];arr['lorenzo']=a
 for name,a in arr.items():
  n,r,dt=signed_blob(a)
  if name=='raw':q=r
  elif name=='dt':q=np.cumsum(r,axis=1,dtype=np.int32)
  elif name=='ds':q=np.cumsum(r,axis=0,dtype=np.int32)
  else:q=np.cumsum(np.cumsum(r,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
  if not np.array_equal(q,K):raise RuntimeError(('signed',name))
  c.append((n+8,name+'_'+dt,q))
 u=zig(K);variants={'zigzag':u.copy()}
 a=u.copy();a[:,1:]=u[:,1:]^u[:,:-1];variants['zigzag_xort']=a
 a=u.copy();a[1:]=u[1:]^u[:-1];variants['zigzag_xors']=a
 variants['gray']=gray(u)
 for name,a in variants.items():
  n,r,dt=unsigned_blob(a)
  if name=='zigzag':uu=r
  elif name=='zigzag_xort':
   uu=r.copy()
   for j in range(1,uu.shape[1]):uu[:,j]^=uu[:,j-1]
  elif name=='zigzag_xors':
   uu=r.copy()
   for i in range(1,uu.shape[0]):uu[i]^=uu[i-1]
  else:uu=ungray(r)
  q=unzig(uu).reshape(K.shape)
  if not np.array_equal(q,K):raise RuntimeError(('unsigned',name))
  c.append((n+8,name+'_'+dt,q))
 mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());bl=[]
 for k in range(nb):bl.append(Z.compress(np.packbits(((u.ravel()>>k)&1).astype(np.uint8),bitorder='little').tobytes()))
 uu=np.zeros(u.size,np.uint64)
 for k,bb in enumerate(bl):uu|=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:u.size].astype(np.uint64)<<k
 q=unzig(uu.reshape(u.shape)).reshape(K.shape)
 if not np.array_equal(q,K):raise RuntimeError('bitplanes')
 c.append((sum(map(len,bl))+4*nb+40,'zigzag_bitplanes',q))
 return min(c,key=lambda x:x[0])

def pred(R,c,t,mode):
 z=0
 t1=int(R[c,t-1]) if t>0 else 0
 t2=int(R[c,t-2]) if t>1 else t1
 l=int(R[c-1,t]) if c>0 else t1
 d=int(R[c-1,t-1]) if c>0 and t>0 else l
 if mode=='fixed0':return 0
 if mode=='time1':return t1
 if mode=='time2':return 2*t1-t2
 if mode=='time15':return (3*t1-t2)//2
 if mode=='left':return l
 if mode=='avg_t_l':return (t1+l)//2
 if mode=='frac_lorenzo':return t1+(l-d)//2
 if mode=='frac_accel':return t1+(t1-t2)//2
 if mode=='frac_both':return t1+((t1-t2)+(l-d))//2
 if mode=='median3':return int(np.median(np.asarray([t1,l,t1+l-d],np.int64)))
 raise ValueError(mode)

def encode_source(X,eps,mode):
 if STEP/2>eps:raise RuntimeError(('step illegal',eps))
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32);P=np.zeros(X.shape,np.int32)
 # time-major raster makes left-current and same-channel history decoder-known.
 for t in range(X.shape[1]):
  for c in range(X.shape[0]):
   p=pred(R,c,t,mode);k=int(np.rint((float(X[c,t])-p)/STEP));r=p+STEP*k
   if abs(float(X[c,t])-r)>STEP/2+1e-9:raise RuntimeError(('rounding',mode,c,t,X[c,t],p,k,r))
   P[c,t]=p;K[c,t]=k;R[c,t]=r
 frame=encode_k(K);Kd=frame[2]
 Rd=np.zeros_like(R)
 for t in range(X.shape[1]):
  for c in range(X.shape[0]):Rd[c,t]=pred(Rd,c,t,mode)+STEP*int(Kd[c,t])
 if not np.array_equal(Rd,R):raise RuntimeError(('recursive decode',mode))
 me=float(np.max(np.abs(X-Rd.astype(np.float64))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard error',mode,me,eps))
 return {'bytes':frame[0]+16,'rep':frame[1],'maxerr':me,'k_zero_fraction':float(np.mean(K==0)),'k_abs1_fraction':float(np.mean(np.abs(K)==1)),'k_std':float(K.std()),'phase_unique':int(np.unique(np.mod(P,256)).size),'phase_entropy':entropy(np.mod(P,256))}

def entropy(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb,ori=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'local_std':float(X.std())})
   for mode in MODES:
    r=encode_source(X,eps,mode);r.update({'tile':name,'mode':mode,'sz3_bytes':sb,'gain_vs_sz3':sb/r['bytes'],'bps':8*r['bytes']/X.size});rows.append(r);print(json.dumps(r),flush=True)
  combos=[];sz=sum(x['sz3_bytes'] for x in tiles);n=C*T*len(tiles)
  for mode in MODES:
   rr=[r for r in rows if r['mode']==mode];b=sum(r['bytes'] for r in rr)
   combos.append({'mode':mode,'bytes':b,'sz3_bytes':sz,'bps':8*b/n,'gain_vs_sz3':sz/b,'gain_vs_fixed0':sum(r['bytes'] for r in rows if r['mode']=='fixed0')/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'median_k_zero_fraction':float(np.median([r['k_zero_fraction'] for r in rr])),'median_phase_entropy':float(np.median([r['phase_entropy'] for r in rr]))})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'modes':list(MODES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Decoder-generated byte-phase automaton codec. For each causal spacetime sample, a frozen predictor computed only from already-decoded reconstructions produces an arbitrary integer P and therefore a free low-byte phase P mod 256. The encoder transmits only k=round((X-P)/256); reconstruction is P+256k, whose error is always <=128 < unchanged 10%-global-std epsilon. No low byte/phase field is transmitted. Fractional predictors intentionally create context-dependent byte phases. The complete k field is actually serialized/byte-decoded through a fixed raw/delta/Lorenzo/zigzag/XOR/Gray/bitplane Zstd menu, then the source is recursively reconstructed and hard-error verified. Four precommitted 128x1024 regimes and matched SZ3. Real-byte screen, no AI.'};print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_decoder_phase_automaton.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
