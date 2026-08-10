# AXIOM Beast v0.8 — negative results retained on purpose

Failed ideas are recorded as constraints so future work does not rediscover them.

## Raw image: spatial predictors alone

Row/channel/spatial predictors strongly beat generic byte compressors but did not beat lossless JPEG XL. A generic lossy JPEG XL basis + exact residual also failed because visual closeness did not imply a cheap exact correction.

**What finally worked:** codec-ancestry search using a compact JPEG basis whose exact FFmpeg-decoded pixels minimize basis-description + correction-description. This is now a v0.8 success, not a failure.

## Raw video

The corrected, SHA-verified FFV1 baseline on the fixed 96-frame 320x180 YUV420 corpus is **418,062 B**.

Failed approaches:
- causal temporal/horizontal/vertical/spatiotemporal block predictors,
- simple temporal difference/XOR preprocessing before FFV1,
- naive H.264 lossy basis + exact residual (best tested CRF10 total ~660 KB).

Conclusion: video needs deeper inverse recovery of motion/transform/codec state or a better joint spatiotemporal law; simple residual preprocessing destroys statistics FFV1 already models well.

## Plain prose

PPMd reaches **174,465 B** on the fixed Pride & Prejudice text corpus. Current AXIOM text-band results are ~194–198 KB. Word dictionaries, separator bands and naive contextual token IDs remained ~206–215 KB.

Conclusion: a high-order language context is only useful if the model itself has a cheap description. Storing a huge context table would merely move the entropy into the model.

## ELF/x86

Direct XZ on the tested `/usr/bin/bash`: 523,712 B. x86 BCJ + XZ: 491,036 B. ELF section/relocation/symbol graphing only improved modestly beyond BCJ. Explicitly separating CALL/JMP target coordinates made the total worse.

Conclusion: standard BCJ already captures much of the easy branch-coordinate law. A radical win needs deeper instruction/semantic or build-ancestry inversion.

## Source-only Android tree

Brotli compresses the fixed 327,680 B Kotlin/XML source-only TAR to 27,782 B. Naive lexical tokenization/global identifier bands were worse.

Conclusion: substring/token repetition is already cheap for modern LZ/context compressors. AXIOM needs relations that ordinary matching cannot express, not syntax tokenization for its own sake.

## Multi-resolution Android icons

Treating launcher icons as a multi-resolution family saved only about 1.5 KB on the tested app. Kept as an optional relation, not promoted as a core breakthrough.

## JSON nested text bands

Applying the text transform inside JSON free-text fields did not improve final backend size. Cross-field/state/aggregate laws were more useful.
