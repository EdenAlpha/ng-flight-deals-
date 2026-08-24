from pathlib import Path

root = Path(__file__).resolve().parents[1]
cpp_path = root / "app/src/main/jni/peerlink_backend.cpp"
kt_path = root / "app/src/main/java/com/peerlink/app/tunnel/NativePeerLinkBackend.kt"
notes_path = root / "SCORE_READER_NOTES.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


cpp = cpp_path.read_text()

cpp = replace_once(
    cpp,
    "    jmethodID native_log_mid = nullptr;\n",
    "    jmethodID native_log_mid = nullptr;\n    jmethodID match_terminal_mid = nullptr;\n",
    "native callback method id",
)

old_detector_start = """void observe_match_terminal_outbound(BackendState *state,
                           uint16_t local_port,
                           uint16_t remote_port,
                           size_t udp_payload_length,
                           uint64_t now_ms) {
    if (state == nullptr || state->match_terminal_detected.load(std::memory_order_relaxed)) return;
    if (!stable_gameplay_known(state)) return;
    if (local_port != static_cast<uint16_t>(load_stable_game_port(state)) ||
        remote_port != static_cast<uint16_t>(load_stable_remote_port(state))) return;

    const uint64_t gameplay_start = state->game_traffic_start_ms.load(std::memory_order_acquire);
    if (gameplay_start == 0 || now_ms < gameplay_start ||
        (now_ms - gameplay_start) < kMatchTerminalArmAfterMs) return;

    if (udp_payload_length > kMatchTerminalMaxUdpPayload) {
        state->match_terminal_candidate_start_ms = 0;
        state->match_terminal_candidate_packets = 0;
        state->match_terminal_rearm_ready = true;
        return;
    }

    if (!state->match_terminal_rearm_ready) return;
    if (state->match_terminal_last_detected_ms != 0 &&
        now_ms >= state->match_terminal_last_detected_ms &&
        (now_ms - state->match_terminal_last_detected_ms) < kMatchTerminalCooldownMs) return;

    if (state->match_terminal_candidate_start_ms == 0) {
        state->match_terminal_candidate_start_ms = now_ms;
        state->match_terminal_candidate_packets = 1;
        return;
    }

    ++state->match_terminal_candidate_packets;
    const uint64_t sustained_ms = now_ms - state->match_terminal_candidate_start_ms;
    if (sustained_ms >= kMatchTerminalSustainMs &&
        state->match_terminal_candidate_packets >= kMatchTerminalMinPackets) {
        state->match_terminal_last_detected_ms = now_ms;
        state->match_terminal_candidate_start_ms = 0;
        state->match_terminal_candidate_packets = 0;
        state->match_terminal_rearm_ready = false;
        state->match_terminal_detected.store(true, std::memory_order_release);
    }
}
"""

new_detector = """bool observe_match_terminal_outbound(BackendState *state,
                                     uint16_t local_port,
                                     uint16_t remote_port,
                                     size_t udp_payload_length,
                                     uint64_t now_ms) {
    if (state == nullptr || state->match_terminal_detected.load(std::memory_order_relaxed)) return false;
    if (!stable_gameplay_known(state)) return false;
    if (local_port != static_cast<uint16_t>(load_stable_game_port(state)) ||
        remote_port != static_cast<uint16_t>(load_stable_remote_port(state))) return false;

    const uint64_t gameplay_start = state->game_traffic_start_ms.load(std::memory_order_acquire);
    if (gameplay_start == 0 || now_ms < gameplay_start ||
        (now_ms - gameplay_start) < kMatchTerminalArmAfterMs) return false;

    if (udp_payload_length > kMatchTerminalMaxUdpPayload) {
        state->match_terminal_candidate_start_ms = 0;
        state->match_terminal_candidate_packets = 0;
        state->match_terminal_rearm_ready = true;
        return false;
    }

    if (!state->match_terminal_rearm_ready) return false;
    if (state->match_terminal_last_detected_ms != 0 &&
        now_ms >= state->match_terminal_last_detected_ms &&
        (now_ms - state->match_terminal_last_detected_ms) < kMatchTerminalCooldownMs) return false;

    if (state->match_terminal_candidate_start_ms == 0) {
        state->match_terminal_candidate_start_ms = now_ms;
        state->match_terminal_candidate_packets = 1;
        return false;
    }

    ++state->match_terminal_candidate_packets;
    const uint64_t sustained_ms = now_ms - state->match_terminal_candidate_start_ms;
    if (sustained_ms >= kMatchTerminalSustainMs &&
        state->match_terminal_candidate_packets >= kMatchTerminalMinPackets) {
        state->match_terminal_last_detected_ms = now_ms;
        state->match_terminal_candidate_start_ms = 0;
        state->match_terminal_candidate_packets = 0;
        state->match_terminal_rearm_ready = false;
        state->match_terminal_detected.store(true, std::memory_order_release);
        return true;
    }
    return false;
}

void dispatch_match_terminal_event(JNIEnv *env, BackendState *state) {
    if (state == nullptr) return;
    if (env != nullptr && state->callbacks != nullptr && state->match_terminal_mid != nullptr) {
        env->CallVoidMethod(state->callbacks, state->match_terminal_mid);
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
            emit_native_log(env, state, kNativeLogWarn, false,
                            "[MATCH-END  ] Native match-end callback threw; event latch released");
        } else {
            emit_native_log(env, state, kNativeLogInfo, false,
                            "[MATCH-END  ] Terminal signature dispatched directly from native TUN path");
        }
    }
    // Rearm is still guarded by match_terminal_rearm_ready and the cooldown.
    // Clearing this transient latch here avoids any polling dependency and allows
    // a later match in the same VPN session after normal (>36-byte) gameplay resumes.
    state->match_terminal_detected.store(false, std::memory_order_release);
}
"""
cpp = replace_once(cpp, old_detector_start, new_detector, "terminal detector replacement")

