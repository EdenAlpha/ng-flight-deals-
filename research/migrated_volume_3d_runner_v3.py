#!/usr/bin/env python3
"""Native-geometry migrated-volume screen with predictive-quantization v3."""
import migrated_volume_3d_runner_v2 as v2
import migrated_volume_3d_predictive_v3 as pq

pq.install()

if __name__=='__main__':
    pq.sanity()
    v2.runner.main()
