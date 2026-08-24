# eFootball event-driven score reader

'
'## Recovered facts
'
'- Native eFootball result structure: `GAME_PHASE +0x48`, `HOME_SCORE +0x4B`, `AWAY_SCORE +0x4C`.
'
'- The observed 26-byte terminal UDP packets are transport/reliability header-only traffic, not score packets.
'
'- In the real custom-P2P capture, outbound application UDP payload stayed `<=36` bytes for about 1.38 s at match termination; after established gameplay there was no comparable outbound run.
'
'- The detector therefore arms after established gameplay, requires >=8 short packets sustained for 500 ms, and fires once.

'
'## Runtime path
'
'Native TUN gameplay classification -> terminal detector -> one-shot Kotlin callback -> one Prime `screencap` -> upper-frame ML Kit OCR -> persisted latest score.

'
'There is deliberately no periodic screenshot loop. A MediaProjection fallback remains to be added for devices where Prime Mode is not active.