cpp = replace_once(
    cpp,
    "                observe_gameplay_flow(state, parsed.source_port, parsed.dest_port, now_ms);\n                observe_match_terminal_outbound(state, parsed.source_port, parsed.dest_port, parsed.udp_payload_length, now_ms);\n",
    "                observe_gameplay_flow(state, parsed.source_port, parsed.dest_port, now_ms);\n                if (observe_match_terminal_outbound(state, parsed.source_port, parsed.dest_port, parsed.udp_payload_length, now_ms)) {\n                    dispatch_match_terminal_event(env, state);\n                }\n",
    "IPv4 direct terminal callback",
)

cpp = replace_once(
    cpp,
    "            observe_gameplay_flow(state, parsed.source_port, parsed.dest_port, monotonic_ms());\n            const int new_stable_port = load_stable_game_port(state);\n",
    "            const uint64_t now_ms = monotonic_ms();\n            observe_gameplay_flow(state, parsed.source_port, parsed.dest_port, now_ms);\n            if (observe_match_terminal_outbound(state, parsed.source_port, parsed.dest_port, parsed.udp_payload_length, now_ms)) {\n                dispatch_match_terminal_event(env, state);\n            }\n            const int new_stable_port = load_stable_game_port(state);\n",
    "IPv6 direct terminal callback",
)

cpp = replace_once(
    cpp,
    "    state->native_log_mid = env->GetMethodID(callback_class, \"onNativeLog\", \"(ILjava/lang/String;Z)V\");\n",
    "    state->native_log_mid = env->GetMethodID(callback_class, \"onNativeLog\", \"(ILjava/lang/String;Z)V\");\n    state->match_terminal_mid = env->GetMethodID(callback_class, \"onMatchTerminalDetected\", \"()V\");\n",
    "lookup terminal callback",
)

cpp = replace_once(
    cpp,
    "    if (state->prepare_peer_socket_mid == nullptr || state->fabricate_stun_mid == nullptr || state->native_log_mid == nullptr) {\n",
    "    if (state->prepare_peer_socket_mid == nullptr || state->fabricate_stun_mid == nullptr ||\n        state->native_log_mid == nullptr || state->match_terminal_mid == nullptr) {\n",
    "required callbacks check",
)
cpp_path.write_text(cpp)

kt = kt_path.read_text()
kt = replace_once(
    kt,
    "        @Suppress(\"unused\")\n        fun onNativeLog(level: Int, message: String, fileOnly: Boolean) {\n            callbacks.onNativeLog(level, message, fileOnly)\n        }\n",
    "        @Suppress(\"unused\")\n        fun onNativeLog(level: Int, message: String, fileOnly: Boolean) {\n            callbacks.onNativeLog(level, message, fileOnly)\n        }\n\n        @Suppress(\"unused\")\n        fun onMatchTerminalDetected() {\n            AppState.appendLog(\"[MATCH-END  ] Native eFootball terminal signature confirmed\")\n            callbacks.onMatchTerminalDetected()\n        }\n",
    "Kotlin JNI terminal callback",
)
kt = replace_once(
    kt,
    "                        callbacks.onStats(stats)\n                        if (pollMatchTerminalDetected()) {\n                            AppState.appendLog(\"[MATCH-END  ] Native eFootball terminal signature confirmed\")\n                            callbacks.onMatchTerminalDetected()\n                        }\n",
    "                        callbacks.onStats(stats)\n",
    "remove one-second terminal polling",
)
kt_path.write_text(kt)

notes = notes_path.read_text()
needle = "`Native TUN gameplay classification -> terminal detector -> one-shot Kotlin callback -> event-only screenshot burst -> upper-frame ML Kit OCR -> persisted latest score`"
replacement = "`Native TUN gameplay classification -> terminal detector -> direct JNI callback on the same event -> event-only screenshot burst -> upper-frame ML Kit OCR -> persisted latest score`"
if needle in notes:
    notes = notes.replace(needle, replacement, 1)
    notes = notes.replace(
        "The screenshot burst occurs only after the terminal event,",
        "The match-end signal no longer waits for the 1-second statistics poll; native code dispatches it immediately when the terminal rule becomes true. The screenshot burst occurs only after that terminal event,",
        1,
    )
    notes_path.write_text(notes)

# One-shot staging script: verified source should not retain patch machinery.
Path(__file__).unlink()
