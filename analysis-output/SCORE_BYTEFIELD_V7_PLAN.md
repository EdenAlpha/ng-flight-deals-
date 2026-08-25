# Concrete score byte-field trace

The next analysis no longer treats `HOME_SCORE`, `AWAY_SCORE`, and `GAME_PHASE` string xrefs as sufficient evidence of a wire serializer. It searches the current ARM64 binary for concrete memory operations using the recovered result-layout offsets `+0x48`, `+0x4B`, and `+0x4C`, then traces those byte users toward the server-result and P2P/crypto families.

A paired `+0x4B/+0x4C` user, especially one that also touches `+0x48`, is the strongest current static seed for following the actual score bytes rather than schema labels.
