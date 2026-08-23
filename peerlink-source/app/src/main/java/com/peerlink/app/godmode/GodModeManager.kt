package com.peerlink.app.godmode

import android.content.Context
import android.content.Intent
import com.peerlink.app.godmode.shizuku.PrimeShizukuBootstrapEngine
import android.content.pm.PackageManager
import android.net.wifi.WifiManager
import android.os.Build
import android.provider.Settings
import com.peerlink.app.core.AppState
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.sync.Semaphore
import kotlinx.coroutines.sync.withPermit
import java.net.InetSocketAddress
import java.net.ServerSocket

/**
 * GodModeManager — Prime Mode controller.
 *
 * Prime setup uses Android Wireless Debugging once to grant
 * WRITE_SECURE_SETTINGS and launch the detached PrimeServer as the ADB shell
 * user. Normal session control then talks only to the authenticated loopback
 * PrimeServer; it does not keep an ADB connection open.
 *
 * Session policy is intentionally conservative:
 *  - optional eFootball standby-bucket promotion, restored on disconnect
 *  - Wi-Fi auto-enable/restore when the user enabled Auto mode
 *
 * Global Wi-Fi scan/sleep/captive-portal/airplane-mode settings are NOT
 * rewritten as "optimizations". PeerLink's VpnService, wake lock, Wi-Fi
 * low-latency lock and native local-UDP path own the latency-sensitive work.
 */

object GodModeManager {

    private const val PREFS         = "godmode_prefs"
    private const val EFOOTBALL_PKG = "jp.konami.pesam"

    // ─── Preference keys ──────────────────────────────────────────────────
    private const val KEY_KEEP_GAME        = "keep_game_in_ram"
    private const val KEY_APEX_MASTER      = "apex_master_enabled"
    private const val KEY_WIFI_WAS_OFF     = "apex_wifi_was_off"
    private const val KEY_AUTO_CONNECT     = "apex_auto_connect"
    private const val KEY_BOOTSTRAP_DONE   = "bootstrap_grant_done"
    private const val KEY_BOOTSTRAP_STATUS = "bootstrap_last_status"
    private const val KEY_PAIRED_TRUST     = "paired_trust_confirmed"

    private const val CONNECT_NSD_WAIT_MS = 20_000L
    private const val SERVER_WAIT_MS      = 10_000L

    // ─── Public state ─────────────────────────────────────────────────────

    enum class State {
        NOT_PAIRED, DISCOVERING, PAIRING,
        PAIRED_IDLE, BOOTSTRAPPING, CONNECTING,
        PRIME_MODE_ACTIVE, ERROR
    }

    data class SetupSnapshot(
        val pairedTrusted: Boolean = false,
        val bootstrapped: Boolean = false,
        val primeServerAlive: Boolean = false,
        val bootstrapStatus: String = "Not set up"
    )

    private val _state               = MutableStateFlow(State.NOT_PAIRED)
    private val _status              = MutableStateFlow("Ready")
    private val _wirelessDebugOn     = MutableStateFlow(false)
    private val _setupSnapshot       = MutableStateFlow(SetupSnapshot())

    val state:               StateFlow<State>    = _state.asStateFlow()
    val status:              StateFlow<String>   = _status.asStateFlow()
    val wirelessDebugOn:     StateFlow<Boolean>  = _wirelessDebugOn.asStateFlow()
    /** null=hidden  false=orange(no wifi)  true=green(tap to retry) */
    val setupSnapshot:       StateFlow<SetupSnapshot> = _setupSnapshot.asStateFlow()

    // ─── Internal ─────────────────────────────────────────────────────────

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private lateinit var appContext: Context

    private var nsdWatcher: AdbNsdWatcher? = null

    @Volatile private var pairingHost: String? = null
    @Volatile private var pairingPort: Int     = 0
    @Volatile private var connectHost: String? = null
    @Volatile private var connectPort: Int     = 0   // set by NSD watcher, consumed by findAdbPort()

