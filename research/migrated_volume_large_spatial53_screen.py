#!/usr/bin/env python3
"""Large native scale screen for exact multiscale spatial lifting."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import migrated_volume_large_native_screen as large
import migrated_volume_3d_spatial_lifting_v1 as sp53
import migrated_volume_3d_codec as c
import migrated_volume_3d_entropy as entropy
c.pack=entropy.pack;c.unpack=entropy.unpack
import migrated_volume_3d_adaptive_v2 as av2
av2.install()
import migrated_volume_3d_context_entropy_v3 as ctx1
ctx1.install()
import migrated_volume_3d_context_entropy_v4 as ctx2
ctx2.install()
import migrated_volume_3d_brotli_bitplanes as br
import migrated_volume_3d_ft_half3d_brotli as fh3
from general_seismic_numeric_io import matched_sz3
TIDS=(av2.T_B128_L1,ctx1.T_B64_CTX,ctx1.T_B128L1_CTX,ctx2.T_B64_CTX2,ctx2.T_B128L1_CTX2)
OVERHEAD=8

def hard(a,b):return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64))))
def compete(X,eps):
 rows=[]
 w,wr=sp53.compete(X,eps);rows.append({'name':w['name'],'bytes':int(w['bytes'])+OVERHEAD,'maxerr':float(w['maxerr']),'diag':w['diag']})
 for tid in TIDS:
  b,_=c.encode(X,eps,int(tid));Y,_=c.decode(b);e=hard(X,Y)
  if e>eps*(1+3e-6):raise RuntimeError(('mono hard',tid,e,eps))
  rows.append({'name':c.NAMES[int(tid)],'bytes':len(b)+OVERHEAD,'maxerr':e,'diag':{}})
 for mod,name in ((br,'fast_delta_brotli_multitraversal'),(fh3,fh3.NAME)):
  q=mod.candidate(X,eps);rows.append({'name':name,'bytes':int(q['bytes'])+OVERHEAD,'maxerr':float(q['maxerr']),'diag':{}})
 return min(rows,key=lambda q:(q['bytes'],q['name'])),rows

def stream(objects,tag,eps):
 r=large.r;rr=r.S3ConcatSequential(r.S3,objects,block_bytes=8*1024*1024)
 try:
  s=r.SegySequential(rr);total=int(s.total_traces);rows=[]
  for wi,frac in enumerate(large.FRACTIONS):
   center=int(round(frac*max(0,total-1)));st=max(0,min(total-large.WINDOW_TRACES,center-large.WINDOW_TRACES//2));n=min(large.WINDOW_TRACES,total-st)
   A=large.read_header_window(rr,s,st,n);geom,_=r.choose_geometry(A);seg=[(a+st,b+st) for a,b in geom['segments']]
   gi,block,minlen,ny,nx=large.choose_large_group(seg);X,_=large.read_tile(rr,s,block,minlen,nx)
   best,cands=compete(X,eps);sb,sme=matched_sz3(X,eps);gain=float(sb/best['bytes'])
   if best['maxerr']>eps*(1+3e-6) or sme>eps*(1+3e-6):raise RuntimeError(('bound',tag,wi))
   row={'window_index':wi,'window_fraction':frac,'shape':list(map(int,X.shape)),'samples':int(X.size),'winner':best['name'],'ours_bytes':int(best['bytes']),'sz3_bytes':int(sb),'gain_vs_sz3':gain,'maxerr':best['maxerr'],'sz3_maxerr':float(sme),'winner_diag':best['diag'],'candidate_bytes':{q['name']:q['bytes'] for q in cands}}
   rows.append(row);print('MVSP53_LARGE',tag,wi,X.shape,sb,best['bytes'],gain,best['name'],best['diag'],flush=True)
  return {'logical_file':tag,'windows':rows}
 finally:rr.close()
def run(a):
 r=large.r;m=json.load(open(a.manifest));ej=json.load(open(a.eps));ds=next(d for d in m['datasets'] if d['id']==a.dataset);eps=float(ej['datasets'][a.dataset]['epsilon']);oo=[r.obj(u) for u in ds['objects']]
 ss=[stream(oo,'assembled',eps)] if ds.get('assembly') else [stream([o],o['key'],eps) for o in oo];rows=[q for s in ss for q in s['windows']]
 out={'kind':'migrated-volume-large-spatial53-v1','compression_class':'migrated_poststack_3d','dataset_id':a.dataset,'epsilon':eps,'positions':len(rows),'wins':sum(q['gain_vs_sz3']>1 for q in rows),'min_gain':min(q['gain_vs_sz3'] for q in rows),'median_gain':float(np.median([q['gain_vs_sz3'] for q in rows])),'byte_weighted_gain':sum(q['sz3_bytes'] for q in rows)/sum(q['ours_bytes'] for q in rows),'all_valid':True,'streams':ss};Path(a.out).write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='streams'},indent=2),flush=True)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--manifest',required=True);ap.add_argument('--eps',required=True);ap.add_argument('--dataset',required=True);ap.add_argument('--out',required=True);run(ap.parse_args())
if __name__=='__main__':main()
