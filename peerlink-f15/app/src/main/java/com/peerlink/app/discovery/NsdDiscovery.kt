package com.peerlink.app.discovery

import android.content.Context
import android.net.wifi.WifiManager
import android.util.Log
import com.peerlink.app.core.AppState
import java.net.*
import java.util.concurrent.atomic.AtomicBoolean

/**
 * HotspotDiscovery — replaces mDNS/NSD with UDP broadcast discovery.
 *
 * Why the change:
 *   Android's NsdManager (DNS-SD / mDNS) requires multicast packets to flow
 *   through the network. Many Android hotspot implementations enable "AP isolation"
 *   which blocks multicast between clients, making NSD completely silent even when
 *   both phones are on the same hotspot. This is the root cause of "I never see my
 *   peer when I turn on hotspot."
 *
 *   UDP directed broadcast (255.255.255.255 or subnet broadcast) bypasses AP
 *   isolation on most hotspot implementations and is reliably delivered.
 *
 * The public interface is IDENTICAL to the old NsdDiscovery — MainActivity.kt
 * requires zero changes.
 *
 * Protocol:
 *   Both peers send a JSON "HELLO" beacon every 2 seconds on port 17026.
 *   When A hears B's HELLO, A calls onPeerFound(B.ip, B.port, B.name).
 *   When the listener stops, onPeerLost fires for all known peers.
 */