    @Volatile private var keepGameWasActive = false
    @Volatile private var keepGameOriginalBucket: String? = null

    // Prevents double-execution when VPN restarts or Prime Mode is toggled rapidly
    private val activeCommands = mutableSetOf<String>()

    // FIX-A/C: True while runGodModeSequence() is executing.
    // Prevents stopWatching() from resetting state to PAIRED_IDLE mid-sequence,
    // and prevents redundant activation calls from slipping through the guard.
    @Volatile private var sequenceRunning = false


    private data class PrimeShellResult(
        val output: String,
        val exitCode: Int,
        val ok: Boolean
    )

    private val primeExitMarker = "__PEERLINK_EXIT__="

    // ─── Lifecycle ────────────────────────────────────────────────────────

    fun init(context: Context) {
        appContext = context.applicationContext
        PrimeClient.configure(PrimeAuth.getOrCreate(appContext))
        val bootstrapped = isBootstrapped()
        val pairedTrusted = isPairingTrusted()
        updateSetupSnapshot()
        _state.value = when {
            bootstrapped || pairedTrusted -> State.PAIRED_IDLE
            else -> State.NOT_PAIRED
        }
        _status.value = when {
            bootstrapped -> "Prime Mode ready"
            pairedTrusted -> "Paired — bootstrap pending"
            else -> "Not paired"
        }
        AppState.appendLog("[PRIME-MODE ] init (bootstrapped=$bootstrapped pairedTrusted=$pairedTrusted keepGame=${getKeepGameInRam()})")
    }

    fun refreshSetupState(checkServer: Boolean = true) {
        if (!::appContext.isInitialized) return
        updateSetupSnapshot()
        syncIdleStateFromSetup()

        if (!checkServer) return
        scope.launch {
            val alive = PrimeClient.isAlive(timeoutMs = 350)
            AppState.primeServerAlive = alive
            updateSetupSnapshot(primeServerAlive = alive)
            syncIdleStateFromSetup()
        }
    }

    /**
     * Start NSD watcher. Idempotent.
     * Caches connectPort whenever adbd advertises _adb-tls-connect._tcp.
     * Does NOT auto-connect via ADB — port is used by findAdbPort() only.
     */
    fun startWatching() {
        if (nsdWatcher != null) return
        AppState.appendLog("[PRIME-MODE ] NSD watcher starting")
        nsdWatcher = AdbNsdWatcher(appContext).apply {
            onPairingPortFound = { host, port ->
                pairingHost = host; pairingPort = port
                AppState.appendLog("[PRIME-MODE ] Pairing port: $host:$port")
                if (_state.value == State.DISCOVERING)
                    setState(State.DISCOVERING, "Enter the 6-digit code shown in your notification")
            }
            onPairingPortLost = {
                pairingHost = null; pairingPort = 0
                AppState.appendLog("[PRIME-MODE ] Pairing service lost")
            }
            onConnectPortFound = { host, port ->
                connectHost = host; connectPort = port
                _wirelessDebugOn.value = true
                AppState.appendLog("[PRIME-MODE ] Connect port cached: $host:$port")
            }
            onConnectPortLost = {
                connectHost = null; connectPort = 0
                _wirelessDebugOn.value = false
                AppState.appendLog("[PRIME-MODE ] ADB connect service lost")
            }
            start()
        }
    }

    fun stopWatching() {
        nsdWatcher?.stop(); nsdWatcher = null
        // FIX-A: Only reset to PAIRED_IDLE if we are genuinely waiting for NSD
        // (the bootstrap/connect phase). If sequenceRunning=true, the CONNECTING
        // state was set by runGodModeSequence() mid-execution. Resetting it here
        // would tell the UI "tap ACTIVATE again" even though all commands are
        // running fine in the background.
        if (_state.value == State.CONNECTING && !sequenceRunning)
            setState(State.PAIRED_IDLE, "Monitoring stopped")
    }

    // ─── Pref accessors ───────────────────────────────────────────────────

