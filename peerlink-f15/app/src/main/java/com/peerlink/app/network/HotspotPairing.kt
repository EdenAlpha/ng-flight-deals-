package com.peerlink.app.network

import android.util.Log
import org.json.JSONObject
import java.net.BindException
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.SocketException
import java.net.SocketTimeoutException
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Deterministic UDP pairing for Hotspot mode.
 *
 * Previous behaviour:
 *  - discovery and pairing both used a generic PAIR packet
 *  - tapping a peer only set targetPeerIp and waited for a later matching packet
 *  - local tunnel port defaulted to 0 unless explicitly updated, so peers often never
 *    learned a usable port
 *
 * New behaviour:
 *  - HELLO beacons are discovery only
 *  - PAIR_REQ is sent immediately when the user taps a peer
 *  - PAIR_ACK is sent immediately in reply, so a single tap is enough
 *  - tunnel port is always advertised with a usable default (17024)
 */
class HotspotPairing {

    companion object {
        private const val TAG = "HotspotPairing"
        private const val PAIR_PORT = 17027
        private const val DEFAULT_TUNNEL_PORT = 17024
        private const val SOCKET_TIMEOUT = 1500
        private const val PAIR_ATTEMPT_TIMEOUT = 15_000L
        private const val PAIR_REQ_INTERVAL_MS = 750L
        private const val BEACON_INTERVAL = 2_000L
        private const val PEER_TTL_MS = 8_000L
        private const val DIRECT_REPLY_THROTTLE_MS = 2_000L
        private const val TYPE_HELLO = "HELLO"
        private const val TYPE_PAIR_REQ = "PAIR_REQ"
        private const val TYPE_PAIR_ACK = "PAIR_ACK"
    }

    private val running = AtomicBoolean(false)
    private var socket: DatagramSocket? = null
    private var thread: Thread? = null

    @Volatile private var targetPeerIp: String? = null
    @Volatile private var peerConfirmed = false
    @Volatile private var pairingStartedAtMs = 0L
    @Volatile private var lastPairReqMs = 0L
    @Volatile private var localTunnelPort = DEFAULT_TUNNEL_PORT
    @Volatile private var myUserName = ""
    @Volatile private var myDeviceId = ""
    // Local LAN IP (Wi-Fi / hotspot). When set, the listener socket is bound to
    // this IP so beacons and pairing packets cannot leak out the cellular
    // interface on multi-homed devices. Blank → wildcard bind (legacy).
    @Volatile private var localIp: String = ""
    @Volatile private var localPrefixLength: Int = 24

    var onPeerDiscovered: ((peerIp: String, peerName: String) -> Unit)? = null
    var onPeerReady: ((peerIp: String) -> Unit)? = null
    var onPeerPortReceived: ((peerPort: Int) -> Unit)? = null
    var onStatus: ((String) -> Unit)? = null
    var onPeerLost: ((peerIp: String) -> Unit)? = null

    private val knownPeerIps = mutableSetOf<String>()
    private val lastSeenMs = mutableMapOf<String, Long>()
    private val lastHelloReplyMs = mutableMapOf<String, Long>()