class NsdDiscovery(
    private val context: Context,
    private val callback: NsdCallback
) {
    companion object {
        private const val TAG              = "HotspotDisc"
        private const val DISCOVERY_PORT   = 17026
        private const val BEACON_INTERVAL  = 2_000L   // ms between broadcasts
        private const val SOCKET_TIMEOUT   = 1_200    // ms receive timeout
        private const val PEER_TTL_MS      = 8_000L   // remove peer if silent this long
    }

    interface NsdCallback {
        fun onPeerFound(ip: InetAddress, port: Int, serviceName: String)
        fun onPeerLost(serviceName: String)
        fun onLog(message: String)
    }

    private val running     = AtomicBoolean(false)
    private var socket: DatagramSocket? = null
    private var beaconThread: Thread?   = null
    private var listenThread: Thread?   = null
    private var multicastLock: WifiManager.MulticastLock? = null

    // Our own identity (set in registerService)
    private var localPort  = 0
    private var userName   = ""
    private var localIp    = ""
    private var localPrefixLength = 24

    private data class SeenPeer(val name: String, val address: InetAddress, val lastSeenMs: Long)
    // Track by IP, not display name. Two players are allowed to choose the same name.
    private val knownPeers = mutableMapOf<String, SeenPeer>()
    private val lastDirectReplyMs = mutableMapOf<String, Long>()

    val isRunning: Boolean get() = running.get()

    // ── Public API (unchanged from old NsdDiscovery) ─────────────────────────

    fun initialize() {
        callback.onLog("[NET-DISC  ] UDP broadcast discovery initialised (replaces mDNS)")
    }

    fun registerService(port: Int, name: String, ip: String, prefixLength: Int = 24) {
        localPort = port
        userName  = name
        localIp   = ip
        localPrefixLength = prefixLength.coerceIn(1, 32)
        callback.onLog("[NET-DISC  ] Registered as \"$name\" on $ip:$port")
    }

    fun startDiscovery() {
        if (!running.compareAndSet(false, true)) return

        // Multicast lock still needed even for broadcast on some chipsets
        acquireMulticastLock()

        try {
            // Bind to the Wi-Fi / hotspot interface explicitly (by local IP) so
            // beacons cannot leak out the cellular interface when mobile data is
            // on. Without this, Android routes 255.255.255.255 broadcasts through
            // the default route — which is cellular on multi-homed devices — and
            // causes the "ghost peer with no name" entries the user has been
            // seeing. Fall back to wildcard binding only if localIp is unknown.
            val bindAddr: InetAddress? =
                if (localIp.isNotBlank() && localIp != "127.0.0.1") {
                    runCatching { InetAddress.getByName(localIp) }.getOrNull()
                } else null
            socket = DatagramSocket(null).apply {
                reuseAddress = true
                soTimeout    = SOCKET_TIMEOUT
                broadcast = true
                try {
                    bind(InetSocketAddress(bindAddr, DISCOVERY_PORT))
                } catch (bindError: Exception) {
                    callback.onLog("[NET-DISC  ] Exact LAN bind failed (${bindError.message}); using wildcard")
                    bind(InetSocketAddress(null as InetAddress?, DISCOVERY_PORT))
                }
            }
        } catch (e: Exception) {
            callback.onLog("[NET-DISC  ] Socket bind failed: ${e.message}")
            running.set(false)
            return
        }

        callback.onLog(
            "[NET-DISC  ] Listening on UDP $DISCOVERY_PORT" +
                (if (localIp.isNotBlank() && localIp != "127.0.0.1") " bound to $localIp" else " (wildcard)")
        )

        // ── Listen thread ──────────────────────────────────────────────────
        listenThread = Thread {
            while (running.get()) {
                // Receive incoming beacons
                try {
                    val buf = ByteArray(512)
                    val pkt = DatagramPacket(buf, buf.size)
                    socket?.receive(pkt)
                    handlePacket(pkt)
                } catch (_: SocketTimeoutException) { /* expected every 1.2 s */ }
                  catch (_: SocketException)        { /* socket closed = shutting down */ break }
                  catch (e: Exception)              { callback.onLog("[NET-DISC  ] recv err: ${e.message}") }

                // Expire silent peers
                val now = System.currentTimeMillis()
                val expired = knownPeers.filter { (_, v) -> now - v.lastSeenMs > PEER_TTL_MS }.keys.toList()
                expired.forEach { key ->
                    val peer = knownPeers.remove(key) ?: return@forEach
                    callback.onLog("[NET-DISC  ] Discovery source expired: ${peer.name} @ $key")
                    callback.onPeerLost(peer.name)
                }
            }
        }.apply { name = "LanLink-Hotspot-Listen"; isDaemon = true; start() }

        // ── Beacon thread ──────────────────────────────────────────────────
        beaconThread = Thread {
            while (running.get()) {
                sendBeacon()
                try { Thread.sleep(BEACON_INTERVAL) } catch (_: InterruptedException) { break }
            }
        }.apply { name = "LanLink-Hotspot-Beacon"; isDaemon = true; start() }
    }

    fun stopDiscovery() {
        if (!running.compareAndSet(true, false)) return
        socket?.runCatching { close() }
        socket = null
        beaconThread?.interrupt()
        listenThread?.interrupt()
        beaconThread = null
        listenThread = null

        // Notify about source shutdown; MainActivity performs final presence expiry
        // using heartbeats from both discovery mechanisms, so one source stopping
        // cannot incorrectly erase a peer still visible through the other.
        knownPeers.values.toList().forEach { callback.onPeerLost(it.name) }
        knownPeers.clear()

        releaseMulticastLock()
        callback.onLog("[NET-DISC  ] Discovery stopped")
    }

    fun tearDown() {
        stopDiscovery()
    }

    // ── Internal ──────────────────────────────────────────────────────────────

    private fun sendBeacon() {
        if (userName.isBlank()) return
        try {
            val payload = """{"type":"LL_HELLO","name":"$userName","port":$localPort,"device_id":"${AppState.deviceId}"}"""
                .toByteArray(Charsets.UTF_8)

            // Subnet broadcast only — bound socket already routes this through the
            // Wi-Fi / hotspot interface. We used to also send 255.255.255.255, but
            // on multi-homed devices with mobile data on, that broadcast can be
            // echoed back over the cellular interface and appear as a "ghost peer".
            val subnetBroadcast = directedBroadcast(localIp, localPrefixLength)
            if (subnetBroadcast != null) {
                socket?.send(
                    DatagramPacket(
                        payload, payload.size,
                        InetAddress.getByName(subnetBroadcast), DISCOVERY_PORT
                    )
                )
            } else {
                // localIp unknown — fall back to limited broadcast. Still safe
                // because the socket is bound to a specific interface when localIp
                // was set; if localIp is blank, this matches the old behavior.
                socket?.send(
                    DatagramPacket(
                        payload, payload.size,
                        InetAddress.getByName("255.255.255.255"), DISCOVERY_PORT
                    )
                )
            }
        } catch (e: Exception) {
            callback.onLog("[NET-DISC  ] beacon send err: ${e.message}")
        }
    }

    private fun directedBroadcast(ip: String, prefixLength: Int): String? {
        val parts = ip.split('.').mapNotNull { it.toIntOrNull() }
        if (parts.size != 4 || parts.any { it !in 0..255 } || prefixLength !in 1..32) return null
        var value = 0L
        for (part in parts) value = (value shl 8) or part.toLong()
        val mask = if (prefixLength == 32) 0xFFFF_FFFFL else (0xFFFF_FFFFL shl (32 - prefixLength)) and 0xFFFF_FFFFL
        val broadcast = (value and mask) or (mask.inv() and 0xFFFF_FFFFL)
        return listOf(24, 16, 8, 0).joinToString(".") { shift -> ((broadcast shr shift) and 0xFF).toString() }
    }

    private fun handlePacket(pkt: DatagramPacket) {
        try {
            val json = org.json.JSONObject(String(pkt.data, 0, pkt.length, Charsets.UTF_8))
            if (json.optString("type") != "LL_HELLO") return

            val peerName = json.optString("name", "").ifBlank { return }
            val peerPort = json.optInt("port", 17024)
            val senderIp = pkt.address ?: return

            // Identity is device-based, not display-name-based. Two players may
            // legitimately choose the same name; only ignore our own device/beacon.
            val peerDeviceId = json.optString("device_id", "")
            if (senderIp.hostAddress == localIp) return
            if (peerDeviceId.isNotBlank() && peerDeviceId == AppState.deviceId) return

            val peerKey = senderIp.hostAddress ?: return
            val isNew = !knownPeers.containsKey(peerKey)
            knownPeers[peerKey] = SeenPeer(peerName, senderIp, System.currentTimeMillis())

            // Reply directly so hotspot hosts/clients can discover each other even
            // when one side's broadcast is not forwarded by the hotspot implementation.
            val now = System.currentTimeMillis()
            val senderKey = senderIp.hostAddress ?: ""
            val lastReply = lastDirectReplyMs[senderKey] ?: 0L
            if (now - lastReply > 2_000L) {
                lastDirectReplyMs[senderKey] = now
                try {
                    val payload = """{"type":"LL_HELLO","name":"$userName","port":$localPort,"device_id":"${AppState.deviceId}"}"""
                        .toByteArray(Charsets.UTF_8)
                    socket?.send(DatagramPacket(payload, payload.size, senderIp, DISCOVERY_PORT))
                } catch (_: Exception) { }
            }

            if (isNew) {
                callback.onLog("[NET-DISC  ] Peer found: $peerName @ $peerKey")
            }
            // Presence heartbeat: always report a valid HELLO. MainActivity merges
            // both discovery sources by IP and only mutates the Compose list when
            // something actually changes.
            callback.onPeerFound(senderIp, peerPort, peerName)
        } catch (_: Exception) { /* malformed packet, ignore */ }
    }

    private fun acquireMulticastLock() {
        val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        multicastLock = wm?.createMulticastLock("LanLinkDisc")?.apply {
            setReferenceCounted(false)
            acquire()
        }
    }

    private fun releaseMulticastLock() {
        multicastLock?.runCatching { release() }
        multicastLock = null
    }
}
