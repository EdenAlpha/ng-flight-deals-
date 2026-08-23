package com.peerlink.app.godmode

import com.peerlink.app.core.AppState
import org.json.JSONObject
import java.net.InetSocketAddress
import java.net.Socket

/** App-side client for PrimeServer. */
object PrimeClient {

    const val HOST = PrimeServer.HOST
    const val PORT = PrimeServer.PORT
    const val PING_TIMEOUT_MS = 500
    const val CMD_TIMEOUT_MS = 8_000

    @Volatile private var authToken: String = ""

    fun configure(token: String) { authToken = token }

    private fun request(command: String): String = JSONObject().apply {
        put("token", authToken)
        put("cmd", command)
    }.toString() + "\n"

    fun isAlive(timeoutMs: Int = PING_TIMEOUT_MS): Boolean {
        return try {
            Socket().use { s ->
                s.soTimeout = timeoutMs
                s.connect(InetSocketAddress(HOST, PORT), timeoutMs)
                if (authToken.isBlank()) return false
                val req = request("__health__")
                s.getOutputStream().write(req.toByteArray(Charsets.UTF_8))
                s.getOutputStream().flush()
                val line = s.getInputStream().bufferedReader().readLine() ?: return false
                JSONObject(line).optString("output", "") == "prime_ok_v2"
            }
        } catch (_: Exception) { false }
    }

    fun execute(command: String, timeoutMs: Int = CMD_TIMEOUT_MS): String? {
        return try {
            Socket().use { s ->
                s.soTimeout = timeoutMs
                s.connect(InetSocketAddress(HOST, PORT), 2_000)
                if (authToken.isBlank()) return null
                val req = request(command)
                s.getOutputStream().write(req.toByteArray(Charsets.UTF_8))
                s.getOutputStream().flush()
                val line = s.getInputStream().bufferedReader().readLine() ?: return null
                val out = JSONObject(line).optString("output", "")
                AppState.appendLog("[PRIME-CLIENT] ${command.take(60)} → ${out.take(60)}")
                out
            }
        } catch (e: Exception) {
            AppState.appendLog("[PRIME-CLIENT] execute FAILED: ${e.message}")
            null
        }
    }

}
