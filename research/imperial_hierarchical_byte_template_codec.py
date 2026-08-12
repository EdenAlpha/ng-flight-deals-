import json,sys,math
import h5py,numpy as np,zstandard as zstd
import imperial_hierarchical_bitplane_codeword as h

Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
STRATEGIES=h.STRATEGIES

def sdtype(a):
 a=np.asarray(a);mn=int(a.min()) if a.size else 0;mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4')):
  z=np.iinfo(dt)
  if mn>=z.min and mx<=z.max:return dt
 raise RuntimeError((mn,mx))
def udtype(a):
 a=np.asarray(a);mx=int(a.max()) if a.size else 0
 for dt in (np.dtype('u1'),np.dtype('<u2')):
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

def pack_signed(a):
 a=np.asarray(a,np.int32);dt=sdtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.int32).reshape(a.shape)
 return len(bb)+24,r,dt.str
def pack_unsigned(a):
 a=np.asarray(a,np.uint64);dt=udtype(a);bb=Z.compress(a.astype(dt).tobytes());r=np.frombuffer(D.decompress(bb),dt,count=a.size).astype(np.uint64).reshape(a.shape)
 return len(bb)+24,r,dt.str

def coarse_reps(B):
 B=np.asarray(B,np.int32);c=[]
 arr={'raw':B.copy()}
 a=B.copy();a[:,1:]=B[:,1:]-B[:,:-1];arr['dt']=a
 a=B.copy();a[1:]=B[1:]-B[:-1];arr['ds']=a
 a=B.copy();a[1:,1:]=B[1:,1:]-B[:-1,1:]-B[1:,:-1]+B[:-1,:-1];a[0,1:]=B[0,1:]-B[0,:-1];a[1:,0]=B[1:,0]-B[:-1,0];arr['lorenzo']=a
 for name,a in arr.items():
  n,r,dt=pack_signed(a)
  if name=='raw':Q=r
  elif name=='dt':Q=np.cumsum(r,axis=1,dtype=np.int32)
  elif name=='ds':Q=np.cumsum(r,axis=0,dtype=np.int32)
  else:Q=np.cumsum(np.cumsum(r,axis=0,dtype=np.int32),axis=1,dtype=np.int32)
  if not np.array_equal(Q,B):raise RuntimeError(('B signed',name))
  c.append((n+8,name+'_'+dt,Q))
 u=zig(B); variants={'zigzag':u.copy()}
 a=u.copy();a[:,1:]=u[:,1:]^u[:,:-1];variants['zigzag_xort']=a
 a=u.copy();a[1:]=u[1:]^u[:-1];variants['zigzag_xors']=a
 variants['gray']=gray(u)
 for name,a in variants.items():
  n,r,dt=pack_unsigned(a)
  if name=='zigzag':uu=r
  elif name=='zigzag_xort':
   uu=r.copy()
   for j in range(1,uu.shape[1]):uu[:,j]^=uu[:,j-1]
  elif name=='zigzag_xors':
   uu=r.copy()
   for i in range(1,uu.shape[0]):uu[i]^=uu[i-1]
  else:uu=ungray(r)
  Q=unzig(uu).reshape(B.shape)
  if not np.array_equal(Q,B):raise RuntimeError(('B unsigned',name))
  c.append((n+8,name+'_'+dt,Q))
 # Independent zigzag bitplanes; B is only a signed byte-ish symbol so <=8 bits after zigzag.
 mx=int(u.max()) if u.size else 0;nb=max(1,mx.bit_length());blobs=[]
 for k in range(nb):blobs.append(Z.compress(np.packbits(((u.ravel()>>k)&1).astype(np.uint8),bitorder='little').tobytes()))
 uu=np.zeros(u.size,np.uint64)
 for k,bb in enumerate(blobs):uu|=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:u.size].astype(np.uint64)<<k
 Q=unzig(uu.reshape(u.shape)).reshape(B.shape)
 if not np.array_equal(Q,B):raise RuntimeError('B bitplane')
 c.append((sum(map(len,blobs))+4*nb+32,'zigzag_bitplanes',Q))
 return min(c,key=lambda x:x[0])

