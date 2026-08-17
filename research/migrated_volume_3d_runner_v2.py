#!/usr/bin/env python3
import migrated_volume_3d_codec as codec
import migrated_volume_3d_entropy as entropy
codec.pack=entropy.pack
codec.unpack=entropy.unpack
import migrated_volume_3d_adaptive_v2 as adaptive_v2
adaptive_v2.install()
import migrated_volume_3d_runner as runner
import migrated_volume_3d_geometry_v2 as geometry_v2
runner.SCAN=40000
# Keep the four-line requirement that transferred across all migrated surveys,
# while doubling fast-axis spatial context from 32 to 64 traces. Requiring
# eight lines rejected otherwise valid Waka geometry before compression.
runner.NY=4
runner.NX=64
_base_geometry_candidates=runner.geometry_candidates
runner.geometry_candidates=lambda A: geometry_v2.geometry_candidates(_base_geometry_candidates,runner,A)
if __name__=='__main__':
 entropy.sanity()
 adaptive_v2.sanity()
 runner.main()
