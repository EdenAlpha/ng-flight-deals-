package com.peerlink.app.godmode.shizuku

import android.Manifest.permission.WRITE_SECURE_SETTINGS
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.provider.Settings
import android.util.Log
import com.peerlink.app.godmode.AdbConnectClient
import com.peerlink.app.godmode.PeerLinkAdbManager
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

// ══════════════════════════════════════════════════════════════════
// TWO PATHS — both must be correct:
//
// needBootstrap=true  (first-time setup, no WRITE_SECURE_SETTINGS yet):
//   NSD find port → ADB connect → pm grant → request wireless debugging →
//   send libpeerlinkstarter.so command → PrimeServer starts
//
// needBootstrap=false (subsequent activations, already bootstrapped):
//   wake adbd via Settings write → NSD find port →
//   ADB connect → send libpeerlinkstarter.so command → PrimeServer starts
//
// ── KEY FIX (Android 14 bootstrap failure) ───────────────────────
// Pairing uses libadb-android (MuntashirAkon) via AdbPairingClient →
// PeerLinkAdbManager. It presents our RSA cert in libadb's TLS format.
//
// Connection and pairing both use libadb-android via AdbConnectClient /
// PeerLinkAdbManager so the TLS stack and certificate format stay consistent
// on Android 14+ devices.
//
// IMPORTANT: PeerLinkAdbManager.resetInstance() MUST be called before
// AdbConnectClient.connect(). After pair(), the manager holds internal
// TLS/stream state from the pairing session. Reusing it for connect()
// silently fails. resetInstance() discards that state cleanly.
//
// ── OTHER FIXES ──────────────────────────────────────────────────
// Bug 3: adb_allowed_connection_time=0L removed. On XOS/Transsion this
//        sets the ADB permission window to 1970 (already expired) →
//        adbd refuses all incoming connections silently.
//
// Bug 4: Added 1.5s wait after writing ADB_WIFI_ENABLED=1. adbd takes
//        ~1-2s to bind its TLS port after the Settings trigger. Without
//        the delay, NSD resolves the service before the port is bound,
//        the port-occupied check fails, the latch never fires → timeout.
// ══════════════════════════════════════════════════════════════════

private const val TAG = "PrimeBootstrapEngine"

class PrimeShizukuBootstrapEngine(private val context: Context) {

    sealed class Result {
        data class Success(val port: Int) : Result()
        data class Failure(val reason: String, val throwable: Throwable? = null) : Result()
    }

    suspend fun start(needBootstrap: Boolean): Result = withContext(Dispatchers.IO) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.R) {
            return@withContext Result.Failure("Wireless debugging start requires Android 11+")
        }

        // ── needBootstrap=false: wake adbd BEFORE NSD ─────────────────────
        // Writing ADB_WIFI_ENABLED=1 triggers adbd to bind its TLS port on
        // the current wlan0 interface. Only then will _adb-tls-connect._tcp
        // be advertised and NSD can find it.
        if (!needBootstrap) {
            val hasPermission = context.checkSelfPermission(WRITE_SECURE_SETTINGS) ==
                    PackageManager.PERMISSION_GRANTED
            if (hasPermission) {
                runCatching {
                    val cr = context.contentResolver
                    // AOSP Wireless Debugging is keyed by ADB_WIFI_ENABLED. Do not
                    // also flip the broader ADB_ENABLED (USB/general debugging) flag.
                    Settings.Global.putInt(cr, "adb_wifi_enabled", 1)
                    // adb_allowed_connection_time intentionally NOT written.
                    // 0L = epoch 1970 = expired on XOS → adbd refuses connections.
                }
                val cr = context.contentResolver
                if (Settings.Global.getInt(cr, "adb_wifi_enabled", 0) != 1) {
                    return@withContext Result.Failure(
                        "adb_wifi_enabled write failed — WRITE_SECURE_SETTINGS may have been revoked"
                    )
                }
                // Wait for adbd to finish binding its TLS port.
                // adbd takes ~1-2s after the Settings write before the port is open.
                Thread.sleep(1500)
            }
            // No permission → adbd may already be running, fall through to NSD
        }

        // ── NSD: find adbd's connect port ──────────────────────────────────
        val foundPort = AtomicInteger(-1)
        val latch = CountDownLatch(1)
        val adbMdns = PrimeShizukuAdbMdns(context, PrimeShizukuAdbMdns.TLS_CONNECT) { port ->
            if (port > 0) {
                foundPort.set(port)
                latch.countDown()
            }
        }

        adbMdns.start()
        try {
            latch.await(20, TimeUnit.SECONDS)
        } finally {
            adbMdns.stop()
        }

        val port = foundPort.get()
        if (port !in 1..65535) {
            return@withContext Result.Failure("NSD connect endpoint not found")
        }

        Log.i(TAG, "adbd connect port found: $port")

        // ── Connect via libadb-android (same stack as pairing) ─────────────
        // Must reset PeerLinkAdbManager before connecting. If pairing just ran,
        // the manager holds stale TLS state from that session which silently
        // breaks the connect call. resetInstance() discards it cleanly.
        var adbClient: AdbConnectClient? = null
        var connected = false
        for (attempt in 1..4) {
            PeerLinkAdbManager.resetInstance(context)
            val candidate = AdbConnectClient(context)
            if (candidate.connect("127.0.0.1", port)) {
                adbClient = candidate
                connected = true
                break
            }
            runCatching { candidate.disconnect() }
            if (attempt < 4) Thread.sleep(500L * attempt)
        }
        if (!connected) {
            return@withContext Result.Failure("ADB connect failed after retries")
        }
        val client = adbClient ?: return@withContext Result.Failure("ADB client unavailable")

        return@withContext try {
            Log.i(TAG, "ADB connected via libadb-android ✅")

            // ── Bootstrap: grant WRITE_SECURE_SETTINGS (first time only) ───
            if (needBootstrap) {
                val pkg = context.packageName
                val grantOut = client.shell("pm grant $pkg android.permission.WRITE_SECURE_SETTINGS")
                Log.d(TAG, "pm grant output: '$grantOut'")

                if (context.checkSelfPermission(WRITE_SECURE_SETTINGS) !=
                        PackageManager.PERMISSION_GRANTED) {
                    client.disconnect()
                    return@withContext Result.Failure("pm grant did not take effect")
                }

                // Request Wireless Debugging to remain enabled after bootstrap.
                // adb_allowed_connection_time NOT written — on XOS this expires
                // the session immediately when written inside an active connection.
                runCatching {
                    val cr = context.contentResolver
                    // AOSP Wireless Debugging is keyed by ADB_WIFI_ENABLED. Do not
                    // also flip the broader ADB_ENABLED (USB/general debugging) flag.
                    Settings.Global.putInt(cr, "adb_wifi_enabled", 1)
                }
            }

            // ── Launch PrimeServer via libpeerlinkstarter.so ───────────────
            // Mirrors Shizuku's Starter.internalCommand exactly.
            // The .so does: fork() → setsid() → execvp(app_process)
            // setsid() puts PrimeServer in a new session, immune to SIGHUP
            // when the ADB shell closes. PrimeServer survives permanently.
            val launchCmd = PrimeShizukuStarter.internalCommand(context)
            Log.i(TAG, "Launching PrimeServer: $launchCmd")
            client.shell(launchCmd)

            client.disconnect()
            Result.Success(port)

        } catch (t: Throwable) {
            Log.e(TAG, "ADB operation failed: ${t.message}", t)
            try { client.disconnect() } catch (_: Exception) {}
            Result.Failure("ADB start failed: ${t.message}", t)
        }
    }
}