    fun start(deviceId: String, myName: String = "", localIp: String = "", prefixLength: Int = 24) {
        if (!running.compareAndSet(false, true)) return
        myUserName = myName
        myDeviceId = deviceId
        this.localIp = localIp.trim()
        this.localPrefixLength = prefixLength.coerceIn(1, 32)

        thread = Thread {
            try {
                // Bind to the Wi-Fi / hotspot interface explicitly (by local IP)
                // so broadcasts cannot leak out the cellular interface. This is
                // what makes direct hotspot-host ⇆ client discovery work
                // reliably even when mobile data is on.
                val bindAddr: InetAddress? =
                    if (this.localIp.isNotBlank() && this.localIp != "127.0.0.1") {
                        runCatching { InetAddress.getByName(this.localIp) }.getOrNull()
                    } else null
                socket = DatagramSocket(null).apply {
                    reuseAddress = true
                    soTimeout = SOCKET_TIMEOUT
                    broadcast = true
                    // Some OEM hotspot-owner interfaces cannot be explicitly
                    // bound from Java even though the kernel route is valid.
                    // Prefer the exact LAN IP, but fall back to wildcard rather
                    // than killing pairing; the data-plane socket is pinned later.
                    try {
                        bind(InetSocketAddress(bindAddr, PAIR_PORT))
                    } catch (bindError: Exception) {
                        Log.w(TAG, "[HOTSPOT   ] Exact discovery bind failed (${bindError.message}); using wildcard")
                        bind(InetSocketAddress(null as InetAddress?, PAIR_PORT))
                    }
                }
                Log.i(
                    TAG,
                    "[HOTSPOT   ] Listener on UDP $PAIR_PORT" +
                        (if (bindAddr != null) " bound to ${this.localIp}" else " (wildcard)")
                )

                var lastBeaconMs = 0L

                // Discovery is a lifecycle, not a one-shot 90-second operation.
                // Keep the listener alive until stop() is explicitly called. Only an
                // individual PAIR_REQ attempt is allowed to time out.
                while (running.get()) {
                    try {
                        val buf = ByteArray(2048)
                        val pkt = DatagramPacket(buf, buf.size)
                        socket!!.receive(pkt)
                        handlePacket(pkt)
                    } catch (_: SocketTimeoutException) {
                        // expected: used to wake up for beacon/expiry work
                    } catch (_: SocketException) {
                        break
                    }

                    expireSilentPeers()

                    val nowMs = System.currentTimeMillis()
                    if (nowMs - lastBeaconMs >= BEACON_INTERVAL) {
                        sendHelloBeacon()
                        lastBeaconMs = nowMs
                    }

                    // While the user has selected a peer but the handshake is not yet complete,
                    // keep nudging with PAIR_REQ so transient packet loss does not stall pairing.
                    val target = targetPeerIp
                    if (!peerConfirmed && target != null) {
                        val elapsed = nowMs - pairingStartedAtMs
                        if (pairingStartedAtMs > 0L && elapsed >= PAIR_ATTEMPT_TIMEOUT) {
                            Log.i(TAG, "[HOTSPOT   ] Pair attempt timed out for $target; discovery stays active")
                            targetPeerIp = null
                            pairingStartedAtMs = 0L
                            lastPairReqMs = 0L
                            onStatus?.invoke("Could not connect — still searching")
                        } else if (nowMs - lastPairReqMs >= PAIR_REQ_INTERVAL_MS) {
                            sendPairReq(target)
                            lastPairReqMs = nowMs
                        }
                    }
                }
            } catch (e: BindException) {
                Log.e(TAG, "[HOTSPOT   ] Port $PAIR_PORT busy: ${e.message}")
                onStatus?.invoke("Port busy — restart the app")
            } catch (e: Exception) {
                if (running.get()) Log.e(TAG, "[HOTSPOT   ] Error: ${e.message}", e)
            } finally {
                socket?.runCatching { close() }
                socket = null
                running.set(false)
            }
        }.apply {
            name = "LanLink-HotspotPairing"
            isDaemon = true
            start()
        }
    }

    /** User tapped a hotspot peer — begin actively sending a real pairing request. */
    fun initiatePairing(peerIp: String) {
        targetPeerIp = peerIp
        peerConfirmed = false
        pairingStartedAtMs = System.currentTimeMillis()
        lastPairReqMs = 0L
        onStatus?.invoke("Connecting to peer…")
        Log.i(TAG, "[HOTSPOT   ] Initiating pairing with $peerIp")
        sendPairReq(peerIp)
    }

    /** Called once VPN is up and the tunnel port is known. */
    fun updateLocalPort(port: Int) {
        if (port > 0) localTunnelPort = port
    }

    fun stop() {
        running.set(false)
        targetPeerIp = null
        peerConfirmed = false
        pairingStartedAtMs = 0L
        lastPairReqMs = 0L
        localTunnelPort = DEFAULT_TUNNEL_PORT
        knownPeerIps.clear()
        lastSeenMs.clear()
        lastHelloReplyMs.clear()
        socket?.runCatching { close() }
        thread?.interrupt()
    }

    val isRunning get() = running.get()

    private fun handlePacket(pkt: DatagramPacket) {
        val senderIp = pkt.address.hostAddress ?: return
        val json = JSONObject(String(pkt.data, 0, pkt.length, Charsets.UTF_8))
        val type = json.optString("type")
        val peerDeviceId = json.optString("device_id", "")
        if (peerDeviceId.isNotBlank() && peerDeviceId == myDeviceId) return

        val peerPort = json.optInt("tunnel_port", DEFAULT_TUNNEL_PORT)
        // optString returns "" if the key exists with an empty value (which is
        // exactly what happens when the sender passed the wrong arg order into
        // start() and myName defaulted to ""). Fall back to the sender IP so
        // the UI never shows a nameless peer.
        val rawName = json.optString("user_name", "")
        val peerName = rawName.ifBlank { senderIp }
        lastSeenMs[senderIp] = System.currentTimeMillis()

        when (type) {
            TYPE_HELLO -> {
                publishPeerIfNeeded(senderIp, peerName)
                maybeReplyHelloDirect(senderIp)
            }
            TYPE_PAIR_REQ -> {
                publishPeerIfNeeded(senderIp, peerName)
                if (peerPort > 0) onPeerPortReceived?.invoke(peerPort)
                targetPeerIp = senderIp
                sendPairAck(senderIp)
                confirmPeer(senderIp, fromAck = false)
            }
            TYPE_PAIR_ACK -> {
                publishPeerIfNeeded(senderIp, peerName)
                if (targetPeerIp == senderIp) {
                    if (peerPort > 0) onPeerPortReceived?.invoke(peerPort)
                    confirmPeer(senderIp, fromAck = true)
                }
            }
        }
    }