    fun isApexMasterEnabled()     = prefs().getBoolean(KEY_APEX_MASTER,    false)
    fun getKeepGameInRam()        = prefs().getBoolean(KEY_KEEP_GAME,       false)
    fun isAutoConnectEnabled()    = prefs().getBoolean(KEY_AUTO_CONNECT,    true)

    fun setApexMasterEnabled(v: Boolean)     { prefs().edit().putBoolean(KEY_APEX_MASTER,   v).apply(); AppState.appendLog("[PRIME-MODE ] Master → $v") }
    fun setKeepGameInRam(v: Boolean)         { prefs().edit().putBoolean(KEY_KEEP_GAME,     v).apply(); AppState.appendLog("[PRIME-MODE ] keepGameInRam → $v") }
    fun setAutoConnectEnabled(v: Boolean)    { prefs().edit().putBoolean(KEY_AUTO_CONNECT,  v).apply(); AppState.appendLog("[PRIME-MODE ] autoConnect → $v") }

    // ─── Bootstrap state ──────────────────────────────────────────────────

    fun isBootstrapped(): Boolean {
        if (prefs().getBoolean(KEY_BOOTSTRAP_DONE, false)) return true
        return appContext.checkSelfPermission("android.permission.WRITE_SECURE_SETTINGS") ==
                PackageManager.PERMISSION_GRANTED
    }

    fun isPairingTrusted(): Boolean {
        return prefs().getBoolean(KEY_PAIRED_TRUST, false) || AdbKeyManager.isPaired(appContext)
    }

    fun selfEnableAdbd() = isBootstrapped()

    fun getBootstrapStatus(): String =
        prefs().getString(KEY_BOOTSTRAP_STATUS, "Not set up") ?: "Not set up"

    private fun markPairingTrusted() {
        prefs().edit().putBoolean(KEY_PAIRED_TRUST, true).apply()
        AdbKeyManager.markPaired(appContext, true)
        updateSetupSnapshot()
        AppState.appendLog("[PRIME-MODE ] Pairing trust confirmed ✅")
    }

    private fun markBootstrapped() {
        prefs().edit().putBoolean(KEY_BOOTSTRAP_DONE, true).apply()
        saveBootstrapStatus("WRITE_SECURE_SETTINGS granted and verified")
        updateSetupSnapshot(primeServerAlive = true)
        AppState.appendLog("[PRIME-MODE ] Bootstrap confirmed ✅")
    }

    private fun saveBootstrapStatus(s: String) {
        prefs().edit().putString(KEY_BOOTSTRAP_STATUS, s).apply()
        updateSetupSnapshot()
    }

    fun forgetPairing() {
        AdbKeyManager.clearAll(appContext)
        sequenceRunning = false   // FIX-C
        activeCommands.clear()
        pairingHost = null; pairingPort = 0
        connectHost = null; connectPort = 0
        prefs().edit()
            .putBoolean(KEY_BOOTSTRAP_DONE, false)
            .putBoolean(KEY_PAIRED_TRUST, false)
            .apply()
        AppState.primeServerAlive = false
        updateSetupSnapshot(primeServerAlive = false)
        setState(State.NOT_PAIRED, "Pairing forgotten — run setup again")
        AppState.appendLog("[PRIME-MODE ] Pairing forgotten")
    }

    // ─── Setup state helpers ──────────────────────────────────────────────

    private fun updateSetupSnapshot(primeServerAlive: Boolean = AppState.primeServerAlive) {
        _setupSnapshot.value = SetupSnapshot(
            pairedTrusted = isPairingTrusted(),
            bootstrapped = isBootstrapped(),
            primeServerAlive = primeServerAlive,
            bootstrapStatus = getBootstrapStatus()
        )
    }

    private fun isSetupBusyState(state: State = _state.value): Boolean {
        return state == State.DISCOVERING ||
               state == State.PAIRING ||
               state == State.BOOTSTRAPPING ||
               state == State.CONNECTING
    }

