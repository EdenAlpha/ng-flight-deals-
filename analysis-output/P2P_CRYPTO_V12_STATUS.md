# eFootball direct-P2P crypto trace status

- Exact `libUE4.so` SHA-256 under analysis: `2ac4ff17ac8ad713d9531c2601e38a3c8335e02ea882ba2dc4445c191c1298cd`.
- Correction: `0x7c0c670` is **not** the packet cipher. It copies/normalizes crypto-related configuration fields, including the session-encryption algorithm and key-length fields.
- The native binary explicitly parses `KeyExchangeEncryptionAlgorithm`, `KeyExchangeEncryptionKey`, `SessionKeyEncryptionAlgorithm`, and `SessionKeyEncryptionKeyLength`.
- The bundled native custom-encryption module repeatedly materializes the names `pes-custom-encrypt`, `AES256`, and `blowfish`; one nearby implementation also exposes `SHA256`.
- P2P/network configuration separately includes `ScrambleEnable` and `ScrambleCode`.
- Therefore the remaining proof target is the runtime packet path: serializer -> optional scramble/cipher -> socket send, and the reciprocal receive path.
- Do not treat configuration parsing alone as proof that a given captured P2P session used AES/Blowfish. Trace the actual runtime dispatch and packet buffer.
