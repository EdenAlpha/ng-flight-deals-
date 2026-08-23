# PeerLink UX, Discovery, VPN and Jitter Audit

## Scope
This pass improves session UX, discovery lifecycle, VPN teardown, hotspot/LAN path reliability, Prime Mode command correctness, and pre-buffer latency. The jitter buffer configuration was intentionally left unchanged.

## VPN / disconnect
- Added explicit session states: DISCONNECTED, CONNECTING, VERIFYING, CONNECTED, DISCONNECTING, ERROR.
- Slide-to-disconnect now enters a real Disconnecting state instead of snapping visually back to connected.
- The native-owned detached TUN file descriptor is closed immediately on user disconnect. Slow worker-thread cleanup happens after the VPN interface has been told to close.
- Deliberate disconnect clears saved sticky-session state and pairing-start latches so a later session can start normally.
- VPN startup now fails closed if eFootball cannot be scoped with addAllowedApplication; PeerLink will not silently become a device-wide VPN.

## Discovery
- Removed the 90-second global discovery lifetime. Discovery remains available while the app is in discovery mode.
- Removed stop-on-onPause behavior. Brief system dialogs/settings transitions no longer permanently kill discovery.
- Removed the 3-second Wi-Fi AP scan loop; PeerLink peer discovery uses its own UDP beacons and does not need WifiManager.startScan().
- Discovery now binds only to an actual Wi-Fi / SoftAP LAN interface. Cellular RFC1918 addresses are not accepted as a fake LAN.
- When no Wi-Fi/hotspot LAN exists, the UI reports WAITING_FOR_WIFI rather than pretending to search.
- Discovery self-heals when the LAN path changes or a listener dies.
- Both discovery mechanisms feed one shared IP/freshness presence table, so one source cannot incorrectly remove a peer still being seen by the other.
- Peer entries expire centrally after a shared freshness timeout.
- Discovery pauses during an active VPN/game session to keep the gameplay path quiet and resumes after disconnect.
- The VPN-start-in-flight latch is released from real session state; successful sessions no longer block the next pairing until app restart.

## Hotspot / LAN path
- PeerLink resolves the exact local interface and address that can route to the selected peer.
- Hotspot-owner SoftAP and normal Wi-Fi station mode are handled separately.
- Native UDP is source-bound and interface-pinned to the resolved peer LAN path.
- A bidirectional native probe/ACK must succeed before the VPN session is considered CONNECTED.
- Verification allows up to 60 seconds for the other phone to complete VPN consent/startup.

## Jitter investigation and changes (jitter buffer untouched)
Likely application-created timing disturbances found and corrected:

1. **Repeated Wi-Fi scans**
   - MainActivity previously called WifiManager.startScan() every 3 seconds.
   - Prime also disabled scan throttling.
   - Both behaviors were removed. Peer discovery does not require AP scans.

2. **Excessive tunnel keepalives**
   - Native keepalive traffic could run around every 50-100 ms on the same UDP socket/mutex as gameplay.
   - Maintenance cadence is now 0.5 s during the first 30 s, 0.75 s to 90 s, then 1 s.
   - Successful gameplay sends refresh the timer, so active ~20 pps gameplay suppresses maintenance keepalives rather than competing with them.

3. **Repeated route/network work during gameplay**
   - A 1-second ConnectivityManager poll was reduced to a 10-second safety check; NetworkCallback is primary.
   - Hotspot-owner/kernel-pinned sessions no longer rewrite underlying network state every second merely because SoftAP lacks a normal Android Network object.

4. **Redundant foreground service**
   - LanLinkForegroundService was removed. It woke every 5 seconds for status notification work while the real VPN service already owns the active tunnel lifecycle.

5. **QoS claims corrected**
   - Removed the incorrect claim that IP_TOS=0x10 guarantees WMM Voice.
   - The local PeerLink tunnel now uses best-effort DSCP 46, SO_PRIORITY 6 and optional SO_BUSY_POLL, and logs which socket options were accepted. Correctness never depends on them.

6. **Timing instrumentation added**
   - `[NATIVE/LAT] localProc ... peakDepth=...` measures TUN-read -> local Wi-Fi send scheduling/queue delay.
   - `[NATIVE/LAT] inboundQueue ... peakDepth=...` measures received peer packet -> TUN injection delay.
   - Existing T0/TX/RX gap diagnostics remain useful.

### Still intentionally not changed
The peer datapath currently has an outbound queue/thread handoff and an inbound queue/thread handoff. Those can create scheduler jitter if a device stalls, but changing queue architecture without evidence could make reliability worse. The new timing logs are intended to determine whether that is the remaining source. The jitter buffer itself is completely untouched in this pass.

## Prime / Shizuku / ADB audit
Kept commands and their intended roles:
- `pm grant com.peerlink.app android.permission.WRITE_SECURE_SETTINGS` during Wireless Debugging bootstrap.
- `svc wifi enable` / `svc wifi disable` for optional Auto Mode radio handling, with real WifiManager state verification before recording/restoring state.
- `am get-standby-bucket jp.konami.pesam` and `am set-standby-bucket jp.konami.pesam active` for optional eFootball standby-bucket promotion, with original bucket restoration.
- `id -u`; `chrt -f -p 10 <tid>` is attempted only when Prime actually reports uid 0. Normal Wireless Debugging shell is not falsely treated as root.

Removed misleading/counterproductive behavior:
- Wi-Fi scan-throttle disabling.
- `pm trim-caches 4096G` labeled as a RAM clear.
- hidden pre-game `am kill-all` RAM-clear behavior.
- captive-portal / Wi-Fi sleep / airplane-radio / fake 5 GHz / fake high-performance setting mutations.
- root-only low-latency shell claims in normal ADB-shell Prime.
- dead Prime Wi-Fi retry/group-owner monitor.

PrimeServer hardening:
- Loopback requests now require a random per-install authentication token passed through the existing starter -> app_process flow.
- PrimeServer remains bound to 127.0.0.1 only.
- ADB/mDNS discovery is stopped once Prime is active and resumed only when setup/recovery needs it, reducing gameplay-time background work.

## Files removed in this pass
- `app/src/main/java/com/peerlink/app/service/BootReceiver.kt`
- `app/src/main/java/com/peerlink/app/service/LanLinkForegroundService.kt`

The comprehensive fixed-files archive also contains a deletion manifest for obsolete files removed during the earlier PeerLink cleanup, so applying it to an older repository will not leave stale Kotlin/resource files behind.

## Next jitter test
Play one match with the jitter buffer still OFF on both phones and export both PeerLink logs. Check/send these lines:
- `[NATIVE/LAT] localProc`
- `[NATIVE/LAT] inboundQueue`
- `NATIVE/T0-GAP`
- `NATIVE/TX-GAP`
- RX gap diagnostics
- `[WIFI-QOS]`
- `[VPN-UNDER]`

Interpretation:
- High `localProc` max/peakDepth -> local TUN-to-TX scheduling/queue problem.
- High `inboundQueue` max/peakDepth -> local RX-to-TUN scheduling problem.
- Both remain low while packet gaps/jitter persist -> Wi-Fi radio/AP/hotspot-driver/topology is the stronger suspect.
