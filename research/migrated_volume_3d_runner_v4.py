#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with all protected modes plus v4 candidates."""
import migrated_volume_3d_runner_v3 as v3
import migrated_volume_3d_predictive_v4 as blend
import migrated_volume_3d_context_entropy_v4 as ctx2

# Add only candidates. The complete v3 portfolio stays available, so a new mode
# cannot regress a tile: smallest actual independently decodable stream wins.
blend.install()
ctx2.install()

if __name__=='__main__':
    blend.sanity()
    ctx2.sanity()
    v3.v2.runner.main()
