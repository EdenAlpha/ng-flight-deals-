#!/usr/bin/env python3
"""4x64 hierarchical scale test for migrated/poststack 3-D seismic."""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_3d_codec as c
import migrated_volume_3d_entropy as entropy
c.pack=entropy.pack; c.unpack=entropy.unpack
import migrated_volume_3d_adaptive_v2 as av2
av2.install()
import migrated_volume_3d_context_entropy_v3 as ctx1
ctx1.install()
import migrated_volume_3d_context_entropy_v4 as ctx2
ctx2.install()
import migrated_volume_3d_brotli_bitplanes as br
import migrated_volume_3d_ft_half3d_brotli as fh3
from general_seismic_numeric_io import matched_sz3

TY,TX=4,64
TIDS=(av2.T_B128_L1,ctx1.T_B64_CTX,ctx1.T_B128L1_CTX,ctx2.T_B64_CTX2,ctx2.T_B128L1_CTX2)
MAGIC=b'MVH64V1\0'; HDR='<8sIIII'; HSZ=struct.calcsize(HDR); FRAME='<BI'; FSZ=struct.calcsize(FRAME)

def hard(a,b):return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))

def best_tile(X,eps):
 rows=[]
 for tid in TIDS:
  b,_=c.encode(X,eps,int(tid));Y,_=c.decode(b);e=hard(X,Y)
  if e>eps*(1+3e-6):raise RuntimeError(('hard common',tid,e,eps))
  rows.append((len(b),0,int(tid),c.NAMES[int(tid)],b))
 for fam,mod,name in ((1,br,'fast_delta_brotli_multitraversal'),(2,fh3,fh3.NAME)):
  q=mod.candidate(X,eps);rows.append((int(q['bytes']),fam,int(q['tid']),name,q['blob']))
 return min(rows,key=lambda q:(q[0],q[1],q[2]))

def decode_one(fam,b):
 if fam==0:return c.decode(b)[0]
 if fam==1:return br.decode(b)[0]
 if fam==2:return fh3.decode(b)[0]
 raise RuntimeError(('family',fam))

def encode_hier(X,eps):
 X=np.asarray(X,np.float32);ny,nx,nt=map(int,X.shape)
 if ny%TY or nx%TX:raise ValueError(('shape',X.shape))
 parts=[];counts={}
 for y in range(0,ny,TY):
  for x in range(0,nx,TX):
   q=best_tile(np.ascontiguousarray(X[y:y+TY,x:x+TX]),eps);parts.append(q);counts[q[3]]=counts.get(q[3],0)+1
 out=bytearray(struct.pack(HDR,MAGIC,ny,nx,nt,len(parts)))
 for L,fam,tid,name,b in parts:out.extend(struct.pack(FRAME,fam,L));out.extend(b)
 return bytes(out),counts

def decode_hier(blob):
 if len(blob)<HSZ:raise RuntimeError('short')
 magic,ny,nx,nt,n=struct.unpack(HDR,blob[:HSZ])
 if magic!=MAGIC or n!=(ny//TY)*(nx//TX):raise RuntimeError(('header',magic,ny,nx,n))
 Y=np.empty((ny,nx,nt),np.float64);p=HSZ;i=0
 for y in range(0,ny,TY):
  for x in range(0,nx,TX):
   fam,L=struct.unpack(FRAME,blob[p:p+FSZ]);p+=FSZ;q=decode_one(fam,blob[p:p+L]);p+=L
   if tuple(q.shape)!=(TY,TX,nt):raise RuntimeError(('tile shape',q.shape))
   Y[y:y+TY,x:x+TX]=q;i+=1
 if p!=len(blob) or i!=n:raise RuntimeError(('trailing',p,len(blob),i,n))
 return Y

def stream(objects,tag,eps):
 r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
  for wi,frac in enumerate(large.FRACTIONS):
   center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
   A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']]
   gi,block,minlen,ny,nx=large.choose_large_group(seg);X,ids=large.read_tile(rr,s,block,minlen,nx)
   # If the largest structural shape is not 4x64 divisible, crop only by the fixed outer shape ladder, never by values.
   ny2=(X.shape[0]//TY)*TY;nx2=(X.shape[1]//TX)*TX;X=np.ascontiguousarray(X[:ny2,:nx2])
   hb,counts=encode_hier(X,eps);Y=decode_hier(hb);me=hard(X,Y);sb,sme=matched_sz3(X,eps);gain=float(sb/len(hb))
   if me>eps*(1+3e-6) or sme>eps*(1+3e-6):raise RuntimeError(('hard',tag,wi,me,sme,eps))
   row={'window_index':wi,'window_fraction':frac,'shape':list(map(int,X.shape)),'samples':int(X.size),'ours_bytes':len(hb),'sz3_bytes':int(sb),'gain_vs_sz3':gain,'maxerr':me,'sz3_maxerr':float(sme),'mode_counts':counts}
   rows.append(row);print('MVH64',tag,wi,X.shape,sb,len(hb),gain,counts,flush=True)
  return {'logical_file':tag,'windows':rows}
 finally:rr.close()

def run(a):
 r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
 ss=[stream(oo,'assembled',eps)] if ds.get('assembly') else [stream([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
 out={'kind':'migrated-volume-hier64-v1','compression_class':'migrated_poststack_3d','dataset_id':a.dataset,'epsilon':eps,'tile_shape':[TY,TX],'positions':len(rows),'wins':sum(q['gain_vs_sz3']>1 for q in rows),'min_gain':min(q['gain_vs_sz3'] for q in rows),'median_gain':float(np.median([q['gain_vs_sz3'] for q in rows])),'byte_weighted_gain':sum(q['sz3_bytes'] for q in rows)/sum(q['ours_bytes'] for q in rows),'all_valid':True,'whole_outer_block_sz3':True,'all_framing_charged':True,'streams':ss}
 Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
