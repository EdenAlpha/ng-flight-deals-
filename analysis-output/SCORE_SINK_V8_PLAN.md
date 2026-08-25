# Score sink trace v8

Trace the concrete HOME_SCORE/AWAY_SCORE byte loads through the serializer helper and identify the first downstream consumer of the structured result buffer. The goal is to prove or falsify a direct score-bytes-to-P2P/crypto path, rather than relying on schema strings or generic call-graph overlap.
