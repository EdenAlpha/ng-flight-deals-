#!/usr/bin/env python3
"""Seven-window robustness screen for the confirmed migrated-volume portfolio.

Installs the confirmed native-geometry/context2 portfolio, then reuses the
header-driven spread-screen machinery at seven deterministic positions through
each logical volume. Window placement depends only on trace count and SEG-Y
headers, never sample values.
"""
# Install the confirmed portfolio first: width-adaptive native geometry,
# blockwise causal prediction, predictive candidates, and context2 arithmetic.
import migrated_volume_3d_runner_v4 as stable  # noqa: F401
import migrated_volume_3d_spread_screen as screen

screen.FRACTIONS=(0.05,0.20,0.35,0.50,0.65,0.80,0.95)
screen.WINDOW_TRACES=40000

if __name__=='__main__':
    screen.main()
