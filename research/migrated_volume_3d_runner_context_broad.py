#!/usr/bin/env python3
import migrated_volume_3d_codec as codec
import migrated_volume_3d_context_entropy as context_entropy
codec.pack=context_entropy.pack
codec.unpack=context_entropy.unpack
import migrated_volume_3d_runner as runner
import migrated_volume_3d_geometry_v2 as geometry_v2
# Broaden geometry discovery beyond the initial 40k-trace mechanics screen.
runner.SCAN=120000
runner.NY=4
runner.NX=32
_base_geometry_candidates=runner.geometry_candidates
runner.geometry_candidates=lambda A: geometry_v2.geometry_candidates(_base_geometry_candidates,runner,A)
if __name__=='__main__':
 context_entropy.sanity()
 runner.main()
