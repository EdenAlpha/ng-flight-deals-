package com.peerlink.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import com.peerlink.app.core.AppState
import com.peerlink.app.core.VpnSessionState
import com.peerlink.app.godmode.GodModeManager
import com.peerlink.app.network.LanPathResolver
import com.peerlink.app.tunnel.NativeBackendConfig
import com.peerlink.app.tunnel.NativeBackendStats
import com.peerlink.app.tunnel.NativePeerLinkBackend
import com.peerlink.app.tunnel.PassthroughBridgeEngine
import com.peerlink.app.ui.MainActivity
import java.io.FileDescriptor
import java.util.concurrent.Executors
import java.util.concurrent.ScheduledExecutorService
import java.util.concurrent.TimeUnit
import java.lang.ref.WeakReference
import java.net.DatagramSocket
import java.net.Inet4Address

class PeerLinkVpnService : VpnService() {

    companion object {
        const val ACTION_STOP = "com.peerlink.STOP_VPN"
        const val NOTIFICATION_CHANNEL_ID = "lanlink_vpn"
        const val NOTIFICATION_ID = 1
        const val EFOOTBALL_PACKAGE = "jp.konami.pesam"
        // Minimum gap between forced peer-socket rebinds. Wi-Fi RSSI/capability
        // changes and brief AP flaps shouldn't each cause a socket tear-down —
        // the native backend can ride through most transient glitches if we
        // just leave it alone for a few seconds. Without this cooldown, a
        // momentary Wi-Fi flap could trigger 3-5 rebinds in rapid succession,
        // each one causing a 100-500ms packet loss window that eFootball
        // interprets as a disconnect.
        const val REBIND_COOLDOWN_MS: Long = 5_000L

        // ── Session-state persistence (for auto-restart after process kill) ──
        // On Android 15 the OS can kill the app process mid-session. START_STICKY
        // restarts the service, but AppState (in-memory) is lost. We persist the
        // session parameters to SharedPreferences so the restart can re-establish
        // the tunnel automatically.
        const val SESSION_STATE_PREFS = "peerlink_session_state"
        const val KEY_PEER_IP = "peer_ip"
        const val KEY_LOCAL_IP = "local_ip"
        const val KEY_CONNECTION_MODE = "connection_mode"
        const val KEY_TRANSPORT_MODE = "transport_mode"
        const val KEY_PEER_PORT = "peer_port"
        const val KEY_WAS_RUNNING = "was_running"
        const val KEY_SAVED_AT_MS = "saved_at_ms"

        @Volatile
        private var activeServiceRef: WeakReference<PeerLinkVpnService>? = null

        @Volatile
        private var lastNativeUdpTraceDump: String = ""

        fun dumpNativeUdpTrace(): String {
            val active = activeServiceRef?.get()
            val liveDump = try {
                active?.nativeBackend?.dumpUdpTrace().orEmpty()
            } catch (_: Exception) {
                ""
            }
            if (liveDump.isNotBlank()) {
                lastNativeUdpTraceDump = liveDump
                return liveDump
            }
            return lastNativeUdpTraceDump
        }

        fun requestGameplayPathRefresh(reason: String) {
            activeServiceRef?.get()?.refreshGameplayPath(reason, force = true)
        }

        fun prepareAuxDatagramSocket(socket: DatagramSocket, preferGameplayNetwork: Boolean = true): Boolean {
            return activeServiceRef?.get()?.prepareAuxDatagramSocketInternal(socket, preferGameplayNetwork) == true
        }

        fun getActiveNativeBackend(): NativePeerLinkBackend? = activeServiceRef?.get()?.nativeBackend
    }

    private var vpnInterface: ParcelFileDescriptor? = null
    // Java owns this descriptor only until detachFd(). After detachFd(), native
    // owns the raw TUN fd and must close that raw fd to remove the VPN interface.
    // If startup is cancelled before detach, Java closes this PFD directly.
    internal var nativeBackend: NativePeerLinkBackend? = null
    private var passthroughBridgeEngine: PassthroughBridgeEngine? = null
    private val stopVpnGuard = java.util.concurrent.atomic.AtomicBoolean(false)
    private val stopCleanupStarted = java.util.concurrent.atomic.AtomicBoolean(false)
    private var gameplayMonitorExecutor: ScheduledExecutorService? = null
    @Volatile private var lastGameplayNetworkIdentity: String? = null
    @Volatile private var gameplayRefreshAllowedAtMs: Long = 0L
    private val gameplayRefreshLock = Any()
    // Timestamp of the last successful rebind. Used by the NetworkCallback's
    // onLost handler to enforce a cooldown — without this, AP roaming or
    // momentary Wi-Fi flaps could trigger a rebind storm that tears down the
    // peer socket multiple times in quick succession, each one causing a
    // 100-500ms packet loss window that eFootball interprets as a disconnect.
    @Volatile private var lastRebindMs: Long = 0L
    private var tunnelWakeLock: android.os.PowerManager.WakeLock? = null
    private var wifiLowLatencyLock: android.net.wifi.WifiManager.WifiLock? = null
    private var notificationRefreshExecutor: ScheduledExecutorService? = null
    private val startupExecutor = Executors.newSingleThreadExecutor { runnable ->
        Thread(runnable, "PeerLink-VPN-Start").apply { isDaemon = true }
    }
    private val startupInFlight = java.util.concurrent.atomic.AtomicBoolean(false)
    private val startupCancelled = java.util.concurrent.atomic.AtomicBoolean(false)
    // NetworkCallback registered against Wi-Fi transports — fires the moment
    // the gameplay network becomes unavailable (Wi-Fi flap, AP roaming, signal
    // loss, hotspot host sleep). NetworkCallback is the primary signal; a slow
    // 10-second monitor exists only as an OEM safety net. We deliberately avoid
    // capability/RSSI-triggered rebinds because they create packet-loss windows.
    private var gameplayNetworkCallback: ConnectivityManager.NetworkCallback? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        activeServiceRef = WeakReference(this)
        AppState.appendLog("[T-STATE   ] VPN service onStartCommand action=${intent?.action ?: "<none>"} flags=$flags startId=$startId running=${AppState.isRunning.get()}")
        if (intent?.action == ACTION_STOP) {
            // Log whether this STOP came from the notification Stop button
            // (PendingIntent) or from stopVpnService() in MainActivity.
            // The notification Stop button's PendingIntent has no extras, so
            // we can't distinguish by extras — but stopVpnService() now logs
            // its own call stack before sending the intent. If we see that log
            // entry immediately before this one, the source was the UI. If not,
            // the source was the notification Stop button.
            AppState.appendLog("[VPN-STOP  ] STOP_VPN intent received — source: ${if (intent.getStringExtra("source") != null) intent.getStringExtra("source") else "notification Stop button or external"}")
            startupCancelled.set(true)
            stopVpn()
            return START_NOT_STICKY
        }

