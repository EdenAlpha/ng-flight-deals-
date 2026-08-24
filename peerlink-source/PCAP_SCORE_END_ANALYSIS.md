# Direct PCAP analysis for eFootball score capture

All timings below are relative to the first packet of the dominant gameplay UDP flow in each capture. The raw captures were parsed directly; the detector values are not guessed from UI timing.

## Capture hashes

- `PCAPdroid_03_Jul_11_46_30.pcap` — SHA-256 `84ecc1551a4a585af4cd1876c5265017ab4acb0dba9faf30b194bdd540450171`
- `PCAPdroid_03_Jul_11_46_34.pcap` — SHA-256 `c57e541fde6fc80c3e12b711107d6acf9a6b8d720b65acbbcc6a38e9a158363c`
- `PCAPdroid_28_Jun_15_53_33.pcap` — SHA-256 `2ed5d20b9e7ff6ba038a58d6d7cdcf4ca8ebb709b8099252bc69044b8d66914e`

## Capture 1: DTLS gameplay, no terminal drain before recording stops

`PCAPdroid_03_Jul_11_46_30.pcap` contains 29,776 IP packets. The dominant UDP flow contains 13,376 packets and lasts about 260.897 s.

The payload begins with `17 FE FD`, i.e. DTLS 1.2 application-data records after the handshake. Common outgoing UDP payload sizes are 83, 103 and 107 bytes; common incoming sizes are 81 and 101 bytes. There is no sustained <=80-byte DTLS terminal run at the end of the recorded dominant flow, so the production detector should not fire on this capture.

## Capture 2: DTLS terminal drain

`PCAPdroid_03_Jul_11_46_34.pcap` contains 28,536 IP packets. The dominant UDP flow contains 17,556 packets and lasts about 347.760 s.

The DTLS handshake is present. The ServerHello selects cipher suite `0xC030`, `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`. Therefore the application records cannot be passively decrypted from the PCAP alone: the session uses ephemeral ECDHE plus authenticated AES-GCM.

During active gameplay the dominant outgoing application-data record is normally 107 bytes and the dominant incoming record is normally 105 bytes. Near termination the flow collapses to a very stable low-size regime:

- incoming: mostly 68 bytes
- outgoing: mostly 70 bytes
- occasional 69/71/74/76/77-byte records

A family-aware detector requiring a DTLS application-data prefix (`17 FE FD`), UDP payload <=80 bytes, >=8 matching packets and >=500 ms sustained duration fires at about +347.296 s. Earlier isolated 79/80-byte packets do not form a sustained run, so they do not trigger it.

## Capture 3: custom P2P terminal drain

`PCAPdroid_28_Jun_15_53_33.pcap` contains 14,104 IP packets. The dominant custom-P2P UDP flow contains 6,937 packets and lasts about 156.886 s.

Its custom transport packet sequence is visible in the first bytes (`00 00` followed by a monotonically changing packet sequence field). At match termination the gameplay payload drains into a low transport/reliability regime from about +152.095 s to +153.852 s:

- 88 consecutive <=36-byte packets in the terminal run
- 71 are exactly 26 bytes
- 7 are 27 bytes
- 7 are 32 bytes
- 2 are 36 bytes
- 1 is 34 bytes

The same >=8 packets / >=500 ms detector fires at about +152.666 s. There is an earlier <=36-byte handshake-era run near +10-12 s, which is why the production detector also waits until established gameplay has been active for at least 30 s.

## Outbound-only validation against PeerLink's actual hook

PeerLink evaluates this detector on the local phone's outbound TUN gameplay path, not on a merged two-direction PCAP stream. Replaying only that outbound direction gives the same decisive behavior:

- `03_Jul_11_46_30`: no trigger.
- `03_Jul_11_46_34`: trigger at +347.2957 s after 14 consecutive matching outbound DTLS records spanning 504 ms.
- `28_Jun_15_53_33`: trigger at +152.6661 s after 16 consecutive matching outbound custom-P2P packets spanning 527 ms.

After the 30 s arm point, capture 2 has exactly one sustained outbound terminal-family run (about 0.968 s total), capture 3 has exactly one (about 1.384 s total), and capture 1 has none. This validates the threshold on the same traffic direction used by the native runtime detector rather than relying on bidirectional packet density.

## Score-data conclusion

A raw byte search across all three captures finds no plaintext `HOME_SCORE`, `AWAY_SCORE`, `GAME_PHASE`, `GAME_RESULT`, `END_REASON`, `score`, or `goal` strings.

The 26-byte custom-P2P terminal packets are transport/reliability traffic, not explicit final-score packets. The DTLS captures are strongly encrypted with ephemeral ECDHE/AES-GCM. Static analysis of the current eFootball binary separately recovers real application result fields (`GAME_PHASE`, `HOME_SCORE`, `AWAY_SCORE`) but has not established that those fields are serialized onto the live P2P wire.

Therefore the production score path is deliberately split:

1. packet traffic supplies the precise one-shot **WHEN** signal for match termination;
2. PeerLink captures the screen only after that event;
3. on-device OCR extracts the final visible score;
4. no continuous screenshot polling is required.

Direct packet score decoding remains a research path that would require locating the plaintext boundary/session key or proving a score/result message is actually present in the live P2P application payload.
