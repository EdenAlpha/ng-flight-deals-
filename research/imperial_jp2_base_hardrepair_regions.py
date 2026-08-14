import io,json,sys
import h5py,numpy as np,zstandard as zstd
from PIL import Image,features
import imperial_huber_ar32_coldstart_arithmetic_regions as a

REGIONS=(('hard',512),('easy',2304),('medium',4608),('far',6784))
C=128;NT=8192;TB=1024;STEP=267
RATIOS=(4,6,8,12,16,24,32,48,64)
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()
DT=(np.dtype('i1'),np.dtype('<i2'),np.dtype('<i4'))

def dtype_id(x):
 lo=int(x.min()) if x.size else 0;hi=int(x.max()) if x.size else 0
 return 0 if -128<=lo and hi<=127 else (1 if -32768<=lo and hi<=32767 else 2)

def pack_int(x):
 k=dtype_id(x);b=Z.compress(np.ascontiguousarray(x).astype(DT[k],copy=False).tobytes());return bytes([k])+b

def unpack_int(b,shape):
 k=b[0];raw=D.decompress(b[1:]);n=int(np.prod(shape));return np.frombuffer(raw,DT[k],count=n).astype(np.int32).reshape(shape)

def correction_encode(Q):
 shape=Q.shape;c=[]
 # raw
 b=pack_int(Q);c.append(('raw',b,Q.copy()))
 # time delta
 T=Q.copy();T[:,1:]-=Q[:,:-1];b=pack_int(T);c.append(('time',b,np.cumsum(unpack_int(b,shape),axis=1,dtype=np.int32)))
 # spatial delta
 S=Q.copy();S[1:]-=Q[:-1];b=pack_int(S);c.append(('space',b,np.cumsum(unpack_int(b,shape),axis=0,dtype=np.int32)))
 # 2-D Lorenzo, inverted by 2-D prefix sum
 L=Q.copy();L[1:,1:]=Q[1:,1:]-Q[:-1,1:]-Q[1:,:-1]+Q[:-1,:-1];L[0,1:]=Q[0,1:]-Q[0,:-1];L[1:,0]=Q[1:,0]-Q[:-1,0]
 b=pack_int(L);Ld=unpack_int(b,shape);R=np.cumsum(np.cumsum(Ld,axis=0,dtype=np.int64),axis=1,dtype=np.int64).astype(np.int32);c.append(('lorenzo',b,R))
 # sparse exact Q
 m=(Q!=0).ravel(order='C');vals=Q.ravel(order='C')[m];mb=Z.compress(np.packbits(m,bitorder='little').tobytes());vb=pack_int(vals) if vals.size else b'\x00'+Z.compress(b'')
 md=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little')[:Q.size].astype(bool);vd=unpack_int(vb,(int(md.sum()),)).ravel();R=np.zeros(Q.size,np.int32);R[md]=vd;R=R.reshape(shape);sb=len(mb).to_bytes(4,'little')+mb+vb;c.append(('sparse',sb,R))
 good=[]
 for mode,b,R in c:
  if not np.array_equal(R,Q):raise RuntimeError(('correction decode',mode))
  good.append((len(b),mode,b))
 return min(good),float(np.mean(Q!=0))

def correction_decode(mode,b,shape):
 if mode=='raw':return unpack_int(b,shape)
 if mode=='time':return np.cumsum(unpack_int(b,shape),axis=1,dtype=np.int32)
 if mode=='space':return np.cumsum(unpack_int(b,shape),axis=0,dtype=np.int32)
 if mode=='lorenzo':return np.cumsum(np.cumsum(unpack_int(b,shape),axis=0,dtype=np.int64),axis=1,dtype=np.int64).astype(np.int32)
 if mode=='sparse':
  n=int.from_bytes(b[:4],'little');mb=b[4:4+n];vb=b[4+n:];m=np.unpackbits(np.frombuffer(D.decompress(mb),np.uint8),bitorder='little')[:int(np.prod(shape))].astype(bool);v=unpack_int(vb,(int(m.sum()),)).ravel();R=np.zeros(m.size,np.int32);R[m]=v;return R.reshape(shape)
 raise ValueError(mode)

def jp2(W,ratio):
 u=np.clip(W.astype(np.int32)+32768,0,65535).astype(np.uint16)
 im=Image.fromarray(u,mode='I;16');bio=io.BytesIO();im.save(bio,format='JPEG2000',quality_mode='rates',quality_layers=[float(ratio)],irreversible=True,mct=0)
 b=bio.getvalue();P=np.asarray(Image.open(io.BytesIO(b)),np.int32)-32768
 if P.shape!=W.shape:raise RuntimeError(('jp2 shape',P.shape,W.shape))
 return b,P