    private fun publishPeerIfNeeded(peerIp: String, peerName: String) {
        val isNew = knownPeerIps.add(peerIp)
        if (isNew) {
            Log.i(TAG, "[HOTSPOT   ] Peer discovered: $peerName @ $peerIp")
            onStatus?.invoke("Found peer: $peerName")
        }
        // Always emit a lightweight presence heartbeat. MainActivity merges this
        // with the secondary discovery source by IP, preventing one listener's
        // expiry from making a still-visible player disappear from the UI.
        onPeerDiscovered?.invoke(peerIp, peerName)
    }

    private fun confirmPeer(peerIp: String, fromAck: Boolean) {
        if (peerConfirmed) return
        peerConfirmed = true
        pairingStartedAtMs = 0L
        lastPairReqMs = 0L
        val msg = if (fromAck) "Peer acknowledged" else "Peer confirmed"
        Log.i(TAG, "[HOTSPOT   ] $msg: $peerIp")
        onStatus?.invoke(msg)
        onPeerReady?.invoke(peerIp)
    }

    private fun expireSilentPeers() {
        val now = System.currentTimeMillis()
        val expired = lastSeenMs.filter { (_, t) -> now - t > PEER_TTL_MS }.keys.toList()
        expired.forEach { ip ->
            lastSeenMs.remove(ip)
            knownPeerIps.remove(ip)
            lastHelloReplyMs.remove(ip)
            if (targetPeerIp == ip && !peerConfirmed) {
                targetPeerIp = null
            }
            onPeerLost?.invoke(ip)
            Log.i(TAG, "[HOTSPOT   ] Peer expired: $ip")
        }
    }

    private fun sendHelloBeacon() {
        val json = JSONObject().apply {
            put("type", TYPE_HELLO)
            put("device_id", myDeviceId)
            put("user_name", myUserName)
            put("tunnel_port", localTunnelPort)
        }
        val data = json.toString().toByteArray(Charsets.UTF_8)
        try {
            // Prefer subnet-directed broadcast (e.g. 192.168.43.255) — the
            // bound socket already routes this through the Wi-Fi / hotspot
            // interface, so it cannot leak to cellular. Fall back to
            // 255.255.255.255 only when localIp is unknown.
            val target = directedBroadcast(localIp, localPrefixLength) ?: "255.255.255.255"
            socket?.send(DatagramPacket(data, data.size, InetAddress.getByName(target), PAIR_PORT))
        } catch (e: Exception) {
            Log.w(TAG, "[HOTSPOT   ] HELLO send: ${e.message}")
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

    private fun maybeReplyHelloDirect(senderIp: String) {
        val now = System.currentTimeMillis()
        val last = lastHelloReplyMs[senderIp] ?: 0L
        if (now - last < DIRECT_REPLY_THROTTLE_MS) return
        lastHelloReplyMs[senderIp] = now
        sendPacket(
            targetIp = senderIp,
            type = TYPE_HELLO
        )
    }

    private fun sendPairReq(targetIp: String) {
        sendPacket(targetIp = targetIp, type = TYPE_PAIR_REQ)
    }

    private fun sendPairAck(targetIp: String) {
        sendPacket(targetIp = targetIp, type = TYPE_PAIR_ACK)
    }

    private fun sendPacket(targetIp: String, type: String) {
        try {
            val json = JSONObject().apply {
                put("type", type)
                    put("device_id", myDeviceId)
                put("user_name", myUserName)
                put("tunnel_port", localTunnelPort)
            }
            val data = json.toString().toByteArray(Charsets.UTF_8)
            socket?.send(DatagramPacket(data, data.size, InetAddress.getByName(targetIp), PAIR_PORT))
        } catch (e: Exception) {
            Log.w(TAG, "[HOTSPOT   ] $type send: ${e.message}")
        }
    }
}
