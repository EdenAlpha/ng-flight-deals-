#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with predictive-context v6."""
import migrated_volume_3d_runner_v5 as v5runner
import migrated_volume_3d_predictive_context_v6 as v6

v6.install()

if __name__=='__main__':
    v6.sanity()
    v5runner.v4runner.v3.v2.runner.main()
