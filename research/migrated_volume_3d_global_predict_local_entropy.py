#!/usr/bin/env python3
"""Global causal prediction with spatially local context arithmetic entropy.

Prediction is performed over the entire native 3-D block, so cells retain
cross-boundary left/up dependencies. Only entropy modeling is spatially tiled,
which lets nonstationary migrated regions carry local probability models.
All predictor codes, local models, framing and payload bytes are serialized.
"""
from __future__ import annotations
import struct
import numpy as np
import migrated_volume_3d_codec as c
import migrated_volume_3d_entropy as ent
c.pack=ent.pack;c.unpack=ent.unpack
import migrated_volume_3d_adaptive_v2 as av2
av2.install()
import migrated_volume_3d_context_entropy_v3 as ctx1
ctx1.install()
import migrated_volume_3d_context_entropy_v4 as ctx2
ctx2.install()

MAGIC=b'MVGPLOCAL'
HDR='<9sddIIIHHHHII'
HSZ=struct.calcsize(HDR)
CELL='<III';CSZ=struct.calcsize(CELL)
CONFIGS=((64,'bits'),(128,'l1'))
TILES=((8,64),(4,64),(4,32))

def hard(a,b):return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))
def metric_id(m):return 0 if m=='bits' else 1
def metric_name(i):return 'bits' if int(i)==0 else 'l1'

def _cell_payload(R,codes,block):
 counts,nesc=ctx2.build_counts(R,codes,block);model=ctx2.pack_model(counts);arith,esc=ctx2.arithmetic_encode(R,codes,block,counts)
 return struct.pack(CELL,len(model),len(arith),len(esc))+model+arith+esc

def _cell_decode(body,codes,shape,block):
 if len(body)<CSZ:raise RuntimeError('short local cell')
 nm,na,ne=struct.unpack(CELL,body[:CSZ]);p=CSZ
 if p+nm+na+ne!=len(body):raise RuntimeError(('cell lengths',len(body),nm,na,ne))
 counts=ctx2.unpack_model(body[p:p+nm]);p+=nm;arith=body[p:p+na];p+=na;esc=body[p:p+ne]
 return ctx2.arithmetic_decode(arith,esc,codes,shape,block,counts)

def encode_config(X,eps,block,metric,ty,tx):
 X=np.asarray(X,np.float64);ny,nx,nt=X.shape
 if ny%ty or nx%tx:raise ValueError(('tile divide',X.shape,ty,tx))
 internal=float(eps)*c.MARGIN;step=2*internal;q=np.rint(X/step)
 if np.any((q<np.iinfo(np.int32).min)|(q>np.iinfo(np.int32).max)):raise OverflowError('quantized int32')
 Q=q.astype(np.int32);R,side=av2.forward(Q,int(block),metric);nb=(nt+block-1)//block;codes=np.frombuffer(side,np.uint8).reshape(ny,nx,nb);sideb=c.CCTX.compress(side)
 cells=[]
 for y in range(0,ny,ty):
  for x in range(0,nx,tx):cells.append(_cell_payload(np.ascontiguousarray(R[y:y+ty,x:x+tx]),np.ascontiguousarray(codes[y:y+ty,x:x+tx]),int(block)))
 h=struct.pack(HDR,MAGIC,float(eps),internal,ny,nx,nt,int(block),metric_id(metric),int(ty),int(tx),len(sideb),len(cells));out=bytearray(h);out.extend(sideb)
 for b in cells:out.extend(struct.pack('<I',len(b)));out.extend(b)
 return bytes(out),{'block':int(block),'metric':metric,'tile':[int(ty),int(tx)],'cells':len(cells),'side_bytes':len(sideb),'cell_bytes':sum(len(b)+4 for b in cells),'nonzero_fraction':float(np.mean(R!=0))}

def decode(blob):
 if len(blob)<HSZ:raise RuntimeError('short global-local stream')
 magic,eps,internal,ny,nx,nt,block,mid,ty,tx,ns,nc=struct.unpack(HDR,blob[:HSZ])
 if magic!=MAGIC or ny%ty or nx%tx or nc!=(ny//ty)*(nx//tx):raise RuntimeError(('global-local header',magic,ny,nx,ty,tx,nc))
 p=HSZ;sideb=blob[p:p+ns];p+=ns;side=c.DCTX.decompress(sideb);nb=(nt+block-1)//block;codes=np.frombuffer(side,np.uint8)
 if codes.size!=ny*nx*nb:raise RuntimeError(('global-local side',codes.size,ny,nx,nb))
 codes=codes.reshape(ny,nx,nb);R=np.empty((ny,nx,nt),np.int32)
 for y in range(0,ny,ty):
  for x in range(0,nx,tx):
   if p+4>len(blob):raise RuntimeError('short cell frame')
   L=struct.unpack('<I',blob[p:p+4])[0];p+=4
   if p+L>len(blob):raise RuntimeError('short cell body')
   R[y:y+ty,x:x+tx]=_cell_decode(blob[p:p+L],np.ascontiguousarray(codes[y:y+ty,x:x+tx]),(ty,tx,nt),int(block));p+=L
 if p!=len(blob):raise RuntimeError(('trailing global-local',p,len(blob)))
 Q=av2.inverse(R,side,int(block));return Q.astype(np.float64)*(2*float(internal)),{'shape':[ny,nx,nt],'block':int(block),'metric':metric_name(mid),'tile':[ty,tx],'eps':float(eps)}

def compete(X,eps):
 rows=[]
 for block,metric in CONFIGS:
  for ty,tx in TILES:
   if X.shape[0]%ty or X.shape[1]%tx:continue
   b,d=encode_config(X,eps,block,metric,ty,tx);Y,_=decode(b);me=hard(X,Y)
   if me>eps*(1+3e-6):raise RuntimeError(('global-local hard',block,metric,ty,tx,me,eps))
   rows.append({'bytes':len(b),'blob':b,'maxerr':me,'name':f'global_predict_{block}_{metric}_localctx_{ty}x{tx}','diag':d})
 return min(rows,key=lambda q:(q['bytes'],q['name'])),rows

def sanity():
 rng=np.random.default_rng(20260817);t=np.arange(257);X=np.empty((8,64,257),np.float32)
 for y in range(8):
  for x in range(64):X[y,x]=(70*np.sin((t+2*x+3*y)/21)+19*np.sin((t-x+y)/8)+rng.normal(0,2,t.size)).astype(np.float32)
 b,rows=compete(X,3.0);print('MV_GLOBAL_PREDICT_LOCAL_ENTROPY_OK',b['bytes'],b['name'],b['maxerr'],flush=True)
if __name__=='__main__':sanity()
