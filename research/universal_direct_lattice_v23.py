#!/usr/bin/env python3
from __future__ import annotations
import json,struct,sys
import h5py,numpy as np,zstandard as zstd,brotli
import universal_auto_entropy_context_v7 as v7
import imperial_resonant_learned_law_address as g
import imperial_decoder_phase_automaton as m
import imperial_fair_ar_coarse_prefix_container as fair

PHASES=np.arange(16,dtype=np.float64)/16.0
BLOCKS=(32,64,128,256)
TOP_EXACT=6
Z=zstd.ZstdCompressor(level=19);D=zstd.ZstdDecompressor()

def entropy(a):
 _,n=np.unique(a,return_counts=True);p=n.astype(np.float64)/n.sum();return float(-(p*np.log2(p)).sum())

def pack_centers(C):
 C=np.asarray(C,np.int32);raw=C.astype('<i4').tobytes();zz=Z.compress(raw);bb=brotli.compress(raw,quality=11)
 if len(zz)<=len(bb):return bytes([0])+struct.pack('<I',len(zz))+zz
 return bytes([1])+struct.pack('<I',len(bb))+bb

def unpack_centers(blob,shape):
 method=blob[0];n=struct.unpack_from('<I',blob,1)[0];p=blob[5:5+n];raw=D.decompress(p) if method==0 else brotli.decompress(p);return np.frombuffer(raw,dtype='<i4').reshape(shape).astype(np.int32)

def quant(X,step,phase):
 P=np.asarray(phase,np.float64)
 if P.ndim==0:return np.rint((X-float(P)*step)/step).astype(np.int32)
 return np.rint((X-P[:,None]*step)/step).astype(np.int32)

def reconstruct(Q,step,phase):
 P=np.asarray(phase,np.float64)
 if P.ndim==0:return float(P)*step+Q.astype(np.float64)*step
 return P[:,None]*step+Q.astype(np.float64)*step

def channel_centers(Q):return np.rint(np.median(Q,axis=1)).astype(np.int32)[:,None]
def block_centers(Q,B):
 C=np.empty((Q.shape[0],(Q.shape[1]+B-1)//B),np.int32)
 for j,t0 in enumerate(range(0,Q.shape[1],B)):C[:,j]=np.rint(np.median(Q[:,t0:min(t0+B,Q.shape[1])],axis=1)).astype(np.int32)
 return C
def expand_centers(C,B,n):return np.repeat(C,B,axis=1)[:,:n]

def candidate(name,X,step,phase,center_kind=None,B=None):
 Q=quant(X,step,phase);cblob=b'';C=None
 if center_kind=='channel':C=channel_centers(Q);J=Q-C;cblob=pack_centers(C)
 elif center_kind=='block':C=block_centers(Q,B);J=Q-expand_centers(C,B,Q.shape[1]);cblob=pack_centers(C)
 else:J=Q
 phase_bytes=1 if np.asarray(phase).ndim==0 else 8 # 4-bit/channel packed conceptually plus header
 fast=int(m.encode_k(J)[0]);meta=16+phase_bytes+len(cblob);total=meta+fast
 return {'name':name,'phase':float(phase) if np.asarray(phase).ndim==0 else [float(x) for x in phase],'center_kind':center_kind,'block':B,'phase_bytes':phase_bytes,'center_bytes':len(cblob),'fast_field_bytes':fast,'fast_total_bytes':int(total),'q_entropy':entropy(Q),'j_entropy':entropy(J)},J,Q,C,cblob,meta

def main(path):
 with h5py.File(path,'r') as f:
  ds=f['Acoustic'];_,std=m.stats(ds);eps=.1*std;X=np.asarray(ds[g.T0:g.T0+g.T,g.C0:g.C0+g.C],np.float64).T
 szb,ori=m.szrun(X,eps);step=2.0*eps;target=szb/2.0;rows=[]
 # Global lattice phases, with and without per-channel relabeling.
 for ph in PHASES:
  for ck in (None,'channel'):
   row,J,Q,C,cblob,meta=candidate(f'global_phase_{ph:.4f}_{ck or "raw"}',X,step,float(ph),ck);rows.append((row['fast_total_bytes'],row,J,Q,C,cblob,meta));print('SCREEN',json.dumps(row),flush=True)
 # One phase per channel, selected only from that channel's own scalar entropy.
 bestph=np.zeros(X.shape[0],np.float64)
 for c in range(X.shape[0]):
  bestph[c]=min(PHASES,key=lambda ph:entropy(np.rint((X[c]-ph*step)/step).astype(np.int32)))
 row,J,Q,C,cblob,meta=candidate('per_channel_phase_plus_center',X,step,bestph,'channel');rows.append((row['fast_total_bytes'],row,J,Q,C,cblob,meta));print('SCREEN',json.dumps(row),flush=True)
 # Local integer relabeling does not change reconstruction at all; it only makes the symbol field cheaper.
 for B in BLOCKS:
  row,J,Q,C,cblob,meta=candidate(f'phase0_blockcenter_{B}',X,step,0.0,'block',B);rows.append((row['fast_total_bytes'],row,J,Q,C,cblob,meta));print('SCREEN',json.dumps(row),flush=True)
 exact=[]
 for ii in np.argsort([x[0] for x in rows])[:TOP_EXACT]:
  _,row,J,Q,C,cblob,meta=rows[int(ii)];fb,Jd,detail=v7.super_frame(J)
  if not np.array_equal(Jd,J):raise RuntimeError('J replay')
  if row['center_kind']=='channel':Cd=unpack_centers(cblob,C.shape);Qd=Jd+Cd
  elif row['center_kind']=='block':Cd=unpack_centers(cblob,C.shape);Qd=Jd+expand_centers(Cd,int(row['block']),J.shape[1])
  else:Qd=Jd
  ph=np.asarray(row['phase'],np.float64);R=reconstruct(Qd,step,ph);me=float(np.max(np.abs(X-R)))
  if me>eps*(1+5e-6):raise RuntimeError(('hard',row['name'],me,eps))
  total=meta+int(fb);z={**row,'field_bytes':int(fb),'bytes':int(total),'gain_vs_sz3':float(szb/total),'crosses_2x':bool(total<=target),'maxerr':me};exact.append(z);print('EXACT',json.dumps(z),flush=True)
 best=min(exact,key=lambda z:z['bytes']);out={'kind':'universal-direct-lattice-v23','shape':list(X.shape),'eps':eps,'step':step,'sz3_bytes':int(szb),'sz3_orientation':ori,'strict_2x_target_bytes':target,'best':best,'exact':exact,'screens':[x[1] for x in rows],
 'principle':'Include the most fundamental SZ-style fallback: no neighbour predictor at all. Quantize each source sample directly to the nearest point of a width-2epsilon reconstruction lattice, which guarantees max error <=epsilon. Search only the lattice phase, then optionally relabel the exact same lattice indices by per-channel or short-block integer centers; relabeling changes no reconstructed value but can reduce integer/bitplane cost. Phase IDs, packed centers, headers and actual residual bytes are charged. This tests whether prediction itself was whitening Imperial into a more expensive residual.'};json.dump(out,open('universal_direct_lattice_v23.json','w'),indent=2);print('FINAL',json.dumps({k:v for k,v in out.items() if k!='screens'},indent=2),flush=True)
if __name__=='__main__':main(sys.argv[1])
