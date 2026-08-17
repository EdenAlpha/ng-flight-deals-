#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with predictive and context-entropy v3."""
import migrated_volume_3d_runner_v2 as v2
import migrated_volume_3d_predictive_v3 as pq
import migrated_volume_3d_context_entropy_v3 as ctx

# Stack both universal candidates on top of the protected v2 portfolio.  Actual
# serialized byte count decides; either candidate can simply lose with no
# regression to the existing v2 modes.
pq.install()
ctx.install()

if __name__=='__main__':
    pq.sanity()
    ctx.sanity()
    v2.runner.main()