def tile(W,eps):
 best=None;allr=[]
 for ratio in RATIOS:
  bb,P=jp2(W,ratio);Q=np.rint((W.astype(np.float64)-P.astype(np.float64))/STEP).astype(np.int32);clen,mode,cb=correction_encode(Q);Qd=correction_decode(mode,cb,W.shape);R=P+STEP*Qd;me=float(np.max(np.abs(W.astype(np.float64)-R.astype(np.float64))))
  if me>eps*(1+1e-12):raise RuntimeError(('hard',ratio,mode,me,eps))
  total=len(bb)+len(cb)+32;rr={'ratio':ratio,'bytes':total,'base_bytes':len(bb),'correction_bytes':len(cb),'mode':mode,'correction_density':float(np.mean(Q!=0)),'base_rmse':float(np.sqrt(np.mean((W.astype(np.float64)-P.astype(np.float64))**2))),'base_maxerr':float(np.max(np.abs(W.astype(np.float64)-P.astype(np.float64)))),'maxerr':me};allr.append(rr)
  if best is None or total<best['bytes']:best=rr
 return best,allr

def main(path):
 if not features.check('jpg_2000'):raise RuntimeError('Pillow JPEG2000 support unavailable')
 a.NT=NT
 with h5py.File(path,'r') as f:
  d=f['Acoustic'];_,gs=a.m.stats(d);eps=.1*gs;rows=[]
  for name,c0 in REGIONS:
   X=np.asarray(d[:NT,c0:c0+C],np.float64).T;_,hu=a.fits(X);Rh,Kh=a.run_ar(X,hu);ab,_,_,Kd=a.arithmetic(Kh);Rd=a.decode_source(Kd,hu)
   if not np.array_equal(Rd,Rh):raise RuntimeError('AR decode')
   if float(np.max(np.abs(X-Rd.astype(np.float64))))>eps*(1+1e-12):raise RuntimeError('AR hard')
   total=0;tiles=[];sz=0
   for t0 in range(0,NT,TB):
    W=X[:,t0:t0+TB].astype(np.int32);q,screen=tile(W,eps);q['t0']=t0;q['screen']=screen;tiles.append(q);total+=q['bytes'];sb,_=a.m.szrun(X[:,t0:t0+TB],eps);sz+=int(sb)
   row={'region':name,'c0':c0,'samples':int(X.size),'jp2_repair_bytes':int(total),'jp2_repair_bps':8*total/X.size,'arithmetic_bytes':int(ab),'arithmetic_bps':8*ab/X.size,'sz3_bytes':int(sz),'sz3_bps':8*sz/X.size,'gain_vs_arithmetic':ab/total,'gain_vs_sz3':sz/total,'ratio_counts':{str(r):sum(t['ratio']==r for t in tiles) for r in RATIOS},'mean_correction_density':float(np.mean([t['correction_density'] for t in tiles])),'base_byte_fraction':float(sum(t['base_bytes'] for t in tiles)/total),'correction_byte_fraction':float(sum(t['correction_bytes'] for t in tiles)/total),'tiles':tiles};rows.append(row);print(json.dumps({k:v for k,v in row.items() if k!='tiles'},indent=2),flush=True)
  out={'global_std':gs,'eps':eps,'repair_step':STEP,'ratios':list(RATIOS),'rows':rows,'scope':'Dense two-layer transform pilot. Each 128x1024 source tile is encoded by a self-contained irreversible JPEG2000 9/7 wavelet base at one of a fixed rate menu; the base is explicitly allowed to violate the public max-error bound. After byte decode, only the exact integer repair Q=round((X-P)/267) is transmitted, using the smallest fully decoded raw/time-delta/space-delta/Lorenzo/sparse Zstd representation. The final integer reconstruction P+267Q has deterministic <=133.5 error, inside the unchanged Imperial epsilon. All JPEG2000, repair and 32 framing bytes are charged. The cheapest actual decoded rate wins per tile; no selector is required because the JPEG2000 stream contains its own quantization parameters. PR402 Huber AR32 cold-start arithmetic and matched SZ3 are rerun on identical full regions. No AI.'};json.dump(out,open('imperial_jp2_base_hardrepair_regions.json','w'),indent=2)
if __name__=='__main__':main(sys.argv[1])
