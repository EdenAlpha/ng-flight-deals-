#!/usr/bin/env python3
import migrated_volume_3d_codec as codec
import migrated_volume_3d_entropy as entropy
codec.pack=entropy.pack
codec.unpack=entropy.unpack

import migrated_volume_3d_block_fix as block_fix
block=block_fix.install()
_base_compete=codec.compete
_base_names=dict(codec.NAMES)

def _frozen_base_compete(X,eps):
    full=codec.NAMES
    codec.NAMES=_base_names
    try:
        return _base_compete(X,eps)
    finally:
        codec.NAMES=full

codec.NAMES[1064]='block_causal_b64'
codec.NAMES[1128]='block_causal_b128'
codec.NAMES[1256]='block_causal_b256'
codec.compete=lambda X,eps: block.compete_with_base(X,eps,_frozen_base_compete)

# Add the independently verified fast-delta / multi-traversal Brotli stream only
# after freezing the legacy transform table, so it cannot leak into the old
# encoder's transform iteration.
import migrated_volume_3d_brotli_bitplanes as brbp
_block_compete=codec.compete
codec.NAMES[brbp.TID]='fast_delta_brotli_multitraversal'
def _all_compete(X,eps):
    best,rows=_block_compete(X,eps)
    c=brbp.candidate(X,eps)
    rows=list(rows)+[c]
    return min(rows,key=lambda r:(r['bytes'],r['tid'])),rows
codec.compete=_all_compete

import migrated_volume_3d_runner as runner
import migrated_volume_3d_geometry_v2 as geometry_v2
runner.SCAN=40000
_base_geometry_candidates=runner.geometry_candidates
runner.geometry_candidates=lambda A: geometry_v2.geometry_candidates(_base_geometry_candidates,runner,A)

if __name__=='__main__':
    entropy.sanity()
    block.sanity()
    brbp.sanity()
    runner.main()