    private fun syncIdleStateFromSetup() {
        if (isSetupBusyState() || _state.value == State.PRIME_MODE_ACTIVE) return

        val snapshot = _setupSnapshot.value
        when {
            snapshot.bootstrapped -> {
                if (_state.value != State.PAIRED_IDLE) {
                    setState(State.PAIRED_IDLE, "Prime Mode ready")
                } else {
                    _status.value = "Prime Mode ready"
                }
            }
            snapshot.pairedTrusted -> {
                if (_state.value != State.PAIRED_IDLE) {
                    setState(State.PAIRED_IDLE, "Paired — bootstrap pending")
                } else {
                    _status.value = "Paired — bootstrap pending"
                }
            }
            _state.value != State.NOT_PAIRED && _state.value != State.ERROR -> setState(State.NOT_PAIRED, "Not paired")
        }
    }

    // ─── Activate ─────────────────────────────────────────────────────────

    /**
     * Main entry point.
     *
     * PrimeServer alive  → runGodModeSequence() via PrimeClient. No ADB. No WiFi.
     * PrimeServer dead   → launchPrimeServer() [requires wlan0] → runGodModeSequence().
     */
    fun activateGodMode() {
        if (!isPairingTrusted()) {
            setState(State.ERROR, "Prime Mode not paired — run setup first")
            AppState.appendLog("[PRIME-MODE ] activateGodMode: not paired")
            return
        }
        // FIX-B: Include PRIME_MODE_ACTIVE in the guard. Without it, tapping ACTIVATE
        // while commands are already done would run the full sequence again — wasting
        // resources and producing the triple-activation seen in logs (three runs 10s apart).
        // Also block if sequenceRunning to handle the brief PAIRED_IDLE window at startup.
        if (_state.value == State.BOOTSTRAPPING ||
            _state.value == State.CONNECTING ||
            _state.value == State.PRIME_MODE_ACTIVE ||
            sequenceRunning) return

        scope.launch {
            try {
                if (PrimeClient.isAlive()) {
                    AppState.appendLog("[PRIME-MODE ] PrimeServer alive — running commands directly")
                    runGodModeSequence()
                } else {
                    val needBootstrap = !isBootstrapped()
                    AppState.appendLog("[PRIME-MODE ] PrimeServer dead — launching (needBootstrap=$needBootstrap)")
                    if (ensurePrimeServerAlive(needBootstrap)) {
                        runGodModeSequence()
                    }
                }
            } catch (e: Exception) {
                AppState.appendLog("[PRIME-MODE ] activateGodMode EXCEPTION: ${e.message}")
                setState(State.ERROR, e.message ?: "Activation failed")
            }
        }
    }

    fun onVpnStopped() {
        if (_state.value == State.PAIRED_IDLE || _state.value == State.NOT_PAIRED) return
        AppState.appendLog("[PRIME-MODE ] VPN stopped — reversing optimizations")
        deactivateGodMode()
    }

    fun deactivateGodMode() {
        sequenceRunning = false
        activeCommands.clear()
        scope.launch {
            if (keepGameWasActive) {
                keepGameOriginalBucket?.let { bucket ->
                    val result = executePrimeShellChecked("am set-standby-bucket $EFOOTBALL_PKG $bucket")
                    AppState.appendLog(if (result.ok)
                        "[PRIME-MODE ] eFootball standby bucket restored to $bucket ✓"
                    else "[PRIME-MODE ] Standby bucket restore failed: ${result.output.take(80)}")
                }
            }
            keepGameWasActive = false
            keepGameOriginalBucket = null
            setState(State.PAIRED_IDLE, "Prime Mode deactivated")
            AppState.isGodModeActive.set(false)
            startWatching()
            AppState.appendLog("[PRIME-MODE ] Prime session state restored; ADB discovery resumed")
        }
    }

    // ─── Launch PrimeServer via ADB (once per reboot) ─────────────────────

