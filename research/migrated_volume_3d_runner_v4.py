#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with v3 plus no-side v4 blends."""
import migrated_volume_3d_runner_v3 as v3
import migrated_volume_3d_predictive_v4 as v4

v4.install()

if __name__=='__main__':
    v4.sanity()
    v3.v2.runner.main()
