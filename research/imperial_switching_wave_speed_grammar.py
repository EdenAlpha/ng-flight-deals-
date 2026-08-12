import json,sys,math
import h5py,numpy as np,zstandard as zstd
from pysz import sz,szConfig,szErrorBoundMode

NC=32;NT=64;SAFETY=1-1e-5;PHASE_FRAC=.5;B=8
SPECS=(('hard',14464,512),('easy',14464,2304),('medium',14464,4608),('far',14464,6880))
MODESETS={
 'single1':(8,),
 'two_05_1':(4,8),
 'near1':(6,7,8,9,10),
 'wide':(0,2,4,6,8,10,12),
}
PENALTIES=(0.0,1.0,4.0)
ZC=zstd.ZstdCompressor(level=19);ZD=zstd.ZstdDecompressor()

def stats(d):
 s=ss=0.;n=0
 for i in range(0,d.shape[0],2048):
  x=np.asarray(d[i:min(i+2048,d.shape[0])],np.float64);s+=float(x.sum());ss+=float((x*x).sum());n+=x.size
 m=s/n;return m,float(np.sqrt(max(0.,ss/n-m*m)))

def szrun(X,eps):
 best=None
 for tr in (False,True):
  A=np.ascontiguousarray((X.T if tr else X).astype(np.float32));cfg=szConfig();cfg.errorBoundMode=szErrorBoundMode.ABS;cfg.absErrorBound=float(eps)
  bb,_=sz.compress(A,cfg);R,_=sz.decompress(bb,np.float32,A.shape);me=float(np.max(np.abs(A-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('sz bound',me,eps))
  row=(int(bb.size),'T' if tr else 'CT')
  if best is None or row[0]<best[0]:best=row
 return best

def dtype_for(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  z=np.iinfo(dt)
  if mn>=z.min and mx<=z.max:return dt
 return np.dtype('<i8')

def pack_array(a):
 a=np.asarray(a);dt=dtype_for(a);blob=ZC.compress(np.ascontiguousarray(a).astype(dt).tobytes());r=np.frombuffer(ZD.decompress(blob),dtype=dt,count=a.size).astype(np.int32).reshape(a.shape)
 if not np.array_equal(r,a.astype(np.int32)):raise RuntimeError('array rt')
 return len(blob)+24,dt.str

def pack_modes(idx,nm):
 # fixed-width bit packing, then Zstd; decoder knows nm from frozen definition
 bits=max(1,int(math.ceil(math.log2(nm))));v=np.asarray(idx,np.uint8).ravel();total=v.size*bits;raw=np.zeros((total+7)//8,np.uint8)
 pos=0
 for x in v:
  y=int(x)
  for k in range(bits):
   if (y>>k)&1: raw[pos>>3]|=np.uint8(1<<(pos&7))
   pos+=1
 blob=ZC.compress(raw.tobytes());decraw=np.frombuffer(ZD.decompress(blob),np.uint8);out=np.empty(v.size,np.uint8);pos=0
 for i in range(v.size):
  y=0
  for k in range(bits):
   y|=((int(decraw[pos>>3])>>(pos&7))&1)<<k;pos+=1
  out[i]=y
 if not np.array_equal(out,v):raise RuntimeError('mode rt')
 return len(blob)+32,bits

def encode_defect(D):
 D=np.asarray(D,np.int32);c=[];rb,rdt=pack_array(D);c.append((rb,'raw_'+rdt))
 T=D.copy();T[:,1:]=D[:,1:]-D[:,:-1];tb,tdt=pack_array(T);c.append((tb+8,'time_delta_'+tdt))
 nz=D!=0;sup=ZC.compress(np.packbits(nz.ravel().astype(np.uint8),bitorder='little').tobytes());vals=D[nz];vdt=dtype_for(vals);vb=ZC.compress(vals.astype(vdt).tobytes()) if vals.size else b''
 mask=np.unpackbits(np.frombuffer(ZD.decompress(sup),np.uint8),bitorder='little')[:D.size].astype(bool).reshape(D.shape);vv=np.frombuffer(ZD.decompress(vb),dtype=vdt).astype(np.int32) if vals.size else np.empty(0,np.int32);R=np.zeros_like(D);R[mask]=vv
 if not np.array_equal(R,D):raise RuntimeError('defect rt')
 c.append((len(sup)+len(vb)+56,'sparse_'+vdt.str));return min(c)

def legal(X,eps):
 bd=eps*SAFETY;h=bd;phi=PHASE_FRAC*h;lo=np.ceil((X-bd-phi)/h-1e-12).astype(np.int32);hi=np.floor((X+bd-phi)/h+1e-12).astype(np.int32)
 if np.any(lo>hi):raise RuntimeError('empty legal');q=np.rint((X-phi)/h).astype(np.int32);q=np.minimum(np.maximum(q,lo),hi);return lo,hi,q,h,phi

def synth(lo,hi,q0,As,penalty):
 q=q0.copy();modes=np.zeros((NC-2,NT-2),np.uint8);D=np.zeros((NC-2,NT-2),np.int32);prev=np.full(NC-2,As.index(8) if 8 in As else 0,np.int16)
 # Boundaries + first two time slices remain nearest legal. Interior future states are generated greedily.
 for t in range(1,NT-1):
  lap=q[2:,t]-2*q[1:-1,t]+q[:-2,t]
  for j,c in enumerate(range(1,NC-1)):
   best=None
   for cand in range(int(lo[c,t+1]),int(hi[c,t+1])+1):
    qtt=cand-2*int(q[c,t])+int(q[c,t-1])
    for mi,A in enumerate(As):
     d=B*qtt-A*int(lap[j]);score=(1000.0 if d else 0.0)+math.log1p(abs(d))+penalty*(mi!=int(prev[j]))
     row=(score,abs(d),mi,cand,d)
     if best is None or row<best:best=row
   _,_,mi,cand,d=best;q[c,t+1]=cand;modes[j,t-1]=mi;D[j,t-1]=d;prev[j]=mi
 return q,modes,D

def decode(q,modes,D,As):
 R=np.zeros_like(q,np.int32);R[:,0]=q[:,0];R[:,1]=q[:,1];R[0,2:]=q[0,2:];R[-1,2:]=q[-1,2:]
 for t in range(1,NT-1):
  lap=R[2:,t]-2*R[1:-1,t]+R[:-2,t]
  A=np.asarray([As[int(x)] for x in modes[:,t-1]],np.int32);num=A*lap+D[:,t-1]
  if np.any(num%B):raise RuntimeError('nondivisible')
  R[1:-1,t+1]=2*R[1:-1,t]-R[1:-1,t-1]+num//B
 return R

def boundary_bytes(q):
 v=np.concatenate([q[:,0],q[:,1],q[0,2:],q[-1,2:]]);return pack_array(v)[0]

def entropy(a):
 _,n=np.unique(np.asarray(a).ravel(),return_counts=True);p=n/n.sum();return float(-(p*np.log2(p)).sum())

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=stats(d);eps=.1*std;tiles=[];rows=[]
  for name,t0,c0 in SPECS:
   X=np.asarray(d[t0:t0+NT,c0:c0+NC],np.float64).T;sb=szrun(X,eps);lo,hi,q0,h,phi=legal(X,eps);tiles.append({'tile':name,'sz3_bytes':sb[0],'sz3_bps':8*sb[0]/X.size,'local_std':float(X.std())})
   for sn,As in MODESETS.items():
    for pen in PENALTIES:
     q,M,D=synth(lo,hi,q0,list(As),pen);R=decode(q,M,D,list(As))
     if not np.array_equal(R,q):raise RuntimeError('decode mismatch')
     me=float(np.max(np.abs(X-(phi+h*R.astype(float)))))
     if me>eps*(1+5e-6):raise RuntimeError(('hard',me,eps))
     mb,modebits=pack_modes(M,len(As));de=encode_defect(D);bb=boundary_bytes(q);total=mb+de[0]+bb+72
     r={'tile':name,'modeset':sn,'A_values':list(As),'penalty':pen,'bytes':total,'bps':8*total/X.size,'sz3_bytes':sb[0],'gain_vs_sz3':sb[0]/total,'boundary_bytes':bb,'mode_bytes':mb,'mode_bits_raw':modebits,'mode_entropy_bps':entropy(M),'defect_bytes':de[0],'defect_rep':de[1],'defect_nonzero_fraction':float(np.mean(D!=0)),'defect_entropy_bps':entropy(D),'maxerr':me};rows.append(r)
     print(json.dumps(r),flush=True)
  combos=[];sz=sum(x['sz3_bytes'] for x in tiles);n=NC*NT*len(SPECS)
  for sn,As in MODESETS.items():
   for pen in PENALTIES:
    rr=[r for r in rows if r['modeset']==sn and r['penalty']==pen];tot=sum(r['bytes'] for r in rr)
    combos.append({'modeset':sn,'A_values':list(As),'penalty':pen,'bytes':tot,'sz3_bytes':sz,'bps':8*tot/n,'gain_vs_sz3':sz/tot,'median_mode_entropy_bps':float(np.median([r['mode_entropy_bps'] for r in rr])),'median_defect_nonzero':float(np.median([r['defect_nonzero_fraction'] for r in rr])),'median_defect_entropy_bps':float(np.median([r['defect_entropy_bps'] for r in rr])),'min_tile_gain':min(r['gain_vs_sz3'] for r in rr)})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'patch_shape':[NC,NT],'B':B,'tiles':tiles,'combos':combos,'rows':rows,'scope':'Switching-wave generative codec gate. Source samples are interval constraints. Starting from decoder-visible initial slices/boundaries, encoder chooses each future legal state jointly with a local propagation multiplier A/B from a frozen finite speed alphabet to minimize exact forcing plus optional speed-state switching cost. Decoder receives bitpacked/Zstd speed states and exact forcing, regenerates the patch recursively, and hard-error checks the unchanged 10%-global-std bound. Real serialized bytes; patch screen only.'};print(json.dumps({'best':combos[:10]},indent=2));json.dump(out,open('imperial_switching_wave_speed_grammar.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