    /**
     * Connects to adbd and runs app_process to start PrimeServer in background.
     * Returns true once PrimeServer is confirmed alive. Does NOT run any session
     * commands — callers decide what to do next.
     */
    private suspend fun ensurePrimeServerAlive(needBootstrap: Boolean): Boolean {
        setState(if (needBootstrap) State.BOOTSTRAPPING else State.CONNECTING,
            if (needBootstrap) "Completing one-time Prime setup…" else "Restoring Prime Mode connection…")
        AppState.appendLog("[PRIME-MODE ] ensurePrimeServerAlive: starting (needBootstrap=$needBootstrap)")

        val result = PrimeShizukuBootstrapEngine(appContext).start(needBootstrap)
        when (result) {
            is PrimeShizukuBootstrapEngine.Result.Failure -> {
                AppState.appendLog("[PRIME-MODE ] Bootstrap FAILED: ${result.reason}${result.throwable?.let { " — ${it.message}" } ?: ""}")
                saveBootstrapStatus("PENDING: ${result.reason}")
                updateSetupSnapshot(primeServerAlive = false)
                setState(State.PAIRED_IDLE, "Paired — bootstrap pending, keep Wireless Debugging ON and tap ACTIVATE")
                return false
            }
            is PrimeShizukuBootstrapEngine.Result.Success -> {
                AppState.appendLog("[PRIME-MODE ] Shizuku-style start sent via 127.0.0.1:${result.port}")
                if (needBootstrap) {
                    try {
                        Settings.Global.putInt(appContext.contentResolver, "prime_mode_active", 1)
                        AppState.appendLog("[PRIME-MODE ] Canary write OK ✅")
                    } catch (e: SecurityException) {
                        AppState.appendLog("[PRIME-MODE ] Canary SecurityException — pm grant did not take: ${e.message}")
                        saveBootstrapStatus("FAILED: pm grant did not take effect")
                        updateSetupSnapshot(primeServerAlive = false)
                        setState(State.PAIRED_IDLE, "Paired — permission grant failed. Check device steps and re-pair.")
                        return false
                    }
                }
            }
        }

        val deadline = System.currentTimeMillis() + SERVER_WAIT_MS
        while (System.currentTimeMillis() < deadline) {
            if (PrimeClient.isAlive()) {
                AppState.appendLog("[PRIME-MODE ] PrimeServer alive ✅")
                AppState.primeServerAlive = true
                if (needBootstrap) markBootstrapped()
                saveBootstrapStatus(if (needBootstrap) "COMPLETE — PrimeServer launched" else "RECOVERY — PrimeServer launched")
                return true
            }
            delay(300L)
        }

        AppState.appendLog("[PRIME-MODE ] PrimeServer did not bind in ${SERVER_WAIT_MS / 1000}s")
        AppState.primeServerAlive = false
        updateSetupSnapshot(primeServerAlive = false)
        setState(State.ERROR, "Prime Server failed to start")
        return false
    }

    private fun executePrimeShellChecked(command: String, timeoutMs: Int = PrimeClient.CMD_TIMEOUT_MS): PrimeShellResult {
        val wrapped = "( $command ); __pl_rc=\$?; printf '\\n${primeExitMarker}%s\\n' \"${'$'}__pl_rc\""
        val raw = PrimeClient.execute(wrapped, timeoutMs)
            ?: return PrimeShellResult("", -1, false)
        val idx = raw.lastIndexOf(primeExitMarker)
        if (idx < 0) return PrimeShellResult(raw.trim(), -1, false)

        val output = raw.substring(0, idx).trim()
        val exitRaw = raw.substring(idx + primeExitMarker.length).trim()
        val exit = exitRaw.lineSequence().firstOrNull()?.trim()?.toIntOrNull() ?: -1
        return PrimeShellResult(output, exit, exit == 0)
    }

    // ─── Radio management ─────────────────────────────────────────────────


