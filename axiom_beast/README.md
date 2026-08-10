# AXIOM Beast v0.8

AXIOM Beast is an experimental **non-AI, byte-exact, lossless compression research codec** built around reversible explanations rather than one universal byte model.

Its working principle is:

> Do not spend bits describing consequences when the decoder can regenerate them from a cheaper law, coordinate system, structure, or generative basis.

AXIOM v0.8 has four materially different winning mechanisms on fixed real corpora:

1. **Causal-coordinate compression (CSV/tabular):** discover entity/time laws and serialize residuals in the coordinate system of the causal process instead of row order.
2. **Causal field graphs (JSON):** path/schema bands, functional dependencies, integer/date laws, aggregate relations, and previous-state relations.
3. **Nested codec-law peeling (TAR/PNG and ZIP/DEFLATE):** replace opaque compressed byte streams with a larger but lower-description-length reversible representation when profitable.
4. **Codec-ancestry basis + exact correction (raw RGB):** search for a compact generative JPEG basis, pin the decoder semantics, and encode only the exact correction needed to reproduce the original pixels.

Every accepted transform is fail-closed: its inverse must recreate the original bytes exactly. Every `.axb` archive stores original length and SHA-256 and refuses output on mismatch.

## Usage

```bash
python3 axiom_beast.py c INPUT OUTPUT.axb --effort max
python3 axiom_beast.py d OUTPUT.axb RESTORED
```

`--effort max` searches the strongest available backends and structural candidates. `--effort fast` keeps the reversible architecture but uses faster backend settings.

Core Python dependencies: standard library. The experimental RGB ancestry mode additionally needs `numpy`, `Pillow`, and `ffmpeg`. Optional backends include `zstd` and `brotli`; Python LZMA/XZ is always available.

## v0.8 verified complete archives

All four archives below were decoded using the **same current AXB7 decoder** and compared by SHA-256 against the source corpus.

| Corpus | Original | Complete AXB7 | Strongest tested opponent | AXIOM improvement |
|---|---:|---:|---:|---:|
| NYTimes county CSV (250k data rows) | 9,875,837 B | **132,510 B** | XZ -9e: 439,560 B | **69.85% smaller** |
| GitHub event JSON corpus | 26,141,343 B | **1,331,926 B** | PPMd: 1,937,485 B | **31.25% smaller** |
| Raw Android app TAR | 696,320 B | **172,428 B** | Brotli-11: 250,233 B | **31.09% smaller** |
| Raw 512x512 RGB24 image | 786,432 B | **139,521 B** | lossless JPEG XL: 235,553 B | **40.77% smaller** |

The raw-image result is the v0.8 breakthrough. The compressor is **not given the source JPEG**. It infers the raw geometry, searches a small canonical JPEG state family, decodes each candidate under a pinned FFmpeg decoder law, then minimizes:

```
compressed basis description + compressed exact correction
```

On this corpus the MDL optimum lands sharply at JPEG quality 92 / subsampling mode 1. The basis itself is ~89.7 KB and the exact channel-coordinate correction compresses to ~49.7 KB. The final AXB7 is 139,521 B and restores every RGB byte exactly.

### Why this matters

The raw RGB benchmark was originally produced by decoding a JPEG. The original JPEG happens to be 91,814 B and FFmpeg regenerates the benchmark RGB bytes exactly. AXIOM does **not** store or require that original JPEG; this oracle observation simply proves the pixels have a much shorter generative explanation than a generic lossless pixel model exposes.

The new research direction is **generative ancestry inversion**:

```
Data = DecoderLaw_k(CompactBasis) + ExactResidual
```

The decoder law itself is part of the compression model. v0.8 pins the FFmpeg version-signature because different JPEG decoders can differ in color-conversion/rounding semantics, which materially changes exact residual entropy.

## Causal-coordinate breakthrough

For a field generated independently per entity,

```
value(entity,t) = value(entity,t-1) + residual(entity,t)
```

it is not enough to compute the right residual and then serialize it in original row order. AXIOM groups the residuals in the coordinate system induced by the causal law:

```
A_t,A_t+1,A_t+2,... | B_t,B_t+1,B_t+2,... | ...
```

No permutation stream is needed because the already-decoded key/date columns regenerate the grouping. On the fixed CSV corpus this reduced an already-strong representation from 155,685 B to 132,465 B payload without changing a single residual value.

v0.7/v0.8 also replace exhaustive CSV relation search with sampled MDL pruning. The optimized search reaches the same best representation in about 10.1 seconds on the fixed 9.88 MB corpus.

## What AXIOM still does not beat

AXIOM is **not** claimed to be the world's best universal compressor. Current hard frontiers include:

- **Plain prose:** PPMd 174,465 B beats the current AXIOM text path (~194–198 KB).
- **Raw YUV video:** verified FFV1 archive is **418,062 B** and decodes to the exact raw sequence. AXIOM's current video experiments do not beat it. Naive H.264 ancestry + exact residual is ~660 KB at the best tested setting.
- **ELF/x86 executables:** BCJ + XZ improves direct XZ, but current AXIOM structural experiments are only single-digit-percent improvements, not Beast-class.
- **Source-only Android/Kotlin/XML:** Brotli already compresses the fixed 327,680 B source-only TAR to 27,782 B; naive token/syntax factorization is worse.
- **ZIP specialist comparison:** the ~30.9% WHL win is against strong direct whole-file compressors. Specialist Preflate/Precomp comparison remains unresolved, so no ZIP-specialist supremacy claim is made.

Negative results are retained in `FAILURES.md` because they are constraints on the next architecture.

## The larger architecture: a causal/law compiler

The long-term target is not a pile of hard-coded format preprocessors. AXIOM should infer a reversible dependency graph:

1. identify candidate variables/objects/states,
2. discover deterministic or cheap near-deterministic relations,
3. choose an independent information basis,
4. search equivalent reversible coordinate systems,
5. serialize residuals in the topology induced by their generating laws,
6. optionally search compact generative codec bases,
7. entropy-code only the unexplained remainder,
8. verify the inverse byte-for-byte.

The objective is minimum **total executable description length**, not minimum intermediate byte count.
