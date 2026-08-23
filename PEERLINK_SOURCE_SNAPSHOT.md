# PeerLink latest recovered source snapshot

This branch contains the latest full PeerLink source snapshot recoverable from the project files available on 2026-08-23.

Source snapshot provenance: `PeerLink-UX-jitter-full.zip` produced 2026-08-09. It was compared against `PeerLink-UX-jitter-fixed-files.zip`: every fixed/changed file already matched and every obsolete-file deletion was already satisfied. Therefore this is the post-jitter/post-cleanup source tree, not an older unpatched copy.

Full browsable project: `peerlink-source/`

Important native networking source: `peerlink-source/app/src/main/jni/peerlink_backend.cpp`

The complete Gradle wrapper and project files are retained. The eFootball reverse-engineering material remains on branch `efootball-packet-analysis-2026-08-23` / PR #771.
