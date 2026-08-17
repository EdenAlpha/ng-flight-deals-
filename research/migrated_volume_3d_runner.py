#!/usr/bin/env python3
"""Auto-discovered native-geometry screen for migrated SEG-Y volumes.

Geometry is inferred from trace-header run/reset structure, never dataset names.
The selected geometry only determines how the same numeric samples are arranged
as line x fast-position x time tiles. Our exact-stream 3-D codec and matched SZ3
receive the identical tile and public survey-global epsilon.
"""
from __future__ import annotations
import argparse,json,math,struct
from pathlib import Path
from urllib.parse import urlparse
import boto3,numpy as np
from botocore import UNSIGNED
from botocore.config import Config
from general_seismic_streaming_segy import S3ConcatSequential,SegySequential
from general_seismic_numeric_io import matched_sz3
import migrated_volume_3d_codec as codec

S3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10}))
FIELDS={'trace_seq_line':0,'trace_seq_file':4,'field_record':8,'trace_in_record':12,'source_point':16,'ensemble':20,'trace_in_ensemble':24,'offset':36,'source_x':72,'source_y':76,'group_x':80,'group_y':84,'cdp_x':180,'cdp_y':184,'inline':188,'crossline':192,'shotpoint':196}
SCAN=14000; NY=4; NX=32; MODE_OVERHEAD=8

def obj(uri):
 u=urlparse(uri);b=u.netloc;k=u.path.lstrip('/');h=S3.head_object(Bucket=b,Key=k);return {'bucket':b,'key':k,'size':int(h['ContentLength'])}
def header_value(th,e,off):return struct.unpack(e+'i',th[off:off+4])[0]
def read_header_matrix(r,s,n):
 if not s.binary_stride_exact or s.total_traces is None:raise RuntimeError(('3D screen needs exact fixed trace stride',s.ns_policy))
 n=min(int(n),int(s.total_traces));r.seek(s.trace_start);raw=r.read(n*s.binary_stride)
 if len(raw)<n*s.binary_stride:raise RuntimeError(('short header scan',len(raw),n*s.binary_stride))
 A=np.empty((n,len(FIELDS)),np.int64)
 for i in range(n):
  th=raw[i*s.binary_stride:i*s.binary_stride+240]
  for j,o in enumerate(FIELDS.values()):A[i,j]=header_value(th,s.endian,o)
 return A

def segments_from_boundaries(n,b):
 bb=np.unique(np.r_[0,np.asarray(b,int),n]);bb=bb[(bb>=0)&(bb<=n)];return [(int(bb[i]),int(bb[i+1])) for i in range(len(bb)-1) if bb[i+1]>bb[i]]
def geometry_candidates(A):
 n=A.shape[0];out=[];names=list(FIELDS)
 for j,name in enumerate(names):
  x=A[:,j];d=np.diff(x);chg=np.flatnonzero(d!=0)+1
  if 2<=chg.size<=n//4:
   seg=segments_from_boundaries(n,chg);lens=np.array([b-a for a,b in seg],float)
   if np.sum(lens>=NX)>=NY:
    out.append({'mode':'field_change:'+name,'segments':seg})
  ad=np.abs(d.astype(np.int64));nz=ad[ad>0]
  if nz.size>=4:
   med=float(np.median(nz));thr=max(1.,8.*med);jump=np.flatnonzero(ad>thr)+1
   if 2<=jump.size<=n//4:
    seg=segments_from_boundaries(n,jump);lens=np.array([b-a for a,b in seg],float)
    if np.sum(lens>=NX)>=NY:out.append({'mode':'large_reset:'+name,'segments':seg})
 # Deduplicate identical segmentations.
 seen=set();ded=[]
 for q in out:
  key=tuple(q['segments'])
  if key not in seen:seen.add(key);ded.append(q)
 return ded

def score_geometry(q,n):
 # Ignore scan-edge fragments when enough interior runs exist.
 seg=q['segments'];lens=np.array([b-a for a,b in seg],float);good=lens[lens>=NX]
 if good.size<NY:return -1e99
 med=float(np.median(good));mad=float(np.median(np.abs(good-med)));cons=1./(1.+mad/max(1.,med))
 # Prefer many coherent lines, but not pathological tiny runs.
 return float(good.size*cons*math.log1p(med))
def choose_geometry(A):
 cc=geometry_candidates(A)
 if not cc:raise RuntimeError('no coherent spatial line segmentation discovered')
 for q in cc:q['score']=score_geometry(q,A.shape[0])
 q=max(cc,key=lambda z:(z['score'],z['mode']))
 return q,[{'mode':x['mode'],'score':x['score'],'runs':len(x['segments']),'median_run':float(np.median([b-a for a,b in x['segments']]))} for x in sorted(cc,key=lambda z:-z['score'])[:12]]
