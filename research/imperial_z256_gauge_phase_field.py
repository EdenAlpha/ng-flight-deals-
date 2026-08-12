import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

C=64;T=512;STEP=256;SWEEPS=2
SPECS=(('hard',14488,512),('easy',14488,2304),('medium',14488,4608),('far',14488,6784))
OBJECTIVES=('l1','contour')
INITS=('zero','alternating','ramp')
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
  if me>eps*(1+5e-6):raise RuntimeError(('sz',me,eps))
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

def B_from(X,r,s):
 P=((r[:,None].astype(np.int16)+s[None,:].astype(np.int16))&255).astype(np.int32)
 B=np.rint((X.astype(np.float64)-P)/256.0).astype(np.int32)
 R=P+256*B
 return B,P,R

def edge_score(B,obj):
 dt=np.diff(B.astype(np.int32),axis=1);ds=np.diff(B.astype(np.int32),axis=0)
 if obj=='l1':return int(np.abs(dt).sum()+np.abs(ds).sum())
 return int(np.count_nonzero(dt)+np.count_nonzero(ds))

def row_cost(X,c,rval,s,r_current,B,obj):
 P=((int(rval)+s.astype(np.int16))&255).astype(np.int32);b=np.rint((X[c].astype(np.float64)-P)/256.0).astype(np.int32)
 z=0
 d=np.diff(b)
 z+=int(np.abs(d).sum()) if obj=='l1' else int(np.count_nonzero(d))
 for cc in (c-1,c+1):
  if 0<=cc<C:
   d=b-B[cc]
   z+=int(np.abs(d).sum()) if obj=='l1' else int(np.count_nonzero(d))
 return z

def col_cost(X,t,sval,r,s_current,B,obj):
 P=((r.astype(np.int16)+int(sval))&255).astype(np.int32);b=np.rint((X[:,t].astype(np.float64)-P)/256.0).astype(np.int32)
 z=0
 d=np.diff(b)
 z+=int(np.abs(d).sum()) if obj=='l1' else int(np.count_nonzero(d))
 for tt in (t-1,t+1):
  if 0<=tt<T:
   d=b-B[:,tt]
   z+=int(np.abs(d).sum()) if obj=='l1' else int(np.count_nonzero(d))
 return z

def optimize(X,obj,init):
 r=np.zeros(C,np.uint8);s=np.zeros(T,np.uint8)
 if init=='alternating':s[1::2]=128
 elif init=='ramp':s=np.mod(np.arange(T)*17,256).astype(np.uint8)
 B,_,_=B_from(X,r,s)
 for _ in range(SWEEPS):
  for c in range(C):
   vals=[row_cost(X,c,v,s,r,B,obj) for v in range(256)];v=int(np.argmin(vals));r[c]=v;B[c]=B_from(X[c:c+1],r[c:c+1],s)[0][0]
  for t in range(T):
   vals=[col_cost(X,t,v,r,s,B,obj) for v in range(256)];v=int(np.argmin(vals));s[t]=v;B[:,t]=B_from(X[:,t:t+1],r,np.asarray([s[t]],np.uint8))[0][:,0]
 return r,s,B,edge_score(B,obj)

def pack_signed(a):
 a=np.asarray(a,np.int32);dt=sdtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.int32).reshape(a.shape);return len(bb)+28,r,dt.str
def pack_unsigned(a):
 a=np.asarray(a,np.uint64);dt=udtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.uint64).reshape(a.shape);return len(bb)+28,r,dt.str

def encode_B(B):
 B=np.asarray(B,np.int32);c=[]
 arr={'raw':B.copy()}
 a=B.copy();a[:,1:]=B[:,1:]-B[:,:-1];arr['dt']=a
 a=B.copy();a[1:]=B[1:]-B[:-1];arr['ds']=a
 a=B.copy();a[1:,1:]=B[1:,1:]-B[:-1,1:]-B[1:,:-1]+B[:-1,:-1];a[0,1:]=B[0,1:]-B[0,:-1];a[1:,0]=B[1:,0]-B[:-1,0];arr['lorenzo']=a
 for name,a in arr.items():
  n,q,dt=pack_signed(a)
  if name=='raw':R=q
  elif name=='dt':R=np.cumsum(q,axis=1,dtype=np.int32)
  elif name=='ds':R=np.cumsum(q,axis=0,dtype=np.int32)
  else:R=np.cumsum(np.cumsum(q,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
  if not np.array_equal(R,B):raise RuntimeError(name)
  c.append((n+8,name+'_'+dt,R))
 u=zig(B);vars={'zigzag':u.copy()};x=u.copy();x[:,1:]=u[:,1:]^u[:,:-1];vars['xort']=x;x=u.copy();x[1:]=u[1:]^u[:-1];vars['xors']=x
 for name,a in vars.items():
  n,q,dt=pack_unsigned(a)
  if name=='zigzag':uu=q
  elif name=='xort':
   uu=q.copy()
   for j in range(1,T):uu[:,j]^=uu[:,j-1]
  else:
   uu=q.copy()
   for i in range(1,C):uu[i]^=uu[i-1]
  R=unzig(uu).reshape(B.shape)
  if not np.array_equal(R,B):raise RuntimeError(name)
  c.append((n+8,'zigzag_'+name+'_'+dt,R))
 mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());bl=[]
 for k in range(nb):bl.append(Z.compress(np.packbits(((u.ravel()>>k)&1).astype(np.uint8),bitorder='little').tobytes()))
 uu=np.zeros(u.size,np.uint64)
 for k,bb in enumerate(bl):uu|=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:u.size].astype(np.uint64)<<k
 R=unzig(uu.reshape(u.shape)).reshape(B.shape)
 if not np.array_equal(R,B):raise RuntimeError('bitplane')
 c.append((sum(map(len,bl))+4*nb+36,'zigzag_bitplanes',R))
 return min(c,key=lambda x:x[0])

