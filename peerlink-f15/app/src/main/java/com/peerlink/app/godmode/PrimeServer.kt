package com.peerlink.app.godmode

import androidx.annotation.Keep
import org.json.JSONObject
import java.io.BufferedReader
import java.io.IOException
import java.io.InputStreamReader
import java.io.PrintWriter
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.security.MessageDigest
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * PrimeServer — long-lived loopback shell server launched with app_process.
 */
@Keep
object PrimeServer {

    const val HOST = "127.0.0.1"
    const val PORT = 13373
    const val PROCESS_NAME = "peerlink_prime"
    const val LOG_PATH = "/data/local/tmp/peerlink_prime.log"

    private const val MAX_BACKLOG = 8
    private const val CONN_TIMEOUT_MS = 30_000
    private const val CMD_TIMEOUT_SEC = 10
    private const val HEALTH_CMD = "__health__"


    fun runForever(authToken: String) {
        require(authToken.length >= 64) { "PrimeServer auth token missing" }
        setProcessName(PROCESS_NAME)
        log("PrimeServer starting on $HOST:$PORT")

        val server = try {
            ServerSocket(PORT, MAX_BACKLOG, InetAddress.getByName(HOST))
        } catch (e: Exception) {
            log("FATAL: cannot bind port $PORT — ${e.message}")
            System.exit(1)
            return
        }

        // The VPN service itself owns the supported WIFI_MODE_FULL_LOW_LATENCY
        // lock. PrimeServer is intentionally only a small authenticated shell
        // command broker; it must not mutate radio state behind the app lifecycle.
        Runtime.getRuntime().addShutdownHook(Thread {
            log("Shutdown hook — closing server")
            try { server.close() } catch (_: Exception) {}
        })

        log("PrimeServer listening (PID=${android.os.Process.myPid()})")

        while (!server.isClosed) {
            try {
                val client = server.accept()
                Thread { handleClient(client, authToken) }.apply {
                    isDaemon = true
                    name = "prime_worker"
                    start()
                }
            } catch (e: Exception) {
                if (!server.isClosed) {
                    log("Accept error: ${e.message}")
                    Thread.sleep(100)
                }
            }
        }
    }

    @JvmStatic
    fun main(args: Array<String>) {
        val token = args.firstOrNull { it.startsWith("--token=") }?.substringAfter("--token=").orEmpty()
        if (token.length >= 64) runForever(token)
    }

    private fun handleClient(socket: Socket, authToken: String) {
        try {
            socket.soTimeout = CONN_TIMEOUT_MS
            val reader = BufferedReader(InputStreamReader(socket.inputStream, Charsets.UTF_8))
            val writer = PrintWriter(socket.outputStream, true, Charsets.UTF_8)
            val line = reader.readLine()?.trim() ?: return
            if (line.isEmpty()) return

            val req = try { JSONObject(line) } catch (_: Exception) {
                log("Bad JSON: ${line.take(60)}")
                return
            }

            val suppliedToken = req.optString("token", "")
            val authenticated = suppliedToken.length == authToken.length && MessageDigest.isEqual(
                suppliedToken.toByteArray(Charsets.UTF_8),
                authToken.toByteArray(Charsets.UTF_8)
            )
            if (!authenticated) {
                log("Rejected unauthenticated loopback client")
                writer.println(JSONObject().apply { put("output", "unauthorized"); put("ok", false) }.toString())
                return
            }

            val cmd = req.optString("cmd", "").trim()
            if (cmd.isEmpty()) return

            val output = if (cmd == HEALTH_CMD) "prime_ok_v2" else runShell(cmd)
            writer.println(JSONObject().apply {
                put("output", output)
                put("ok", true)
            }.toString())
        } catch (_: IOException) {
        } catch (e: Exception) {
            log("Handler error: ${e.message}")
        } finally {
            try { socket.close() } catch (_: Exception) {}
        }
    }

    private fun runShell(cmd: String): String {
        val process = try {
            ProcessBuilder("sh", "-c", cmd).redirectErrorStream(true).start()
        } catch (e: Exception) {
            return "ERROR: spawn failed — ${e.message}"
        }

        val watchdog = Thread {
            try {
                Thread.sleep(CMD_TIMEOUT_SEC * 1000L)
                process.destroyForcibly()
                log("TIMEOUT killed: $cmd")
            } catch (_: InterruptedException) {}
        }.apply { isDaemon = true; start() }

        val output = try {
            process.inputStream.bufferedReader(Charsets.UTF_8).readText().trim()
        } catch (e: Exception) {
            "ERROR: read failed — ${e.message}"
        } finally {
            watchdog.interrupt()
        }

        process.waitFor()
        return output
    }

    private fun setProcessName(name: String) {
        try {
            android.os.Process::class.java.getMethod("setArgV0", String::class.java).invoke(null, name)
        } catch (_: Exception) {}
        Thread.currentThread().name = name
    }

    private val fmt = SimpleDateFormat("HH:mm:ss.SSS", Locale.US)
    private fun log(msg: String) = println("[${fmt.format(Date())}][PrimeServer] $msg")
}
