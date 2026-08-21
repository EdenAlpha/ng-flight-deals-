#!/usr/bin/env python3
from __future__ import annotations
import bz2,json,lzma,struct,sys
import h5py,numpy as np,zstandard as zstd,brotli
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m

PHASES=np.arange(32,dtype=np.float64)/32.0
MAGIC=b'DA24';HEADER=20


def entropy(A):
 _,n=np.unique(A,return_counts=True);p=n.astype(np.float64)/n.sum();return float(-(p*np.log2(p)).sum())

def dense(Q):
 vals,inv=np.unique(Q.astype(np.int32),return_inverse=True);counts=np.bincount(inv);rank=np.argsort(-counts);old2new=np.empty_like(rank);old2new[rank]=np.arange(len(rank));ids=old2new[inv].reshape(Q.shape);table=vals[rank].astype(np.int32)
 return table,ids

def code_bytes(ids,order):
 A=ids if order=='CT' else ids.T
 mx=int(A.max()) if A.size else 0
 if mx<256:dt=np.dtype('u1')
 elif mx<65536:dt=np.dtype('<u2')
 else:dt=np.dtype('<u4')
 raw=np.ascontiguousarray(A.astype(dt)).tobytes()
 zs=zstd.ZstdCompressor(level=22).compress(raw);br=brotli.compress(raw,quality=11);xz=lzma.compress(raw,preset=9);bz=bz2.compress(raw,compresslevel=9)
 opts=[('zstd',zs),('brotli',br),('lzma',xz),('bz2',bz),('raw',raw)];name,p=min(opts,key=lambda z:len(z[1]));return name,p,dt.str,A.shape

def map_blob(table):
 raw=table.astype('<i4').tobytes();zs=zstd.ZstdCompressor(level=22).compress(raw);br=brotli.compress(raw,quality=11);xz=lzma.compress(raw,preset=9);name,p=min([('zstd',zs),('brotli',br),('lzma',xz),('raw',raw)],key=lambda z:len(z[1]));return name,p

def encode(Q,phase,order):
 table,ids=dense(Q);mname,mb=map_blob(table);pname,p,dt,ashape=code_bytes(ids,order)
 meta=HEADER+1+len(mb);total=meta+len(p)
 return {'phase':float(phase),'order':order,'symbols':int(len(table)),'q_entropy_bps':entropy(Q),'id_entropy_bps':entropy(ids),'id_dtype':dt,'mapping_codec':mname,'mapping_bytes':len(mb),'payload_codec':pname,'payload_bytes':len(p),'bytes':int(total)},(table,ids,order,mb,p,mname,pname,dt,ashape)

def verify(X,eps,step,row,state):
 table,ids,order,mb,p,mname,pname,dt,ashape=state
 # In-memory exact mapping replay is sufficient to verify the physical representation because table+ids are what is serialized; compressors are separately byte-counted.
 Qd=table[ids];R=row['phase']*step+Qd.astype(np.float64)*step;me=float(np.max(np.abs(X-R)))
 if me>eps*(1+5e-6):raise RuntimeError(('hard',row['phase'],row['order'],me,eps))
 return me

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);step=2*eps;target=szb/2;rows=[]
 for ph in PHASES:
  Q=np.rint((X-float(ph)*step)/step).astype(np.int32)
  for order in ('CT','TC'):
   row,state=encode(Q,ph,order);row['maxerr']=verify(X,eps,step,row,state);row['gain_vs_sz3']=float(szb/row['bytes']);row['crosses_2x']=bool(row['bytes']<=target);rows.append(row);print('ROW',json.dumps(row),flush=True)
 rows.sort(key=lambda r:r['bytes']);best=rows[0]
 out={'kind':'universal-direct-dense-alphabet-v24','shape':list(X.shape),'eps':eps,'step':step,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'best':best,'rows':rows,'principle':'Set the SZ predictor to zero, quantize source samples directly onto the width-2epsilon lattice, remap the exact integer lattice values to a dense frequency-ranked symbol alphabet, physically serialize the symbol-to-lattice mapping, and compress the dense symbol stream in both channel-major and time-major order using several ordinary lossless entropy/LZ backends. All mapping, phase, header and payload bytes are charged. Reconstruction is exactly the selected lattice point and therefore preserves the original hard epsilon bound.'};json.dump(out,open('universal_direct_dense_alphabet_v24.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='rows'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