def low_reps(L):
 L=np.asarray(L,np.uint8);c=[]
 def raw_variant(name,a,inv):
  bb=Z.compress(np.ascontiguousarray(a).tobytes());r=np.frombuffer(D.decompress(bb),np.uint8,count=a.size).reshape(a.shape);Q=inv(r)
  if not np.array_equal(Q,L):raise RuntimeError(('L rep',name))
  c.append((len(bb)+28,name,Q))
 raw_variant('raw',L.copy(),lambda r:r)
 xt=L.copy();xt[:,1:]=L[:,1:]^L[:,:-1]
 def invt(r):
  q=r.copy()
  for j in range(1,q.shape[1]):q[:,j]^=q[:,j-1]
  return q
 raw_variant('xort',xt,invt)
 xs=L.copy();xs[1:]=L[1:]^L[:-1]
 def invs(r):
  q=r.copy()
  for i in range(1,q.shape[0]):q[i]^=q[i-1]
  return q
 raw_variant('xors',xs,invs)
 # Bitplanes.
 blobs=[]
 for k in range(8):blobs.append(Z.compress(np.packbits(((L.ravel()>>k)&1).astype(np.uint8),bitorder='little').tobytes()))
 rr=np.zeros(L.size,np.uint8)
 for k,bb in enumerate(blobs):rr|=np.unpackbits(np.frombuffer(D.decompress(bb),np.uint8),bitorder='little')[:L.size].astype(np.uint8)<<k
 Q=rr.reshape(L.shape)
 if not np.array_equal(Q,L):raise RuntimeError('L bitplanes')
 c.append((sum(map(len,blobs))+4*8+36,'bitplanes',Q))
 # Mode + sparse deviations. Decoder receives one template byte, support and exact exception bytes.
 hist=np.bincount(L.ravel(),minlength=256);mode=int(np.argmax(hist));mask=L!=mode;sup=Z.compress(np.packbits(mask.ravel().astype(np.uint8),bitorder='little').tobytes());vals=L[mask]
 for vname,v in [('vals',vals),('xorvals',(vals^np.uint8(mode)).astype(np.uint8))]:
  vb=Z.compress(v.tobytes()) if v.size else b'';m=np.unpackbits(np.frombuffer(D.decompress(sup),np.uint8),bitorder='little')[:L.size].astype(bool).reshape(L.shape);vv=np.frombuffer(D.decompress(vb),np.uint8,count=v.size) if v.size else np.empty(0,np.uint8)
  if vname=='xorvals':vv=vv^np.uint8(mode)
  Q=np.full(L.shape,mode,np.uint8);Q[m]=vv
  if not np.array_equal(Q,L):raise RuntimeError(('L sparse',vname))
  c.append((len(sup)+len(vb)+48,'mode_sparse_'+vname,Q))
 best=min(c,key=lambda x:x[0]);return best,mode,float(hist[mode]/L.size)

def encode_word(Y):
 # Euclidean/floor quotient gives B in [-128,127], L in [0,255], exact R=256B+L.
 B=np.floor_divide(Y,256).astype(np.int32);L=(Y-256*B).astype(np.uint8)
 bn,brep,Bd=coarse_reps(B);(ln,lrep,Ld),mode,mfrac=low_reps(L);R=256*Bd.astype(np.int32)+Ld.astype(np.int32)
 if not np.array_equal(R,Y.astype(np.int32)):raise RuntimeError('word frame')
 return {'bytes':bn+ln+40,'B_bytes':bn,'B_rep':brep,'L_bytes':ln,'L_rep':lrep,'L_mode':mode,'L_mode_fraction':mfrac,'R':R}

