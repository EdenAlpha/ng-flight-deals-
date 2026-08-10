# AXIOM Beast v0.9

v0.9 adds a byte-exact TrueType glyph-law transform inside the TAR nested-law graph.

For suitable TTF/OTF files with a `glyf` table, AXIOM preserves the original SFNT byte layout as a compressible skeleton, removes the opaque original `glyf` bytes, stores canonical WOFF2 glyph semantics, and deterministically reconstructs the original glyph table. The transform is accepted only if its inverse reproduces the original font bytes exactly.

## Fixed Android corpus

- original deterministic TAR: 696,320 B
- AXIOM v0.8: 172,428 B
- AXIOM v0.9: **161,588 B**
- improvement over v0.8: **6.29%**
- exact source/output SHA-256: `73529d3651eb4d3942f2175ca36d89a95dcbf0e43ec4f95ee5206a7ba7446a75`

Strong archival baselines on the identical source SHA-256:

- Brotli-11: 250,233 B
- 7-Zip LZMA2: 250,634 B
- XZ -9e: 251,276 B
- 7-Zip PPMd: 259,294 B
- Zstd ultra-22: 259,651 B

AXIOM v0.9 is therefore **35.43% smaller than the strongest measured archival baseline** on this fixed corpus.

## Dependency

The TTF glyph-law path requires `fonttools`. If unavailable at compression time, the transform is skipped. Archives that actually use the TTF law require FontTools during decoding.