def factor_frame(r,s):
 rb=Z.compress(np.asarray(r,np.uint8).tobytes());sb=Z.compress(np.asarray(s,np.uint8).tobytes());rr=np.frombuffer(D.decompress(rb),np.uint8,count=C);ss=np.frombuffer(D.decompress(sb),np.uint8,count=T)
 if not np.array_equal(rr,r) or not np.array_equal(ss,s):raise RuntimeError('factor')
 return len(rb)+len(sb)+40,rr,ss

def eval_def(X,eps,r,s,obj,init,proxy):
 B,P,R=B_from(X,r,s);me=float(np.max(np.abs(X-R.astype(float))))
 if me>eps*(1+1e-12):raise RuntimeError(('hard',me,eps))
 bf=encode_B(B);ff,rr,ss=factor_frame(r,s);Bd=bf[2];Pd=((rr[:,None].astype(np.int16)+ss[None,:].astype(np.int16))&255).astype(np.int32);Rd=Pd+256*Bd
 if not np.array_equal(Rd,R):raise RuntimeError('decode')
 return {'bytes':bf[0]+ff+16,'B_bytes':bf[0],'B_rep':bf[1],'factor_bytes':ff,'factor_bps':8*ff/X.size,'bps':8*(bf[0]+ff+16)/X.size,'maxerr':me,'objective':obj,'init':init,'proxy':proxy,'r_entropy':H(r),'s_entropy':H(s),'phase_entropy':H(P),'B_edge_l1':edge_score(B,'l1'),'B_edge_contour':edge_score(B,'contour')}
def H(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+T,c0:c0+C],np.float64).T;sb,ori=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'local_std':float(X.std())})
   r0=np.zeros(C,np.uint8);s0=np.zeros(T,np.uint8);base=eval_def(X,eps,r0,s0,'baseline','zero',edge_score(B_from(X,r0,s0)[0],'l1'));base.update({'tile':name,'kind':'fixed0','sz3_bytes':sb,'gain_vs_sz3':sb/base['bytes']});rows.append(base)
   for obj in OBJECTIVES:
    for init in INITS:
     r,s,B,proxy=optimize(X,obj,init);q=eval_def(X,eps,r,s,obj,init,proxy);q.update({'tile':name,'kind':'z256_gauge','sz3_bytes':sb,'gain_vs_sz3':sb/q['bytes'],'gain_vs_fixed0':base['bytes']/q['bytes']});rows.append(q);print(json.dumps(q),flush=True)
  combos=[];sz=sum(x['sz3_bytes'] for x in tiles);n=C*T*len(tiles)
  for kind,obj,init in [('fixed0','baseline','zero')]+[('z256_gauge',o,i) for o in OBJECTIVES for i in INITS]:
   rr=[r for r in rows if r['kind']==kind and r['objective']==obj and r['init']==init];b=sum(r['bytes'] for r in rr)
   combos.append({'kind':kind,'objective':obj,'init':init,'bytes':b,'sz3_bytes':sz,'bps':8*b/n,'gain_vs_sz3':sz/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'mean_factor_bps':float(np.mean([r['factor_bps'] for r in rr]))})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'step':STEP,'patch_shape':[C,T],'sweeps':SWEEPS,'objectives':list(OBJECTIVES),'inits':list(INITS),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Full-byte Z_256 gauge phase screen. Because epsilon>128, every sample may use any integer byte phase P and still has a legal point P+256B. Instead of transmitting P per sample, constrain P(c,t)=r(c)+s(t) mod256, giving 256^(C+T-1) legal phase fields for only C+T byte factors. Coordinate descent optimizes row/time factors under coarse-byte L1-delta or contour proxy. Factors and exact coarse B are actually Zstd serialized/decoded; reconstruction P+256B is hard-error verified. Fixed P=0 uses identical framing. Four precommitted 64x512 regimes and matched SZ3. Real-byte screen, no AI.'};print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_z256_gauge_phase_field.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
