import json,sys
import h5py,numpy as np,zstandard as zstd
import imperial_decoder_phase_automaton as m

SPECS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TRAIN=1024;P=32;STEP=267;TB=1024;MODEL_BYTES=177
SHAPES=((4,32),(8,32),(8,64),(16,32),(16,64),(32,32))
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def fit_shared_ar(X):
 rows=[];ys=[]
 for c in range(X.shape[0]):
  x=np.asarray(X[c,:TRAIN],np.float64)
  for t in range(P,TRAIN):
   rows.append(np.r_[1.0,x[t-P:t][::-1]]);ys.append(x[t])
 A=np.asarray(rows,np.float64);y=np.asarray(ys,np.float64)
 return np.linalg.lstsq(A,y,rcond=None)[0].astype(np.float32)

def run_ar(X,coef):
 R=np.zeros(X.shape,np.int32);K=np.zeros(X.shape,np.int32)
 b=np.asarray(coef[1:],np.float32);a=float(coef[0])
 for c in range(X.shape[0]):
  for t in range(X.shape[1]):
   if t<P:p=0
   else:p=int(np.rint(a+float(np.dot(b,R[c,t-P:t][::-1].astype(np.float32)))))
   k=int(np.rint((float(X[c,t])-p)/STEP));K[c,t]=k;R[c,t]=p+STEP*k
 return R,K

def zig(a):
 a=np.asarray(a,np.int64);return ((a<<1)^(a>>63)).astype(np.uint64)
def unzig(u):
 u=np.asarray(u,np.uint64);return ((u>>1).astype(np.int64)^-(u&1).astype(np.int64)).astype(np.int32)
def bw(v):
 x=int(np.max(v)) if np.size(v) else 0
 return x.bit_length()

def tiles(K,cs,ts,order):
 cc=range(0,K.shape[0],cs);tt=range(0,K.shape[1],ts)
 if order=='CT':
  for c0 in cc:
   for t0 in tt:yield c0,t0,K[c0:min(c0+cs,K.shape[0]),t0:min(t0+ts,K.shape[1])]
 else:
  for t0 in tt:
   for c0 in cc:yield c0,t0,K[c0:min(c0+cs,K.shape[0]),t0:min(t0+ts,K.shape[1])]

def pack_bits(values,width):
 v=np.asarray(values,np.uint64).ravel()
 if width==0:return np.empty(0,np.uint8),0
 bits=((v[:,None]>>np.arange(width,dtype=np.uint64))&1).astype(np.uint8).ravel()
 return np.packbits(bits,bitorder='little'),int(bits.size)

def unpack_bits(raw,offset,n,width):
 if width==0:return np.zeros(n,np.uint64),offset
 bits=np.unpackbits(raw,bitorder='little')
 q=bits[offset:offset+n*width].reshape(n,width).astype(np.uint64)
 v=np.sum(q<<np.arange(width,dtype=np.uint64),axis=1,dtype=np.uint64)
 return v,offset+n*width

def encode_zero_bitwidth(K,cs,ts,order):
 desc=[];pieces=[];total_bits=0
 for c0,t0,A in tiles(K,cs,ts,order):
  u=zig(A);w=bw(u);p,nb=pack_bits(u,w);desc.append((c0,t0,A.shape[0],A.shape[1],w,nb));pieces.append((u,w,nb))
 widths=np.asarray([x[4] for x in desc],np.uint8);mapb=Z.compress(widths.tobytes())
 bit_arrays=[]
 for u,w,nb in pieces:
  if w:bit_arrays.append(((u.ravel()[:,None]>>np.arange(w,dtype=np.uint64))&1).astype(np.uint8).ravel())
 allbits=np.concatenate(bit_arrays) if bit_arrays else np.empty(0,np.uint8)
 raw=np.packbits(allbits,bitorder='little').tobytes();payload=Z.compress(raw)
 wd=np.frombuffer(D.decompress(mapb),np.uint8,count=len(desc));raw_d=np.frombuffer(D.decompress(payload),np.uint8)
 bit_d=np.unpackbits(raw_d,bitorder='little');pos=0;Kd=np.zeros_like(K);j=0
 for c0,t0,h,w0,A in tiles(K,cs,ts,order):
  width=int(wd[j]);j+=1;n=A.size
  if width:
   q=bit_d[pos:pos+n*width].reshape(n,width).astype(np.uint64);u=np.sum(q<<np.arange(width,dtype=np.uint64),axis=1,dtype=np.uint64);pos+=n*width
  else:u=np.zeros(n,np.uint64)
  Kd[c0:c0+h,t0:t0+w0]=unzig(u).reshape(h,w0)
 if not np.array_equal(Kd,K):raise RuntimeError(('zero bitwidth decode',cs,ts,order))
 return len(mapb)+len(payload)+80,{'map':len(mapb),'payload':len(payload),'tiles':len(desc),'mean_width':float(widths.mean()),'max_width':int(widths.max()),'raw_packed_bytes':len(raw)}

