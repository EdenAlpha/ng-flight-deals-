#pragma once

#include <jni.h>

#ifdef __cplusplus
extern "C" {
#endif

JNIEXPORT jlongArray JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativeStart(
        JNIEnv *env,
        jobject thiz,
        jint tun_fd,
        jstring peer_lan_ip,
        jint peer_port,
        jstring my_fabricated_ip,
        jstring peer_fabricated_ip,
        jstring vpn_address,
        jstring vpn_address_ipv6,
        jstring local_lan_ip,
        jint local_interface_index,
        jint mtu,
        jobject callbacks);

JNIEXPORT void JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativeRequestStop(
        JNIEnv *env,
        jobject thiz,
        jlong handle);

JNIEXPORT void JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativeStop(
        JNIEnv *env,
        jobject thiz,
        jlong handle);

JNIEXPORT jlongArray JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativePollStats(
        JNIEnv *env,
        jobject thiz,
        jlong handle);

JNIEXPORT jstring JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativeDumpUdpTrace(
        JNIEnv *env,
        jobject thiz,
        jlong handle);

JNIEXPORT jboolean JNICALL
Java_com_peerlink_app_tunnel_NativePeerLinkBackend_nativeVerifyPeerPath(
        JNIEnv *env, jobject thiz, jlong handle, jint timeout_ms);

#ifdef __cplusplus
}
#endif
