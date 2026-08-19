#!/usr/bin/env python3
"""Decompose SZ3's Waka 16x128 scale gain without changing samples.

Extract the exact frozen held-out 16x128 Waka region. Compare matched SZ3 bytes
for the whole array against sums of independent contiguous x slabs (2x64, 4x32,
8x16). If whole-width SZ3 is much smaller than the summed slabs, there is a real
cross-slab/global coding benefit. If not, the prior width gain mainly reflects
data composition rather than long-range interaction. No learned model involved.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import waka_tall16_probability_scale_v1 as base
from general_seismic_numeric_io import matched_sz3

def sz3(X,eps):
    b,e=matched_sz3(X,eps);return int(b),float(e)
def main(a):
    m=json.load(open(a.manifest));ej=json.load(open(a.eps));X,eps,md=base.extract16x128(m,ej,base.TEST_FRAC)
    wb,we=sz3(X,eps);rows={}
    for w in (64,32,16):
        parts=[]
        for x0 in range(0,X.shape[1],w):
            b,e=sz3(X[:,x0:x0+w,:],eps);parts.append({'x0':x0,'x1':x0+w,'bytes':b,'bps':8*b/X[:,x0:x0+w,:].size,'maxerr':e})
        sb=sum(z['bytes'] for z in parts);rows[str(w)]={'slabs':parts,'sum_bytes':sb,'sum_bps':8*sb/X.size,'whole_over_slab_sum':wb/sb,'slab_sum_over_whole':sb/wb,'extra_bytes_if_independent':sb-wb}
    out={'kind':'waka-sz3-width-decomposition-v1','dataset':base.DATASET,'epsilon':eps,'location':md,'shape':list(X.shape),'whole_sz3_bytes':wb,'whole_sz3_bps':8*wb/X.size,'whole_sz3_maxerr':we,'slab_results':rows,'selection_uses_sample_values':False}
    Path(a.out).write_text(json.dumps(out,indent=2));print('SZ3_WIDTH_DECOMP',json.dumps(out,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True);p.add_argument('--eps',required=True);p.add_argument('--out',required=True);main(p.parse_args())
