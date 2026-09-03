package com.peerlink.app.godmode

import android.content.Context
import android.util.Log
import io.github.muntashirakon.adb.AdbStream

/**
 * AdbConnectClient — thin wrapper around libadb-android's connection API.
 *
 * Replaces the hand-rolled ADB message protocol (24-byte headers, CRC32,
 * CMD_CNXN/CMD_OPEN/CMD_WRTE/CMD_OKAY) with libadb-android's proven engine.
 *
 * libadb-android handles:
 *   - mTLS connection to adbd (presents our RSA-2048 cert via PeerLinkAdbManager)
 *   - ADB CONNECT handshake
 *   - Stream multiplexing (OPEN/OKAY/WRTE/CLSE)
 *   - Shell service via openStream("shell:cmd")
 */
class AdbConnectClient(private val context: Context) {

    companion object {
        private const val TAG = "AdbConnectClient"
    }

    private var stream: AdbStream? = null

    /**
     * Connects to adbd at host:port via mTLS.
     * Returns true on success. Call from a background thread.
     */
    fun connect(host: String, port: Int): Boolean {
        return try {
            Log.i(TAG, "Connecting to ADB daemon at $host:$port …")
            val manager = PeerLinkAdbManager.getInstance(context)
            manager.connect(host, port)
            Log.i(TAG, "✅ ADB connected via libadb-android")
            true
        } catch (e: Exception) {
            Log.e(TAG, "ADB connect failed: ${e.message}", e)
            false
        }
    }

    /**
     * Runs a shell command and returns its output, or null on error.
     * libadb opens a new stream for each command (stateless shell).
     */
    fun shell(command: String): String? {
        return try {
            val manager = PeerLinkAdbManager.getInstance(context)
            val s = manager.openStream("shell:$command")
            stream = s
            val output = s.openInputStream().bufferedReader().readText().trim()
            s.close()
            Log.d(TAG, "shell('$command') → ${output.take(80)}")
            output
        } catch (e: Exception) {
            Log.e(TAG, "shell('$command') error: ${e.message}", e)
            null
        }
    }

    /**
     * Sends the ADB tcpip service command — restarts adbd listening on the given
     * port across ALL interfaces including loopback (127.0.0.1).
     *
     * This is NOT a shell command. It opens a dedicated ADB service stream
     * "tcpip:<port>" which tells adbd to switch to TCP mode permanently until
     * the next reboot. After this call succeeds:
     *   - No BSSID authorization check — works on any network
     *   - Works over a reachable Wi-Fi/LAN path
     *   - Works as Group Owner (binds to loopback, no STA interface needed)
     *   - Works on XOS/Transsion — no adb_wifi_enabled=1 required
     *
     * Returns true if adbd acknowledged the switch.
     */
    fun tcpip(port: Int): Boolean {
        return try {
            val manager = PeerLinkAdbManager.getInstance(context)
            val s = manager.openStream("tcpip:$port")
            val response = s.openInputStream().bufferedReader().readText().trim()
            s.close()
            val success = response.contains("restarting", ignoreCase = true) ||
                          response.contains("already", ignoreCase = true) ||
                          response.isBlank() // some adbd versions send no response on success
            Log.i(TAG, "tcpip($port) → '$response' success=$success")
            success
        } catch (e: Exception) {
            Log.e(TAG, "tcpip($port) failed: ${e.message}", e)
            false
        }
    }

    /** Closes the ADB connection. */
    fun disconnect() {
        try {
            stream?.close()
            val manager = PeerLinkAdbManager.getInstance(context)
            manager.disconnect()
        } catch (_: Exception) {}
        stream = null
        Log.d(TAG, "ADB disconnected")
    }

    val isConnected: Boolean
        get() = try {
            PeerLinkAdbManager.getInstance(context).isConnected
        } catch (_: Exception) { false }
}
