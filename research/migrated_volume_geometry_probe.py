#!/usr/bin/env python3
"""Cheap SEG-Y geometry probe for the migrated-volume benchmark surveys."""
import json, struct, argparse
from pathlib import Path
from urllib.parse import urlparse

import boto3
import numpy as np
from botocore import UNSIGNED
from botocore.config import Config

from general_seismic_streaming_segy import S3ConcatSequential, SegySequential

S3 = boto3.client('s3', config=Config(signature_version=UNSIGNED, retries={'max_attempts': 10}))
TARGETS = {'marine_waka_3d','marine_opunake_3d','marine_tui_3d','marine_kahu_3d'}


def parse_uri(uri):
    u=urlparse(uri)
    if u.scheme!='s3': raise ValueError(uri)
    return u.netloc,u.path.lstrip('/')


def i32(th, off, endian):
    return struct.unpack(endian+'i', th[off:off+4])[0]


def probe_dataset(ds, traces_per_window=48):
    objs=[]
    for uri in ds['objects']:
        b,k=parse_uri(uri); h=S3.head_object(Bucket=b,Key=k)
        objs.append({'bucket':b,'key':k,'size':int(h['ContentLength'])})
    r=S3ConcatSequential(S3,objs,block_bytes=2*1024*1024)
    try:
        s=SegySequential(r)
        if not s.binary_stride_exact or s.total_traces is None:
            raise RuntimeError((ds['id'],'probe requires exact fixed trace stride',s.ns_policy))
        nt=int(s.total_traces); nwin=min(int(traces_per_window),nt)
        starts=sorted(set(max(0,min(nt-nwin,int(round(f*max(0,nt-nwin))))) for f in (0.0,0.1,0.25,0.5,0.75,0.9,1.0)))
        windows=[]
        for st in starts:
            r.seek(s.trace_start+st*s.binary_stride); s.trace_index=st
            rec=[]
            for j in range(nwin):
                a,th=s.next_trace()
                rec.append({
                    'trace_index':st+j,
                    'inline':i32(th,188,s.endian),
                    'crossline':i32(th,192,s.endian),
                    'cdp_x':i32(th,180,s.endian),
                    'cdp_y':i32(th,184,s.endian),
                    'trace_seq_line':i32(th,4,s.endian),
                })
            il=np.asarray([q['inline'] for q in rec],np.int64); xl=np.asarray([q['crossline'] for q in rec],np.int64)
            windows.append({
                'start_trace':st,
                'records':rec,
                'unique_inline':int(np.unique(il).size),
                'unique_crossline':int(np.unique(xl).size),
                'inline_nonzero_fraction':float(np.mean(il!=0)),
                'crossline_nonzero_fraction':float(np.mean(xl!=0)),
                'inline_step_counts':{str(int(k)):int(v) for k,v in zip(*np.unique(np.diff(il),return_counts=True))},
                'crossline_step_counts':{str(int(k)):int(v) for k,v in zip(*np.unique(np.diff(xl),return_counts=True))},
            })
        return {
            'dataset_id':ds['id'],'name':ds['name'],'total_traces':nt,'samples_per_trace':int(s.binary_ns),
            'format_code':int(s.format_code),'endian':s.endian,'binary_stride':int(s.binary_stride),
            'windows':windows,
        }
    finally:
        r.close()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--manifest',default='benchmarks/general_seismic_v1.json'); ap.add_argument('--out',default='migrated_volume_geometry_probe.json'); a=ap.parse_args()
    m=json.load(open(a.manifest)); rows=[]
    for ds in m['datasets']:
        if ds['id'] in TARGETS:
            q=probe_dataset(ds); rows.append(q)
            for w in q['windows']:
                print('GEOM',q['dataset_id'],w['start_trace'],'UI',w['unique_inline'],'UX',w['unique_crossline'],'DI',w['inline_step_counts'],'DX',w['crossline_step_counts'],flush=True)
    out={'kind':'migrated-volume-geometry-probe-v1','datasets':rows}; Path(a.out).write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

if __name__=='__main__': main()
