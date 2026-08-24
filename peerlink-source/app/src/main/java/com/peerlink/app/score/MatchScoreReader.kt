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
import kotlinx.coroutines.launch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.abs
import kotlin.math.max

/**
 * Event-driven final-score reader.
 *
 * The native packet path decides WHEN the match has entered eFootball's terminal
 * transport drain.  Only then do we take one screenshot.  There is no screenshot
 * polling loop, so gameplay pays no continuous image-capture/OCR cost.
 *
 * Prime shell is the first capture transport because PeerLink already owns that
 * authenticated loopback bridge.  A MediaProjection fallback can be added later
 * for users who never enable Prime Mode.
 */
object MatchScoreReader {
    data class MatchScore(val left: Int, val right: Int, val rawText: String)

    private data class Token(val value: Int, val box: Rect)

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val captureInFlight = AtomicBoolean(false)

    @Volatile var latestScore: MatchScore? = null
        private set

    fun captureAtTerminal(context: Context) {
        if (!captureInFlight.compareAndSet(false, true)) return
        val app = context.applicationContext
        scope.launch {
  try {
      val bitmap = captureViaPrime()
      if (bitmap == null) {
          AppState.appendLog("[MATCH-SCORE] Prime screenshot unavailable; packet end was still detected")
          return@launch
      }
      val score = recognizeScore(bitmap)
      if (score == null) {
          AppState.appendLog("[MATCH-SCORE] Screenshot captured but no confident score pair was found")
          return@launch
      }
      latestScore = score
      app.getSharedPreferences("peerlink_match_score", Context.MODE_PRIVATE)
          .edit()
          .putInt("left", score.left)
          .putInt("right", score.right)
          .putLong("captured_at_ms", System.currentTimeMillis())
          .putString("ocr_text", score.rawText.take(512))
          .apply()
      AppState.appendLog("[MATCH-SCORE] Final score ${score.left}-${score.right}")
  } catch (t: Throwable) {
      AppState.appendLog("[MATCH-SCORE] Capture/OCR failed: ${t.javaClass.simpleName}: ${t.message}")
  } finally {
      captureInFlight.set(false)
  }
        }
    }

    private fun captureViaPrime(): Bitmap? {
        if (!PrimeClient.isAlive(700)) return null
        // toybox base64 differs across Android releases; stripping line breaks
        // with tr works on the supported API range and keeps the JSON response one line.
        val encoded = PrimeClient.execute("screencap -p | base64 | tr -d '\\n'", 10_000)
  ?.trim()
  ?.takeIf { it.length > 128 }
  ?: return null
        val bytes = runCatching { Base64.decode(encoded, Base64.DEFAULT) }.getOrNull() ?: return null
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }

    private fun recognizeScore(bitmap: Bitmap): MatchScore? {
        // eFootball's live/final scoreboard is in the upper part of the landscape
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
          val m = explicit.find(line.text) ?: continue
          val a = m.groupValues[1].toIntOrNull() ?: continue
          val b = m.groupValues[2].toIntOrNull() ?: continue
          // Reject match clocks such as 90:00 and implausible OCR noise.
          if (a in 0..20 && b in 0..20) return MatchScore(a, b, result.text)
      }
  }

  // Fallback: score digits are often separate OCR elements. Pair two
  // similarly-sized integers on the same horizontal band and prefer the
  // upper/central pair. No answer is emitted unless geometry is plausible.
  val tokens = ArrayList<Token>()
  for (block in result.textBlocks) for (line in block.lines) for (element in line.elements) {
      val s = element.text.trim()
      if (!s.matches(Regex("\\d{1,2}"))) continue
      val v = s.toIntOrNull() ?: continue
      if (v !in 0..20) continue
      val box = element.boundingBox ?: continue
      if (box.height() <= 0 || box.width() <= 0) continue
      tokens += Token(v, box)
  }

  var best: Pair<Token, Token>? = null
  var bestCost = Long.MAX_VALUE
  for (i in 0 until tokens.size) for (j in i + 1 until tokens.size) {
      var a = tokens[i]
      var b = tokens[j]
      if (a.box.centerX() > b.box.centerX()) { val t = a; a = b; b = t }
      val yDelta = abs(a.box.centerY() - b.box.centerY())
      val h = max(a.box.height(), b.box.height())
      if (yDelta > max(18, h)) continue
      val gap = b.box.centerX() - a.box.centerX()
      if (gap < max(24, bitmap.width / 30) || gap > bitmap.width * 3 / 5) continue
      val midX = (a.box.centerX() + b.box.centerX()) / 2
      val midY = (a.box.centerY() + b.box.centerY()) / 2
      val cost = midY.toLong() * 5L +
          abs(midX - bitmap.width / 2).toLong() * 2L +
          abs(a.box.height() - b.box.height()).toLong() * 6L +
          yDelta.toLong() * 8L
      if (cost < bestCost) {
          bestCost = cost
          best = a to b
      }
  }
  best?.let { MatchScore(it.first.value, it.second.value, result.text) }
        } finally {
  recognizer.close()
  if (top !== bitmap && !top.isRecycled) top.recycle()
        }
    }
}
