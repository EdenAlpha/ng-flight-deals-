package com.peerlink.app.score

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Rect
import android.util.Base64
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.text.TextRecognition
import com.google.mlkit.vision.text.latin.TextRecognizerOptions
import com.peerlink.app.core.AppState
import com.peerlink.app.godmode.PrimeClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs
import kotlin.math.max

/**
 * Event-driven final-score reader.
 *
 * The native packet path decides WHEN the match has entered eFootball's terminal
 * transport drain. Only then do we capture the screen. There is no gameplay-time
 * screenshot polling loop.
 *
 * We use a tiny three-attempt burst after the one-shot terminal event because the
 * packet state can switch a few hundred milliseconds before the final scoreboard
 * has fully settled. The burst stops immediately after a confident score is read.
 */
object MatchScoreReader {
    data class MatchScore(val left: Int, val right: Int, val rawText: String)

    private data class Token(val value: Int, val box: Rect)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val captureInFlight = AtomicBoolean(false)

    // Delays are relative to the preceding attempt: captures occur at roughly
    // t=0 ms, t=350 ms and t=900 ms after the terminal signal.
    private val retryDelaysMs = longArrayOf(0L, 350L, 550L)

    @Volatile
    var latestScore: MatchScore? = null
        private set

    fun captureAtTerminal(context: Context) {
        if (!captureInFlight.compareAndSet(false, true)) return
        val app = context.applicationContext

        scope.launch {
            try {
                var score: MatchScore? = null
                var sawScreenshot = false

                for ((index, waitMs) in retryDelaysMs.withIndex()) {
                    if (waitMs > 0L) delay(waitMs)

                    val bitmap = captureViaPrime()
                    if (bitmap == null) {
                        if (index == 0) {
                            AppState.appendLog(
                                "[MATCH-SCORE] Prime screenshot unavailable on first terminal capture"
                            )
                        }
                        continue
                    }

                    sawScreenshot = true
                    try {
                        score = recognizeScore(bitmap)
                    } finally {
                        if (!bitmap.isRecycled) bitmap.recycle()
                    }

                    if (score != null) {
                        AppState.appendLog("[MATCH-SCORE] OCR locked on terminal attempt ${index + 1}")
                        break
                    }
                }

                val finalScore = score
                if (finalScore == null) {
                    AppState.appendLog(
                        if (sawScreenshot) {
                            "[MATCH-SCORE] Terminal screenshots captured but no confident score pair was found"
                        } else {
                            "[MATCH-SCORE] Match end detected but Prime screenshot transport was unavailable"
                        }
                    )
                    return@launch
                }

                latestScore = finalScore
                app.getSharedPreferences("peerlink_match_score", Context.MODE_PRIVATE)
                    .edit()
                    .putInt("left", finalScore.left)
                    .putInt("right", finalScore.right)
                    .putLong("captured_at_ms", System.currentTimeMillis())
                    .putString("ocr_text", finalScore.rawText.take(512))
                    .apply()

                AppState.appendLog("[MATCH-SCORE] Final score ${finalScore.left}-${finalScore.right}")
            } catch (t: Throwable) {
                AppState.appendLog(
                    "[MATCH-SCORE] Capture/OCR failed: ${t.javaClass.simpleName}: ${t.message}"
                )
            } finally {
                captureInFlight.set(false)
            }
        }
    }

    private fun captureViaPrime(): Bitmap? {
        if (!PrimeClient.isAlive(700)) return null

        // toybox base64 differs across Android releases; stripping line breaks
        // keeps PrimeServer's JSON response on one line.
        val encoded = PrimeClient.execute(
            "screencap -p | base64 | tr -d '\\n'",
            10_000,
        )
            ?.trim()
            ?.takeIf { it.length > 128 }
            ?: return null

        val bytes = runCatching { Base64.decode(encoded, Base64.DEFAULT) }.getOrNull()
            ?: return null
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    private fun recognizeScore(bitmap: Bitmap): MatchScore? {
        // eFootball's score presentation is in the upper part of the landscape
        // frame. Cropping removes most shirt numbers, menu counters and footer text.
        val cropHeight = max(1, (bitmap.height * 45) / 100)
        val top = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, cropHeight)
        val recognizer = TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS)

        return try {
            val result = Tasks.await(
                recognizer.process(InputImage.fromBitmap(top, 0)),
                5,
                TimeUnit.SECONDS,
            )

            // Strong path: OCR saw an explicit score separator on a single line.
            val explicit = Regex("(?<!\\d)(\\d{1,2})\\s*[-–—:]\\s*(\\d{1,2})(?!\\d)")
            for (block in result.textBlocks) {
                for (line in block.lines) {
                    val match = explicit.find(line.text) ?: continue
                    val left = match.groupValues[1].toIntOrNull() ?: continue
                    val right = match.groupValues[2].toIntOrNull() ?: continue
                    // Reject match clocks such as 90:00 and implausible OCR noise.
                    if (left in 0..20 && right in 0..20) {
                        return MatchScore(left, right, result.text)
                    }
                }
            }

            // Fallback: score digits are sometimes separate OCR elements. Pair two
            // similarly-sized integers on the same horizontal band and prefer the
            // upper/central pair. No answer is emitted unless geometry is plausible.
            val tokens = ArrayList<Token>()
            for (block in result.textBlocks) {
                for (line in block.lines) {
                    for (element in line.elements) {
                        val raw = element.text.trim()
                        if (!raw.matches(Regex("\\d{1,2}"))) continue
                        val value = raw.toIntOrNull() ?: continue
                        if (value !in 0..20) continue
                        val box = element.boundingBox ?: continue
                        if (box.height() <= 0 || box.width() <= 0) continue
                        tokens += Token(value, box)
                    }
                }
            }

            var best: Pair<Token, Token>? = null
            var bestCost = Long.MAX_VALUE

            for (i in 0 until tokens.size) {
                for (j in i + 1 until tokens.size) {
                    var left = tokens[i]
                    var right = tokens[j]
                    if (left.box.centerX() > right.box.centerX()) {
                        val tmp = left
                        left = right
                        right = tmp
                    }

                    val yDelta = abs(left.box.centerY() - right.box.centerY())
                    val height = max(left.box.height(), right.box.height())
                    if (yDelta > max(18, height)) continue

                    val gap = right.box.centerX() - left.box.centerX()
                    if (gap < max(24, bitmap.width / 30) || gap > bitmap.width * 3 / 5) continue

                    val midX = (left.box.centerX() + right.box.centerX()) / 2
                    val midY = (left.box.centerY() + right.box.centerY()) / 2
                    val cost = midY.toLong() * 5L +
                        abs(midX - bitmap.width / 2).toLong() * 2L +
                        abs(left.box.height() - right.box.height()).toLong() * 6L +
                        yDelta.toLong() * 8L

                    if (cost < bestCost) {
                        bestCost = cost
                        best = left to right
                    }
                }
            }

            best?.let { MatchScore(it.first.value, it.second.value, result.text) }
        } finally {
            recognizer.close()
            if (top !== bitmap && !top.isRecycled) top.recycle()
        }
    }
}