def encode_range_bitwidth(K,cs,ts,order):
 desc=[];bit_arrays=[];mins=[];widths=[]
 for c0,t0,A in tiles(K,cs,ts,order):
  mn=int(A.min());v=(A.astype(np.int64)-mn).astype(np.uint64);w=bw(v);mins.append(mn);widths.append(w)
  if w:bit_arrays.append(((v.ravel()[:,None]>>np.arange(w,dtype=np.uint64))&1).astype(np.uint8).ravel())
  desc.append((c0,t0,A.shape[0],A.shape[1]))
 mins=np.asarray(mins,np.int32);widths=np.asarray(widths,np.uint8)
 minb=Z.compress(mins.astype('<i4').tobytes());mapb=Z.compress(widths.tobytes())
 allbits=np.concatenate(bit_arrays) if bit_arrays else np.empty(0,np.uint8);raw=np.packbits(allbits,bitorder='little').tobytes();payload=Z.compress(raw)
 md=np.frombuffer(D.decompress(minb),'<i4',count=len(desc));wd=np.frombuffer(D.decompress(mapb),np.uint8,count=len(desc));bit_d=np.unpackbits(np.frombuffer(D.decompress(payload),np.uint8),bitorder='little')
 pos=0;Kd=np.zeros_like(K)
 for j,(c0,t0,h,w0) in enumerate(desc):
  width=int(wd[j]);n=h*w0
  if width:
   q=bit_d[pos:pos+n*width].reshape(n,width).astype(np.uint64);v=np.sum(q<<np.arange(width,dtype=np.uint64),axis=1,dtype=np.uint64);pos+=n*width
  else:v=np.zeros(n,np.uint64)
  Kd[c0:c0+h,t0:t0+w0]=(v.astype(np.int64)+int(md[j])).astype(np.int32).reshape(h,w0)
 if not np.array_equal(Kd,K):raise RuntimeError(('range bitwidth decode',cs,ts,order))
 return len(minb)+len(mapb)+len(payload)+96,{'mins':len(minb),'map':len(mapb),'payload':len(payload),'tiles':len(desc),'mean_width':float(widths.mean()),'max_width':int(widths.max()),'raw_packed_bytes':len(raw)}

def main(path):
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gstd=m.stats(d);eps=.1*gstd;rows=[]
  for name,c0 in SPECS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;coef=fit_shared_ar(X);R,K=run_ar(X,coef);me=float(np.max(np.abs(X-R.astype(np.float64))))
   if me>eps*(1+1e-12):raise RuntimeError((name,me,eps))
   base=MODEL_BYTES;sz=0;candidates={}
   for cs,ts in SHAPES:
    for order in ('CT','TC'):
     for mode in ('zero','range'):candidates[(mode,cs,ts,order)]={'bytes':MODEL_BYTES,'frames':[]}
   for t0 in range(TRAIN,NT,TB):
    KK=K[:,t0:t0+TB];n,rep,Kd=m.encode_k(KK);base+=n
    if not np.array_equal(Kd,KK):raise RuntimeError('baseline decode')
    sb,_=m.szrun(X[:,t0:t0+TB],eps);sz+=sb
    for key,v in candidates.items():
     mode,cs,ts,order=key
     if mode=='zero':nn,meta=encode_zero_bitwidth(KK,cs,ts,order)
     else:nn,meta=encode_range_bitwidth(KK,cs,ts,order)
     v['bytes']+=nn;v['frames'].append(meta)
   samples=C*(NT-TRAIN);base_bps=8*base/samples;szbps=8*sz/samples
   cr=[]
   for key,v in candidates.items():
    b=v['bytes'];mode,cs,ts,order=key
    cr.append({'mode':mode,'microshape':[cs,ts],'order':order,'bytes':b,'bps':8*b/samples,'gain_vs_incumbent':base/b,'gain_vs_sz3':sz/b,'mean_width':float(np.mean([x['mean_width'] for x in v['frames']])),'map_bytes':int(sum(x['map'] for x in v['frames'])),'payload_bytes':int(sum(x['payload'] for x in v['frames'])),'extra_base_bytes':int(sum(x.get('mins',0) for x in v['frames']))})
   cr.sort(key=lambda x:x['bytes']);best=cr[0]
   row={'region':name,'c0':c0,'samples':samples,'incumbent_bytes':base,'incumbent_bps':base_bps,'sz3_bytes':sz,'sz3_bps':szbps,'incumbent_gain_vs_sz3':sz/base,'best':best,'top5':cr[:5],'maxerr':me}
   rows.append(row);print(json.dumps(row,indent=2),flush=True)
 out={'global_std':gstd,'eps':eps,'ar_order':P,'step':STEP,'heldout':[TRAIN,NT],'rows':rows,'scope':'Real-byte backend experiment on the current decoder-real shared AR32 + step267 innovation field. The AR model is fit only from t<1024, then frozen. Held-out K frames are unchanged, so reconstruction and the hard error contract are identical to the incumbent. Instead of global zigzag bitplanes, each candidate partitions K into fixed microblocks, transmits a Zstd-compressed bit-width map (and for range mode a compressed local minimum map), packs every microblock at exactly its needed width, Zstd-compresses the packed payload, byte-decodes it back to exact K, and charges conservative framing. Both channel-major and time-major microblock orders and six precommitted shapes are tested. This directly tests whether the high-kurtosis/heteroskedastic innovation field exposed by PR #369 contains cheap local activity structure that the incumbent global bitplanes miss. No AI; diagnostic codec gate; do not merge.'}
 json.dump(out,open('imperial_ar32_activity_bitpack.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
