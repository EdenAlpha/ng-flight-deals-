package com.peerlink.app.godmode

import android.content.Context
import java.security.SecureRandom

/** Per-install secret used to authenticate the app to the shell-UID PrimeServer. */
object PrimeAuth {
    private const val PREFS = "prime_auth"
    private const val KEY_TOKEN = "token_v1"

    fun getOrCreate(context: Context): String {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.getString(KEY_TOKEN, null)?.takeIf { it.length >= 64 }?.let { return it }
        val bytes = ByteArray(32)
        SecureRandom().nextBytes(bytes)
        val token = bytes.joinToString("") { "%02x".format(it) }
        prefs.edit().putString(KEY_TOKEN, token).commit()
        return token
    }
}
