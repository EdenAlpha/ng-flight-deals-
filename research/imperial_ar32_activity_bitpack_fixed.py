import sys
import numpy as np
import imperial_ar32_activity_bitpack as a

def encode_zero_bitwidth(K,cs,ts,order):
 desc=[];pieces=[]
 for c0,t0,A in a.tiles(K,cs,ts,order):
  u=a.zig(A);w=a.bw(u);_,nb=a.pack_bits(u,w);desc.append((c0,t0,A.shape[0],A.shape[1],w,nb));pieces.append((u,w,nb))
 widths=np.asarray([x[4] for x in desc],np.uint8);mapb=a.Z.compress(widths.tobytes())
 bit_arrays=[]
 for u,w,nb in pieces:
  if w:bit_arrays.append(((u.ravel()[:,None]>>np.arange(w,dtype=np.uint64))&1).astype(np.uint8).ravel())
 allbits=np.concatenate(bit_arrays) if bit_arrays else np.empty(0,np.uint8)
 raw=np.packbits(allbits,bitorder='little').tobytes();payload=a.Z.compress(raw)
 wd=np.frombuffer(a.D.decompress(mapb),np.uint8,count=len(desc));bit_d=np.unpackbits(np.frombuffer(a.D.decompress(payload),np.uint8),bitorder='little')
 pos=0;Kd=np.zeros_like(K)
 for j,(c0,t0,h,w0,_,_) in enumerate(desc):
  width=int(wd[j]);n=h*w0
  if width:
   q=bit_d[pos:pos+n*width].reshape(n,width).astype(np.uint64);u=np.sum(q<<np.arange(width,dtype=np.uint64),axis=1,dtype=np.uint64);pos+=n*width
  else:u=np.zeros(n,np.uint64)
  Kd[c0:c0+h,t0:t0+w0]=a.unzig(u).reshape(h,w0)
 if not np.array_equal(Kd,K):raise RuntimeError(('zero bitwidth decode',cs,ts,order))
 return len(mapb)+len(payload)+80,{'map':len(mapb),'payload':len(payload),'tiles':len(desc),'mean_width':float(widths.mean()),'max_width':int(widths.max()),'raw_packed_bytes':len(raw)}

a.encode_zero_bitwidth=encode_zero_bitwidth
if __name__=='__main__':a.main(sys.argv[1])
