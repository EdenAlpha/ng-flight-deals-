package com.peerlink.app.godmode

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.util.Log
import java.io.IOException
import java.net.InetSocketAddress
import java.net.NetworkInterface
import java.net.ServerSocket
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Shizuku-style NSD watcher.
 *
 * A resolved ADB service is trusted only when BOTH are true:
 *   1. resolved host belongs to one of this device's local interfaces
 *   2. the same port is already occupied on 127.0.0.1
 *
 * After validation, callers should always connect to 127.0.0.1:port.
 */
class AdbNsdWatcher(private val context: Context) {

    companion object {
        private const val TAG = "AdbNsdWatcher"
        const val TYPE_PAIR = "_adb-tls-pairing._tcp"
        const val TYPE_CONNECT = "_adb-tls-connect._tcp"
    }

    var onPairingPortFound: ((host: String, port: Int) -> Unit)? = null
    var onPairingPortLost: (() -> Unit)? = null
    var onConnectPortFound: ((host: String, port: Int) -> Unit)? = null
    var onConnectPortLost: (() -> Unit)? = null

    private val nsdManager: NsdManager? = context.getSystemService(Context.NSD_SERVICE) as? NsdManager
    private val resolverExecutor = Executors.newSingleThreadExecutor()
    private val resolvingPair = AtomicBoolean(false)
    private val resolvingConnect = AtomicBoolean(false)

    private var multicastLock: WifiManager.MulticastLock? = null
    private var pairListener: NsdManager.DiscoveryListener? = null
    private var connectListener: NsdManager.DiscoveryListener? = null

    @Volatile private var pairServiceName: String? = null
    @Volatile private var connectServiceName: String? = null

    fun start() {
        startPairingDiscovery()
        startConnectDiscovery()
    }

    fun startPairingDiscovery() {
        if (pairListener != null) return
        acquireMulticastLock()
        if (nsdManager == null) {
            Log.e(TAG, "NsdManager unavailable")
            return
        }
        pairListener = makeDiscoveryListener(
            TYPE_PAIR,
            resolvingPair,
            onValidated = { serviceName, port ->
                pairServiceName = serviceName
                onPairingPortFound?.invoke("127.0.0.1", port)
                Log.i(TAG, "Validated pairing service -> 127.0.0.1:$port")
            },
            onLost = { info ->
                if (info.serviceName == pairServiceName) onPairingPortLost?.invoke()
            }
        )
        safely { nsdManager.discoverServices(TYPE_PAIR, NsdManager.PROTOCOL_DNS_SD, pairListener!!) }
    }

    fun startConnectDiscovery() {
        if (connectListener != null) return
        acquireMulticastLock()
        if (nsdManager == null) {
            Log.e(TAG, "NsdManager unavailable")
            return
        }
        connectListener = makeDiscoveryListener(
            TYPE_CONNECT,
            resolvingConnect,
            onValidated = { serviceName, port ->
                connectServiceName = serviceName
                onConnectPortFound?.invoke("127.0.0.1", port)
                Log.i(TAG, "Validated connect service -> 127.0.0.1:$port")
            },
            onLost = { info ->
                if (info.serviceName == connectServiceName) onConnectPortLost?.invoke()
            }
        )
        safely { nsdManager.discoverServices(TYPE_CONNECT, NsdManager.PROTOCOL_DNS_SD, connectListener!!) }
    }

    fun stopPairingDiscovery() {
        pairListener?.let { safely { nsdManager?.stopServiceDiscovery(it) } }
        pairListener = null
        maybeReleaseMulticastLock()
    }

    fun stopConnectDiscovery() {
        connectListener?.let { safely { nsdManager?.stopServiceDiscovery(it) } }
        connectListener = null
        maybeReleaseMulticastLock()
    }

    fun stop() {
        stopPairingDiscovery()
        stopConnectDiscovery()
    }

