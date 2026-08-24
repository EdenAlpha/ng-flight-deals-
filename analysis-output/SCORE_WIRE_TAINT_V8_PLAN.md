# Score wire taint v8

Trace only the eFootball result-byte loads proven by adjacent HOME_SCORE/AWAY_SCORE labels, then inspect their serializer helper, result-structure provenance, stack result builder, and downstream P2P/crypto paths. This deliberately excludes unrelated structures that merely reuse offsets +0x4B/+0x4C.
