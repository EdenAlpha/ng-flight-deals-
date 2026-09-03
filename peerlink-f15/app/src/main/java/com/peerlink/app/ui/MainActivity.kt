package com.peerlink.app.ui

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.ConnectivityManager
import android.net.VpnService
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import android.net.Uri
import android.util.Log
import android.widget.Toast
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.setValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.draw.scale
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.material3.Typography
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import com.peerlink.app.network.HotspotPairing
import com.peerlink.app.network.LanPath
import com.peerlink.app.network.LanPathResolver
import com.peerlink.app.godmode.PrimeLadderManager
import com.peerlink.app.core.PeerConnectionType
import com.peerlink.app.core.PeerInfo
import com.peerlink.app.core.AppState
import com.peerlink.app.core.VpnSessionState
import com.peerlink.app.core.DiscoveryState
import com.peerlink.app.discovery.NsdDiscovery
import com.peerlink.app.godmode.GodModeManager
import com.peerlink.app.service.PeerLinkVpnService
import com.peerlink.app.service.CallMonitorService
import androidx.compose.ui.unit.Dp
import android.content.ContentValues
import android.provider.MediaStore
import kotlinx.coroutines.launch
import java.net.InetAddress
import java.net.NetworkInterface
import java.security.MessageDigest

class MainActivity : AppCompatActivity(), NsdDiscovery.NsdCallback {

    companion object {
        private const val MASTER_KEY = "DENIS-BOSS-2026"
        private const val DESTRUCT_TIME_MS = 5L * 60L * 1000L
        private const val SHARED_PEER_TTL_MS = 12_000L
    }

    private val handler = Handler(Looper.getMainLooper())
    private var nsdDiscovery: NsdDiscovery? = null
    private val prefs by lazy { getSharedPreferences("peerlink_prefs", Context.MODE_PRIVATE) }
    private var hotspotPairing: HotspotPairing? = null

    private val _discoveredPeers = mutableStateListOf<PeerInfo>()
    // Unified presence clock shared by both UDP discovery mechanisms. Individual
    // discovery sources are not allowed to remove UI peers independently.
    private val peerLastSeenMs = mutableMapOf<String, Long>()
    private var myLocalIp by mutableStateOf<String?>(null)
    private var deviceShortId: String = ""
    private var vpnConsentLauncher: ActivityResultLauncher<Intent>? = null
    private var pendingVpnStartedCallback: (() -> Unit)? = null
    private val hotspotVpnStartInFlight = java.util.concurrent.atomic.AtomicBoolean(false)

    private var discoveryHealthRunnable: Runnable? = null
    private var discoverySuspendedForSession = false

    // ── Match system ───────────────────────────────────────────────────────

