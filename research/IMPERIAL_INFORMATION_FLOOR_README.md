# Imperial information-floor audit

This experiment does not claim to compute the Kolmogorov complexity or exact rate-distortion function of the finite Imperial hard-region file.

It reports three distinct kinds of evidence:

1. **Actual achievable upper bounds** from a fixed legal step-267 scalar reconstruction followed by reversible transforms and physical zstd byte streams.
2. **Held-out causal predictive diagnostics** from models fitted only on the first 8,192 time samples and evaluated on later samples. Residual H0 and zstd rates estimate how much source structure remains after progressively stronger causal prediction.
3. **A deliberately noncausal oracle diagnostic** using current right-neighbor and future-time information. The gap from the causal models is evidence of exploitable spatiotemporal structure, but the oracle itself is not a codec.

The reported `H0 - log2(error-ball)` quantity is a Shannon-style diagnostic only. It is not a rigorous lower bound for this one finite file and must not be used to claim that a target is impossible.

Canonical comparison constants used by the run:
- hard region: 128 x 30,000 = 3,840,000 samples
- current exact codec: 2,468,803 B
- matched SZ3: 2,767,977 B
- strict 2x-SZ3 target: 1,383,988.5 B