def fixed_phase_baseline(X,phase):
 q=np.rint((X-float(phase))/256.0).astype(np.int32);Y=phase+256*q;return encode_word(Y.astype(np.int32))

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,std=h.stats(d);eps=.1*std;rows=[];tiles=[]
  for name,t0,c0 in h.SPECS:
   X=np.asarray(d[t0:t0+h.NT,c0:c0+h.NC],np.float64).T;lo,hi=h.legal_integer_bounds(X,eps);sb,ori=h.szrun(X,eps);base=fixed_phase_baseline(X,0);meb=float(np.max(np.abs(X-base['R'].astype(float))))
   if meb>eps*(1+1e-9):raise RuntimeError(('base hard',name,meb,eps))
   tiles.append({'tile':name,'sz3_bytes':sb,'sz3_bps':8*sb/X.size,'fixed256_bytes':base['bytes'],'fixed256_bps':8*base['bytes']/X.size,'fixed256_rep':[base['B_rep'],base['L_rep']],'local_std':float(X.std())})
   for strategy in STRATEGIES:
    Y,planes,audit=h.synth(lo,hi,strategy);fr=encode_word(Y);me=float(np.max(np.abs(X-fr['R'].astype(float))))
    if me>eps*(1+1e-9):raise RuntimeError(('hard',name,strategy,me,eps))
    r={'tile':name,'strategy':strategy,'bytes':fr['bytes'],'bps':8*fr['bytes']/X.size,'sz3_bytes':sb,'gain_vs_sz3':sb/fr['bytes'],'gain_vs_fixed256_sameframe':base['bytes']/fr['bytes'],'B_bytes':fr['B_bytes'],'B_rep':fr['B_rep'],'L_bytes':fr['L_bytes'],'L_rep':fr['L_rep'],'L_mode':fr['L_mode'],'L_mode_fraction':fr['L_mode_fraction'],'maxerr':me,'mean_highbit_flex':float(np.mean([a['flexible_fraction'] for a in audit if a['bit']>=8])),'mean_lowbit_flex':float(np.mean([a['flexible_fraction'] for a in audit if a['bit']<8]))};rows.append(r);print(json.dumps(r,indent=2),flush=True)
  combos=[];sz=sum(t['sz3_bytes'] for t in tiles);fb=sum(t['fixed256_bytes'] for t in tiles);n=h.NC*h.NT*len(tiles)
  for s in STRATEGIES:
   rr=[r for r in rows if r['strategy']==s];b=sum(r['bytes'] for r in rr)
   combos.append({'strategy':s,'bytes':b,'fixed256_bytes_sameframe':fb,'sz3_bytes':sz,'bps':8*b/n,'gain_vs_sz3':sz/b,'gain_vs_fixed256_sameframe':fb/b,'min_tile_gain':min(r['gain_vs_sz3'] for r in rr),'median_low_byte_mode_fraction':float(np.median([r['L_mode_fraction'] for r in rr])),'low_byte_bytes_fraction':sum(r['L_bytes'] for r in rr)/b})
  combos.sort(key=lambda x:x['bytes']);out={'std':std,'eps':eps,'patch_shape':[h.NC,h.NT],'strategies':list(STRATEGIES),'tiles':tiles,'combos':combos,'rows':rows,'scope':'Serialization follow-up to hierarchical hard-box bit synthesis. The same legal MSB-to-LSB graph-cut reconstructions from PR #295 are used, but the final 16-bit word is not transmitted as 16 independent planes. It is factored exactly into a signed coarse byte B=floor(R/256) and low byte L=R-256B. B uses decoder-real signed/delta/Lorenzo/zigzag/XOR/bitplane Zstd frames. L uses raw/XOR/bitplane or one transmitted modal low-byte template plus sparse exact deviations. Both are byte-decoded and recombined before the unchanged hard-error check. A fixed phase-0 256-grid baseline is encoded through the same B+L framing, isolating whether the synthesized low-byte freedom actually buys coarse-byte simplification. Patch screen only, no AI.'};print(json.dumps({'combos':combos},indent=2));json.dump(out,open('imperial_hierarchical_byte_template_codec.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
