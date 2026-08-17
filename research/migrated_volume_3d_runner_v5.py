#!/usr/bin/env python3
"""Native migrated-volume portfolio with split-symbol predictive and model-free PPM v5."""
import migrated_volume_3d_runner_v4 as v4runner
import migrated_volume_3d_predictive_v5 as split
import migrated_volume_3d_context_entropy_v5 as ppm

# Preserve v4 exactly and add two independent v5 families. Actual serialized
# bytes decide; neither survey identity nor an oracle participates.
split.install()
ppm.install()

if __name__=='__main__':
    split.sanity()
    ppm.sanity()
    v4runner.v3.v2.runner.main()
