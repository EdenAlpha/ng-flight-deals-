package com.peerlink.app.tunnel

import androidx.annotation.Keep
import com.peerlink.app.core.AppState
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit

@Keep
class NativePeerLinkBackend(
    private val config: NativeBackendConfig,
    private val callbacks: Callbacks,
) {

    interface Callbacks {
        fun preparePeerSocket(fdForBinding: Int): Boolean
        fun fabricateStunResponse(packet: ByteArray, length: Int): ByteArray?
        fun onNativeLog(level: Int, message: String, fileOnly: Boolean) {}
        fun onStats(stats: NativeBackendStats) {}
        fun onMatchTerminalDetected() {}
    }

    @Keep
    private inner class NativeCallbacks {
        @Suppress("unused")
        fun preparePeerSocket(fdForBinding: Int): Boolean {
            return callbacks.preparePeerSocket(fdForBinding)
        }

        @Suppress("unused")
        fun fabricateStunResponse(packet: ByteArray, length: Int): ByteArray? {
            return callbacks.fabricateStunResponse(packet, length)
        }

        @Suppress("unused")
        fun onNativeLog(level: Int, message: String, fileOnly: Boolean) {
            callbacks.onNativeLog(level, message, fileOnly)
        }

        @Suppress("unused")
        fun onMatchTerminalDetected() {
            AppState.appendLog("[MATCH-END  ] Native eFootball terminal signature confirmed")
            callbacks.onMatchTerminalDetected()
        }
    }

    private var nativeHandle: Long = 0L
    private val nativeCallbacks = NativeCallbacks()
    private var statsExecutor: ScheduledExecutorService? = null

    @Volatile
    var latestStats: NativeBackendStats = NativeBackendStats.EMPTY
        private set

    fun start(tunFd: Int): Int {
        check(nativeHandle == 0L) { "Native backend already started" }

        val startResult = nativeStart(
            tunFd = tunFd,
            peerLanIp = config.peerLanIp,
            peerPort = config.peerPort,
            myFabricatedIp = config.myFabricatedIp,
            peerFabricatedIp = config.peerFabricatedIp,
            vpnAddress = config.vpnAddress,
            vpnAddressIpv6 = config.vpnAddressIpv6,
            localLanIp = config.localLanIp,
            localInterfaceIndex = config.localInterfaceIndex,
            mtu = config.mtu,
            callbacks = nativeCallbacks,
        )

        if (startResult.size < 2 || startResult[0] == 0L || startResult[1] <= 0L) {
            throw IllegalStateException("Native backend failed to start")
        }

        nativeHandle = startResult[0]
        latestStats = NativeBackendStats.EMPTY
        startStatsPolling()
        return startResult[1].toInt()
    }

    /** Close the live transport FDs immediately without waiting for thread joins.
     * This is used by the UI disconnect path so Android can tear down the TUN
     * interface promptly; stop() still performs the full join/delete cleanup.
     */
    fun requestImmediateStop() {
        val handle = nativeHandle
        if (handle != 0L) nativeRequestStop(handle)
    }

    fun stop() {
        stopStatsPolling()
        val handle = nativeHandle
        nativeHandle = 0L
        if (handle != 0L) {
            nativeStop(handle)
        }
        latestStats = NativeBackendStats.EMPTY
    }

    fun pollStats(): NativeBackendStats {
        val handle = nativeHandle
        if (handle == 0L) return NativeBackendStats.EMPTY
        val stats = NativeBackendStats.fromRaw(nativePollStats(handle))
        latestStats = stats
        return stats
    }

    fun pollMatchTerminalDetected(): Boolean {
        val handle = nativeHandle
        if (handle == 0L) return false
        return nativePollMatchTerminal(handle)
    }

    fun dumpUdpTrace(): String {
        val handle = nativeHandle
        if (handle == 0L) return ""
        return nativeDumpUdpTrace(handle)
    }

    fun rebindPeerSocket(): Boolean {
        val handle = nativeHandle
        if (handle == 0L) return false
        return nativeRebindPeerSocket(handle)
    }

    /**
     * Kernel thread IDs (gettid) of the latency-critical native loops — the TUN
     * reader, peer RX and peer TX threads. Returned in registration order as
     * each loop starts. Used by GodMode to promote them to SCHED_FIFO via the
     * Prime helper only when it is actually running as uid 0; normal ADB-shell
     * Prime cannot assume SCHED_FIFO privileges. This exposes the TIDs for that
     * best-effort root-only promotion path and for diagnostics.
     * eFootball's render threads from preempting packet handling. Returns an
     * empty array if the backend isn't running yet.
     */
    fun hotThreadTids(): IntArray {
        val handle = nativeHandle
        if (handle == 0L) return IntArray(0)
        return runCatching { nativeGetHotThreadTids(handle) }.getOrDefault(IntArray(0))
    }

    /** Prove the real native UDP data plane works in both directions. */
    fun verifyPeerPath(timeoutMs: Int = 60_000): Boolean {
        val handle = nativeHandle
        if (handle == 0L) return false
        return nativeVerifyPeerPath(handle, timeoutMs.coerceIn(500, 90_000))
    }

    private fun startStatsPolling() {
        stopStatsPolling()
        statsExecutor = Executors.newSingleThreadScheduledExecutor { runnable ->
            Thread(runnable, "PeerLink-Native-Stats").apply { isDaemon = true }
        }.also { executor ->
            executor.scheduleAtFixedRate(
                {
                    runCatching {
                        val stats = pollStats()
                        AppState.tunneled.set(stats.totalTunneledPackets)
                        callbacks.onStats(stats)
                    }
                },
                1L,
                1L,
                TimeUnit.SECONDS,
            )
        }
    }

    private fun stopStatsPolling() {
        statsExecutor?.shutdownNow()
        statsExecutor = null
    }

    private external fun nativeStart(
        tunFd: Int,
        peerLanIp: String,
        peerPort: Int,
        myFabricatedIp: String,
        peerFabricatedIp: String,
        vpnAddress: String,
        vpnAddressIpv6: String,
        localLanIp: String,
        localInterfaceIndex: Int,
        mtu: Int,
        callbacks: Any,
    ): LongArray

    private external fun nativeRequestStop(handle: Long)
    private external fun nativeStop(handle: Long)

    private external fun nativePollStats(handle: Long): LongArray
    private external fun nativeDumpUdpTrace(handle: Long): String
    private external fun nativePollMatchTerminal(handle: Long): Boolean
    private external fun nativeRebindPeerSocket(handle: Long): Boolean
    private external fun nativeGetHotThreadTids(handle: Long): IntArray
    private external fun nativeVerifyPeerPath(handle: Long, timeoutMs: Int): Boolean

    companion object {
        const val LOG_LEVEL_INFO = 1
        const val LOG_LEVEL_WARN = 2
        const val LOG_LEVEL_ERROR = 3

        init {
            System.loadLibrary("peerlinkbackend")
        }

        fun fabricateStunWithExistingLogic(
            config: NativeBackendConfig,
            packet: ByteArray,
            length: Int,
        ): ByteArray? {
            if (length <= 0 || packet.isEmpty()) return null
            val version = (packet[0].toInt() ushr 4) and 0x0F
            return when (version) {
                4 -> {
                    val parsed = PacketParser.parse(packet, length)
                    if (!parsed.isValid) {
                        null
                    } else {
                        StunFabricator.fabricateStunResponse(
                            originalPacket = parsed,
                            rawData = packet,
                            rawDataLength = length,
                            fabricatedIp = config.myFabricatedIp,
                            fabricatedPort = parsed.sourcePort,
                            vpnAddress = config.vpnAddress,
                        )
                    }
                }
                6 -> {
                    if (length < 48) {
                        null
                    } else {
                        val srcPort = ((packet[40].toInt() and 0xFF) shl 8) or (packet[41].toInt() and 0xFF)
                        StunFabricator.fabricateIpv6StunResponse(
                            ipv6Packet = packet,
                            length = length,
                            fabricatedIpv4 = config.myFabricatedIp,
                            fabricatedPort = srcPort,
                        )
                    }
                }
                else -> null
            }
        }
    }
}
