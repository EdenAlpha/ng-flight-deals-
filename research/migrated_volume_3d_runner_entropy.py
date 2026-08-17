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

import migrated_volume_3d_runner as runner
import migrated_volume_3d_geometry_v2 as geometry_v2
runner.SCAN=40000
_base_geometry_candidates=runner.geometry_candidates
runner.geometry_candidates=lambda A: geometry_v2.geometry_candidates(_base_geometry_candidates,runner,A)

if __name__=='__main__':
    entropy.sanity()
    block.sanity()
    runner.main()
