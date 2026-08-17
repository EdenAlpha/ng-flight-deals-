#!/usr/bin/env python3
"""Cheap SEG-Y geometry probe for migrated-volume benchmark surveys."""
import json,struct,argparse
from pathlib import Path
from urllib.parse import urlparse
import boto3,numpy as np
from botocore import UNSIGNED
from botocore.config import Config
from general_seismic_streaming_segy import S3ConcatSequential,SegySequential
S3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10}))
TARGETS={'marine_waka_3d','marine_opunake_3d','marine_tui_3d','marine_kahu_3d'}
def parse_uri(uri):
 u=urlparse(uri);return u.netloc,u.path.lstrip('/')
def make_obj(uri):
 b,k=parse_uri(uri);h=S3.head_object(Bucket=b,Key=k);return {'bucket':b,'key':k,'size':int(h['ContentLength'])}
def i32(th,off,e):return struct.unpack(e+'i',th[off:off+4])[0]
def rec(s,idx):
 a,th=s.next_trace();return {'trace_index':idx,'inline':i32(th,188,s.endian),'crossline':i32(th,192,s.endian),'cdp_x':i32(th,180,s.endian),'cdp_y':i32(th,184,s.endian)}
def summary(rr):
 il=np.array([q['inline'] for q in rr],dtype=np.int64);xl=np.array([q['crossline'] for q in rr],dtype=np.int64)
 return {'count':len(rr),'unique_inline':int(np.unique(il).size),'unique_crossline':int(np.unique(xl).size),'inline_min':int(il.min()),'inline_max':int(il.max()),'crossline_min':int(xl.min()),'crossline_max':int(xl.max()),'inline_step_counts':{str(int(k)):int(v) for k,v in zip(*np.unique(np.diff(il),return_counts=True))},'crossline_step_counts':{str(int(k)):int(v) for k,v in zip(*np.unique(np.diff(xl),return_counts=True))}}
def runs(rr):
 out=[];st=0
 for j in range(1,len(rr)+1):
  if j==len(rr) or rr[j]['inline']!=rr[st]['inline']:
   out.append({'inline':rr[st]['inline'],'start':st,'length':j-st,'crossline_first':rr[st]['crossline'],'crossline_last':rr[j-1]['crossline']});st=j
 return out[:32]
def probe_stream(objects,tag,nscan=4096,nwin=64):
 r=S3ConcatSequential(S3,objects,block_bytes=2*1024*1024)
 try:
  s=SegySequential(r);out={'logical_file':tag,'samples_per_trace':int(s.binary_ns),'format_code':int(s.format_code),'endian':s.endian,'binary_stride_exact':bool(s.binary_stride_exact),'ns_policy':s.ns_policy,'windows':[]}
  if s.binary_stride_exact and s.total_traces is not None:
   nt=int(s.total_traces);out['total_traces']=nt;n=min(nscan,nt);r.seek(s.trace_start);s.trace_index=0;rr=[rec(s,j) for j in range(n)];out['beginning_scan']=summary(rr);out['beginning_inline_runs']=runs(rr)
   nw=min(nwin,nt)
   for f in (0,.1,.25,.5,.75,.9,1):
    st=max(0,min(nt-nw,int(round(f*max(0,nt-nw)))));r.seek(s.trace_start+st*s.binary_stride);s.trace_index=st;ww=[rec(s,st+j) for j in range(nw)];q={'start_trace':st};q.update(summary(ww));out['windows'].append(q)
  else:
   rr=[]
   for j in range(nscan):
    q=s.next_trace()
    if q is None:break
    a,th=q;rr.append({'trace_index':j,'inline':i32(th,188,s.endian),'crossline':i32(th,192,s.endian),'cdp_x':i32(th,180,s.endian),'cdp_y':i32(th,184,s.endian)})
   out['total_traces']=None;out['beginning_scan']=summary(rr) if rr else {'count':0};out['beginning_inline_runs']=runs(rr) if rr else []
  return out
 finally:r.close()
def probe_dataset(ds):
 oo=[make_obj(u) for u in ds['objects']]
 ss=[probe_stream(oo,'assembled:'+','.join(o['key'] for o in oo))] if ds.get('assembly') else [probe_stream([o],o['key']) for o in oo]
 return {'dataset_id':ds['id'],'name':ds['name'],'streams':ss}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',default='benchmarks/general_seismic_v1.json');ap.add_argument('--out',default='migrated_volume_geometry_probe.json');a=ap.parse_args();m=json.load(open(a.manifest));rows=[];errors=[]
 for ds in m['datasets']:
  if ds['id'] not in TARGETS:continue
  try:
   q=probe_dataset(ds);rows.append(q)
   for s in q['streams']:print('GEOM_STREAM',q['dataset_id'],s['logical_file'],'N',s.get('total_traces'),'SCAN',s.get('beginning_scan'),'RUNS',s.get('beginning_inline_runs',[])[:8],flush=True)
  except Exception as e:errors.append({'dataset_id':ds['id'],'error':repr(e)});print('GEOM_ERROR',ds['id'],repr(e),flush=True)
 out={'kind':'migrated-volume-geometry-probe-v2','datasets':rows,'errors':errors};Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({'datasets':[r['dataset_id'] for r in rows],'errors':errors},indent=2))
 if errors:raise RuntimeError(('geometry probe incomplete',errors))
if __name__=='__main__':main()
