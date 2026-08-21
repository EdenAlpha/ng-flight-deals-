# Compression phenotype v1

This experiment deliberately avoids seismic dataset names as classifier inputs. Every source is reduced to the same plain 2-D trace/channel x time view and measured at epsilon = 0.10 * full-object standard deviation.

The fingerprint is built from properties visible to a compression engine: legal error-bounded lattice state sparsity, actual Zstd rates after temporal/spatial/Lorenzo transforms, a generic sparse-anchor carrier probe, temporal and spatial causal correlation, best adjacent-trace time shift, 2-D spectral concentration, low-rank concentration, and across-tile stationarity.

Initial validation set: F1, Tie, Soda p45, independent raw Utah FORGE, Brady PoroTomo DAS, and Imperial Valley DAS. The clustering stage receives only the numeric fingerprint vectors. It does not receive acquisition labels or historical compressor results.

The purpose is to test whether historical >2x winners occupy reproducible neighborhoods in compression-structure space, and whether Brady/Imperial separate for measurable mathematical reasons. A future source cannot be outside this representation merely because its survey type has a new name: it still receives a numeric compression phenotype and competes by actual rate.