    private fun acquireMulticastLock() {
        if (multicastLock != null) return
        val wm = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        multicastLock = wm?.createMulticastLock("PeerLinkAdbNsd").apply {
            this?.setReferenceCounted(false)
            try { this?.acquire() } catch (_: Exception) {}
        }
    }

    private fun maybeReleaseMulticastLock() {
        if (pairListener != null || connectListener != null) return
        try { multicastLock?.release() } catch (_: Exception) {}
        multicastLock = null
    }

    private fun makeDiscoveryListener(
        type: String,
        resolving: AtomicBoolean,
        onValidated: (serviceName: String, port: Int) -> Unit,
        onLost: (NsdServiceInfo) -> Unit
    ) = object : NsdManager.DiscoveryListener {
        override fun onDiscoveryStarted(regType: String) { Log.d(TAG, "Started: $regType") }
        override fun onDiscoveryStopped(regType: String) { Log.d(TAG, "Stopped: $regType") }
        override fun onStartDiscoveryFailed(t: String, e: Int) { Log.w(TAG, "Start failed $t: $e") }
        override fun onStopDiscoveryFailed(t: String, e: Int) { Log.w(TAG, "Stop failed $t: $e") }
        override fun onServiceFound(service: NsdServiceInfo) {
            if (!service.serviceType.contains(type.removeSuffix("."))) return
            resolveService(service, resolving, onValidated)
        }
        override fun onServiceLost(service: NsdServiceInfo) {
            if (!service.serviceType.contains(type.removeSuffix("."))) return
            onLost(service)
        }
    }

    private fun resolveService(
        service: NsdServiceInfo,
        resolving: AtomicBoolean,
        onValidated: (serviceName: String, port: Int) -> Unit
    ) {
        if (!resolving.compareAndSet(false, true)) return
        val listener = object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                resolving.set(false)
                Log.w(TAG, "Resolve failed ${serviceInfo.serviceName}: $errorCode")
            }

            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                resolverExecutor.execute {
                    try {
                        val host = serviceInfo.host?.hostAddress ?: return@execute
                        val port = serviceInfo.port
                        if (!isLocalAddress(host)) {
                            Log.d(TAG, "Ignoring non-local NSD host $host:$port")
                            return@execute
                        }

                        if (!waitForLoopbackPort(port)) {
                            // adbd can publish mDNS before the loopback socket is observable.
                            // Trust the local-address validation and let the ADB client perform
                            // the final connect attempt instead of losing the setup event.
                            Log.w(TAG, "Loopback port 127.0.0.1:$port not observable yet — accepting NSD result")
                        }

                        onValidated(serviceInfo.serviceName ?: "", port)
                    } finally {
                        resolving.set(false)
                    }
                }
            }
        }
        safely {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                nsdManager?.resolveService(service, resolverExecutor, listener)
            } else {
                @Suppress("DEPRECATION")
                nsdManager?.resolveService(service, listener)
            }
        }
    }

    private fun isLocalAddress(host: String): Boolean = try {
        NetworkInterface.getNetworkInterfaces().asSequence().any { iface ->
            iface.inetAddresses.asSequence().any { it.hostAddress == host }
        }
    } catch (_: Exception) {
        false
    }

    private fun isLoopbackPortOccupied(port: Int): Boolean = try {
        ServerSocket().use {
            it.bind(InetSocketAddress("127.0.0.1", port), 1)
            false
        }
        } catch (_: IOException) {
        true
    }

    private fun waitForLoopbackPort(port: Int): Boolean {
        if (isLoopbackPortOccupied(port)) return true
        repeat(6) { attempt ->
            try {
                Thread.sleep(400)
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                return false
            }
            if (isLoopbackPortOccupied(port)) {
                Log.d(TAG, "Loopback port 127.0.0.1:$port occupied after ${attempt + 1} retry(ies)")
                return true
            }
        }
        return false
    }

    private inline fun safely(block: () -> Unit) {
        try { block() } catch (e: Exception) { Log.w(TAG, "NSD safe-call: ${e.message}") }
    }
}
