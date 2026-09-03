package com.peerlink.app.godmode.shizuku

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.os.Build
import android.util.Log
import java.net.NetworkInterface

class PrimeShizukuAdbMdns(
    context: Context, private val serviceType: String,
    private val observer: (Int) -> Unit
) {

    private var registered = false
    private var running = false
    private var serviceName: String? = null
    private val listener = DiscoveryListener(this)
    private val nsdManager: NsdManager = context.getSystemService(NsdManager::class.java)

    fun start() {
        if (running) return
        running = true
        if (!registered) {
            nsdManager.discoverServices(serviceType, NsdManager.PROTOCOL_DNS_SD, listener)
        }
    }

    fun stop() {
        if (!running) return
        running = false
        if (registered) {
            nsdManager.stopServiceDiscovery(listener)
        }
    }

    private fun onDiscoveryStart() { registered = true }
    private fun onDiscoveryStop() { registered = false }
    private fun onServiceFound(info: NsdServiceInfo) { nsdManager.resolveService(info, ResolveListener(this)) }
    private fun onServiceLost(info: NsdServiceInfo) { if (info.serviceName == serviceName) observer(-1) }

    private fun onServiceResolved(resolvedService: NsdServiceInfo) {
        if (!running) return

        // Validate: resolved host must belong to one of our local interfaces
        val isLocal = try {
            NetworkInterface.getNetworkInterfaces()
                .asSequence()
                .any { iface ->
                    iface.inetAddresses.asSequence()
                        .any { resolvedService.host.hostAddress == it.hostAddress }
                }
        } catch (_: Exception) { false }

        if (!isLocal) return

        // NSD resolution is only endpoint discovery. Do not sleep/retry inside
        // NsdManager's callback thread; the bootstrap engine owns connection
        // retries after it receives this port.
        val port = resolvedService.port

        if (running) {
            serviceName = resolvedService.serviceName
            observer(port)
        }
    }

    internal class DiscoveryListener(private val adbMdns: PrimeShizukuAdbMdns) : NsdManager.DiscoveryListener {
        override fun onDiscoveryStarted(serviceType: String) {
            Log.v(TAG, "onDiscoveryStarted: $serviceType")
            adbMdns.onDiscoveryStart()
        }
        override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
            Log.w(TAG, "onStartDiscoveryFailed: $serviceType, $errorCode")
            adbMdns.registered = false
            adbMdns.running = false
            adbMdns.observer(-1)
        }
        override fun onDiscoveryStopped(serviceType: String) {
            Log.v(TAG, "onDiscoveryStopped: $serviceType")
            adbMdns.onDiscoveryStop()
        }
        override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
            Log.v(TAG, "onStopDiscoveryFailed: $serviceType, $errorCode")
        }
        override fun onServiceFound(serviceInfo: NsdServiceInfo) {
            Log.v(TAG, "onServiceFound: ${serviceInfo.serviceName}")
            adbMdns.onServiceFound(serviceInfo)
        }
        override fun onServiceLost(serviceInfo: NsdServiceInfo) {
            Log.v(TAG, "onServiceLost: ${serviceInfo.serviceName}")
            adbMdns.onServiceLost(serviceInfo)
        }
    }

    internal class ResolveListener(private val adbMdns: PrimeShizukuAdbMdns) : NsdManager.ResolveListener {
        override fun onResolveFailed(nsdServiceInfo: NsdServiceInfo, i: Int) {}
        override fun onServiceResolved(nsdServiceInfo: NsdServiceInfo) { adbMdns.onServiceResolved(nsdServiceInfo) }
    }

    companion object {
        const val TLS_CONNECT = "_adb-tls-connect._tcp"
        const val TLS_PAIRING = "_adb-tls-pairing._tcp"
        const val TAG = "PrimeShizukuAdbMdns"
    }
}
