#!/usr/bin/env python3
"""Benchmark the slope-aware migrated-volume codec on the four failing 3D volumes."""
from __future__ import annotations
import argparse, hashlib, json, tempfile
from pathlib import Path
from collections import Counter
import numpy as np
import general_seismic_benchmark_runner as br
import general_seismic_all_engines_gauntlet as gg
from general_seismic_numeric_io import matched_sz3
import migrated_volume_geometry_codec as mv

TARGETS={"marine_waka_3d","marine_opunake_3d","marine_tui_3d","marine_kahu_3d"}

def hard_error(a,b):
    return float(np.max(np.abs(np.asarray(a,np.float64)-np.asarray(b,np.float64)))) if np.size(a) else 0.0

def run_survey(args):
    manifest=br.load_json(args.manifest); pre=br.load_json(args.preflight); cfg=br.load_json(args.config)
    ds=br.dataset_def(manifest,args.dataset); row=br.dataset_row(pre,args.dataset)
    if ds["id"] not in TARGETS: raise RuntimeError(("not a frozen migrated-volume target",ds["id"]))
    seed=int.from_bytes(hashlib.sha256(("GAUNTLET-V1:"+ds["id"]).encode()).digest()[:8],"little")
    with tempfile.TemporaryDirectory(prefix="migrated_geo_") as tmp:
        st,panels=gg.reservoir_stats_and_panels(ds,row,cfg,tmp,None,int(args.sample_panels),seed)
    eps=.10*float(st["std"])
    if not np.isfinite(eps) or eps<=0 or eps>1e12: raise RuntimeError(("implausible epsilon",ds["id"],st["std"],eps))
    print("MVGEO_EPSILON",ds["id"],st["std"],eps,"sampled",len(panels),"of",st["panels"],flush=True)
    total=0; sz_total=0; samples=0; maxerr=0.; szerr=0.; blocks=Counter(); modes=np.zeros(3,dtype=np.int64); lag_weight=0.; map_bytes=0; residual_bytes=0; rows=[]
    for rank,(source_panel_index,P,meta) in enumerate(panels):
        blob,cm=mv.encode_array(P,eps); R,dm=mv.decode_stream(blob); me=hard_error(P,R)
        if me>eps*(1+3e-6): raise RuntimeError(("MVGEO hard-bound",source_panel_index,me,eps))
        sb,sme=matched_sz3(P,eps)
        if float(sme)>eps*(1+3e-6): raise RuntimeError(("SZ3 hard-bound",source_panel_index,sme,eps))
        cb=len(blob); total+=cb; sz_total+=int(sb); samples+=int(P.size); maxerr=max(maxerr,me); szerr=max(szerr,float(sme)); blocks[str(cm["block"])]+=1
        mc=np.asarray(cm["mode_counts"],dtype=np.int64); modes[:len(mc)]+=mc; nw=max(1,int(mc.sum())); lag_weight+=float(cm["lag_mean_abs"])*nw; map_bytes+=int(cm["map_bytes"]); residual_bytes+=int(cm["residual_bytes"])
        pr={"sample_rank":rank,"source_panel_index":int(source_panel_index),"shape":list(map(int,P.shape)),"bytes":cb,"sz3_bytes":int(sb),"gain_vs_sz3":float(sb/cb),"maxerr":me,"best_block":int(cm["block"]),"map_bytes":int(cm["map_bytes"]),"residual_bytes":int(cm["residual_bytes"]),"mode_counts":cm["mode_counts"],"lag_mean_abs":cm["lag_mean_abs"],"candidates":cm["candidates"]}
        rows.append(pr); print("MVGEO_PANEL",ds["id"],source_panel_index,"SZ3",int(sb),"MVGEO",cb,"GAIN",sb/cb,"B",cm["block"],flush=True)
    result={"kind":"migrated-volume-geometry-gauntlet-v1","dataset_id":ds["id"],"std":float(st["std"]),"epsilon":eps,"sampled_panels":len(panels),"total_source_panels":int(st["panels"]),"samples":samples,"bytes":total,"sz3_bytes":sz_total,"gain_vs_sz3":float(sz_total/total),"reduction_percent_vs_sz3":float(100*(1-total/sz_total)),"bps":float(8*total/samples),"sz3_bps":float(8*sz_total/samples),"maxerr":maxerr,"sz3_maxerr":szerr,"winner_block_counts":dict(blocks),"mode_counts":modes.tolist(),"mean_abs_selected_lag":float(lag_weight/max(1,int(modes.sum()))),"map_bytes":map_bytes,"residual_bytes":residual_bytes,"all_streams_materialized_and_decoded":True,"same_reservoir_seed_as_all_engines_gauntlet":True,"panels":rows}
    Path(args.out).write_text(json.dumps(result,indent=2)); print(json.dumps({k:v for k,v in result.items() if k!="panels"},indent=2),flush=True)

def aggregate(args):
    rows=[json.loads(p.read_text()) for p in sorted(Path(args.results).glob("*.json"))]
    out={"kind":"migrated-volume-geometry-headline-v1","complete_surveys":len(rows),"wins":sum(r["gain_vs_sz3"]>1 for r in rows),"median_gain":float(np.median([r["gain_vs_sz3"] for r in rows])) if rows else None,"byte_weighted_gain":float(sum(r["sz3_bytes"] for r in rows)/sum(r["bytes"] for r in rows)) if rows else None,"surveys":[{k:r[k] for k in ("dataset_id","gain_vs_sz3","reduction_percent_vs_sz3","bps","sz3_bps","winner_block_counts","mode_counts","mean_abs_selected_lag")} for r in rows]}
    Path(args.out).write_text(json.dumps(out,indent=2)); print(json.dumps(out,indent=2))

def main():
    ap=argparse.ArgumentParser(); sp=ap.add_subparsers(dest="cmd",required=True)
    s=sp.add_parser("survey"); s.add_argument("--manifest",required=True); s.add_argument("--preflight",required=True); s.add_argument("--config",required=True); s.add_argument("--dataset",required=True); s.add_argument("--sample-panels",type=int,default=48); s.add_argument("--out",required=True)
    a=sp.add_parser("aggregate"); a.add_argument("--results",required=True); a.add_argument("--out",required=True)
    args=ap.parse_args(); run_survey(args) if args.cmd=="survey" else aggregate(args)
if __name__=="__main__": main()