    // ── Post-unlock startup gate ────────────────────────────────────────────
    // Nothing heavy starts until the user has unlocked the app.
    @Volatile private var postUnlockStartupDone = false
    @Volatile private var pendingSessionIdForRecovery: String? = null
    @Volatile private var pendingNotificationAction: (() -> Unit)? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            window.setDecorFitsSystemWindows(false)
        }

        val deviceId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "UNKNOWN"
        deviceShortId = if (deviceId.length > 6) deviceId.takeLast(6).uppercase() else deviceId.uppercase()

        AppState.deviceId = deviceId.take(8)

        if (!prefs.getBoolean("isDestroyed", false)) {
            nsdDiscovery = NsdDiscovery(this, this)
            nsdDiscovery?.initialize()
        }

        myLocalIp = getLocalIp()

        // PeerLink is Wi-Fi/hotspot only. Clear any legacy transport choice.
        prefs.edit().putString("transport_mode", "wifi").apply()

        vpnConsentLauncher = registerForActivityResult(
            ActivityResultContracts.StartActivityForResult()
        ) { result ->
            val startedCb = pendingVpnStartedCallback
            pendingVpnStartedCallback = null
            if (result.resultCode == Activity.RESULT_OK) {
                startedCb?.invoke()
                if (!AppState.isRunning.get()) {
                    startVpnService()
                }
                scheduleVpnStartLatchRelease()
            } else {
                hotspotVpnStartInFlight.set(false)
                AppState.appendLog("[VPN-START ] User denied VPN permission")
            }
        }

        setContent {
            var isDestroyed by remember { mutableStateOf(prefs.getBoolean("isDestroyed", false)) }
                var isUnlocked by remember { mutableStateOf(prefs.getBoolean("isUnlocked", false)) }
                var isAdminState by remember { mutableStateOf(prefs.getBoolean("isAdmin", false)) }
                val showPrimeSetup = remember { mutableStateOf(false) }

                if (isDestroyed) {
                    PeerLinkTheme { DestructionScreen() }
                } else if (!isUnlocked) {
                    PeerLinkTheme {
                        LockScreen(
                            onUnlocked = { admin ->
                                isAdminState = admin
                                isUnlocked = true
                                runPostUnlockStartupOnce()
                            },
                            onDestroyed = { isDestroyed = true }
                        )
                    }
                } else if (showPrimeSetup.value) {
                    PeerLinkTheme {
                        PrimeSetupScreen(ctx = this@MainActivity, onBack = { showPrimeSetup.value = false })
                    }
                } else PeerLinkTheme {
                    LaunchedEffect(Unit) { runPostUnlockStartupOnce() }

                    var pendingDiscovery by remember { mutableStateOf<(() -> Unit)?>(null) }
                    val nearbyLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { perms ->
                        if (perms.values.all { it }) pendingDiscovery?.invoke()
                        else Toast.makeText(this@MainActivity, "Location/Wi-Fi permission needed to find players", Toast.LENGTH_SHORT).show()
                        pendingDiscovery = null
                    }
                    fun withDiscoveryPerms(run: () -> Unit) {
                        val req = discoveryPermissionsToRequest()
                        val ok = req.all { ContextCompat.checkSelfPermission(this@MainActivity, it) == PackageManager.PERMISSION_GRANTED }
                        if (ok) run() else { pendingDiscovery = run; nearbyLauncher.launch(req) }
                    }

                PeerLinkScreen(
                    ctx = this@MainActivity,
                    peers = _discoveredPeers,
                    actions = PeerLinkActions(
                        saveName = { n ->
                            prefs.edit().putString("username", n).apply()
                            // Re-register discovery under the new name immediately so
                            // peers see the right name and a fresh install (which loaded
                            // the screen before any name existed) starts broadcasting.
                            withDiscoveryPerms { startBroadcastAndDiscovery(n) {} }
                        },
                        connectToPeer = { peer ->
                            when (peer.connectionType) {
                                PeerConnectionType.HOTSPOT -> hotspotPairing?.initiatePairing(peer.ip)
                                else -> { }
                            }
                        },
                        disconnect = { stopVpnService() },
                        isAdmin = isAdminState,
                        tryAdminUnlock = { entered ->
                            if (entered.trim() == MASTER_KEY) {
                                prefs.edit().putBoolean("isAdmin", true).apply(); isAdminState = true; true
                            } else false
                        },
                        deviceId = deviceShortId,
                        generateKey = { id -> generateKey(id) },
                        onSetupPrimeMode = { showPrimeSetup.value = true },
                        exportMatchLogs = {
                            // Read the FULL session log from the session file
                            // (contains both appendLog and appendFileOnly entries —
                            // the latter is what carries the gameplay-traffic traces).
                            // The previous implementation read CrashLogger.getLiveLog()
                            // which is a 50KB SharedPreferences snapshot and was
                            // missing most of the actual match traffic diagnostics.
                            // Also flush the file writer first so the latest entries
                            // are on disk before we read.
                            val fullLog = try {
                                com.peerlink.app.core.AppState.flushAndReadSessionLog(this@MainActivity)
                            } catch (t: Throwable) {
                                AppState.appendLog("[EXPORT ] Failed to read session file: ${t.message}")
                                // Fallback to the in-memory buffer (still much better
                                // than the 50KB SharedPreferences snapshot).
                                AppState.getLogs()
                            }
                            val ok = saveLogsToDownloads("peerlink_match_${System.currentTimeMillis()}.txt", fullLog)
                            runOnUiThread {
                                android.widget.Toast.makeText(
                                    this@MainActivity,
                                    if (ok) "Match logs saved to Downloads (${fullLog.length} chars)"
                                    else "Failed to save logs — check permissions",
                                    android.widget.Toast.LENGTH_LONG
                                ).show()
                            }
                            AppState.appendLog("[EXPORT ] Match logs exported: ${fullLog.length} chars, ok=$ok")
                        },
                        callBlockEnabled = {
                            CallMonitorService.isActive(this@MainActivity)
                        },
                        setCallBlock = { on ->
                            prefs.edit().putBoolean("apex_call_block_gameplay", on).apply()
                            if (on) {
                                CallMonitorService.start(this@MainActivity, gameplayMode = true)
                            } else {
                                CallMonitorService.stop(this@MainActivity)
                            }
                        },
                        startDiscovery = {
                            withDiscoveryPerms {
                                // User/UI refresh means a real fresh discovery view,
                                // not a no-op start on stale sockets/peer rows.
                                _discoveredPeers.clear()
                                peerLastSeenMs.clear()
                                prefs.edit().putString("transport_mode", "wifi").apply()
                                val nm = prefs.getString("username", "") ?: ""
                                startBroadcastAndDiscovery(nm) {}
                            }
                        },
                    )
                )
                }
        }
    }

    private fun noteDiscoveredPeer(peerIp: String, peerName: String) {
        if (peerIp.isBlank() || peerIp == "127.0.0.1") return
        peerLastSeenMs[peerIp] = System.currentTimeMillis()
        val displayName = peerName.ifBlank { peerIp }
        val index = _discoveredPeers.indexOfFirst { it.ip == peerIp }
        if (index < 0) {
            _discoveredPeers.add(PeerInfo(
                name = displayName,
                ip = peerIp,
                mac = "",
                connectionType = PeerConnectionType.HOTSPOT
            ))
            AppState.discoveryState.set(DiscoveryState.PEERS_FOUND)
            AppState.appendLog("[NET-DISC  ] Player visible: $displayName @ $peerIp")
        } else if (_discoveredPeers[index].name != displayName) {
            _discoveredPeers[index] = _discoveredPeers[index].copy(name = displayName)
        }
    }

    private fun expireSharedPeers(nowMs: Long = System.currentTimeMillis()) {
        val expired = peerLastSeenMs.filterValues { nowMs - it > SHARED_PEER_TTL_MS }.keys.toList()
        if (expired.isEmpty()) return
        expired.forEach { peerLastSeenMs.remove(it) }
        _discoveredPeers.removeAll { it.ip in expired }
        if (_discoveredPeers.isEmpty() &&
            (AppState.vpnSessionState.get() == VpnSessionState.DISCONNECTED || AppState.vpnSessionState.get() == VpnSessionState.ERROR)) {
            AppState.discoveryState.set(DiscoveryState.SEARCHING)
        }
        AppState.appendFileOnly("[NET-DISC  ] Expired ${expired.size} stale player(s): ${expired.joinToString()}")
    }

    private fun startHotspotPairingListener(myName: String = getSharedPreferences("peerlink_prefs", Context.MODE_PRIVATE).getString("username", "") ?: "") {
        // Re-resolve on every listener start. This matters after returning from
        // hotspot/Wi-Fi settings: the interface that existed before onPause may
        // no longer be the peer LAN interface.
        val freshPath = LanPathResolver.bestDiscoveryPath(this)
        if (freshPath == null) {
            hotspotPairing?.stop()
            hotspotPairing = null
            AppState.discoveryState.set(DiscoveryState.WAITING_FOR_WIFI)
            AppState.appendFileOnly("[HOTSPOT   ] No Wi-Fi/SoftAP LAN yet — listener deferred")
            return
        }
        lockLanPath(freshPath)
        myLocalIp = freshPath.localIp
        AppState.localIp.set(freshPath.localIp)
        AppState.appendFileOnly(
            "[HOTSPOT   ] Discovery path refreshed: ${freshPath.interfaceName}#${freshPath.interfaceIndex} " +
                "${freshPath.localIp}/${freshPath.prefixLength}"
        )

        hotspotPairing?.stop()
        hotspotPairing = HotspotPairing().apply {

            // NEW: Peer discovered — add to list so user can tap before pairing.
            onPeerDiscovered = { peerIp, peerName ->
                runOnUiThread { noteDiscoveredPeer(peerIp, peerName) }
            }

            // Fires after user taps peer and initiatePairing is called.
            onPeerReady = { peerIpStr ->
                runOnUiThread {
                    try {
                        // Establish peer identity FIRST, then resolve the exact LAN path
                        // that reaches it. The old ordering called local-IP detection before
                        // peerIp/connectionMode were set, so the hotspot-specific branch could
                        // never run and cellular 10.x addresses were sometimes selected.
                        AppState.peerIp.set(InetAddress.getByName(peerIpStr))
                        AppState.connectionMode = "hotspot"
                        AppState.activeTransportMode.set("wifi_udp")

                        val lanPath = LanPathResolver.resolveForPeer(this@MainActivity, peerIpStr)
                            ?: throw IllegalStateException("No LAN interface can reach peer $peerIpStr")
                        lockLanPath(lanPath)
                        val detectedLocalIp = lanPath.localIp
                        AppState.isPaired.set(true)

                        val fabricatedOk = AppState.calculateFabricatedIps()

                        AppState.appendLog("[HOTSPOT   ] Local LAN path locked: ${lanPath.interfaceName}#${lanPath.interfaceIndex} $detectedLocalIp/${lanPath.prefixLength}")
                        AppState.appendLog("[HOTSPOT   ] Peer confirmed for pairing: $peerIpStr")
                        AppState.appendLog("[HOTSPOT   ] Fabricated IPs ready=$fabricatedOk | my=${AppState.myFabricatedIp} peer=${AppState.peerFabricatedIp}")
                        if (!hotspotVpnStartInFlight.compareAndSet(false, true)) {
                            AppState.appendLog("[VPN-START ] Hotspot VPN start already in flight — ignoring duplicate pair event")
                            return@runOnUiThread
                        }

                        val startAction: () -> Unit = {
                            startVpnService()
                            scheduleVpnStartLatchRelease()
                            Unit
                        }

                        val consentIntent = VpnService.prepare(this@MainActivity)
                        if (consentIntent != null) {
                            pendingVpnStartedCallback = startAction
                            vpnConsentLauncher?.launch(consentIntent) ?: run {
                                pendingVpnStartedCallback = null
                                hotspotVpnStartInFlight.set(false)
                                AppState.appendLog("[VPN-START ] ERROR: VPN consent launcher unavailable")
                            }
                        } else {
                            startAction()
                        }
                    } catch (e: Exception) {
                        AppState.appendLog("Failed to set peer IP: ${e.message}")
                    }
                }
            }

            onPeerPortReceived = { port ->
                runOnUiThread {
                    val effectivePort = if (port > 0) port else 17024
                    AppState.peerPort.set(effectivePort)
                    AppState.appendLog("[HOTSPOT   ] Peer tunnel port: $effectivePort")
                }
            }

            onPeerLost = { peerIp ->
                // Do not remove immediately: the secondary discovery source may
                // still be receiving this same player. Central TTL expiry decides.
                AppState.appendFileOnly("[NET-DISC  ] Hotspot source lost $peerIp; awaiting unified TTL")
            }

            onStatus = { status ->
                runOnUiThread { AppState.appendLog("[HOTSPOT   ] $status") }
            }
        }
        hotspotPairing?.updateLocalPort(AppState.peerPort.get())
        // Pass the detected local LAN IP so the listener socket binds to the
        // Wi-Fi / hotspot interface and beacons cannot leak to cellular.
        hotspotPairing?.start(
            deviceId = AppState.deviceId,
            myName   = myName,
            localIp  = myLocalIp ?: AppState.localIp.get() ?: "",
            prefixLength = AppState.localLanPrefixLength.get().takeIf { it in 1..32 } ?: 24
        )
    }



    private fun hasNotificationPermission(): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun ensureNotificationPermissionThen(action: () -> Unit) {
        if (hasNotificationPermission()) {
            action()
            return
        }
        pendingNotificationAction = action
        requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1002)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        when (requestCode) {
            1002 -> {
                val granted = grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED
                if (granted) {
                    pendingNotificationAction?.invoke()
                } else {
                    AppState.appendLog("[PRIME-MODE ] Notification permission denied — pairing notification cannot be shown")
                    Toast.makeText(this, "Notification permission is needed for Prime Mode pairing", Toast.LENGTH_LONG).show()
                }
                pendingNotificationAction = null
            }
        }
    }






















    private fun startBroadcastAndDiscovery(userName: String, onStarted: () -> Unit) {
        discoverySuspendedForSession = false
        // Auto mode may turn Wi-Fi on asynchronously. Discovery must never fake a
        // working LAN by falling back to a private cellular 10.x address while that
        // happens; the health monitor will start us as soon as a real Wi-Fi/SoftAP
        // interface appears.
        GodModeManager.enableRadiosForSession()

        val effectiveName = userName.ifBlank {
            val m = Build.MODEL?.takeIf { it.isNotBlank() } ?: "Player"
            m.take(14)
        }
        val discoveryPath = LanPathResolver.bestDiscoveryPath(this)
        if (discoveryPath == null) {
            runCatching { hotspotPairing?.stop() }
            hotspotPairing = null
            runCatching { nsdDiscovery?.stopDiscovery() }
            myLocalIp = null
            AppState.discoveryState.set(DiscoveryState.WAITING_FOR_WIFI)
            AppState.appendLog("[NET-DISC  ] Waiting for a Wi-Fi/hotspot LAN — cellular is intentionally ignored")
            startDiscoveryHealthMonitor()
            onStarted()
            return
        }

        val ip = discoveryPath.localIp
        val prefix = discoveryPath.prefixLength
        myLocalIp = ip
        AppState.localIp.set(ip)
        lockLanPath(discoveryPath)
        AppState.discoveryState.set(if (_discoveredPeers.isEmpty()) DiscoveryState.SEARCHING else DiscoveryState.PEERS_FOUND)
        AppState.appendLog("[NET-DISC  ] Discovery LAN path: ${discoveryPath.interfaceName} $ip/$prefix")

        // NsdDiscovery is UDP broadcast rather than platform mDNS. Every explicit
        // refresh is a real socket refresh so stale Wi-Fi/hotspot binds cannot survive.
        runCatching { nsdDiscovery?.stopDiscovery() }
        nsdDiscovery?.registerService(AppState.peerPort.get(), effectiveName, ip, prefix)
        nsdDiscovery?.startDiscovery()

        startHotspotPairingListener(effectiveName)
        startDiscoveryHealthMonitor()
        onStarted()
    }

    /**
     * Keep discovery self-healing without triggering Wi-Fi AP scans. PeerLink
     * discovers players with its own UDP beacons; WifiManager.startScan() is
     * unrelated to that protocol and can disturb a latency-sensitive Wi-Fi link.
     */
    private fun startDiscoveryHealthMonitor() {
        if (discoveryHealthRunnable != null) return
        discoveryHealthRunnable = object : Runnable {
            override fun run() {
                try {
                    val sessionState = AppState.vpnSessionState.get()
                    val discoveryAllowed = sessionState == VpnSessionState.DISCONNECTED || sessionState == VpnSessionState.ERROR
                    if (!discoveryAllowed) {
                        // Once pairing hands off to the VPN, discovery should go quiet.
                        if (!discoverySuspendedForSession) {
                            discoverySuspendedForSession = true
                            runCatching { hotspotPairing?.stop() }
                            runCatching { nsdDiscovery?.stopDiscovery() }
                            AppState.discoveryState.set(DiscoveryState.PAUSED_FOR_SESSION)
                            AppState.appendLog("[NET-DISC  ] Discovery paused for active VPN session")
                        }
                    } else if (prefs.getBoolean("isUnlocked", false)) {
                        expireSharedPeers()
                        val path = LanPathResolver.bestDiscoveryPath(this@MainActivity)
                        if (path == null) {
                            if (AppState.discoveryState.get() != DiscoveryState.WAITING_FOR_WIFI) {
                                runCatching { hotspotPairing?.stop() }
                                hotspotPairing = null
                                runCatching { nsdDiscovery?.stopDiscovery() }
                                _discoveredPeers.clear()
                                peerLastSeenMs.clear()
                                AppState.discoveryState.set(DiscoveryState.WAITING_FOR_WIFI)
                                AppState.appendLog("[NET-DISC  ] Wi-Fi/hotspot LAN disappeared — waiting for it to return")
                            }
                        } else {
                            val pathChanged = AppState.localIp.get() != path.localIp ||
                                AppState.localLanInterfaceIndex.get() != path.interfaceIndex ||
                                AppState.localLanPrefixLength.get() != path.prefixLength
                            val hotspotDead = hotspotPairing?.isRunning != true
                            val secondaryDead = nsdDiscovery?.isRunning != true
                            if (discoverySuspendedForSession || pathChanged || hotspotDead || secondaryDead ||
                                AppState.discoveryState.get() == DiscoveryState.WAITING_FOR_WIFI) {
                                val reasons = buildList {
                                    if (discoverySuspendedForSession) add("session ended")
                                    if (pathChanged) add("LAN path changed")
                                    if (hotspotDead) add("pair listener stopped")
                                    if (secondaryDead) add("secondary listener stopped")
                                }
                                discoverySuspendedForSession = false
                                if (pathChanged) {
                                    _discoveredPeers.clear()
                                    peerLastSeenMs.clear()
                                }
                                AppState.appendLog("[NET-DISC  ] Self-heal: ${reasons.ifEmpty { listOf("Wi-Fi ready") }.joinToString()} — refreshing discovery")
                                val nm = prefs.getString("username", "") ?: ""
                                startBroadcastAndDiscovery(nm) {}
                                return
                            }
                            AppState.discoveryState.set(if (_discoveredPeers.isEmpty()) DiscoveryState.SEARCHING else DiscoveryState.PEERS_FOUND)
                        }
                    }
                } catch (t: Throwable) {
                    AppState.appendFileOnly("[NET-DISC  ] Health check failed: ${t.message}")
                } finally {
                    val nextDelay = if (AppState.discoveryState.get() == DiscoveryState.WAITING_FOR_WIFI) 1_500L else 5_000L
                    handler.postDelayed(this, nextDelay)
                }
            }
        }
        handler.postDelayed(discoveryHealthRunnable!!, 5_000L)
    }

    private fun stopDiscoveryHealthMonitor() {
        discoveryHealthRunnable?.let { handler.removeCallbacks(it) }
        discoveryHealthRunnable = null
    }


    private fun generateKey(id: String): String {
        val normalized = id.trim().uppercase()
        val digest = MessageDigest.getInstance("SHA-256")
            .digest("PeerLink::${normalized}::LanLink-Admin-2026".toByteArray())
        val alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
        val raw = buildString {
            repeat(12) { idx ->
                val b = digest[idx].toInt() and 0xFF
                append(alphabet[b % alphabet.length])
            }
        }
        return raw.chunked(4).joinToString("-")
    }


    @Composable
    fun LockScreen(onUnlocked: (isAdmin: Boolean) -> Unit, onDestroyed: () -> Unit) {
        val activity = this@MainActivity
        BackHandler { activity.finish() }

        val lockStartTime = remember {
            val saved = prefs.getLong("lockStartTime", 0L)
            if (saved == 0L) {
                val now = System.currentTimeMillis()
                prefs.edit().putLong("lockStartTime", now).apply()
                now
            } else {
                saved
            }
        }

        val initialRemaining = remember {
            val elapsed = System.currentTimeMillis() - lockStartTime
            (DESTRUCT_TIME_MS - elapsed).coerceAtLeast(0L)
        }

        if (initialRemaining <= 0L) {
            LaunchedEffect(Unit) {
                prefs.edit().putBoolean("isDestroyed", true).apply()
                onDestroyed()
            }
            Box(modifier = Modifier.fillMaxSize().background(Color(0xFFECEEF2)))
            return
        }

        var timeLeftMs by remember { mutableLongStateOf(initialRemaining) }
        var keyInput by remember { mutableStateOf("") }
        var showError by remember { mutableStateOf(false) }
        val focusManager = LocalFocusManager.current

        val userKey = remember { generateKey(deviceShortId) }

        LaunchedEffect(Unit) {
            while (timeLeftMs > 0L) {
                kotlinx.coroutines.delay(1000L)
                val elapsed = System.currentTimeMillis() - lockStartTime
                timeLeftMs = (DESTRUCT_TIME_MS - elapsed).coerceAtLeast(0L)
            }
            prefs.edit().putBoolean("isDestroyed", true).apply()
            onDestroyed()
        }

        val minutes = timeLeftMs / 1000L / 60L
        val seconds = timeLeftMs / 1000L % 60L

        val infiniteTransition = rememberInfiniteTransition(label = "LockPulse")
        val timerAlpha by infiniteTransition.animateFloat(
            initialValue = 1f, targetValue = 0.4f,
            animationSpec = infiniteRepeatable(tween(1000), RepeatMode.Reverse),
            label = "TimerAlpha"
        )

        val glowAlpha by infiniteTransition.animateFloat(
            initialValue = 0.05f, targetValue = 0.15f,
            animationSpec = infiniteRepeatable(tween(2000), RepeatMode.Reverse),
            label = "GlowAlpha"
        )

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFECEEF2))
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0xFFF0BE43).copy(alpha = glowAlpha), Color.Transparent),
                        center = Offset(size.width / 2f, size.height * 0.3f),
                        radius = size.width * 0.8f
                    )
                )
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .systemBarsPadding()
                    .padding(32.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    "PeerLink",
                    style = TextStyle(
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 4.sp,
                        color = Color(0xFF8A929C)
                    )
                )

                Spacer(modifier = Modifier.weight(0.3f))

                Text(
                    "%d:%02d".format(minutes, seconds),
                    color = Color(0xFFCB5C6B).copy(alpha = timerAlpha),
                    fontSize = 72.sp,
                    fontWeight = FontWeight.Thin,
                    fontFamily = FontFamily.Monospace
                )

                Spacer(modifier = Modifier.height(40.dp))

                Text(
                    "DEVICE ID",
                    color = Color(0xFF8A929C),
                    fontSize = 10.sp,
                    letterSpacing = 2.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    deviceShortId,
                    color = Color(0xFFC9961F),
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    fontFamily = FontFamily.Monospace,
                    letterSpacing = 4.sp
                )

                Spacer(modifier = Modifier.height(40.dp))

                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp)
                        .border(
                            1.dp,
                            if (showError) Color(0xFFCB5C6B) else Color(0xFFDBE0E6),
                            RoundedCornerShape(12.dp)
                        )
                        .padding(horizontal = 16.dp),
                    contentAlignment = Alignment.Center
                ) {
                    BasicTextField(
                        value = keyInput,
                        onValueChange = { keyInput = it; showError = false },
                        textStyle = TextStyle(
                            color = Color(0xFF202531),
                            fontSize = 18.sp,
                            textAlign = TextAlign.Center,
                            fontFamily = FontFamily.Monospace
                        ),
                        cursorBrush = SolidColor(Color(0xFFC9961F)),
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                        keyboardActions = KeyboardActions(onDone = { focusManager.clearFocus() }),
                        decorationBox = { innerTextField ->
                            Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                                if (keyInput.isEmpty()) {
                                    Text(
                                        "ENTER ACCESS KEY",
                                        color = Color(0xFF8A929C).copy(alpha = 0.4f),
                                        fontSize = 14.sp,
                                        letterSpacing = 2.sp
                                    )
                                }
                                innerTextField()
                            }
                        }
                    )
                }

                AnimatedVisibility(visible = showError) {
                    Text(
                        "INVALID KEY",
                        color = Color(0xFFCB5C6B),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }

                Spacer(modifier = Modifier.height(24.dp))

                Button(
                    onClick = {
                        focusManager.clearFocus()
                        val entered = keyInput.trim()
                        when {
                            entered == MASTER_KEY -> {
                                prefs.edit()
                                    .putBoolean("isUnlocked", true)
                                    .putBoolean("isAdmin", true)
                                    .remove("lockStartTime")
                                    .apply()
                                onUnlocked(true)
                            }
                            entered == userKey -> {
                                prefs.edit()
                                    .putBoolean("isUnlocked", true)
                                    .putBoolean("isAdmin", false)
                                    .remove("lockStartTime")
                                    .apply()
                                onUnlocked(false)
                            }
                            else -> showError = true
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(56.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC9961F), contentColor = Color(0xFF3A2C06)),
                    shape = RoundedCornerShape(14.dp),
                    elevation = ButtonDefaults.buttonElevation(0.dp)
                ) {
                    Icon(
                        Icons.Default.Lock,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        "UNLOCK",
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 2.sp
                    )
                }

                Spacer(modifier = Modifier.weight(1f))
            }
        }
    }

    @Composable
    fun DestructionScreen() {
        val activity = this@MainActivity
        BackHandler { activity.finish() }

        val infiniteTransition = rememberInfiniteTransition(label = "DestructPulse")
        val pulseAlpha by infiniteTransition.animateFloat(
            initialValue = 1f, targetValue = 0.3f,
            animationSpec = infiniteRepeatable(tween(1500), RepeatMode.Reverse),
            label = "DestructAlpha"
        )
        val pulseScale by infiniteTransition.animateFloat(
            initialValue = 1f, targetValue = 1.1f,
            animationSpec = infiniteRepeatable(tween(1500), RepeatMode.Reverse),
            label = "DestructScale"
        )

        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(Color(0xFFECEEF2))
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                drawCircle(
                    brush = Brush.radialGradient(
                        colors = listOf(Color(0xFFF0BE43).copy(alpha = 0.10f), Color.Transparent),
                        center = Offset(size.width / 2f, size.height / 2f),
                        radius = size.width * 0.6f
                    )
                )
            }

            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .systemBarsPadding(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Icon(
                    Icons.Default.Warning,
                    contentDescription = null,
                    tint = Color(0xFFCB5C6B).copy(alpha = pulseAlpha),
                    modifier = Modifier
                        .size(80.dp)
                        .scale(pulseScale)
                )
                Spacer(modifier = Modifier.height(32.dp))
                Text(
                    "SYSTEM FAILURE",
                    color = Color(0xFFCB5C6B).copy(alpha = pulseAlpha),
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 4.sp
                )
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    "This app has been permanently disabled\ndue to unauthorized access.",
                    color = Color(0xFF8A929C),
                    fontSize = 14.sp,
                    textAlign = TextAlign.Center,
                    lineHeight = 22.sp
                )
            }
        }
    }












    /**
     * Compact God Mode status card shown in SetupView.
     * Tapping it opens the full GodModeDialog.
     */



    // ── MatchView — slides in from right of DiscoveryView ─────────────────
    //
    // Layout:
    //   1. PeerCoin balance dashboard (tappable → shows opponents bubble)
    //   2. Latest match score
    //   3. Scrollable full match history
    //
    // Opponents bubble (almost full-screen):
    //   Scrollable list of everyone you've played, with win-rate per person.
    //   Tap a name → filters history to only that opponent.

    // Sample data — replace with server data when backend is ready



    // ── PeerCoin dashboard card ─────────────────────────────────────────────



    // ── Unique hexagonal coin icon ──────────────────────────────────────────



    // Helper extension for Box with size

    // ── Latest match card ───────────────────────────────────────────────────



    // ── Match history row ───────────────────────────────────────────────────



    // ── Opponents bubble (almost full screen sheet) ─────────────────────────



    // ── Opponent row with unique avatar ──────────────────────────────────────











    /**
     * Runs once after the user unlocks the app or when an already-unlocked
     * process is recreated. This keeps heavy startup work away from the lock
     * screen while still ensuring Prime Mode pieces are ready before use.
     */
    private fun runPostUnlockStartupOnce() {
        if (postUnlockStartupDone) return
        postUnlockStartupDone = true

        // Request POST_NOTIFICATIONS up-front so the VPN foreground notification is visible
        // on Android 13+ (API 33+). Without this, the notification is silently suppressed —
        // the root cause of the invisible-notification issue on Android 13+/15 devices.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            ensureNotificationPermissionThen { }
        }

        try {
            GodModeManager.init(this)
            AppState.appendLog("[STARTUP    ] GodModeManager.init ok")
        } catch (t: Throwable) {
            Log.e("MainActivity", "GodModeManager.init failed", t)
            AppState.appendLog("[STARTUP    ] GodModeManager.init failed: ${t.message}")
        }

        try {
            PrimeLadderManager.checkAliveOnAppOpen()
            AppState.appendLog("[STARTUP    ] Prime alive check ok")
        } catch (t: Throwable) {
            Log.e("MainActivity", "PrimeLadderManager.checkAliveOnAppOpen failed", t)
            AppState.appendLog("[STARTUP    ] Prime alive check failed: ${t.message}")
        }

        // Auto Mode is handled through the already-running PrimeServer when
        // available. Never throw the user into Wi-Fi Settings automatically on
        // app open; if Wi-Fi is off, the nearby-player UI simply waits and its
        // network callback resumes discovery as soon as Wi-Fi becomes available.
        try { GodModeManager.enableRadiosForSession() } catch (_: Throwable) { }

        // ── Request battery-optimisation exemption ────────────────────────
        // Some OEMs are unusually aggressive with long-running background
        // networking. Prime Mode does NOT mutate DeviceIdle/Doze state; this is
        // the system-owned, user-controlled exemption dialog shown once per install.
        // We do it from here (MainActivity, in the foreground) rather than
        // from Application.onCreate() because starting activities from the
        // Application context is restricted on Android 12+ and was crashing
        // the app on Android 13 (Hot 30i).
        try {
            requestBatteryOptimisationExemptionOnce()
        } catch (t: Throwable) {
            AppState.appendLog("[STARTUP    ] Battery-opt-out request failed: ${t.message}")
        }
    }

    /**
     * Fire the system "ignore battery optimisations" dialog once per install
     * if we're not already exempt. Safe to call from an Activity context.
     */
    private fun requestBatteryOptimisationExemptionOnce() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M) return
        val pm = getSystemService(POWER_SERVICE) as? android.os.PowerManager ?: return
        if (pm.isIgnoringBatteryOptimizations(packageName)) return
        // Only ask once per install — Android remembers the user's choice.
        if (prefs.getBoolean("battery_opt_dialog_shown", false)) return
        prefs.edit().putBoolean("battery_opt_dialog_shown", true).apply()
        try {
            val intent = Intent(
                android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS
            ).apply {
                data = android.net.Uri.parse("package:$packageName")
            }
            startActivity(intent)
        } catch (_: Throwable) {
            // Some OEMs don't honour the direct intent. Fall back to opening
            // the battery-optimisation settings page so the user can do it
            // manually.
            try {
                val fallback = Intent(
                    android.provider.Settings.ACTION_IGNORE_BATTERY_OPTIMIZATION_SETTINGS
                )
                startActivity(fallback)
            } catch (_: Throwable) { }
        }
    }

    private fun saveLogsToDownloads(filename: String, text: String): Boolean {
        return try {
            val values = ContentValues().apply {
                put(MediaStore.Downloads.DISPLAY_NAME, filename)
                put(MediaStore.Downloads.MIME_TYPE, "text/plain")
            }
            val uri = contentResolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
            uri?.let {
                contentResolver.openOutputStream(it)?.use { os ->
                    os.write(text.toByteArray(Charsets.UTF_8))
                }
                true
            } ?: false
        } catch (e: Exception) {
            Log.e("MainActivity", "saveLogsToDownloads failed: ${e.message}", e)
            false
        }
    }













    private fun discoveryPermissionsToRequest(): Array<String> {
        val permissions = mutableListOf<String>()
        
        // PeerLink discovery only needs Nearby Wi-Fi on Android 13+.
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.NEARBY_WIFI_DEVICES)
        }
        
        return permissions.toTypedArray()
    }









    private fun lockLanPath(path: LanPath) {
        AppState.localIp.set(path.localIp)
        AppState.localLanInterfaceName.set(path.interfaceName)
        AppState.localLanInterfaceIndex.set(path.interfaceIndex)
        AppState.localLanPrefixLength.set(path.prefixLength)
        AppState.localLanNetwork.set(path.androidNetwork)
        myLocalIp = path.localIp
    }















    private fun startVpnService() {
        // Hotspot pairing already locks the session LAN identity before VPN startup.
        // Do not override that identity here, otherwise the fabricated-IP assignment can
        // flip at service start and split the session between the paired control plane
        // and the native datapath. Only refresh hotspot IP if we somehow do not have one.
        val peer = AppState.peerIp.get()?.hostAddress
        if (!peer.isNullOrBlank()) {
            val path = LanPathResolver.resolveForPeer(this, peer)
            if (path != null) {
                lockLanPath(path)
                AppState.appendLog("[VPN-START ] Revalidated LAN path ${path.interfaceName}#${path.interfaceIndex} ${path.localIp}/${path.prefixLength} -> $peer")
            } else {
                AppState.appendLog("[VPN-START ] WARNING: could not re-resolve peer LAN path; preserving ${AppState.localIp.get()}")
            }
        }

        
        // Auto-activate Prime Mode if paired and master toggle is on.
        // This covers all connection paths (hotspot / LAN) without
        // requiring the user to tap ACTIVATE every session.
        if (GodModeManager.isApexMasterEnabled() &&
            GodModeManager.state.value == GodModeManager.State.PAIRED_IDLE) {
            AppState.appendLog("[PRIME-MODE ] VPN started — auto-activating Prime Mode")
            GodModeManager.activateGodMode()
        }

        val intent = Intent(this, PeerLinkVpnService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) startForegroundService(intent) else startService(intent)
    }

    private fun scheduleVpnStartLatchRelease() {
        // Startup now includes a real peer-path verification and may legitimately
        // take tens of seconds. Do not keep a one-shot 3 s latch around forever.
        val startedAt = System.currentTimeMillis()
        val check = object : Runnable {
            override fun run() {
                when (AppState.vpnSessionState.get()) {
                    VpnSessionState.CONNECTED,
                    VpnSessionState.DISCONNECTED,
                    VpnSessionState.ERROR -> {
                        hotspotVpnStartInFlight.set(false)
                    }
                    else -> {
                        if (System.currentTimeMillis() - startedAt < 70_000L) {
                            handler.postDelayed(this, 500L)
                        } else {
                            hotspotVpnStartInFlight.set(false)
                        }
                    }
                }
            }
        }
        handler.postDelayed(check, 500L)
    }

    private fun stopVpnService() {
        // Log the call stack so we can see WHO triggered the disconnect.
        val caller = Throwable().stackTrace.take(4)
            .filter { it.className.contains("peerlink") }
            .joinToString(" ← ") { "${it.fileName}:${it.lineNumber}.${it.methodName}" }
        AppState.appendLog("[VPN-STOP  ] stopVpnService() called from: $caller")
        // A successful session used to leave this latch true forever, so the next
        // peer tap could be rejected until MainActivity was recreated. Disconnect
        // starts a new pairing lifecycle; release the start latch immediately.
        hotspotVpnStartInFlight.set(false)
        val intent = Intent(this, PeerLinkVpnService::class.java).apply {
            action = PeerLinkVpnService.ACTION_STOP
            putExtra("source", "MainActivity.stopVpnService: $caller")
        }
        startService(intent)
    }

    private fun getLocalIp(): String {
        return try {
            val interfaceIp = findFirstNonLoopbackIpv4 { ip ->
                ip.startsWith("192.168.") || ip.startsWith("10.") ||
                (ip.startsWith("172.") && ip.split(".").getOrNull(1)?.toIntOrNull()?.let { it in 16..31 } == true)
            }

            if (interfaceIp != null) {
                return interfaceIp
            }

            val cm = getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

            for (network in cm.allNetworks) {
                val lp = cm.getLinkProperties(network) ?: continue

                val ip = lp.linkAddresses.asSequence()
                    .map { it.address }
                    .filterIsInstance<java.net.Inet4Address>()
                    .firstOrNull { !it.isLoopbackAddress && !it.isLinkLocalAddress }
                    ?.hostAddress

                if (ip != null) {
                    return ip
                }
            }

            findFirstNonLoopbackIpv4 { true } ?: "127.0.0.1"

        } catch (e: Exception) {
            "127.0.0.1"
        }
    }

    private fun findFirstNonLoopbackIpv4(match: (String) -> Boolean): String? {
        val interfaces = NetworkInterface.getNetworkInterfaces() ?: return null

        return interfaces.asSequence()
            .filter { !it.isLoopback && it.isUp }
            .filter {
                val name = it.name.lowercase()
                !name.startsWith("tun") && !name.startsWith("tap") && !name.startsWith("ppp")
            }
            .flatMap { it.inetAddresses.asSequence() }
            .filterIsInstance<java.net.Inet4Address>()
            .filter { !it.isLoopbackAddress && !it.isLinkLocalAddress }
            .mapNotNull { it.hostAddress }
            .firstOrNull(match)
    }

    override fun onPeerFound(ip: InetAddress, port: Int, serviceName: String) {
        val peerIp = ip.hostAddress ?: return
        runOnUiThread { noteDiscoveredPeer(peerIp, serviceName) }
    }

    override fun onPeerLost(serviceName: String) {
        // A single discovery source expiring is not authoritative. Shared
        // IP/freshness expiry handles removal after both sources go quiet.
        AppState.appendFileOnly("[NET-DISC  ] Secondary source lost $serviceName; awaiting unified TTL")
    }

    override fun onLog(message: String) {
        Log.d("LanLink", message)
        AppState.appendLog(message)
    }

    override fun onPause() {
        super.onPause()
        // Do NOT tear discovery down for a transient pause (VPN consent, settings,
        // permission dialogs, notification shade, etc.). The Activity may resume a
        // moment later and the old behaviour made discovery feel one-shot.
        AppState.appendLog("[T-STATE   ] MainActivity onPause running=${AppState.isRunning.get()} — discovery preserved")
    }

    override fun onResume() {
        super.onResume()
        AppState.appendLog("[T-STATE   ] MainActivity onResume running=${AppState.isRunning.get()} mode=${AppState.connectionMode}")

        // If the app is still locked, do nothing.
        // Heavy subsystems must not start before the user unlocks.
        if (!prefs.getBoolean("isUnlocked", false)) return


        val sessionState = AppState.vpnSessionState.get()
        if (sessionState != VpnSessionState.DISCONNECTED && sessionState != VpnSessionState.ERROR) {
            AppState.appendLog("[RESUME     ] Session $sessionState detected — preserving live transport; discovery remains paused")
            // Do not restart peer or ADB/mDNS discovery while a match is active.
            // PrimeServer already communicates over loopback and the native tunnel
            // owns the gameplay path; control-plane discovery can resume after stop.
            try { GodModeManager.refreshSetupState() } catch (e: Exception) {
                AppState.appendLog("[RESUME     ] Prime status refresh failed: ${e.message}")
            }
            return
        }

        try {
            // A real refresh, not startDiscovery() on a socket that may still be
            // bound to yesterday's Wi-Fi/hotspot interface.
            val required = discoveryPermissionsToRequest()
            val allowed = required.all { ContextCompat.checkSelfPermission(this, it) == PackageManager.PERMISSION_GRANTED }
            if (allowed) {
                val nm = prefs.getString("username", "") ?: ""
                startBroadcastAndDiscovery(nm) {}
            }
        } catch (e: Exception) {
            Log.e("MainActivity", "onResume discovery refresh failed: ${e.message}", e)
            AppState.appendLog("[RESUME     ] Discovery refresh failed: ${e.message}")
        }
        try {
            GodModeManager.startWatching()
            GodModeManager.refreshSetupState()
        } catch (e: Exception) {
            Log.e("MainActivity", "GodModeManager.startWatching failed: ${e.message}", e)
            AppState.appendLog("[RESUME     ] Prime watcher failed: ${e.message}")
        }
    }



    override fun onDestroy() {
        stopDiscoveryHealthMonitor()
        val sessionActive = when (AppState.vpnSessionState.get()) {
            VpnSessionState.CONNECTING, VpnSessionState.VERIFYING,
            VpnSessionState.CONNECTED, VpnSessionState.DISCONNECTING -> true
            else -> false
        }
        AppState.appendLog("[T-STATE   ] MainActivity onDestroy sessionActive=$sessionActive mode=${AppState.connectionMode}")

        // Activity recreation must never change the radio underneath an active
        // VPN/game session. Restore Auto Mode radio state only after the session
        // has actually ended.
        if (!sessionActive) GodModeManager.restoreRadiosIfNeeded(this)

        if (!sessionActive && CallMonitorService.isGameplayMode.get()) {
            try { CallMonitorService.stop(this) } catch (_: Exception) { }
        }

        // These sockets are discovery/control-plane only; the active gameplay
        // tunnel lives in PeerLinkVpnService/native. Always close discovery when
        // this Activity is destroyed to avoid leaking callbacks/threads. A recreated
        // Activity will restart discovery only when no VPN session is active.
        try { hotspotPairing?.stop() } catch (_: Exception) { }
        hotspotPairing = null
        try { nsdDiscovery?.tearDown() } catch (_: Exception) { }
        if (!sessionActive) AppState.discoveryState.set(DiscoveryState.IDLE)

        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
