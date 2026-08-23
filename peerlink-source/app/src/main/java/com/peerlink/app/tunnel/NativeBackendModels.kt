package com.peerlink.app.tunnel

/** Static configuration for the native packet backend. */
data class NativeBackendConfig(
    val peerLanIp: String,
    val peerPort: Int,
    val myFabricatedIp: String,
    val peerFabricatedIp: String,
    /** Exact peer-reachable source IPv4 locked before VPN startup. */
    val localLanIp: String,
    /** Kernel interface index for the same LAN path (SoftAP or wlan). */
    val localInterfaceIndex: Int,
    val vpnAddress: String = "10.0.0.2",
    val vpnAddressIpv6: String = "fd00::2",
    val mtu: Int = 1400,
)

/** Pollable counters exported by the native backend. */
data class NativeBackendStats(
    val tunnelOutPackets: Long,
    val tunnelOutBytes: Long,
    val tunnelInPackets: Long,
    val tunnelInBytes: Long,
    val stunInterceptedIpv4: Long,
    val stunInterceptedIpv6: Long,
    val passthroughToJvmPackets: Long,
    val passthroughToTunPackets: Long,
    val droppedPackets: Long,
    val keepaliveTx: Long,
    val keepaliveRx: Long,
) {
    val totalTunneledPackets: Long get() = tunnelOutPackets + tunnelInPackets

    companion object {
        val EMPTY = NativeBackendStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

        fun fromRaw(raw: LongArray?): NativeBackendStats {
            if (raw == null || raw.size < 11) return EMPTY
            return NativeBackendStats(
                tunnelOutPackets = raw[0],
                tunnelOutBytes = raw[1],
                tunnelInPackets = raw[2],
                tunnelInBytes = raw[3],
                stunInterceptedIpv4 = raw[4],
                stunInterceptedIpv6 = raw[5],
                passthroughToJvmPackets = raw[6],
                passthroughToTunPackets = raw[7],
                droppedPackets = raw[8],
                keepaliveTx = raw[9],
                keepaliveRx = raw[10],
            )
        }
    }
}
