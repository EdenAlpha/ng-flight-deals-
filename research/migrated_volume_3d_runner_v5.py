#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with split-symbol predictive v5."""
import migrated_volume_3d_runner_v4 as v4runner
import migrated_volume_3d_predictive_v5 as v5

v5.install()

if __name__=='__main__':
    v5.sanity()
    v4runner.v3.v2.runner.main()
