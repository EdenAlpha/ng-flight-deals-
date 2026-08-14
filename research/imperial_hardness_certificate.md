# Imperial Valley compression-hardness certificate

This note joins two already-audited 54-block results on the canonical Imperial record at the unchanged hard-error tolerance `epsilon = 133.69778037805762`:

- PR #444: exact full-array Huber AR32 + activity6 compressed rates, plus exact K zero fraction and K standard deviation for every contiguous 128-channel block.
- PR #475: raw-data local amplitude, first-difference scale, robust scale, adjacent-channel correlation and lag-1 correlation for those same 54 blocks.

No new compressor result is claimed here. This is a diagnostic relationship within this record.

## Strongest observed predictors of activity6 rate

Spearman rank correlation with exact activity6 bits/sample across all 54 blocks:

- AR innovation zero fraction: **-0.992758**
- median per-channel first-difference standard deviation: **+0.947017**
- robust first-difference sigma: **+0.939831**
- block first-difference sigma / epsilon: **+0.930093**
- AR innovation K standard deviation: **+0.919421**
- robust raw-signal sigma: **+0.892286**
- median per-channel raw standard deviation: **+0.890375**
- raw local standard deviation / epsilon: **+0.842882**
- adjacent-channel correlation: only about **-0.33**
- ordinary lag-1 correlation: only about **-0.20 to -0.25**

The dominant raw-data predictor is therefore the scale of rapid sample-to-sample variation relative to epsilon, not raw amplitude alone and not ordinary local correlation alone.

## One-feature pre-compression predictor

Let

`r = median_per_channel_std(diff_t(x)) / epsilon`.

A least-squares fit across the 54 blocks is

`predicted_bps = 0.84566559 + 0.84579218 * log2(r)`.

Leave-one-block-out validation on the same Imperial record gives:

- **R^2 = 0.946887**
- **MAE = 0.164291 bps**
- **RMSE = 0.211798 bps**

The same one-feature predictor classifies:

- actual activity6 rate <= 2 bps with **92.6% accuracy**
- actual activity6 rate >= 3 bps with **94.4% accuracy**
- actual activity6 rate >= 3.5 bps with **96.3% accuracy**

## Four-feature raw-data predictor

Using only pre-compression raw features

1. `log2(median channel diff std / epsilon)`
2. `log2(median channel raw std / epsilon)`
3. mean adjacent-channel correlation
4. mean lag-1 temporal correlation

leave-one-block-out validation gives:

- **R^2 = 0.981354**
- **MAE = 0.071603 bps**
- **RMSE = 0.125493 bps**

The full-data linear coefficients, recorded only for reproducibility and not as independent validation, are:

`bps ~= 1.00573449 + 0.84224836*log2(diff_scale/epsilon) + 0.02956050*log2(raw_scale/epsilon) - 0.81083198*adjacent_corr + 0.64488519*lag1_corr`.

## Interpretation

At a fixed absolute L-infinity tolerance, Imperial becomes hard when the rapid innovation scale is large compared with the legal +/-epsilon interval. The AR32 K stream then has a very low zero fraction and a broad symbol distribution, so each sample carries substantial new information even after strong prediction. This is consistent with the independent impossible-oracle experiments: true future samples and all other sensors supplied for free still leave the hard region far above its local 2x-SZ3 target.

Conversely, favorable blocks have first-difference scale only a few times epsilon and a high K=0 fraction, which is exactly the regime where persistence, activity coding and legal-set multiplicity have room to work.

## Scope warning

These predictive accuracies are leave-one-block-out **within one Imperial Valley record**. They are strong evidence for the physical/statistical driver of difficulty in this file, but they are not yet a universal seismic-data law. The next validation should freeze the formula and test it on independent Imperial minutes and on other datasets such as FORGE/Brady before using it as a general production feasibility certificate.