    fun enableRadiosForSession() {
        if (!isApexMasterEnabled() || !isAutoConnectEnabled() || !PrimeClient.isAlive()) return
        scope.launch {
            try {
                val wm = appContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager ?: return@launch
                if (!wm.isWifiEnabled) {
                    val result = executePrimeShellChecked("svc wifi enable")
                    val deadline = System.currentTimeMillis() + 4_000L
                    while (!wm.isWifiEnabled && System.currentTimeMillis() < deadline) delay(150L)
                    if (result.ok && wm.isWifiEnabled) {
                        // Record restoration responsibility only after the command
                        // demonstrably changed the radio from the user's prior OFF state.
                        prefs().edit().putBoolean(KEY_WIFI_WAS_OFF, true).apply()
                        AppState.appendLog("[PRIME-MODE ] Auto-connect: Wi-Fi enabled ✓")
                    } else {
                        AppState.appendLog("[PRIME-MODE ] Auto-connect Wi-Fi enable failed/was ignored (exit=${result.exitCode})")
                    }
                }
            } catch (e: Exception) {
                AppState.appendLog("[PRIME-MODE ] enableRadiosForSession: ${e.message}")
            }
        }
    }

    fun restoreRadiosIfNeeded(context: Context) {
        val p = prefs()
        val wifiWasOff = p.getBoolean(KEY_WIFI_WAS_OFF, false)
        if (!wifiWasOff) return
        if (!PrimeClient.isAlive()) {
            AppState.appendLog("[PRIME-MODE ] Wi-Fi restore pending — PrimeServer unavailable")
            return
        }
        scope.launch {
            try {
                val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
                val result = executePrimeShellChecked("svc wifi disable")
                val deadline = System.currentTimeMillis() + 4_000L
                while (wm?.isWifiEnabled == true && System.currentTimeMillis() < deadline) delay(150L)
                if (result.ok && wm?.isWifiEnabled != true) {
                    p.edit().putBoolean(KEY_WIFI_WAS_OFF, false).apply()
                    AppState.appendLog("[PRIME-MODE ] Wi-Fi restored to off ✓")
                } else {
                    // Keep the flag so a later clean lifecycle opportunity can retry.
                    AppState.appendLog("[PRIME-MODE ] Wi-Fi restore failed/was ignored (exit=${result.exitCode}); will retry later")
                }
            } catch (e: Exception) {
                AppState.appendLog("[PRIME-MODE ] Wi-Fi restore failed: ${e.message}")
            }
        }
    }
/**
     * Best-effort native-thread promotion. A normal Wireless-Debugging Prime
     * server runs as the ADB shell uid, not root, so it must not assume it can
     * assign SCHED_FIFO. We only attempt `chrt` when `id -u` proves uid 0;
     * otherwise the native loops keep their app-permitted urgent priority.
     */
    fun promoteHotThreads(tidsProvider: () -> IntArray) {
        if (!isApexMasterEnabled() || !PrimeClient.isAlive()) {
            AppState.appendLog("[PRIME-RT  ] Prime inactive — using app-owned thread priority only")
            return
        }
        scope.launch {
            // Shizuku started through wireless debugging normally runs as UID 2000
            // (shell), not root. Do not claim CAP_SYS_NICE or repeatedly issue chrt
            // commands that stock Android will reject. Native threads already set
            // their own permitted urgent-audio priority.
            val uid = executePrimeShellChecked("id -u").output.trim()
            if (uid != "0") {
                AppState.appendLog("[PRIME-RT  ] SCHED_FIFO skipped (Prime uid=$uid, root required); using native app priority")
                return@launch
            }
            var tids = IntArray(0)
            val deadline = System.currentTimeMillis() + 3000L
            while (System.currentTimeMillis() < deadline) {
                tids = runCatching { tidsProvider() }.getOrDefault(IntArray(0))
                if (tids.size >= 3) break
                delay(150L)
            }
            var promoted = 0
            for (tid in tids) {
                if (tid <= 0) continue
                val r = executePrimeShellChecked("chrt -f -p 10 $tid")
                if (r.ok) promoted++ else AppState.appendLog("[PRIME-RT  ] chrt tid=$tid failed: ${r.output.take(80)}")
            }
            AppState.appendLog("[PRIME-RT  ] Root SCHED_FIFO applied to $promoted/${tids.size} hot thread(s)")
        }
    }

