#!/usr/bin/env python3
import argparse,json,struct
from pathlib import Path
from urllib.parse import urlparse
import boto3,numpy as np
from botocore import UNSIGNED
from botocore.config import Config
from general_seismic_streaming_segy import S3ConcatSequential,SegySequential
S3=boto3.client('s3',config=Config(signature_version=UNSIGNED,retries={'max_attempts':10}))
TARGETS={'marine_waka_3d','marine_opunake_3d','marine_tui_3d','marine_kahu_3d'}
FIELDS={'trace_seq_line':0,'trace_seq_file':4,'field_record':8,'trace_in_record':12,'source_point':16,'ensemble':20,'trace_in_ensemble':24,'offset':36,'source_x':72,'source_y':76,'group_x':80,'group_y':84,'cdp_x':180,'cdp_y':184,'inline':188,'crossline':192,'shotpoint':196}
def obj(uri):
 u=urlparse(uri);b=u.netloc;k=u.path.lstrip('/');h=S3.head_object(Bucket=b,Key=k);return {'bucket':b,'key':k,'size':int(h['ContentLength'])}
def hv(th,e):return [struct.unpack(e+'i',th[o:o+4])[0] for o in FIELDS.values()]
def stats(x):
 x=np.asarray(x,np.int64);d=np.diff(x);u=np.unique(x);du,c=np.unique(d,return_counts=True);ii=np.argsort(c)[::-1][:6];ch=np.flatnonzero(d!=0)+1;rl=np.diff(np.r_[0,ch,len(x)])
 return {'unique':int(u.size),'min':int(x.min()),'max':int(x.max()),'diff_zero_fraction':float(np.mean(d==0)) if d.size else 1.0,'top_steps':[[int(du[i]),int(c[i])] for i in ii],'run_median':float(np.median(rl)),'run_max':int(rl.max()),'first':[int(q) for q in x[:10]]}
def probe(oo,tag,n=8192):
 r=S3ConcatSequential(S3,oo,block_bytes=2*1024*1024)
 try:
  s=SegySequential(r);rows=[]
  if s.binary_stride_exact and s.total_traces is not None:
   for i in range(min(n,int(s.total_traces))):r.seek(s.trace_start+i*s.binary_stride);rows.append(hv(r.read(240),s.endian))
  else:
   for i in range(n):
    q=s.next_trace()
    if q is None:break
    rows.append(hv(q[1],s.endian))
  A=np.asarray(rows,np.int64);ff={k:stats(A[:,j]) for j,k in enumerate(FIELDS)}
  return {'logical_file':tag,'total_traces':None if s.total_traces is None else int(s.total_traces),'fields':ff}
 finally:r.close()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',default='benchmarks/general_seismic_v1.json');ap.add_argument('--out',default='migrated_volume_header_fields.json');a=ap.parse_args();m=json.load(open(a.manifest));rows=[]
 for ds in m['datasets']:
  if ds['id'] not in TARGETS:continue
  oo=[obj(u) for u in ds['objects']];ss=[probe(oo,'assembled')] if ds.get('assembly') else [probe([o],o['key']) for o in oo];rows.append({'dataset_id':ds['id'],'streams':ss})
  for st in ss:
   print('FIELD_DATASET',ds['id'],st['logical_file'],flush=True)
   for k,x in st['fields'].items():
    if x['unique']>1:print('FIELD',k,'U',x['unique'],'DZ',round(x['diff_zero_fraction'],4),'RM',x['run_median'],'RX',x['run_max'],'ST',x['top_steps'][:3],'F',x['first'][:5],flush=True)
 Path(a.out).write_text(json.dumps({'kind':'migrated-volume-header-field-probe-v1','datasets':rows},indent=2))
if __name__=='__main__':main()
