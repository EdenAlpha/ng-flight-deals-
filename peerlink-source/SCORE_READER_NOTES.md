# eFootball event-driven score reader

## Recovered facts

- Native eFootball result structure: `GAME_PHASE +0x48`, `HOME_SCORE +0x4B`, `AWAY_SCORE +0x4C`.
- The observed 26-byte terminal UDP packets are transport/reliability traffic, not an explicit score packet.
- `HOME_SCORE`, `AWAY_SCORE`, and `GAME_PHASE` are referenced by native result serializer/parser code, while `CMD_ADD_SCORE`, `CMD_GET_GAME_RESULT`, and `CMD_SET_GAME_RESULT` exist as separate game/server command paths.
- We have not yet proved a direct call path from those score serializers into the live P2P gameplay ciphertext path. Direct wire decoding therefore remains a parallel research track rather than a dependency of the practical reader.

## PCAP validation of match-end detector

The detector was checked against the three available real captures by parsing the dominant gameplay UDP flow and evaluating application UDP payload lengths.

| Capture | Dominant gameplay flow | Duration | Post-30s false terminal trigger | Terminal evidence |
| --- | --- | ---: | --- | --- |
| `PCAPdroid_03_Jul_11_46_30.pcap` | `10.215.173.1:36656 <-> 34.14.65.240:31808` | 260.9 s | none | none |
| `PCAPdroid_03_Jul_11_46_34.pcap` | `10.215.173.1:49915 <-> 34.62.54.28:32758` | 347.8 s | none | none |
| `PCAPdroid_28_Jun_15_53_33.pcap` | `10.233.65.237:56008 <-> 105.112.105.35:24722` | 156.9 s | none before terminal | clear terminal drain |

In the third capture, outbound application UDP payload stayed `<=36` bytes from about `+152.139 s` to `+153.522 s`: approximately `1.384 s` and 39 outbound packets. The run was dominated by 26-byte payloads (31 packets), with a few 27/32/34/36-byte packets. With the current rules the detector fires at about `+152.666 s`, after 16 qualifying packets.

There was an earlier short-payload episode around `+8.8 s`, which is why the detector does not arm until established gameplay has lasted 30 seconds.

Current detector requirements:

- stable classified gameplay UDP flow;
- at least 30 seconds since gameplay traffic began;
- application UDP payload `<=36` bytes;
- at least 8 qualifying packets;
- qualifying state sustained for at least 500 ms;
- one-shot terminal event with rearm/cooldown protection.

## Runtime path

`Native TUN gameplay classification -> terminal detector -> direct JNI callback on the same event -> event-only screenshot burst -> upper-frame ML Kit OCR -> persisted latest score`

The match-end signal no longer waits for the 1-second statistics poll; native code dispatches it immediately when the terminal rule becomes true. The screenshot burst occurs only after that terminal event, at roughly `t=0 ms`, `t=350 ms`, and `t=900 ms`, and stops immediately after a confident score is found. This protects against the transport entering its terminal state slightly before the final score UI settles while avoiding continuous screenshot polling during gameplay.

Prime Mode currently supplies the screenshot via `screencap`. A MediaProjection fallback remains to be added for devices where Prime Mode is not active.