        // ── Auto-restart recovery ──────────────────────────────────────
        // On Android 15 (and to a lesser extent 13/14) the OS can kill the
        // app process for memory pressure or app-standby enforcement. The
        // VPN service dies with it. START_STICKY causes Android to restart
        // the service, but AppState (in-memory) is lost — peerIp, localIp,
        // peerPort, connectionMode all reset to defaults. Without restoring
        // them, startVpn() would fail with "Peer LAN IP is not set" and the
        // tunnel would never come back. The user sees "VPN was killed" and
        // has to manually reconnect.
        //
        // Fix: if onStartCommand is called with a null intent (which is what
        // happens on a START_STICKY restart — the system has no original
        // intent to redeliver), AND AppState.isRunning was true before the
        // kill (which we persist to SharedPreferences), restore the session
        // state from SharedPreferences so startVpn() can re-establish the
        // tunnel automatically.
        if (intent == null) {
            AppState.appendLog("[T-STATE   ] VPN service restarted by OS (null intent) — attempting session recovery")
            restoreSessionStateIfAvailable()
        }

        createNotificationChannel()
        // Foreground type MUST match manifest declaration: connectedDevice.
        // We tried specialUse for Android 15 hardening but it broke Android 13
        // (Hot 30i) because specialUse was only added in API 34. The VPN
        // service is started by the system VpnService infrastructure (not by
        // the app), so ForegroundServiceStartNotAllowedException doesn't
        // apply here. connectedDevice works on Android 13+ and accurately
        // describes the peer-to-peer tunnel use case.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                NOTIFICATION_ID,
                buildNotification(),
                android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE
            )
        } else {
            startForeground(NOTIFICATION_ID, buildNotification())
        }
        // Keep the foreground notification useful without waking the app every few seconds
        // during gameplay. Counters do not need real-time UI refresh; 10 s is responsive enough
        // while reducing periodic binder/CPU work on the latency-sensitive path.
        if (notificationRefreshExecutor == null || notificationRefreshExecutor!!.isShutdown) {
            notificationRefreshExecutor = Executors.newSingleThreadScheduledExecutor { r ->
                Thread(r, "pl-notif-refresh").apply { isDaemon = true }
            }.also { exec ->
                exec.scheduleWithFixedDelay({
                    try {
                        getSystemService(NotificationManager::class.java)
                            ?.notify(NOTIFICATION_ID, buildNotification())
                    } catch (_: Exception) { }
                }, 10L, 10L, TimeUnit.SECONDS)
            }
        }
        if (!AppState.isRunning.get() && startupInFlight.compareAndSet(false, true)) {
            startupCancelled.set(false)
            startupExecutor.execute {
                try {
                    startVpn()
                } finally {
                    startupInFlight.set(false)
                }
            }
        }
        // START_STICKY asks Android to restart the service with a null intent
        // if the process is killed by the OS (low-memory / app-standby). When
        // Android restarts it, onStartCommand sees a null intent — our
        // existing guard "if (!AppState.isRunning.get()) startVpn()" then
        // re-establishes the tunnel automatically.
        return START_STICKY
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                NOTIFICATION_CHANNEL_ID,
                "PeerLink VPN",
                NotificationManager.IMPORTANCE_LOW,
            ).apply {
                description = "PeerLink tunnel status"
                setShowBadge(false)
            }
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val stopPi = PendingIntent.getService(
            this,
            0,
            Intent(this, PeerLinkVpnService::class.java).apply { action = ACTION_STOP },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val mainPi = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java).apply { addFlags(Intent.FLAG_ACTIVITY_NEW_TASK) },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val transportLabel = "Wi-Fi"

        val tunPkts = AppState.tunneled.get()
        val pktsStr = when {
            tunPkts >= 1_000_000L -> "${tunPkts / 1_000_000}M pkts"
            tunPkts >= 1_000L     -> "${tunPkts / 1_000}K pkts"
            else                   -> "$tunPkts pkts"
        }

        return (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Notification.Builder(this, NOTIFICATION_CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        })
            .setContentTitle(if (AppState.isRunning.get()) "PeerLink Active" else "PeerLink Starting")
            .setContentText("▲▼ $pktsStr · $transportLabel")
            .setSmallIcon(android.R.drawable.ic_menu_share)
            .setContentIntent(mainPi)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Stop", stopPi)
            .setOngoing(true)
            .build()
    }

    private fun startVpn() {
        AppState.vpnSessionState.set(VpnSessionState.CONNECTING)
        stopVpnGuard.set(false)
        stopCleanupStarted.set(false)
        try {
            AppState.initFileLog(this)
            AppState.appendLog("[VPN-START ] PeerLink VPN starting")

            val transportMode = canonicalTransportMode()
            val peerLanIp = AppState.peerIp.get()?.hostAddress
            if (peerLanIp.isNullOrBlank()) {
                throw IllegalStateException("Peer LAN IP is not set (mode=$transportMode)")
            }

            // Resolve the LAN path only after the peer is known. Hotspot owners
            // are often multi-homed; selecting an arbitrary private 10.x address
            // here can accidentally choose cellular instead of the SoftAP.
            val lanPath = LanPathResolver.resolveForPeer(this, peerLanIp)
                ?: throw IllegalStateException("No local LAN interface can reach peer $peerLanIp")
            AppState.localIp.set(lanPath.localIp)
            AppState.localLanInterfaceName.set(lanPath.interfaceName)
            AppState.localLanInterfaceIndex.set(lanPath.interfaceIndex)
            AppState.localLanPrefixLength.set(lanPath.prefixLength)
            AppState.localLanNetwork.set(lanPath.androidNetwork)
            AppState.appendLog(
                "[VPN-UNDER ] Locked LAN path ${lanPath.interfaceName}#${lanPath.interfaceIndex} " +
                    "${lanPath.localIp}/${lanPath.prefixLength} -> $peerLanIp " +
                    "(${if (lanPath.androidNetwork != null) "Android Wi-Fi Network" else "kernel/SoftAP"})"
            )

            if (!AppState.calculateFabricatedIps()) {
                throw IllegalStateException("Fabricated IPs are not ready")
            }
            if (startupCancelled.get()) return

            val builder = Builder()
                .setSession("LanLink")
                .setMtu(1400)
                .addAddress("10.0.0.2", 32)
                .addRoute("0.0.0.0", 0)
                .addAddress("fd00::2", 128)
                .addRoute("::", 0)
                .addDnsServer("8.8.8.8")
                .addDnsServer("8.8.4.4")
                .setBlocking(true)
                .allowBypass()

            try {
                builder.addAllowedApplication(EFOOTBALL_PACKAGE)
                AppState.appendLog("[VPN-START ] Per-app VPN: $EFOOTBALL_PACKAGE only")
            } catch (e: Exception) {
                // Fail closed. Falling back to an all-app VPN makes a simple game
                // connection error turn into a whole-device networking problem.
                throw IllegalStateException("eFootball is not installed or cannot be scoped to PeerLink", e)
            }

            vpnInterface = builder.establish()
            if (vpnInterface == null) {
                AppState.appendLog("[T-STATE   ] builder.establish() returned null prepared=${VpnService.prepare(this) == null}")
                AppState.appendLog("[VPN-START ] ERROR: VPN interface establish failed")
                stopVpn()
                return
            }

            AppState.appendLog("[VPN-START ] Interface established (IPv4 + IPv6)")
            updateUnderlyingNetworks()

            try {
            } catch (_: Exception) {
            }

            val backendConfig = NativeBackendConfig(
                peerLanIp = peerLanIp,
                peerPort = AppState.peerPort.get(),
                myFabricatedIp = AppState.myFabricatedIp,
                peerFabricatedIp = AppState.peerFabricatedIp,
                localLanIp = lanPath.localIp,
                localInterfaceIndex = lanPath.interfaceIndex,
            )

            // After detachFd(), native code owns the raw TUN descriptor. The
            // detached ParcelFileDescriptor no longer owns that FD; native must
            // close the raw descriptor when the session ends.
            val detachedTunFd = vpnInterface!!.detachFd()
            vpnInterface = null
            lastNativeUdpTraceDump = ""
            AppState.appendLog("[VPN-START ] TUN detached to native backend")

            nativeBackend = NativePeerLinkBackend(
                config = backendConfig,
                callbacks = object : NativePeerLinkBackend.Callbacks {
                    override fun preparePeerSocket(fdForBinding: Int): Boolean {
                        return prepareNativePeerSocket(fdForBinding)
                    }

                    override fun fabricateStunResponse(packet: ByteArray, length: Int): ByteArray? {
                        return NativePeerLinkBackend.fabricateStunWithExistingLogic(
                            config = backendConfig,
                            packet = packet,
                            length = length,
                        )
                    }

                    override fun onNativeLog(level: Int, message: String, fileOnly: Boolean) {
                        val elevated = !fileOnly || level >= NativePeerLinkBackend.LOG_LEVEL_WARN
                        if (elevated) {
                            AppState.appendLog(message)
                        } else {
                            AppState.appendFileOnly(message)
                        }
                    }

                    override fun onStats(stats: NativeBackendStats) {
                        AppState.tunneled.set(stats.totalTunneledPackets)
                    }
                },
            )

            val bridgeFd = nativeBackend!!.start(detachedTunFd)
            val bridgePfd = ParcelFileDescriptor.adoptFd(bridgeFd)

            // Discovery/pairing proves only that the phones saw each other.
            // This probe proves the actual native UDP dataplane works both ways.
            // It is intentionally done before declaring the VPN session active.
            AppState.vpnSessionState.set(VpnSessionState.VERIFYING)
            AppState.appendLog("[VPN-UNDER ] Verifying bidirectional peer tunnel...")
            val peerReachable = nativeBackend!!.verifyPeerPath(60_000)
            if (!peerReachable || startupCancelled.get()) {
                runCatching { bridgePfd.close() }
                throw IllegalStateException(
                    if (startupCancelled.get()) "VPN startup cancelled"
                    else "PeerLink LAN tunnel probe failed — peer data path is not bidirectionally reachable"
                )
            }
            AppState.appendLog("[VPN-UNDER ] Bidirectional peer tunnel verified")
            AppState.isRunning.set(true)
            AppState.vpnSessionState.set(VpnSessionState.CONNECTED)

            passthroughBridgeEngine = PassthroughBridgeEngine(
                context = this,
                vpnInterface = bridgePfd,
                protectDatagramSocket = { socket -> protect(socket) },
                protectTcpSocket = { socket -> protect(socket) },
            )
            passthroughBridgeEngine?.start()
            gameplayRefreshAllowedAtMs = System.currentTimeMillis() + 5000L
            startGameplayPathMonitor()
            refreshGameplayPath("startup", force = true)

            // Acquire PARTIAL_WAKE_LOCK to prevent Android from suspending the
            // CPU/network stack mid-session. This is the correct API for a
            // background VPN service — LOW_LATENCY requires foreground+screen-on,
            // HIGH_PERF is deprecated at API 34. PARTIAL_WAKE_LOCK keeps the
            // tunnel threads alive through screen-off and power-save events.
            try {
                val pm = getSystemService(POWER_SERVICE) as android.os.PowerManager
                tunnelWakeLock = pm.newWakeLock(
                    android.os.PowerManager.PARTIAL_WAKE_LOCK,
                    "LanLink:TunnelSession"
                ).also { it.acquire() }
                AppState.appendLog("[VPN-START ] PARTIAL_WAKE_LOCK acquired")
            } catch (e: Exception) {
                AppState.appendLog("[VPN-START ] Wake lock acquire failed: ${e.message}")
            }

            // Request Android's supported low-latency Wi-Fi mode for the session.
            // This is best-effort: Android/Wi-Fi firmware decide whether it can become
            // active, and normal app locks may stop being effective when PeerLink's UID
            // is no longer foreground (for example while eFootball owns the screen).
            // Never claim this lock guarantees WMM/driver latency by itself.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                try {
                    val wm = applicationContext.getSystemService(WIFI_SERVICE) as android.net.wifi.WifiManager
                    wifiLowLatencyLock = wm.createWifiLock(
                        android.net.wifi.WifiManager.WIFI_MODE_FULL_LOW_LATENCY,
                        "LanLink:LowLatency"
                    ).apply {
                        setReferenceCounted(false)
                        acquire()
                    }
                    AppState.appendLog("[VPN-START ] WIFI_MODE_FULL_LOW_LATENCY lock acquired")
                } catch (e: Exception) {
                    AppState.appendLog("[VPN-START ] Wi-Fi low-latency lock failed: ${e.message}")
                }
            }

            // Best-effort hot-loop promotion. Normal Wireless-Debugging Prime runs
            // as shell (uid 2000), which cannot assume SCHED_FIFO privileges; the
            // manager only issues chrt when it has positively detected uid 0.
            try {
                GodModeManager.promoteHotThreads { nativeBackend?.hotThreadTids() ?: IntArray(0) }
            } catch (_: Exception) {
            }

            AppState.appendLog("[VPN-START ] Native datapath active — passthrough bridge ready")
            AppState.appendLog("[VPN-TRACE ] UDP trace armed (save-only, stages=5, udp-only)")
            AppState.appendLog("[VPN-START ] Tunnel active — waiting for game traffic")

            // Persist session state so START_STICKY restart can re-establish
            // the tunnel automatically if the OS kills the process (Android 15
            // app-standby, low-memory, etc.). Without this, the restart would
            // find AppState empty and fail with "Peer LAN IP is not set".
            saveSessionState()
        } catch (e: Exception) {
            AppState.vpnSessionState.set(VpnSessionState.ERROR)
            AppState.appendLog("[VPN-START ] Start error: ${e.message}")
            stopVpn()
        }
    }

    private fun prepareAuxDatagramSocketInternal(socket: DatagramSocket, preferGameplayNetwork: Boolean): Boolean {
        val protectedOk = runCatching { protect(socket) }.getOrElse {
            AppState.appendLog("[VPN-UNDER ] Aux socket protect error: ${it.message}")
            false
        }
        if (!protectedOk) return false

        val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        val target = if (preferGameplayNetwork) {
            resolveExactGameplayNetwork(cm, canonicalTransportMode())
        } else {
            resolveExactGameplayNetwork(cm, canonicalTransportMode())
        }
        if (target == null) return true

        return runCatching {
            target.bindSocket(socket)
            true
        }.getOrElse {
            AppState.appendLog("[VPN-UNDER ] Aux socket bind error: ${it.message}")
            false
        }
    }

    private fun prepareNativePeerSocket(fdForBinding: Int): Boolean {
        val transportMode = canonicalTransportMode()
        var protectedOk = false
        var bindOk = false
        try {
            protectedOk = protect(fdForBinding)
            AppState.appendLog("[VPN-UNDER ] Native peer socket protect=${if (protectedOk) "ok" else "failed"}")
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] Native peer socket protect error: ${e.message}")
        }

        try {
            updateUnderlyingNetworks()
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] updateUnderlyingNetworks error: ${e.message}")
        }

        try {
            ParcelFileDescriptor.adoptFd(fdForBinding).use { pfd ->
                bindOk = bindSocketFdToPreferredNetwork(pfd.fileDescriptor)
                AppState.appendLog("[VPN-UNDER ] Native peer socket bind=${if (bindOk) "ok" else "failed"}")
            }
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] Native peer socket bind error: ${e.message}")
        }

        return protectedOk && bindOk
    }

    private fun isUsableUnderlay(cm: ConnectivityManager, network: Network): Boolean {
        val caps = cm.getNetworkCapabilities(network) ?: return false
        if (caps.hasTransport(NetworkCapabilities.TRANSPORT_VPN)) return false
        val iface = try { cm.getLinkProperties(network)?.interfaceName } catch (_: Exception) { null }
        if (!iface.isNullOrBlank()) {
            val lowered = iface.lowercase()
            if (lowered.startsWith("tun") || lowered.contains("vpn")) return false
        }
        return true
    }

    private fun canonicalTransportMode(): String {
        val active = AppState.activeTransportMode.get()
        if (active != "none") return active
        return when (AppState.connectionMode) {
            "hotspot" -> "wifi_udp"
            else -> "none"
        }
    }

    private fun resolveExactGameplayNetwork(cm: ConnectivityManager, transportMode: String): Network? {
        if (transportMode != "wifi_udp") return null

        // Pairing/startup already resolved the exact LAN path. Prefer that
        // Network object for ordinary Wi-Fi station/client mode.
        AppState.localLanNetwork.get()?.let { locked ->
            if (isUsableUnderlay(cm, locked)) {
                val caps = cm.getNetworkCapabilities(locked)
                if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true) return locked
            }
        }

        val localIp = AppState.localIp.get()
        if (localIp.isNullOrBlank() || localIp == "127.0.0.1") return null
        val matches = cm.allNetworks.filter { network ->
            if (!isUsableUnderlay(cm, network)) return@filter false
            val caps = cm.getNetworkCapabilities(network) ?: return@filter false
            if (!caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) return@filter false
            val lp = cm.getLinkProperties(network) ?: return@filter false
            lp.linkAddresses.any { it.address is Inet4Address && it.address.hostAddress == localIp }
        }
        if (matches.size == 1) return matches.first()
        val active = cm.activeNetwork
        return active?.takeIf { matches.contains(it) }
    }

    private fun bindSocketFdToPreferredNetwork(fileDescriptor: FileDescriptor): Boolean {
        val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
        val transportMode = canonicalTransportMode()
        val exactNetwork = resolveExactGameplayNetwork(cm, transportMode)
        if (exactNetwork == null) {
            // Android commonly does not publish the hotspot owner's SoftAP as a
            // ConnectivityManager Network. Native has already source-bound and
            // interface-pinned the peer socket using the locked LanPath, so this
            // is a valid path rather than a bind failure.
            val ifIndex = AppState.localLanInterfaceIndex.get()
            val iface = AppState.localLanInterfaceName.get()
            val localIp = AppState.localIp.get()
            if (transportMode == "wifi_udp" && ifIndex > 0 && !localIp.isNullOrBlank()) {
                AppState.appendLog(
                    "[VPN-UNDER ] No Android Network for $iface#$ifIndex/$localIp — using native kernel/SoftAP pin"
                )
                return true
            }
            AppState.appendLog("[VPN-UNDER ] No exact gameplay network or locked kernel LAN path available")
            return false
        }
        return try {
            exactNetwork.bindSocket(fileDescriptor)
            AppState.appendLog("[VPN-UNDER ] Native peer socket bound to exact ${describeNetwork(cm, exactNetwork)}")
            true
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] Exact gameplay bind failed on ${describeNetwork(cm, exactNetwork)}: ${e.message}")
            false
        }
    }


    private fun gameplayNetworkIdentity(cm: ConnectivityManager, network: Network?): String? {
        if (network == null) return null
        val lp = runCatching { cm.getLinkProperties(network) }.getOrNull()
        val iface = lp?.interfaceName ?: "?"
        val addrs = lp?.linkAddresses?.joinToString(",") { it.address.hostAddress ?: "?" } ?: ""
        return "${network}|$iface|$addrs"
    }

    private fun startGameplayPathMonitor() {
        stopGameplayPathMonitor()
        gameplayMonitorExecutor = Executors.newSingleThreadScheduledExecutor { runnable ->
            Thread(runnable, "PeerLink-GameplayPath").apply { isDaemon = true }
        }.also { executor ->
            executor.scheduleAtFixedRate(
                {
                    runCatching {
                        if (AppState.isRunning.get() && System.currentTimeMillis() >= gameplayRefreshAllowedAtMs) {
                            refreshGameplayPath("monitor", force = false)
                        }
                    }
                },
                10L,
                10L,
                TimeUnit.SECONDS,
            )
        }
        // NetworkCallback is the primary path-change signal. The 10-second
        // timer above is only a slow safety net for OEMs that miss callbacks;
        // it must not become periodic work on the latency-sensitive path.
        registerGameplayNetworkCallback()
    }

    private fun stopGameplayPathMonitor() {
        gameplayMonitorExecutor?.shutdownNow()
        gameplayMonitorExecutor = null
        lastGameplayNetworkIdentity = null
        unregisterGameplayNetworkCallback()
    }

    /**
     * Register a NetworkCallback for any Wi-Fi transport network. We deliberately
     * only react to onLost for the SPECIFIC network we're actually bound to —
     * reacting to every Wi-Fi network's comings and goings (or to capability
     * changes, which fire constantly due to RSSI/signal-strength fluctuations)
     * caused a rebind storm that was tearing down the peer socket every few
     * seconds. That was the root cause of the worsening disconnects after the
     * previous patch.
     *
     * Strategy:
     *  - onAvailable: do nothing. The slow safety monitor will verify the path;
     *    force-rebinding on every onAvailable caused avoidable packet-loss windows.
     *  - onLost: ONLY act if the lost network is the one we're currently bound
     *    to. Otherwise it's some other Wi-Fi in range going away — irrelevant.
     *  - onCapabilitiesChanged: do nothing. The slow safety monitor handles
     *    gradual drift. Reacting here causes a rebind storm.
     */
    private fun registerGameplayNetworkCallback() {
        if (gameplayNetworkCallback != null) return
        try {
            val cm = getSystemService(CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return
            val request = NetworkRequest.Builder()
                .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                .build()
            val cb = object : ConnectivityManager.NetworkCallback() {
                override fun onAvailable(network: Network) {
                    // Deliberately not acting here — see method comment.
                }
                override fun onLost(network: Network) {
                    if (!AppState.isRunning.get()) return
                    // Only react if the lost network is the one we're actually
                    // using for the gameplay tunnel. If it's some other Wi-Fi
                    // in range going away, ignore it — clearing the underlay
                    // for an unrelated network loss was causing real disconnects.
                    val cmNow = getSystemService(CONNECTIVITY_SERVICE) as? ConnectivityManager
                    val transportMode = canonicalTransportMode()
                    val currentGameplayNetwork = cmNow?.let { resolveExactGameplayNetwork(it, transportMode) }
                    // If our current gameplay network can't be resolved anymore,
                    // OR the lost network IS the current one, react.
                    // Note: by the time onLost fires, the network is already
                    // gone from cm.allNetworks, so resolveExactGameplayNetwork
                    // will return null if it WAS our network. We can't directly
                    // compare Network objects here because the lost one is no
                    // longer queryable. Instead, just check if we still have a
                    // valid gameplay network — if not, react.
                    if (currentGameplayNetwork == null) {
                        val kernelPinned = transportMode == "wifi_udp" &&
                            AppState.localLanNetwork.get() == null &&
                            AppState.localLanInterfaceIndex.get() > 0
                        if (kernelPinned) {
                            AppState.appendFileOnly("[VPN-UNDER ] Wi-Fi Network object lost/absent, but hotspot-owner kernel path remains pinned — ignoring")
                            return
                        }
                        // Cooldown — don't rebind more than once every 5 seconds.
                        // Repeated onLost events (e.g. during AP roaming) shouldn't
                        // each trigger a tear-down of the peer socket.
                        val now = System.currentTimeMillis()
                        synchronized(gameplayRefreshLock) {
                            if (now - lastRebindMs < REBIND_COOLDOWN_MS) {
                                AppState.appendFileOnly("[VPN-UNDER ] Wi-Fi lost but rebind on cooldown (${now - lastRebindMs}ms < ${REBIND_COOLDOWN_MS}ms) — skipping")
                                return
                            }
                            lastRebindMs = now
                        }
                        AppState.appendLog("[VPN-UNDER ] Gameplay Wi-Fi network lost — resetting underlay")
                        lastGameplayNetworkIdentity = null
                        runCatching { setUnderlyingNetworks(null) }
                        refreshGameplayPath("wifi-lost", force = true)
                    } else {
                        // Some other Wi-Fi network went away — we don't care.
                        AppState.appendFileOnly("[VPN-UNDER ] Unrelated Wi-Fi network lost — ignoring (current gameplay network still up)")
                    }
                }
                override fun onCapabilitiesChanged(network: Network, caps: NetworkCapabilities) {
                    // Deliberately not acting here — see method comment.
                    // Capabilities change every second due to signal strength
                    // fluctuations; reacting here caused a rebind storm.
                }
            }
            cm.registerNetworkCallback(request, cb)
            gameplayNetworkCallback = cb
            AppState.appendLog("[VPN-UNDER ] Wi-Fi NetworkCallback registered (loss-only, gameplay-network-gated)")
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] NetworkCallback register failed: ${e.message}")
        }
    }

    private fun unregisterGameplayNetworkCallback() {
        val cb = gameplayNetworkCallback ?: return
        try {
            val cm = getSystemService(CONNECTIVITY_SERVICE) as? ConnectivityManager
            cm?.unregisterNetworkCallback(cb)
        } catch (_: Exception) { }
        gameplayNetworkCallback = null
    }

    private fun refreshGameplayPath(reason: String, force: Boolean): Boolean {
        synchronized(gameplayRefreshLock) {
            val backend = nativeBackend ?: return false
            val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
            val transportMode = canonicalTransportMode()
            val network = resolveExactGameplayNetwork(cm, transportMode)
            if (network == null) {
                val kernelPinned = transportMode == "wifi_udp" &&
                    AppState.localLanInterfaceIndex.get() > 0 &&
                    !AppState.localIp.get().isNullOrBlank()
                if (kernelPinned) {
                    // Hotspot-owner/SoftAP interfaces often have no ConnectivityManager
                    // Network object. Native is already source-bound + interface-pinned;
                    // do not rewrite VPN underlying networks on every health poll.
                    if (reason == "startup") updateUnderlyingNetworks()
                    AppState.appendFileOnly(
                        "[VPN-UNDER ] Gameplay path healthy ($reason): native kernel/SoftAP pin " +
                            "${AppState.localLanInterfaceName.get()}#${AppState.localLanInterfaceIndex.get()} " +
                            "${AppState.localIp.get()}"
                    )
                    return true
                }
                updateUnderlyingNetworks()
                AppState.appendFileOnly("[VPN-UNDER ] Gameplay path refresh deferred ($reason): no exact network for mode=$transportMode")
                return false
            }
            val identity = gameplayNetworkIdentity(cm, network)
            val changed = identity != lastGameplayNetworkIdentity
            if (!force && !changed) return true
            // Enforce the rebind cooldown even when force=true. The only caller
            // that bypasses this is startVpn() (which sets gameplayRefreshAllowedAtMs
            // to 5s in the future, gating all refreshes until then). All other
            // callers — including the NetworkCallback's onLost — respect the
            // cooldown so we don't tear down the peer socket more than once
            // every REBIND_COOLDOWN_MS.
            val now = System.currentTimeMillis()
            if (now - lastRebindMs < REBIND_COOLDOWN_MS && reason != "startup") {
                AppState.appendFileOnly("[VPN-UNDER ] Rebind skipped ($reason): cooldown active (${now - lastRebindMs}ms < ${REBIND_COOLDOWN_MS}ms)")
                return false
            }
            updateUnderlyingNetworks()
            val rebound = runCatching { backend.rebindPeerSocket() }.getOrElse {
                AppState.appendLog("[VPN-UNDER ] Gameplay path rebind error ($reason): ${it.message}")
                false
            }
            if (rebound) {
                lastGameplayNetworkIdentity = identity
                lastRebindMs = System.currentTimeMillis()
                AppState.appendLog("[VPN-UNDER ] Gameplay path rebound ($reason): ${describeNetwork(cm, network)}")
            } else {
                AppState.appendLog("[VPN-UNDER ] Gameplay path rebind failed ($reason) on ${describeNetwork(cm, network)}")
            }
            return rebound
        }
    }

    private fun stopVpn() {
        if (!stopVpnGuard.compareAndSet(false, true)) return
        AppState.vpnSessionState.set(VpnSessionState.DISCONNECTING)
        AppState.isRunning.set(false)
        // Clear the saved session state — the user deliberately stopped the
        // session, so we don't want a START_STICKY restart to bring it back.
        clearSessionState()
        notificationRefreshExecutor?.shutdownNow()
        notificationRefreshExecutor = null
        stopGameplayPathMonitor()

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) stopForeground(STOP_FOREGROUND_REMOVE)
            else @Suppress("DEPRECATION") stopForeground(true)
        } catch (_: Exception) {
        }

        if (!stopCleanupStarted.compareAndSet(false, true)) return

        val backend = nativeBackend
        nativeBackend = null
        // Close the native-owned TUN/UDP descriptors now. This makes the VPN
        // interface disappear promptly instead of waiting for the asynchronous
        // thread-join cleanup below. native stop() remains idempotent.
        try {
            backend?.requestImmediateStop()
            AppState.appendLog("[VPN-STOP  ] Native TUN close requested immediately")
        } catch (e: Exception) {
            AppState.appendLog("[VPN-STOP  ] Immediate native stop failed (cleanup will retry): ${e.message}")
        }
        val bridge = passthroughBridgeEngine
        passthroughBridgeEngine = null
        val iface = vpnInterface
        vpnInterface = null
        // If startup was cancelled before detachFd(), Java still owns this TUN.
        // Close it synchronously for the same immediate-disconnect guarantee.
        try { iface?.close() } catch (e: Exception) {
            AppState.appendLog("[VPN-STOP  ] Immediate interface close failed: ${e.message}")
        }

        Thread({
            lastNativeUdpTraceDump = try {
                backend?.dumpUdpTrace().orEmpty()
            } catch (_: Exception) {
                lastNativeUdpTraceDump
            }

            try {
                GodModeManager.onVpnStopped()
            } catch (e: Exception) {
                AppState.appendLog("[VPN-STOP  ] GodMode stop error (non-fatal): ${e.message}")
            }

            try {
                bridge?.stop()
            } catch (e: Exception) {
                AppState.appendLog("[VPN-STOP  ] Bridge engine stop error (non-fatal): ${e.message}")
            }

            try {
                backend?.stop()
            } catch (e: Exception) {
                AppState.appendLog("[VPN-STOP  ] Native backend stop error (non-fatal): ${e.message}")
            }

            // Release wake lock acquired at tunnel start.
            try {
                val wl = tunnelWakeLock
                tunnelWakeLock = null
                if (wl?.isHeld == true) {
                    wl.release()
                    AppState.appendLog("[VPN-STOP  ] PARTIAL_WAKE_LOCK released")
                }
            } catch (e: Exception) {
                AppState.appendLog("[VPN-STOP  ] Wake lock release error (non-fatal): ${e.message}")
            }

            // Release the Wi-Fi low-latency lock acquired at tunnel start.
            try {
                val wfl = wifiLowLatencyLock
                wifiLowLatencyLock = null
                if (wfl?.isHeld == true) {
                    wfl.release()
                    AppState.appendLog("[VPN-STOP  ] WIFI_MODE_FULL_LOW_LATENCY lock released")
                }
            } catch (e: Exception) {
                AppState.appendLog("[VPN-STOP  ] Wi-Fi low-latency lock release error (non-fatal): ${e.message}")
            }

            AppState.vpnSessionState.set(VpnSessionState.DISCONNECTED)
            AppState.appendLog("[T-STATE   ] stopVpn completed guard=${stopVpnGuard.get()}")
            AppState.appendLog("[VPN-STOP  ] VPN stopped cleanly")
            AppState.closeFileLog()

            try {
                stopSelf()
            } catch (_: Exception) {
            }
        }, "PeerLink-VPN-Stop").apply {
            isDaemon = true
            start()
        }
    }

    private fun updateUnderlyingNetworks() {
        try {
            val cm = getSystemService(CONNECTIVITY_SERVICE) as ConnectivityManager
            val transportMode = canonicalTransportMode()

            val ordered = LinkedHashSet<Network>()
            val exactGameplay = resolveExactGameplayNetwork(cm, transportMode)

            exactGameplay?.let { ordered.add(it) }

            val kernelPinnedHotspotPath = transportMode == "wifi_udp" &&
                exactGameplay == null &&
                AppState.localLanNetwork.get() == null &&
                AppState.localLanInterfaceIndex.get() > 0
            if (kernelPinnedHotspotPath) {
                // SoftAP owner: the peer UDP socket is independently pinned in
                // native. Keep the VPN's ordinary Internet passthrough on the
                // system default so eFootball auth/matchmaking can still use
                // cellular/available Internet.
                runCatching { setUnderlyingNetworks(null) }
                AppState.appendFileOnly("[VPN-UNDER ] Hotspot-owner kernel path locked; VPN Internet underlay left on system default")
                return
            }

            if (transportMode != "none" && ordered.isEmpty()) {
                // The exact gameplay network (e.g. the specific Wi-Fi we were
                // paired on) is no longer available. Previously we kept the OLD
                // underlying-networks list, which meant the VPN kept pointing
                // at a dead Network object and packets went nowhere — this is
                // what caused eFootball to detect a network drop and kick both
                // players mid-match. Fall back to the system default instead:
                // pass null to setUnderlyingNetworks(), which makes the VPN
                // route through whatever the OS considers the current default
                // network (often the same Wi-Fi once it re-appears, or
                // cellular). Even if the new underlay isn't the right one for
                // the session, at least the VPN interface stays up and the
                // session can potentially recover when Wi-Fi returns.
                AppState.appendLog("[VPN-UNDER ] mode=$transportMode exact gameplay network gone — falling back to system default underlay")
                runCatching { setUnderlyingNetworks(null) }
                return
            }

            setUnderlyingNetworks(ordered.takeIf { it.isNotEmpty() }?.toTypedArray())
            AppState.appendLog("[VPN-UNDER ] mode=$transportMode ${if (ordered.isEmpty()) "Using system default underlay" else "Underlying networks: ${ordered.joinToString { describeNetwork(cm, it) }}"}")
        } catch (e: Exception) {
            AppState.appendLog("[VPN-UNDER ] Failed to set underlying networks: ${e.message}")
        }
    }

    /**
     * Describe a network for logging (show transport type + interface name).
     */
    private fun describeNetwork(cm: ConnectivityManager, network: Network): String {
        val caps = cm.getNetworkCapabilities(network)
        val lp = cm.getLinkProperties(network)
        val transport = when {
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true -> "WiFi"
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true -> "Cell"
            caps?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true -> "VPN"
            else -> "?"
        }
        return "$transport:${lp?.interfaceName ?: network}"
    }

    /**
     * Persist the current session state to SharedPreferences so that if the
     * OS kills the process (Android 15 app-standby, low-memory), the START_STICKY
     * restart can re-establish the tunnel automatically without user intervention.
     *
     * Called from startVpn() after the tunnel is successfully established.
     */
    private fun saveSessionState() {
        try {
            val peerIpStr = AppState.peerIp.get()?.hostAddress ?: return
            val localIpStr = AppState.localIp.get() ?: return
            val mode = AppState.connectionMode
            if (mode.isBlank()) return
            val transport = AppState.activeTransportMode.get()
            val port = AppState.peerPort.get()

            val prefs = getSharedPreferences(SESSION_STATE_PREFS, MODE_PRIVATE)
            prefs.edit()
                .putString(KEY_PEER_IP, peerIpStr)
                .putString(KEY_LOCAL_IP, localIpStr)
                .putString(KEY_CONNECTION_MODE, mode)
                .putString(KEY_TRANSPORT_MODE, transport)
                .putInt(KEY_PEER_PORT, port)
                .putBoolean(KEY_WAS_RUNNING, true)
                .putLong(KEY_SAVED_AT_MS, System.currentTimeMillis())
                .commit()  // synchronous — must complete before any potential kill
            AppState.appendLog("[T-STATE   ] Session state persisted for auto-restart (peer=$peerIpStr local=$localIpStr mode=$mode)")
        } catch (e: Exception) {
            AppState.appendLog("[T-STATE   ] Failed to persist session state: ${e.message}")
        }
    }

    /**
     * Restore session state from SharedPreferences if available. Called from
     * onStartCommand when intent is null (START_STICKY restart after kill).
     * Restores peerIp, localIp, peerPort, connectionMode, activeTransportMode
     * into AppState so that startVpn() can re-establish the tunnel.
     */
    private fun restoreSessionStateIfAvailable() {
        try {
            val prefs = getSharedPreferences(SESSION_STATE_PREFS, MODE_PRIVATE)
            if (!prefs.getBoolean(KEY_WAS_RUNNING, false)) {
                AppState.appendLog("[T-STATE   ] No saved session state — not auto-restarting")
                return
            }
            val savedAt = prefs.getLong(KEY_SAVED_AT_MS, 0L)
            val ageMs = System.currentTimeMillis() - savedAt
            // If the saved state is older than 30 minutes, the peer has almost
            // certainly gone away by now — don't try to auto-restart into a
            // stale session.
            if (ageMs > 30 * 60 * 1000L) {
                AppState.appendLog("[T-STATE   ] Saved session state is ${ageMs / 1000}s old — too stale, discarding")
                clearSessionState()
                return
            }
            val peerIpStr = prefs.getString(KEY_PEER_IP, null) ?: return
            val localIpStr = prefs.getString(KEY_LOCAL_IP, null) ?: return
            val mode = prefs.getString(KEY_CONNECTION_MODE, null) ?: return
            val transport = prefs.getString(KEY_TRANSPORT_MODE, "none") ?: "none"
            val port = prefs.getInt(KEY_PEER_PORT, 17024)

            // Restore into AppState
            AppState.peerIp.set(java.net.InetAddress.getByName(peerIpStr))
            AppState.localIp.set(localIpStr)
            AppState.connectionMode = mode
            AppState.activeTransportMode.set(transport)
            AppState.peerPort.set(port)
            AppState.isPaired.set(true)
            // isRunning is intentionally NOT set here — startVpn() will set it
            // if the re-establish succeeds.
            AppState.appendLog("[T-STATE   ] Session state restored — peer=$peerIpStr local=$localIpStr mode=$mode transport=$transport")
        } catch (e: Exception) {
            AppState.appendLog("[T-STATE   ] Failed to restore session state: ${e.message}")
        }
    }

    /**
     * Clear the saved session state. Called from stopVpn() when the user
     * deliberately ends the session — we don't want auto-restart to bring
     * it back.
     */
    private fun clearSessionState() {
        try {
            getSharedPreferences(SESSION_STATE_PREFS, MODE_PRIVATE)
                .edit()
                .clear()
                .commit()
        } catch (_: Exception) {}
    }

    override fun onRevoke() {
        // onRevoke fires when the user toggles "Always-on VPN" off, revokes
        // our VPN permission, or starts a different VPN. We currently treat
        // this as a stop — but DON'T call stopSelf, because Android may
        // re-grant us the VPN moments later (e.g. user toggling back).
        // START_STICKY means we'll be restarted; the next onStartCommand
        // will re-establish the tunnel if AppState.isRunning is still true.
        AppState.appendLog("[T-STATE   ] VPN service onRevoke — tearing down tunnel but staying alive")
        stopVpn()
        super.onRevoke()
    }

    override fun onDestroy() {
        AppState.appendLog("[T-STATE   ] VPN service onDestroy")
        // Don't fully stop the VPN if the system is just destroying us to
        // recreate (low-memory / config change). The START_STICKY return
        // from onStartCommand means Android will restart us shortly. Calling
        // stopVpn() here would mark AppState.isRunning=false and prevent
        // the auto-restart from re-establishing the tunnel.
        if (activeServiceRef?.get() === this) {
            activeServiceRef = null
        }
        startupCancelled.set(true)
        startupExecutor.shutdownNow()
        super.onDestroy()
    }
}
