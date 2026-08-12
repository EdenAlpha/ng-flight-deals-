import json,sys,math
import h5py,numpy as np,zstandard as zstd,maxflow
from pysz import sz,szConfig,szErrorBoundMode

NC=64;NT=256;SAFETY=1-2e-5;EDGE=1.0;BIAS=.20
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6784))
STRATEGIES=('contour','zero','one','forced_majority')
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
  if not math.isfinite(me) or me>eps*(1+5e-6):raise RuntimeError(('sz hard',me,eps))
  row=(int(b.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def legal_integer_bounds(X,eps):
 b=eps*SAFETY
 lo=np.ceil(np.asarray(X,np.float64)-b).astype(np.int32);hi=np.floor(np.asarray(X,np.float64)+b).astype(np.int32)
 lo=np.maximum(lo,-32768);hi=np.minimum(hi,32767)
 if np.any(lo>hi):raise RuntimeError('empty integer hard box')
 return lo,hi

def graph_plane(allow0,allow1,strategy):
 nc,nt=allow0.shape;n=nc*nt
 if np.any(~allow0 & ~allow1):raise RuntimeError('no legal bit')
 g=maxflow.Graph[float](n,2*n);nodes=g.add_nodes(n)
 def ix(c,t):return c*nt+t
 for c in range(nc):
  for t in range(nt-1):g.add_edge(ix(c,t),ix(c,t+1),EDGE,EDGE)
 for c in range(nc-1):
  for t in range(nt):g.add_edge(ix(c,t),ix(c+1,t),EDGE,EDGE)
 forced0=int(np.sum(allow0 & ~allow1));forced1=int(np.sum(allow1 & ~allow0))
 majority=0 if forced0>=forced1 else 1
 BIG=1e6
 for c in range(nc):
  for t in range(nt):
   a0=bool(allow0[c,t]);a1=bool(allow1[c,t]);D0=D1=0.0
   if a0 and not a1:D1=BIG
   elif a1 and not a0:D0=BIG
   else:
    if strategy=='zero':D1=BIAS
    elif strategy=='one':D0=BIAS
    elif strategy=='forced_majority':
     if majority==0:D1=BIAS
     else:D0=BIAS
   # source-side label 0 has cut cost D0; sink-side label 1 has cost D1
   g.add_tedge(ix(c,t),D1,D0)
 g.maxflow();bits=np.empty((nc,nt),np.uint8)
 for c in range(nc):
  for t in range(nt):bits[c,t]=np.uint8(g.get_segment(ix(c,t)))
 if np.any((bits==0)&~allow0) or np.any((bits==1)&~allow1):raise RuntimeError(('graph violated forced bit',strategy))
 return bits,forced0,forced1

def synth(lo,hi,strategy):
 # Work in unsigned-biased 16-bit coordinate so binary prefixes are ordinary intervals.
 L=(lo.astype(np.int64)+32768).astype(np.int64);U=(hi.astype(np.int64)+32768).astype(np.int64)
 prefix=np.zeros(lo.shape,np.int64);planes=[];audit=[]
 for k in range(15,-1,-1):
  base=prefix << (k+1);mid=base+(1<<k);top=base+(1<<(k+1))-1
  a0=np.maximum(L,base)<=np.minimum(U,mid-1)
  a1=np.maximum(L,mid)<=np.minimum(U,top)
  bits,f0,f1=graph_plane(a0,a1,strategy);planes.append(bits.copy());
  audit.append({'bit':k,'flexible_fraction':float(np.mean(a0&a1)),'forced0_fraction':f0/bits.size,'forced1_fraction':f1/bits.size,'one_fraction':float(bits.mean()),'edge_fraction':float((np.sum(bits[:,1:]!=bits[:,:-1])+np.sum(bits[1:]!=bits[:-1]))/(bits.shape[0]*(bits.shape[1]-1)+(bits.shape[0]-1)*bits.shape[1]))})
  prefix=(prefix<<1)|bits.astype(np.int64)
 Y=prefix-32768
 if np.any(Y<lo)|np.any(Y>hi):raise RuntimeError(('prefix result outside box',strategy))
 return Y.astype(np.int32),planes,audit

def plane_rep(bits):
 bits=np.asarray(bits,np.uint8);nc,nt=bits.shape;c=[]
 variants={'raw':bits.copy(),'transpose':bits.T.copy()}
 xt=bits.copy();xt[:,1:]^=bits[:,:-1];variants['xort']=xt
 xs=bits.copy();xs[1:]^=bits[:-1];variants['xors']=xs
 for name,a in variants.items():
  raw=np.packbits(a.ravel(),bitorder='little').tobytes();bb=Z.compress(raw)
  dec=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:a.size].reshape(a.shape).astype(np.uint8)
  if name=='transpose':r=dec.T.copy()
  elif name=='xort':
   r=dec.copy()
   for j in range(1,nt):r[:,j]^=r[:,j-1]
  elif name=='xors':
   r=dec.copy()
   for i in range(1,nc):r[i]^=r[i-1]
  else:r=dec
  if not np.array_equal(r,bits):raise RuntimeError(('plane decode',name))
  c.append((len(bb)+6,name,r))
 return min(c,key=lambda x:x[0])

def encode_planes(Y,planes):
 # Rebuild unsigned word from decoded bitplanes. Planes are stored MSB->LSB.
 total=40;reps=[];decoded=[]
 for p in planes:
  b,n,r=plane_rep(p);total+=b;reps.append(n);decoded.append(r)
 u=np.zeros(Y.shape,np.uint32)
 for p in decoded:u=(u<<1)|p.astype(np.uint32)
 R=u.astype(np.int64)-32768
 if not np.array_equal(R,Y.astype(np.int64)):raise RuntimeError('word decode')
 return total,reps,R.astype(np.int32)

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;lo,hi=legal_integer_bounds(X,eps);sb,ori=szrun(X,eps);tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'local_std':float(X.std()),'eps_over_local_std':eps/float(X.std())})
   for strategy in STRATEGIES:
    Y,planes,audit=synth(lo,hi,strategy);bb,reps,R=encode_planes(Y,planes);me=float(np.max(np.abs(X-R.astype(np.float64))))
    if me>eps*(1+1e-9):raise RuntimeError(('hard error',name,strategy,me,eps))
    r={'tile':name,'strategy':strategy,'bytes':bb,'bps':8*bb/X.size,'sz3_bytes':sb,'gain_vs_sz3':sb/bb,'maxerr':me,'plane_reps':reps,'bit_audit':audit,'mean_flexible_fraction':float(np.mean([x['flexible_fraction'] for x in audit])),'low9_mean_flexible_fraction':float(np.mean([x['flexible_fraction'] for x in audit if x['bit']<=8])),'mean_edge_fraction':float(np.mean([x['edge_fraction'] for x in audit]))};rows.append(r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('bit_audit','plane_reps')},indent=2),flush=True)
  combos=[];sz=sum(x['sz3_bytes'] for x in tiles);n=NC*NT*len(tiles)
  for s in STRATEGIES:
   rr=[r for r in rows if r['strategy']==s];b=sum(r['bytes'] for r in rr)
   combos.append({'strategy':s,'bytes':b,'sz3_bytes':sz,'bps':8*b/n,'gain_vs_sz3':sz/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'median_low9_flexible_fraction':float(np.median([r['low9_mean_flexible_fraction'] for r in rr])),'median_plane_edge_fraction':float(np.median([r['mean_edge_fraction'] for r in rr]))})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'patch_shape':[NC,NT],'strategies':list(STRATEGIES),'edge_weight':EDGE,'bias':BIAS,'tiles':tiles,'combos':combos,'rows':rows,'scope':'Hierarchical binary hard-box codeword screen. Each source sample is represented only by its exact integer interval under the unchanged 10%-global-std bound. Starting at bit15 and descending to bit0 in unsigned-biased int16 coordinates, the current legal interval determines whether each bit is forced or flexible given the already chosen prefix. A global s-t min-cut chooses every flexible bit on the whole 2-D patch to minimize bitplane contour complexity with optional tiny 0/1 bias. The chosen prefix restricts the next plane, so all 16 bit decisions remain jointly compatible with one legal integer reconstruction. Every final bitplane is actually packed/Zstd serialized using decoder-real raw/transpose/temporal-XOR/spatial-XOR forms, byte-decoded, the 16-bit word rebuilt, and hard-error checked. Matched SZ3 is rerun on identical patches. No AI; patch screen only.'};print(json.dumps({'best':combos},indent=2));json.dump(out,open('imperial_hierarchical_bitplane_codeword.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