    // ─── Pairing flow ─────────────────────────────────────────────────────

    fun startNotificationPairing(context: Context) {
        setState(State.DISCOVERING, "Check notification shade — enter the 6-digit code")
        AppState.appendLog("[PRIME-MODE ] Starting notification pairing service")
        GodModePairingService.start(context)
    }

    fun onNsdPairingTimeout() {
        if (_state.value == State.DISCOVERING) {
            setState(State.NOT_PAIRED, "Timed out — tap Re-send to try again")
            AppState.appendLog("[PRIME-MODE ] NSD timeout — NOT_PAIRED")
        }
    }

    fun beginPairingDiscovery() {
        setState(State.DISCOVERING, "Waiting for Wireless Debugging service")
        startWatching()
    }

    fun onPairingPortDiscovered(host: String, port: Int) {
        pairingHost = host; pairingPort = port
        AppState.appendLog("[PRIME-MODE ] Pairing endpoint cached: $host:$port")
    }

    /**
     * First-time setup. Called by GodModePairingService when user submits PIN.
     *
     * pair → find connect port → connect → pm grant WRITE_SECURE_SETTINGS →
     * canary write → markBootstrapped → adb_wifi_enabled=1 →
     * app_process PrimeServer & → wait isAlive → runGodModeSequence
     */
    fun submitPairingPin(
        pin: String,
        manualHost: String = "",
        manualPort: Int = 0,
        onResult: (success: Boolean, message: String) -> Unit
    ) {
        val port = when {
            manualPort > 0 -> manualPort
            pairingPort > 0 -> pairingPort
            else -> {
                onResult(false, "Pairing port unknown. Enter PORT:CODE (e.g. 45678:123456).")
                return
            }
        }
        val hostsToTry = buildList {
            add("127.0.0.1")
            val alt = manualHost.ifBlank { pairingHost }
            if (alt != null && alt != "127.0.0.1") add(alt)
        }

        setState(State.PAIRING, "Connecting to ADB daemon")
        startWatching()
        AppState.appendLog("[PRIME-MODE ] Pairing port=$port hosts=$hostsToTry")

        scope.launch {
            var lastFail = "All hosts failed"
            for (host in hostsToTry) {
                AppState.appendLog("[PRIME-MODE ] Trying $host:$port")
                when (val result = AdbPairingClient(appContext).pair(host, port, pin)) {
                    is AdbPairingClient.Result.Success -> {
                        AppState.appendLog("[PRIME-MODE ] Paired via $host ✅")
                        pairingHost = null
                        pairingPort = 0
                        markPairingTrusted()
                        saveBootstrapStatus("PENDING: paired, waiting for explicit ACTIVATE/start")
                        setState(State.PAIRED_IDLE, "Paired — bootstrap pending, keep Wireless Debugging ON and tap ACTIVATE")
                        onResult(true, "Paired successfully. Keep Wireless Debugging ON and tap ACTIVATE in LanLink.")
                        return@launch
                    }
                    is AdbPairingClient.Result.Failure -> {
                        lastFail = result.reason
                        AppState.appendLog("[PRIME-MODE ] $host failed: ${result.reason}")
                    }
                }
            }
            setState(State.NOT_PAIRED, "Pairing failed: $lastFail")
            updateSetupSnapshot(primeServerAlive = false)
            onResult(false, lastFail)
        }
    }

    // ─── runGodModeSequence — all via PrimeClient ─────────────────────────