def groups_from_segments(seg,max_tiles=2):
 # Find groups of NY consecutive sufficiently long runs. Spread choices within the scan.
 valid=[]
 for i in range(0,len(seg)-NY+1):
  block=seg[i:i+NY];lens=[b-a for a,b in block]
  if min(lens)>=NX:valid.append((i,block,min(lens)))
 if not valid:raise RuntimeError(('no rectangular 3D tile group',seg[:20]))
 picks=[]
 for pos in np.linspace(0,len(valid)-1,min(max_tiles,len(valid))).round().astype(int):
  q=valid[int(pos)]
  if q[0] not in [x[0] for x in picks]:picks.append(q)
 return picks
def read_tile(r,s,block,minlen):
 # Center the common fast-axis interval; sample positions align by index within each line.
 fast0=max(0,(int(minlen)-NX)//2);tile=[];indices=[]
 for a,b in block:
  st=int(a)+fast0
  r.seek(s.trace_start+st*s.binary_stride);s.trace_index=st;rows=[]
  for x in range(NX):
   q=s.next_trace()
   if q is None:raise RuntimeError(('unexpected eof',st,x))
   arr,th=q;rows.append(np.asarray(arr,np.float32));indices.append(st+x)
  tile.append(np.asarray(rows,np.float32))
 X=np.asarray(tile,np.float32)
 if X.ndim!=3 or X.shape[0]!=NY or X.shape[1]!=NX:raise RuntimeError(('bad tile shape',X.shape))
 return np.ascontiguousarray(X),indices

def screen_stream(oo,tag,eps,max_tiles=2):
 r=S3ConcatSequential(S3,oo,block_bytes=8*1024*1024)
 try:
  s=SegySequential(r);A=read_header_matrix(r,s,SCAN);geom,ranked=choose_geometry(A);groups=groups_from_segments(geom['segments'],max_tiles);rows=[]
  print('MV3D_GEOMETRY',tag,geom['mode'],'score',geom['score'],'top',ranked[:5],flush=True)
  for gi,block,minlen in groups:
   X,ids=read_tile(r,s,block,minlen);best,cands=codec.compete(X,eps);sb,sme=matched_sz3(X,eps);ours=int(best['bytes'])+MODE_OVERHEAD;gain=float(sb/ours)
   rows.append({'geometry_mode':geom['mode'],'group_index':gi,'shape':list(map(int,X.shape)),'trace_indices':[int(ids[0]),int(ids[-1])],'samples':int(X.size),'ours_bytes':ours,'codec_bytes':int(best['bytes']),'geometry_mode_overhead':MODE_OVERHEAD,'sz3_bytes':int(sb),'gain_vs_sz3':gain,'winner':codec.NAMES[best['tid']],'maxerr':float(best['maxerr']),'sz3_maxerr':float(sme),'candidates':[{'transform':codec.NAMES[c['tid']],'bytes':int(c['bytes'])+MODE_OVERHEAD,'gain_vs_sz3':float(sb/(c['bytes']+MODE_OVERHEAD)),'maxerr':float(c['maxerr']),**c['diag']} for c in cands]})
   print('MV3D_TILE',tag,gi,'SHAPE',X.shape,'SZ3',sb,'OURS',ours,'GAIN',gain,'WIN',codec.NAMES[best['tid']],flush=True)
  return {'logical_file':tag,'epsilon':eps,'geometry':{'selected':geom['mode'],'score':geom['score'],'ranked':ranked},'tiles':rows}
 finally:r.close()
def run(args):
 m=json.load(open(args.manifest));e=json.load(open(args.eps));ds=next(d for d in m['datasets'] if d['id']==args.dataset);eps=float(e['datasets'][args.dataset]['epsilon']);oo=[obj(u) for u in ds['objects']]
 streams=[screen_stream(oo,'assembled',eps,args.max_tiles)] if ds.get('assembly') else [screen_stream([o],o['key'],eps,args.max_tiles) for o in oo]
 tiles=[t for s in streams for t in s['tiles']];out={'kind':'migrated-volume-native-3d-screen-v1','dataset_id':args.dataset,'epsilon':eps,'streams':streams,'tile_count':len(tiles),'byte_weighted_gain':float(sum(t['sz3_bytes'] for t in tiles)/sum(t['ours_bytes'] for t in tiles)),'median_gain':float(np.median([t['gain_vs_sz3'] for t in tiles])),'all_valid':all(t['maxerr']<=eps*(1+3e-6) and t['sz3_maxerr']<=eps*(1+3e-6) for t in tiles)};Path(args.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',default='benchmarks/migrated_volume_global_eps_v1.json');ap.add_argument('--dataset',required=True);ap.add_argument('--max-tiles',type=int,default=2);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
