#!/usr/bin/env python3
from __future__ import annotations

import argparse,json


def candidates(pred):
    if pred=='soda_or_forge_lattice':return {'soda_record_run_lattice_pr169','forge_wholefile_lattice_pr203'}
    return {pred}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--predictions',required=True);ap.add_argument('--bakeoff',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    P=json.load(open(a.predictions));B=json.load(open(a.bakeoff))
    pmap={x['target']:x for x in P['predictions']}
    by={}
    for f in B.get('files',[]):by.setdefault(f['dataset_id'],[]).append(f)
    rows=[]
    for target,p in sorted(pmap.items()):
        ff=by.get(target,[]);allowed=candidates(p['predicted_engine_family']);fr=[]
        sum_sz=sum_pred=0;eligible=0;primitive_match=0
        for f in ff:
            rank=f.get('ranking',[]);primitive=[q for q in rank if q['engine'] not in ('SZ3','V1_portfolio')]
            actual=min(primitive,key=lambda q:q['bytes']) if primitive else None
            predrows=[q for q in rank if q['engine'] in allowed]
            pred=min(predrows,key=lambda q:q['bytes']) if predrows else None
            sz=int(f.get('sz3_bytes',0))
            if pred and sz>0:
                eligible+=1;sum_sz+=sz;sum_pred+=int(pred['bytes'])
            if pred and actual and pred['engine']==actual['engine']:primitive_match+=1
            fr.append({'logical_file':f['logical_file'],'sz3_bytes':sz,'predicted_candidate':pred,'actual_best_primitive':actual,'predicted_matches_best_primitive':bool(pred and actual and pred['engine']==actual['engine'])})
        gain=float(sum_sz/sum_pred) if sum_pred else None
        rows.append({**p,'files_scored':len(ff),'predicted_engine_eligible_files':eligible,'primitive_winner_matches':primitive_match,'aggregate_predicted_gain_vs_sz3':gain,'aggregate_crosses_2x':bool(gain is not None and gain>=2.0),'file_results':fr})
    out={'kind':'seismic-compression-phenotype-blind-validation-v2','predictions_frozen_before_bakeoff_judging':True,'results':rows}
    json.dump(out,open(a.out,'w'),indent=2);print('BLIND_JUDGE',json.dumps([{k:v for k,v in r.items() if k!='file_results'} for r in rows],indent=2),flush=True)
if __name__=='__main__':main()