    /**
     * Runs all optimisation commands through PrimeClient → TCP loopback → PrimeServer → shell.
     * Zero ADB. Zero WiFi needed. Works completely offline once PrimeServer is running.
     * Each command is verified with a follow-up read for [OK]/[WARN] logging.
     */
    private suspend fun runGodModeSequence() {
        sequenceRunning = true
        setState(State.CONNECTING, "Preparing Prime Mode…")
        try {
            // Keep Prime deliberately small. PeerLink's supported Android APIs
            // (foreground VpnService, PARTIAL_WAKE_LOCK and LOW_LATENCY WifiLock)
            // own the actual latency policy. We do not mutate global Wi-Fi scan,
            // sleep, captive-portal or airplane-mode settings behind the user.

            val keepGame = getKeepGameInRam()
            keepGameWasActive = keepGame
            if (keepGame) {
                val before = executePrimeShellChecked("am get-standby-bucket $EFOOTBALL_PKG").output.trim()
                keepGameOriginalBucket = when (before.lineSequence().lastOrNull()?.trim()) {
                    "10" -> "active"
                    "20" -> "working_set"
                    "30" -> "frequent"
                    "40" -> "rare"
                    "45" -> "restricted"
                    else -> null
                }
                runAndLog(
                    "am set-standby-bucket $EFOOTBALL_PKG active",
                    "Keep eFootball active", "bucket_efootball",
                    verify = "am get-standby-bucket $EFOOTBALL_PKG", expectation = "10"
                )
            }

            setState(State.PRIME_MODE_ACTIVE, "Prime Mode active${if (keepGame) " · Game active" else ""}")
            AppState.isGodModeActive.set(true)
            // PrimeServer is already on loopback; ADB mDNS discovery is no longer needed
            // during gameplay. Release its MulticastLock and discovery listeners so the
            // control plane stays quiet while the latency-sensitive tunnel is active.
            stopWatching()
            AppState.appendLog("[PRIME-MODE ] Prime Mode ready — ADB discovery paused during session")
        } finally {
            sequenceRunning = false
        }
    }

    private suspend fun runAndLog(
        cmd:         String,
        label:       String,
        key:         String,
        verify:      String? = null,
        expectation: String? = null
    ) {
        if (activeCommands.contains(key)) {
            AppState.appendLog("[PRIME] $label — already active, skipping")
            return
        }
        val ts = java.text.SimpleDateFormat("HH:mm:ss", java.util.Locale.US).format(java.util.Date())
        val result = executePrimeShellChecked(cmd)
        if (!result.ok) {
            AppState.appendLog("[PRIME] [$ts] [FAIL] $label → exit=${result.exitCode} ${result.output.take(80)}")
            return
        }

        if (verify != null && expectation != null) {
            val verifyResult = executePrimeShellChecked(verify)
            val ok = verifyResult.ok && verifyResult.output.contains(expectation, ignoreCase = true)
            AppState.appendLog("[PRIME] [$ts] ${if (ok) "[OK] " else "[WARN]"} $label → ${verifyResult.output.take(80)}")
            if (ok) activeCommands.add(key)
        } else {
            AppState.appendLog("[PRIME] [$ts] [OK]  $label")
            activeCommands.add(key)
        }
    }

    // ─── Misc helpers ─────────────────────────────────────────────────────

    fun openWirelessDebuggingSettings(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            try {
                context.startActivity(
                    Intent(Settings.ACTION_APPLICATION_DEVELOPMENT_SETTINGS)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            } catch (_: Exception) {
                context.startActivity(
                    Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            }
        }
    }

    fun isSupported() = Build.VERSION.SDK_INT >= Build.VERSION_CODES.R

    val isPairingPortReady: Boolean get() = pairingPort > 0

    private fun setState(s: State, msg: String = "") {
        _state.value = s; _status.value = msg
        if (msg.isNotBlank()) AppState.appendLog("[PRIME-MODE ] $s — $msg")
        else                  AppState.appendLog("[PRIME-MODE ] $s")
    }

    private fun prefs(): android.content.SharedPreferences {
        if (!::appContext.isInitialized) {
            val app = try {
                val cls = Class.forName("android.app.ActivityThread")
                val method = cls.getMethod("currentApplication")
                method.invoke(null) as? android.app.Application
            } catch (_: Throwable) {
                null
            }
            if (app != null) {
                appContext = app.applicationContext
            } else {
                throw IllegalStateException("GodModeManager appContext unavailable")
            }
        }
        return appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    }
}
