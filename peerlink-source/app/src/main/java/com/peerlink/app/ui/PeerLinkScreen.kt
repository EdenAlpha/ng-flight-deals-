package com.peerlink.app.ui

import android.content.Context
import android.widget.Toast
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.*
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.onGloballyPositioned
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.TextFieldValue
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.peerlink.app.core.AppState
import com.peerlink.app.core.CrashLogger
import com.peerlink.app.core.PeerInfo
import com.peerlink.app.core.VpnSessionState
import com.peerlink.app.core.DiscoveryState
import com.peerlink.app.godmode.GodModeManager
import com.peerlink.app.service.CallMonitorService
import kotlinx.coroutines.delay
import kotlin.math.roundToInt

/* ═════════ DARK THEME — PeerLink Redesign ═════════ */
private object PL {
    val bg        = Color(0xFF0B0F19)
    val elevated  = Color(0xFF111827)
    val surface   = Color(0xFF151D2E)
    val ink       = Color(0xFFF8FAFC)
    val inkSoft   = Color(0xFF94A3B8)
    val muted     = Color(0xFF64748B)
    val line      = Color(0xFF1E293B)
    val lineSoft  = Color(0xFF334155)
    val gold      = Color(0xFFF59E0B)
    val goldSoft  = Color(0xFFFCD34D)
    val goldDeep  = Color(0xFFD97706)
    val green     = Color(0xFF10B981)
    val greenGlow = Color(0xFF34D399)
    val indigo    = Color(0xFF6366F1)
    val indigoGlow= Color(0xFF818CF8)
    val red       = Color(0xFFEF4444)
}

/* ═════════ Prototype-faithful glass + glow primitives ═════════ */
// .glass — translucent white gradient, bright top edge, soft drop shadow.
private fun Modifier.glass(radius: Dp = 20.dp): Modifier = this
    .shadow(18.dp, RoundedCornerShape(radius), clip = false, ambientColor = Color.Black.copy(alpha = 0.35f), spotColor = Color.Black.copy(alpha = 0.5f))
    .clip(RoundedCornerShape(radius))
    .background(Brush.linearGradient(listOf(Color.White.copy(alpha = 0.07f), Color.White.copy(alpha = 0.03f))))
    .border(1.dp, Brush.verticalGradient(listOf(Color.White.copy(alpha = 0.12f), Color.White.copy(alpha = 0.06f))), RoundedCornerShape(radius))

// .glass-solid — opaque elevated surface variant.
private fun Modifier.glassSolid(radius: Dp = 20.dp): Modifier = this
    .shadow(14.dp, RoundedCornerShape(radius), clip = false, ambientColor = Color.Black.copy(alpha = 0.3f), spotColor = Color.Black.copy(alpha = 0.45f))
    .clip(RoundedCornerShape(radius))
    .background(PL.surface)
    .border(1.dp, Color.White.copy(alpha = 0.07f), RoundedCornerShape(radius))

class PeerLinkActions(
    val saveName: (String) -> Unit,
    val connectToPeer: (PeerInfo) -> Unit,
    val disconnect: () -> Unit,
    val isAdmin: Boolean = false,
    val tryAdminUnlock: (String) -> Boolean = { false },
    val deviceId: String = "",
    val generateKey: (String) -> String = { "" },
    val onSetupPrimeMode: () -> Unit = {},
    val exportMatchLogs: () -> Unit = {},
    val callBlockEnabled: () -> Boolean = { false },
    val setCallBlock: (Boolean) -> Unit = {},
    val startDiscovery: () -> Unit = {},
)

@Composable
fun PeerLinkTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = PL.gold, onPrimary = PL.bg,
            secondary = PL.indigo, onSecondary = Color.White,
            background = PL.bg, onBackground = PL.ink,
            surface = PL.surface, onSurface = PL.ink,
            surfaceVariant = PL.elevated, outline = PL.line,
            error = PL.red
        ),
        content = content
    )
}

@Composable
fun PeerLinkScreen(ctx: Context, peers: List<PeerInfo>, actions: PeerLinkActions) {
    val prefs = remember { ctx.getSharedPreferences("peerlink_prefs", Context.MODE_PRIVATE) }
    LaunchedEffect(Unit) { prefs.edit().putString("transport_mode", "wifi").apply() }

    var sessionState by remember { mutableStateOf(AppState.vpnSessionState.get()) }
    var connected by remember { mutableStateOf(sessionState == VpnSessionState.CONNECTED || sessionState == VpnSessionState.DISCONNECTING) }
    var tunneled by remember { mutableStateOf(AppState.tunneled.get()) }
    var passed by remember { mutableStateOf(AppState.passedThrough.get()) }
    var discoveryState by remember { mutableStateOf(AppState.discoveryState.get()) }
    var myIp by remember { mutableStateOf(AppState.myFabricatedIp) }
    var peerIp by remember { mutableStateOf(AppState.peerFabricatedIp) }
    var since by remember { mutableStateOf(0L) }
    LaunchedEffect(Unit) {
        while (true) {
            val state = AppState.vpnSessionState.get()
            val r = state == VpnSessionState.CONNECTED || state == VpnSessionState.DISCONNECTING
            sessionState = state
            if (r && since == 0L) since = System.currentTimeMillis(); if (!r) since = 0L
            connected = r; tunneled = AppState.tunneled.get(); passed = AppState.passedThrough.get()
            discoveryState = AppState.discoveryState.get()
            myIp = AppState.myFabricatedIp; peerIp = AppState.peerFabricatedIp
            delay(400)
        }
    }

    LaunchedEffect(Unit) { actions.startDiscovery() }

    // Discovery lifecycle/rebinding belongs to MainActivity. Keeping the network
    // callback out of the Composable avoids duplicate listeners and makes UI state a
    // pure reflection of the shared discovery state machine.

    var name by remember { mutableStateOf(prefs.getString("username", "") ?: "") }
    var drawerOpen by remember { mutableStateOf(false) }
    var adminOpen by remember { mutableStateOf(false) }
    var adminUnlockOpen by remember { mutableStateOf(false) }


    val primeState by GodModeManager.state.collectAsState()
    // isPaired now requires PRIME_MODE_ACTIVE — previously it was true during
    // DISCOVERING, PAIRING, and PAIRED_IDLE (which includes "Bootstrap pending"),
    // making all Prime tools clickable long before PrimeServer was actually
    // running. The user reported "all the prime mode buttons turn on fully
    // clickable and am wondering did it connect or not?" — this fixes that.
    // Tools are visually disabled (alpha 0.35) until Prime Mode is truly active.
    val isPaired = primeState == GodModeManager.State.PRIME_MODE_ACTIVE

    fun primeToast() = Toast.makeText(ctx, "Set up Prime Mode first", Toast.LENGTH_SHORT).show()

    val pager = rememberPagerState(pageCount = { 2 })

    // Ambient background with animated orbs
    Box(Modifier.fillMaxSize().background(PL.bg)) {
        // ── Ambient mesh: three large blurred orbs drifting slowly (prototype .orb) ──
        val amb = rememberInfiniteTransition(label = "ambient")
        val drift1 by amb.animateFloat(0f, 1f, infiniteRepeatable(tween(12000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "d1")
        val drift2 by amb.animateFloat(0f, 1f, infiniteRepeatable(tween(15000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "d2")
        // Orb 1 — gold, top-right
        Box(Modifier.fillMaxSize().blur(60.dp).background(Brush.radialGradient(
            listOf(PL.gold.copy(alpha = 0.22f), Color.Transparent),
            center = Offset(1050f + 60f * drift1, -40f - 50f * drift1), radius = 460f
        )))
        // Orb 2 — indigo, bottom-left
        Box(Modifier.fillMaxSize().blur(60.dp).background(Brush.radialGradient(
            listOf(PL.indigo.copy(alpha = 0.10f), Color.Transparent),
            center = Offset(-60f - 40f * drift2, 1480f + 30f * drift2), radius = 520f
        )))
        // Orb 3 — green, center
        Box(Modifier.fillMaxSize().blur(60.dp).background(Brush.radialGradient(
            listOf(PL.green.copy(alpha = 0.12f), Color.Transparent),
            center = Offset(560f, 820f - 40f * drift1), radius = 420f
        )))

        // Noise overlay — subtle texture
        Box(Modifier.fillMaxSize().background(Color.White.copy(alpha = 0.015f)))

        val blurAmt = if (drawerOpen || adminOpen) 7.dp else 0.dp

        Column(Modifier.fillMaxSize().statusBarsPadding().blur(blurAmt)) {
            // ── HEADER ──
            Row(Modifier.fillMaxWidth().padding(16.dp, 10.dp, 16.dp, 6.dp), verticalAlignment = Alignment.CenterVertically) {
                DarkHeaderBtn(Icons.Rounded.Menu) { drawerOpen = true }
                Spacer(Modifier.weight(1f))
                // Wordmark: Peer + Link
                Row(verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.pointerInput(Unit) {
                        detectTapGestures(onLongPress = { if (!actions.isAdmin) adminUnlockOpen = true })
                    }) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Row {
                            Text("Peer", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink, letterSpacing = (-0.5).sp)
                            Text("Link", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, color = PL.gold, letterSpacing = (-0.5).sp)
                        }
                        Box(Modifier.padding(top = 1.dp).width(54.dp).height(2.dp).clip(RoundedCornerShape(2.dp))
                            .background(Brush.horizontalGradient(listOf(Color.Transparent, PL.gold.copy(alpha = 0.5f), Color.Transparent))))
                    }
                }
                Spacer(Modifier.weight(1f))
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                    if (actions.isAdmin) DarkHeaderBtn(Icons.Rounded.Settings) { adminOpen = true }
                    StatusChip(sessionState)
                }
            }

            HorizontalPager(state = pager, modifier = Modifier.weight(1f)) { page ->
                if (page == 0) MainPage(
                    name, { name = it; actions.saveName(it) },
                    connected, sessionState, peers, tunneled, passed, myIp, peerIp, since, isPaired,
                    onTapPeer = { p -> if (sessionState == VpnSessionState.DISCONNECTED || sessionState == VpnSessionState.ERROR) actions.connectToPeer(p) },
                    onDisconnect = { actions.disconnect() },
                    onRefreshDiscovery = { actions.startDiscovery() },
                    discoveryState = discoveryState,
                    onToolToggle = { key, want ->
                        if (!isPaired) { primeToast(); false }
                        else {
                            when (key) {
                                "ram" -> GodModeManager.setKeepGameInRam(want)
                                "calls" -> actions.setCallBlock(want)
                                "auto" -> GodModeManager.setAutoConnectEnabled(want)
                            }; true
                        }
                    },
                    callBlockOn = actions.callBlockEnabled(),
                    ctx = ctx
                ) else CoinPage()
            }
            PagerDots(pager.currentPage)
        }

        if (drawerOpen || adminOpen) Box(Modifier.fillMaxSize().background(Color(0xCC000000)).clickable(
            indication = null, interactionSource = null) { drawerOpen = false; adminOpen = false })

        SidePanel(drawerOpen, true, { drawerOpen = false }) {
            SettingsMenu(isPaired) { drawerOpen = false; actions.onSetupPrimeMode() }
        }
        SidePanel(adminOpen, false, { adminOpen = false }) { AdminMenu(ctx, actions) }

        if (adminUnlockOpen) AdminUnlockDialog(onClose = { adminUnlockOpen = false }) { entered ->
            if (actions.tryAdminUnlock(entered)) {
                adminUnlockOpen = false; Toast.makeText(ctx, "Admin unlocked", Toast.LENGTH_SHORT).show(); true
            } else false
        }


    }
}

/* ═════════ MAIN PAGE ═════════ */
@Composable
private fun MainPage(
    name: String, onName: (String) -> Unit,
    connected: Boolean, sessionState: VpnSessionState, peers: List<PeerInfo>, tunneled: Long, passed: Long, myIp: String, peerIp: String,
    since: Long, isPaired: Boolean,
    onTapPeer: (PeerInfo) -> Unit,
    onDisconnect: () -> Unit,
    onRefreshDiscovery: () -> Unit,
    discoveryState: DiscoveryState,
    onToolToggle: (String, Boolean) -> Boolean, callBlockOn: Boolean,
    ctx: Context
) {
    // Fixed layout — no scroll. Every section has a defined weight so the whole
    // screen fills exactly without overflow or dead space.
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
        Spacer(Modifier.height(4.dp))
        // ── Player identity ──
        NameRow(name, onName)
        Spacer(Modifier.height(10.dp))
        // ── Connection core — the hero, takes available vertical space ──
        Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
            ConnectionCore(connected, discoveryState, myIp, peerIp, since)
        }
        Spacer(Modifier.height(10.dp))
        // ── Stats row ──
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            StatCard(Modifier.weight(1f), "Tunneled", tunneled, PL.green, true)
            StatCard(Modifier.weight(1f), "Passthrough", passed, PL.gold, false)
        }
        Spacer(Modifier.height(12.dp))
        // ── Players nearby OR Slide-to-Disconnect ──
        // Once a session is live, the peer-tap area morphs
        // into a slide-to-disconnect bar so the user can end the session
        // deliberately without accidental taps.
        val sessionBusy = sessionState == VpnSessionState.CONNECTING || sessionState == VpnSessionState.VERIFYING
        if (connected || sessionBusy) {
            SectionTitle("Session")
            Spacer(Modifier.height(6.dp))
            // Find the connected peer's name (if still in the discovered list)
            // to personalise the bar. AppState.peerIp holds the peer's actual LAN
            // IP (set during pairing), not the fabricated IP — so we match
            // against that. If it is no longer in discovery, the bar simply
            // says "Slide to disconnect".
            val peerLanIp = AppState.peerIp.get()?.hostAddress
            val connectedPeerName = peers.firstOrNull { it.ip == peerLanIp }?.name
            if (sessionBusy) {
                SessionStartingBar(sessionState = sessionState, onCancel = onDisconnect)
            } else {
                SlideToDisconnectBar(
                    peerName = connectedPeerName,
                    disconnecting = sessionState == VpnSessionState.DISCONNECTING,
                    onDisconnect = onDisconnect
                )
            }
        } else {
            SectionTitle("Players nearby")
            Spacer(Modifier.height(6.dp))
            // Track which peers are "new" (appeared since the last composition)
            // so they can play a bounce/pulse animation for 6 seconds to signal
            // "look at me — a new peer just showed up". We remember the set of
            // peer IPs we've already seen; any peer in the current list that
            // isn't in the remembered set is "new", and we add it to the set
            // and record when we first saw it.
            val seenPeerIps = remember { mutableStateMapOf<String, Long>() }
            val now = System.currentTimeMillis()
            peers.forEach { p ->
                if (!seenPeerIps.containsKey(p.ip)) {
                    seenPeerIps[p.ip] = now
                }
            }
            // A peer is "new" if it was first seen less than 6 seconds ago.
            // The animation plays for those 6 seconds, then stops.
            val newPeerIps = remember(peers, now) {
                peers.filter { p ->
                    val firstSeen = seenPeerIps[p.ip] ?: now
                    (now - firstSeen) < 6_000L
                }.map { it.ip }.toSet()
            }

            // Size-to-content with a cap — previously this was a fixed 120dp
            // height which wasted space when 0 or 1 peers were visible (the
            // user explicitly complained about this). Now it shrinks to fit
            // content (~40dp empty, ~48dp with 1 peer) and only caps at 120dp
            // when 3+ peers would overflow. The ConnectionCore animation above
            // reclaims the saved space.
            Box(
                Modifier
                    .fillMaxWidth()
                    .heightIn(max = 120.dp)
            ) {
                if (peers.isEmpty()) {
                    EmptyPeers(discoveryState, onRefreshDiscovery)
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(7.dp),
                        contentPadding = PaddingValues(vertical = 0.dp)
                    ) {
                        items(peers) { p ->
                            PeerRow(
                                peer = p,
                                isConnected = connected && peerIp == p.ip,
                                isNew = p.ip in newPeerIps,
                                onTap = { onTapPeer(p) }
                            )
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(12.dp))
        // ── Prime Tools ──
        SectionTitle(if (isPaired) "Prime Tools" else "Prime Tools \u00b7 Set up to unlock")
        Spacer(Modifier.height(7.dp))
        PrimeDeck(isPaired, callBlockOn, onToolToggle, ctx)
        Spacer(Modifier.height(10.dp))
    }
}

/* ─── Components ─── */
@Composable private fun DarkHeaderBtn(icon: ImageVector, onClick: () -> Unit) {
    Box(Modifier.size(40.dp).clip(RoundedCornerShape(10.dp))
        .background(Color.White.copy(alpha = 0.04f))
        .border(1.dp, PL.lineSoft, RoundedCornerShape(10.dp))
        .clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Icon(icon, null, tint = PL.inkSoft, modifier = Modifier.size(20.dp))
    }
}

@Composable private fun StatusChip(sessionState: VpnSessionState) {
    val (label, c, active) = when (sessionState) {
        VpnSessionState.CONNECTED -> Triple("CONNECTED", PL.green, true)
        VpnSessionState.CONNECTING -> Triple("STARTING", PL.gold, true)
        VpnSessionState.VERIFYING -> Triple("VERIFYING", PL.gold, true)
        VpnSessionState.DISCONNECTING -> Triple("STOPPING", PL.red, true)
        VpnSessionState.ERROR -> Triple("ERROR", PL.red, false)
        VpnSessionState.DISCONNECTED -> Triple("READY", PL.muted, false)
    }
    val bg = if (active) c.copy(alpha = 0.08f) else Color.White.copy(alpha = 0.04f)
    val borderC = if (active) c.copy(alpha = 0.3f) else PL.line
    val ping = rememberInfiniteTransition(label = "ping")
    val pingScale by ping.animateFloat(1f, 2.2f, infiniteRepeatable(tween(2000, easing = LinearEasing)), label = "ps")
    val pingAlpha by ping.animateFloat(0.6f, 0f, infiniteRepeatable(tween(2000, easing = LinearEasing)), label = "pa")
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp),
        modifier = Modifier.background(bg, RoundedCornerShape(100.dp)).border(1.dp, borderC, RoundedCornerShape(100.dp)).padding(horizontal = 11.dp, vertical = 5.dp)) {
        Text(label, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, color = c, letterSpacing = 1.sp)
        Box(contentAlignment = Alignment.Center) {
            if (active) Box(Modifier.size(6.dp).graphicsLayer { scaleX = pingScale; scaleY = pingScale; alpha = pingAlpha }.border(1.dp, c, CircleShape))
            Box(Modifier.size(6.dp).clip(CircleShape).background(c))
        }
    }
}

@Composable private fun DarkCard(modifier: Modifier = Modifier, padding: Dp = 16.dp, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier = modifier.glass(20.dp).padding(padding), content = content)
}

@Composable private fun SectionTitle(t: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Text(t.uppercase(), fontSize = 9.5.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 1.8.sp, modifier = Modifier.padding(start = 4.dp))
        Box(Modifier.weight(1f).height(1.dp).background(Brush.horizontalGradient(listOf(PL.line, Color.Transparent))))
    }
}

/* ─── Player name ─── */
@Composable private fun NameRow(name: String, onSave: (String) -> Unit) {
    var editing by remember { mutableStateOf(name.isBlank()) }
    var field by remember(name) { mutableStateOf(TextFieldValue(name, selection = androidx.compose.ui.text.TextRange(name.length))) }
    val focusRequester = remember { androidx.compose.ui.focus.FocusRequester() }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        // Name strip — a greeting, not a form field
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            // Small gold identity dot with initial
            Box(Modifier.size(26.dp).clip(CircleShape)
                .background(Brush.linearGradient(listOf(PL.gold, PL.goldDeep))),
                contentAlignment = Alignment.Center) {
                Text(
                    name.trim().firstOrNull()?.uppercase() ?: "?",
                    color = Color.White, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold
                )
            }
            Spacer(Modifier.width(10.dp))
            if (editing) {
                LaunchedEffect(Unit) { focusRequester.requestFocus() }
                BasicTextField(
                    field, { if (it.text.length <= 18) field = it },
                    singleLine = true,
                    textStyle = androidx.compose.ui.text.TextStyle(PL.ink, 17.sp, FontWeight.Bold),
                    cursorBrush = SolidColor(PL.gold),
                    modifier = Modifier.weight(1f)
                        .focusRequester(focusRequester)
                        .drawBehind {
                            // Sleek gold underline instead of a box
                            drawLine(
                                brush = Brush.horizontalGradient(listOf(PL.gold, PL.gold.copy(alpha = 0.15f))),
                                start = Offset(0f, size.height + 6.dp.toPx()),
                                end = Offset(size.width, size.height + 6.dp.toPx()),
                                strokeWidth = 2f
                            )
                        },
                    decorationBox = { inner ->
                        Box { if (field.text.isEmpty()) Text("What do players call you?", color = PL.muted, fontSize = 16.sp); inner() }
                    }
                )
                Spacer(Modifier.width(10.dp))
                Box(Modifier.size(30.dp).clip(CircleShape)
                    .background(Brush.linearGradient(listOf(PL.gold, PL.goldDeep)))
                    .clickable { if (field.text.isNotBlank()) { onSave(field.text.trim()); editing = false } },
                    contentAlignment = Alignment.Center) {
                    Icon(Icons.Rounded.Check, null, tint = Color.White, modifier = Modifier.size(15.dp))
                }
            } else {
                Row(Modifier.weight(1f)
                    .clickable(indication = null, interactionSource = remember { androidx.compose.foundation.interaction.MutableInteractionSource() }) {
                        field = TextFieldValue(name, selection = androidx.compose.ui.text.TextRange(name.length)); editing = true
                    },
                    verticalAlignment = Alignment.CenterVertically) {
                    if (name.isBlank()) {
                        Text("Tap to set your player name", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = PL.gold.copy(alpha = 0.85f))
                    } else {
                        Text("Hey, ", fontSize = 16.sp, fontWeight = FontWeight.Medium, color = PL.muted)
                        Text(name, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    }
                    Spacer(Modifier.width(7.dp))
                    Icon(Icons.Rounded.Edit, null, tint = PL.muted.copy(alpha = 0.7f), modifier = Modifier.size(12.dp))
                }
            }
        }

    }
}

/* ─── Connection Core — THE HERO (prototype-faithful) ─── */
@Composable private fun ConnectionCore(connected: Boolean, discoveryState: DiscoveryState, myIp: String, peerIp: String, since: Long) {
    val tr = rememberInfiniteTransition(label = "core")
    val spin by tr.animateFloat(0f, 360f, infiniteRepeatable(tween(15000, easing = LinearEasing)), label = "spin")
    val spinRev by tr.animateFloat(360f, 0f, infiniteRepeatable(tween(20000, easing = LinearEasing)), label = "spinRev")
    val orbit by tr.animateFloat(0f, 360f, infiniteRepeatable(tween(8000, easing = LinearEasing)), label = "orbit")
    val orbitRev by tr.animateFloat(360f, 0f, infiniteRepeatable(tween(6000, easing = LinearEasing)), label = "orbitRev")
    val glowPulse by tr.animateFloat(0.4f, 0.85f, infiniteRepeatable(tween(2000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "glow")
    val coreScale by tr.animateFloat(1f, 1.08f, infiniteRepeatable(tween(2000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "coreScale")
    val floatY by tr.animateFloat(-3f, 3f, infiniteRepeatable(tween(3000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "floatY")
    val breathe by tr.animateFloat(1f, 1.12f, infiniteRepeatable(tween(3000, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "breathe")

    var elapsed by remember { mutableStateOf("00:00") }
    LaunchedEffect(since) {
        while (since > 0L) {
            val s = ((System.currentTimeMillis() - since) / 1000).toInt()
            elapsed = "%02d:%02d".format(s / 60, s % 60); delay(1000)
        }
        elapsed = "00:00"
    }
    val accent = if (connected) PL.green else PL.gold
    val mainLabel = when {
        connected -> "Connected"
        discoveryState == DiscoveryState.WAITING_FOR_WIFI -> "Wi-Fi needed"
        discoveryState == DiscoveryState.ERROR -> "Discovery issue"
        else -> "Ready"
    }
    val subLabel = when {
        connected -> "Wi-Fi · tunnel live"
        discoveryState == DiscoveryState.WAITING_FOR_WIFI -> "Connect to Wi-Fi or enable a hotspot"
        discoveryState == DiscoveryState.ERROR -> "Tap refresh below to restart discovery"
        discoveryState == DiscoveryState.SEARCHING -> "Searching continuously for nearby players"
        else -> "Nearby players appear automatically"
    }
    val statusLabel = when {
        connected -> "LIVE"
        discoveryState == DiscoveryState.WAITING_FOR_WIFI -> "WAIT"
        discoveryState == DiscoveryState.ERROR -> "CHECK"
        else -> "READY"
    }

    Column(Modifier.fillMaxSize()) {
        Box(Modifier.fillMaxWidth().weight(1f), contentAlignment = Alignment.Center) {
            // Status dot top-left
            Row(Modifier.align(Alignment.TopStart).padding(top = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                Box(Modifier.size(7.dp).clip(CircleShape).background(accent))
                Text(statusLabel, color = if (connected) PL.green else PL.gold, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 1.6.sp)
            }
            // Transport badge top-right — shows the active mode at a glance
            Row(Modifier.align(Alignment.TopEnd).padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(3.dp)) {
                Icon(Icons.Rounded.Wifi, null, tint = PL.gold.copy(alpha = 0.55f), modifier = Modifier.size(14.dp))
            }

            // Pulsing radial glow behind the core
            Box(Modifier.size(190.dp).graphicsLayer { scaleX = coreScale; scaleY = coreScale }
                .background(Brush.radialGradient(
                    listOf(accent.copy(alpha = 0.12f * (glowPulse / 0.85f)), Color.Transparent)
                ), CircleShape))

            // ── CONNECTED: expanding ripple waves radiating from the core ──
            if (connected) {
                val ripple = rememberInfiniteTransition(label = "ripple")
                val r1 by ripple.animateFloat(0.5f, 1.5f, infiniteRepeatable(tween(2000, easing = FastOutSlowInEasing)), label = "r1")
                val a1 by ripple.animateFloat(0.5f, 0f, infiniteRepeatable(tween(2000, easing = LinearEasing)), label = "a1")
                val r2 by ripple.animateFloat(0.5f, 1.5f, infiniteRepeatable(tween(2000, easing = FastOutSlowInEasing, delayMillis = 1000)), label = "r2")
                val a2 by ripple.animateFloat(0.5f, 0f, infiniteRepeatable(tween(2000, easing = LinearEasing, delayMillis = 1000)), label = "a2")
                Box(Modifier.size(120.dp).graphicsLayer { scaleX = r1; scaleY = r1; alpha = a1 }
                    .border(1.5.dp, PL.green, CircleShape))
                Box(Modifier.size(120.dp).graphicsLayer { scaleX = r2; scaleY = r2; alpha = a2 }
                    .border(1.5.dp, PL.green.copy(alpha = 0.7f), CircleShape))
            }

            // Ring system + orbiting particles
            Box(Modifier.size(176.dp).graphicsLayer { translationY = floatY * 2 }, contentAlignment = Alignment.Center) {
                Canvas(Modifier.fillMaxSize()) {
                    val c = center
                    val rOuter = size.minDimension / 2f - 2f
                    val rInner = rOuter - 16f
                    val ringA = if (connected) PL.green else PL.gold
                    // Outer ring-track — gold-dominant gradient
                    drawCircle(
                        brush = Brush.sweepGradient(listOf(
                            ringA.copy(alpha = 0.35f), ringA.copy(alpha = 0.08f),
                            ringA.copy(alpha = 0.20f), ringA.copy(alpha = 0.35f)
                        ), center = c),
                        radius = rOuter, style = Stroke(width = 1.5f)
                    )
                    // Inner ring-track: spins reverse, soft gold→transparent
                    rotate(spinRev, c) {
                        drawCircle(
                            brush = Brush.sweepGradient(listOf(
                                ringA.copy(alpha = 0.25f), Color.Transparent,
                                ringA.copy(alpha = 0.12f), ringA.copy(alpha = 0.25f)
                            ), center = c),
                            radius = rInner, style = Stroke(width = 1f)
                        )
                    }
                    // CONNECTED: fast bright comet arc sweeping the outer track
                    if (connected) {
                        rotate(orbit * 2.2f, c) {
                            drawArc(
                                brush = Brush.sweepGradient(listOf(
                                    Color.Transparent, Color.Transparent,
                                    PL.green.copy(alpha = 0.9f)
                                ), center = c),
                                startAngle = 0f, sweepAngle = 80f, useCenter = false,
                                topLeft = Offset(c.x - rOuter, c.y - rOuter),
                                size = androidx.compose.ui.geometry.Size(rOuter * 2, rOuter * 2),
                                style = Stroke(width = 3f, cap = StrokeCap.Round)
                            )
                        }
                    }
                    // Spinning dot pair on the outer track
                    rotate(spin, c) {
                        drawCircle(PL.gold, radius = 3.5f, center = Offset(c.x, c.y - rOuter))
                        drawCircle(PL.gold.copy(alpha = 0.4f), radius = 7f, center = Offset(c.x, c.y - rOuter))
                        drawCircle(ringA, radius = 3f, center = Offset(c.x, c.y + rOuter))
                        drawCircle(ringA.copy(alpha = 0.4f), radius = 6f, center = Offset(c.x, c.y + rOuter))
                    }
                    // Orbiting particles — gold pair, one tiny indigo accent
                    rotate(orbit, c) {
                        drawCircle(PL.gold, radius = 2.5f, center = Offset(c.x + rOuter * 0.62f, c.y))
                        drawCircle(PL.gold.copy(alpha = 0.4f), radius = 6f, center = Offset(c.x + rOuter * 0.62f, c.y))
                    }
                    rotate(orbitRev, c) {
                        drawCircle(PL.indigo.copy(alpha = 0.8f), radius = 1.8f, center = Offset(c.x + rOuter * 0.44f, c.y))
                    }
                }

                // Floating core button with glow halo + breathing outer ring
                Box(contentAlignment = Alignment.Center, modifier = Modifier.graphicsLayer { translationY = floatY * 2 }) {
                    Box(Modifier.size(92.dp).graphicsLayer { scaleX = breathe; scaleY = breathe }
                        .border(1.dp, accent.copy(alpha = 0.18f), CircleShape))
                    Box(Modifier.size(76.dp)
                        .background(Brush.radialGradient(listOf(accent.copy(alpha = 0.35f), Color.Transparent), radius = 95f), CircleShape))
                    Box(Modifier.size(76.dp)
                        .shadow(26.dp, CircleShape, clip = false, ambientColor = accent, spotColor = accent)
                        .clip(CircleShape)
                        .background(Brush.linearGradient(
                            if (connected) listOf(Color(0xFF34D399), PL.green, Color(0xFF059669))
                            else listOf(PL.goldSoft, PL.gold, PL.goldDeep)
                        ))
                        .border(2.dp, Color.White.copy(alpha = 0.18f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        // Inner sheen
                        Box(Modifier.matchParentSize().background(Brush.verticalGradient(
                            listOf(Color.White.copy(alpha = 0.22f), Color.Transparent, Color.Black.copy(alpha = 0.08f)))))
                        if (connected) {
                            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                                Text("LIVE", fontSize = 8.sp, fontWeight = FontWeight.ExtraBold, color = Color.White, letterSpacing = 1.8.sp)
                                Text(elapsed, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, color = Color.White, letterSpacing = (-0.5).sp, fontFamily = FontFamily.Monospace)
                            }
                        } else {
                            Icon(Icons.Rounded.Wifi, null, tint = Color.White, modifier = Modifier.size(30.dp))
                        }
                    }
                }
            }

            // Connected IP bar (below the core button)
            if (connected) {
                Row(Modifier.align(Alignment.BottomCenter).padding(bottom = 2.dp), horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.CenterVertically) {
                    IpPill("YOU", myIp)
                    Box(Modifier.size(3.dp).clip(CircleShape).background(PL.green.copy(alpha = 0.6f)))
                    IpPill("PEER", peerIp)
                }
            }
        }
        // Core status text
        Spacer(Modifier.height(6.dp))
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
            Text(mainLabel, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = PL.inkSoft)
            Text(subLabel, fontSize = 11.sp, fontWeight = FontWeight.Medium,
                color = PL.muted,
                textAlign = TextAlign.Center, maxLines = 2, overflow = TextOverflow.Ellipsis, modifier = Modifier.padding(top = 3.dp))
        }
    }
}

@Composable private fun IpPill(label: String, ip: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp),
        modifier = Modifier.clip(RoundedCornerShape(100.dp)).background(Color.White.copy(alpha = 0.05f)).padding(horizontal = 9.dp, vertical = 4.dp)) {
        Text(label, fontSize = 8.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 0.8.sp)
        Text(ip, fontSize = 9.sp, fontWeight = FontWeight.SemiBold, color = PL.inkSoft, fontFamily = FontFamily.Monospace)
    }
}


/* ─── Stat Cards ─── */
@Composable private fun StatCard(modifier: Modifier, label: String, value: Long, color: Color, up: Boolean) {
    Box(modifier.glass(20.dp)) {
        // Top gradient hairline
        Box(Modifier.fillMaxWidth().height(2.dp).align(Alignment.TopCenter)
            .background(Brush.horizontalGradient(listOf(Color.Transparent, color.copy(alpha = 0.6f), Color.Transparent))))
        Column(Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(if (up) Icons.Rounded.ArrowUpward else Icons.Rounded.ArrowDownward, null, tint = color, modifier = Modifier.size(14.dp))
                Box {
                    // soft glow under number
                    Text("%,d".format(value), fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, color = color.copy(alpha = 0.35f),
                        modifier = Modifier.blur(8.dp))
                    Text("%,d".format(value), fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, color = color)
                }
            }
            Spacer(Modifier.height(6.dp))
            Text(label.uppercase(), fontSize = 10.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 1.sp)
        }
    }
}

/* ─── Empty Peers ─── */
@Composable private fun EmptyPeers(discoveryState: DiscoveryState, onRefresh: () -> Unit) {
    val text = when (discoveryState) {
        DiscoveryState.WAITING_FOR_WIFI -> "Connect to Wi-Fi or turn on a hotspot"
        DiscoveryState.ERROR -> "Discovery needs attention — tap refresh"
        DiscoveryState.PAUSED_FOR_SESSION -> "Discovery paused while a session is active"
        else -> "Searching for nearby players…"
    }
    val activelySearching = discoveryState == DiscoveryState.SEARCHING || discoveryState == DiscoveryState.PEERS_FOUND
    Row(Modifier.fillMaxWidth().glass(14.dp).padding(12.dp, 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        if (activelySearching) {
            CircularProgressIndicator(modifier = Modifier.size(15.dp), strokeWidth = 1.5.dp, color = PL.gold)
        } else {
            Icon(Icons.Rounded.WifiOff, contentDescription = null, tint = PL.muted, modifier = Modifier.size(16.dp))
        }
        Text(text, modifier = Modifier.weight(1f), fontSize = 12.sp, color = PL.muted, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
        IconButton(onClick = onRefresh, enabled = discoveryState != DiscoveryState.PAUSED_FOR_SESSION, modifier = Modifier.size(32.dp)) {
            Icon(Icons.Rounded.Refresh, contentDescription = "Refresh discovery", tint = if (discoveryState == DiscoveryState.PAUSED_FOR_SESSION) PL.muted else PL.gold, modifier = Modifier.size(17.dp))
        }
    }
}

/* ─── Peer Row ─── */
@Composable private fun PeerRow(peer: PeerInfo, isConnected: Boolean, isNew: Boolean = false, onTap: () -> Unit) {
    val initials = peer.name.split(" ").filter { it.isNotBlank() }.take(2).joinToString("") { it.first().uppercase() }

    // ── "New peer" bounce/pulse animation ──────────────────────────────
    // When a peer first appears in the discovery list, we play a gentle
    // upward-bounce + gold-glow pulse for 6 seconds to signal "look at me,
    // a new peer just showed up". The pulse repeats every 1 second (the
    // "lively upward movement at every sec for 6 secs" the user asked for).
    // After 6 seconds the animation stops and the row settles into its
    // normal state.
    //
    // We use plain Float vars (not State) for the non-animated case so we
    // avoid the overload-resolution mess with mutableStateOf(0f) as a
    // fallback — when isNew is false there's no animation to drive, so we
    // just want a constant 0f. The .value accessor on the animated case
    // returns a plain Float, so both branches type-check as Float.
    //
    // Using tween + RepeatMode.Restart gives a simple 0 → -3 → (restart) → 0 → -3 → ...
    // pattern — one bounce per second. Not as crisp as a keyframes curve
    // but compiles cleanly and reads the same to the user.
    val bounceOffset: Float
    val glowAlpha: Float
    if (isNew) {
        val bounceAnim = rememberInfiniteTransition(label = "peerBounce_${peer.ip}")
        // Upward nudge: 0 → -3dp, 1-second period, restart each cycle.
        // Positional float args + named spec/label — matches the pattern used
        // elsewhere in the active UI animation code.
        bounceOffset = bounceAnim.animateFloat(
            0f, -3f,
            infiniteRepeatable(
                tween(1000, easing = FastOutSlowInEasing),
                RepeatMode.Restart
            ),
            label = "bounceY"
        ).value
        // Gold glow pulse: 0.15 ↔ 0.45 alpha, synced with the bounce.
        glowAlpha = bounceAnim.animateFloat(
            0.15f, 0.45f,
            infiniteRepeatable(
                tween(1000, easing = FastOutSlowInEasing),
                RepeatMode.Reverse
            ),
            label = "glow"
        ).value
    } else {
        bounceOffset = 0f
        glowAlpha = 0f
    }

    Box(Modifier.fillMaxWidth().height(IntrinsicSize.Min)
        .graphicsLayer { translationY = bounceOffset.dp.toPx() }
        .then(
            if (isNew) Modifier.shadow(
                12.dp, RoundedCornerShape(16.dp), clip = false,
                ambientColor = PL.gold.copy(alpha = glowAlpha),
                spotColor = PL.gold.copy(alpha = glowAlpha)
            ) else Modifier
        )
        .glass(16.dp)
        .then(if (isConnected) Modifier.background(Brush.horizontalGradient(listOf(PL.green.copy(alpha = 0.05f), Color.White.copy(alpha = 0.02f))), RoundedCornerShape(16.dp)) else Modifier)
        .clickable(onClick = onTap)
    ) {
        // Left accent bar — pulses gold while the peer is "new"
        Box(Modifier.align(Alignment.CenterStart).width(3.dp).fillMaxHeight()
            .clip(RoundedCornerShape(topEnd = 3.dp, bottomEnd = 3.dp))
            .background(if (isConnected) PL.green else if (isNew) PL.gold.copy(alpha = glowAlpha) else PL.gold))
        Row(Modifier.padding(start = 13.dp, end = 12.dp, top = 10.dp, bottom = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            // Gold avatar — compact
            Box(Modifier.size(36.dp)
                .shadow(8.dp, RoundedCornerShape(9.dp), clip = false, ambientColor = PL.gold, spotColor = PL.gold)
                .clip(RoundedCornerShape(9.dp))
                .background(Brush.linearGradient(listOf(PL.gold, PL.goldDeep))), contentAlignment = Alignment.Center) {
                Box(Modifier.matchParentSize().background(Brush.linearGradient(listOf(Color.Transparent, Color.White.copy(alpha = 0.18f)))))
                Text(initials.ifBlank { "?" }, color = Color.White, fontWeight = FontWeight.ExtraBold, fontSize = 12.sp)
            }
            Spacer(Modifier.width(11.dp))
            Column(Modifier.weight(1f)) {
                Text(peer.name, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = PL.ink, maxLines = 1, overflow = TextOverflow.Ellipsis)
                Text(if (isConnected) "Connected · tap to disconnect" else "Tap to connect", fontSize = 11.sp, color = if (isConnected) PL.green else PL.muted)
            }
            val mi = Icons.Rounded.Wifi
            Box(Modifier.size(30.dp)
                .then(if (isConnected) Modifier.shadow(10.dp, RoundedCornerShape(8.dp), clip = false, ambientColor = PL.green, spotColor = PL.green) else Modifier)
                .clip(RoundedCornerShape(8.dp))
                .background(if (isConnected) PL.green else Color.White.copy(alpha = 0.04f))
                .border(1.dp, if (isConnected) PL.green else PL.line, RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center
            ) {
                Icon(if (isConnected) Icons.Rounded.Check else mi, null, tint = if (isConnected) Color.White else PL.gold, modifier = Modifier.size(13.dp))
            }
        }
    }
}

@Composable
private fun SessionStartingBar(sessionState: VpnSessionState, onCancel: () -> Unit) {
    val label = if (sessionState == VpnSessionState.VERIFYING)
        "Checking the Wi-Fi tunnel both ways…" else "Starting PeerLink…"
    Row(Modifier.fillMaxWidth().glass(16.dp).padding(14.dp, 10.dp), verticalAlignment = Alignment.CenterVertically) {
        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp, color = PL.gold)
        Spacer(Modifier.width(10.dp))
        Text(label, modifier = Modifier.weight(1f), color = PL.inkSoft, fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
        TextButton(onClick = onCancel) { Text("Cancel", color = PL.red, fontSize = 12.sp, fontWeight = FontWeight.Bold) }
    }
}

/* ─── Slide-to-Disconnect bar ───
 * Replaces the "Players nearby" list once a Wi-Fi session is live.
 * The user has to drag the knob from left → right across ~85% of the track
 * to confirm disconnect; releasing early springs the knob back. This prevents
 * accidental disconnects from a stray tap.
 */
@Composable private fun SlideToDisconnectBar(peerName: String?, disconnecting: Boolean, onDisconnect: () -> Unit) {
    var trackWidthPx by remember { mutableStateOf(0f) }
    var dragOffsetPx by remember { mutableStateOf(0f) }
    var disconnectRequested by remember { mutableStateOf(false) }
    val density = LocalDensity.current

    val trackHeightDp = 56.dp
    val knobSizeDp    = 44.dp
    val sidePaddingDp = 6.dp
    val trackHeightPx = with(density) { trackHeightDp.toPx() }
    val knobSizePx    = with(density) { knobSizeDp.toPx() }
    val sidePaddingPx = with(density) { sidePaddingDp.toPx() }
    val maxDragPx     = (trackWidthPx - knobSizePx - 2 * sidePaddingPx).coerceAtLeast(0f)
    val thresholdPx   = maxDragPx * 0.85f
    val atThreshold   = dragOffsetPx >= thresholdPx && thresholdPx > 0f
    val stopping = disconnecting || disconnectRequested

    LaunchedEffect(disconnecting) {
        if (disconnecting) disconnectRequested = true
    }

    // Use rememberUpdatedState so the gesture detector (keyed on Unit) always
    // sees the latest values without restarting when they change. This was a
    // major bug: pointerInput(maxDragPx) would restart and cancel the gesture
    // mid-drag whenever the track was re-measured.
    val maxDragPxState by rememberUpdatedState(maxDragPx)
    val thresholdPxState by rememberUpdatedState(thresholdPx)
    val stoppingState by rememberUpdatedState(stopping)
    val onDisconnectState by rememberUpdatedState(onDisconnect)

    // Smooth spring-back when the user releases before reaching the threshold.
    val animatedOffset by animateFloatAsState(
        targetValue = dragOffsetPx,
        animationSpec = spring(dampingRatio = 0.55f, stiffness = 320f),
        label = "slideSpring"
    )
    // Knob scales up slightly as the user approaches the threshold for feedback.
    val knobScale by animateFloatAsState(
        targetValue = if (atThreshold) 1.05f else 1f,
        animationSpec = spring(dampingRatio = 0.6f, stiffness = 380f),
        label = "knobScale"
    )

    Box(
        Modifier
            .fillMaxWidth()
            .height(trackHeightDp)
            .onGloballyPositioned { trackWidthPx = it.size.width.toFloat() }
            .clip(RoundedCornerShape(16.dp))
            .background(
                Brush.linearGradient(
                    listOf(
                        PL.red.copy(alpha = if (atThreshold) 0.22f else 0.10f),
                        PL.surface
                    )
                )
            )
            .border(
                1.dp,
                if (atThreshold) PL.red.copy(alpha = 0.55f) else PL.red.copy(alpha = 0.25f),
                RoundedCornerShape(16.dp)
            )
            // ── Gesture detection on the FULL TRACK (not just the knob) ──
            // Previously the pointerInput was on the 44dp knob, so the user
            // had to hit a tiny target. Now the entire 56dp-tall track is
            // the drag surface. Also switched from detectHorizontalDragGestures
            // (which cancels on diagonal initial motion) to detectDragGestures
            // (which accepts any direction) with a horizontal-only clamp.
            // pointerInput(Unit) + rememberUpdatedState means the gesture
            // detector never restarts mid-drag, even if the track is
            // re-measured.
            .pointerInput(Unit) {
                detectDragGestures(
                    onDragEnd = {
                        if (!stoppingState && dragOffsetPx >= thresholdPxState && thresholdPxState > 0f) {
                            disconnectRequested = true
                            dragOffsetPx = maxDragPxState
                            onDisconnectState()
                        } else if (!stoppingState) {
                            dragOffsetPx = 0f
                        }
                    },
                    onDragCancel = { if (!stoppingState) dragOffsetPx = 0f }
                ) { _, dragAmount ->
                    if (!stoppingState) {
                        // Only accumulate horizontal drag; ignore vertical.
                        dragOffsetPx = (dragOffsetPx + dragAmount.x).coerceIn(0f, maxDragPxState)
                    }
                }
            }
    ) {
        // ── Track label ──
        Box(
            Modifier
                .fillMaxSize()
                .padding(start = sidePaddingDp + knobSizeDp + 10.dp, end = sidePaddingDp + 10.dp),
            contentAlignment = Alignment.CenterEnd
        ) {
            val label = if (stopping) "Disconnecting…"
                else if (atThreshold) "Release to disconnect"
                else "Slide to disconnect" + (peerName?.takeIf { it.isNotBlank() }?.let { " · $it" } ?: "")
            Text(
                label,
                color = if (atThreshold) PL.red else PL.red.copy(alpha = 0.85f),
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                letterSpacing = 0.4.sp,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }

        // ── Draggable knob (visual only — gesture is on the track above) ──
        val knobTopPx = (trackHeightPx - knobSizePx) / 2f
        Box(
            Modifier
                .offset { IntOffset((sidePaddingPx + animatedOffset).roundToInt(), knobTopPx.roundToInt()) }
                .size(knobSizeDp)
                .graphicsLayer { scaleX = knobScale; scaleY = knobScale }
                .clip(RoundedCornerShape(12.dp))
                .background(
                    Brush.linearGradient(
                        listOf(PL.red, PL.red.copy(alpha = 0.82f))
                    )
                )
                .border(1.dp, Color.White.copy(alpha = 0.20f), RoundedCornerShape(12.dp)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                Icons.Rounded.ChevronRight,
                null,
                tint = Color.White,
                modifier = Modifier.size(22.dp)
            )
        }
    }



}

/* ─── Prime Deck (5 tools) ─── */
@Composable private fun PrimeDeck(isPaired: Boolean, callBlockOn: Boolean, onToggle: (String, Boolean) -> Boolean, ctx: Context) {
    val gm = GodModeManager
    // Fixed: Auto mode now properly reads its state from prefs
    var autoOn by remember { mutableStateOf(gm.isAutoConnectEnabled()) }
    val tools = listOf(
        Tool("ram", "Game", Icons.Rounded.SportsEsports),
        Tool("calls", "No Calls", Icons.Rounded.PhoneDisabled),
        Tool("auto", "Auto", Icons.Rounded.Autorenew)
    )
    val states = remember(isPaired, callBlockOn, autoOn) {
        mutableStateMapOf(
            "ram" to gm.getKeepGameInRam(),
            "calls" to callBlockOn,
            "auto" to autoOn
        )
    }
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        tools.forEach { t ->
            val on = isPaired && states[t.key] == true
            val glowColor = if (t.key == "calls") PL.red else PL.gold
            val activeBrush = if (t.key == "calls") Brush.verticalGradient(listOf(PL.red, Color(0xFFB91C1C)))
                else Brush.verticalGradient(listOf(PL.gold, PL.goldDeep))
            Box(Modifier.weight(1f).aspectRatio(0.95f)
                .then(if (on) Modifier.shadow(16.dp, RoundedCornerShape(14.dp), clip = false, ambientColor = glowColor, spotColor = glowColor) else Modifier)
                .clip(RoundedCornerShape(14.dp))
                .then(if (on) Modifier.background(activeBrush) else Modifier.background(Brush.linearGradient(listOf(Color.White.copy(alpha = 0.05f), Color.White.copy(alpha = 0.02f)))))
                .border(1.dp, if (on) Color.White.copy(alpha = 0.18f) else PL.line, RoundedCornerShape(14.dp))
                .alpha(if (isPaired) 1f else 0.35f)
                .clickable(enabled = isPaired) {
                    val want = !(states[t.key] ?: false)
                    if (onToggle(t.key, want)) {
                        states[t.key] = want
                        if (t.key == "auto") autoOn = want
                        // NOTE: "calls" is handled entirely by onToggle → actions.setCallBlock(want)
                        // → ensureCallBlockPermissionThen → CallMonitorService.start/stop.
                        // Do NOT call CallMonitorService directly here — it bypasses the runtime
                        // ANSWER_PHONE_CALLS permission check and crashes on Android 14+.
                    }
                },
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Icon(t.icon, null, tint = if (on) Color.White else PL.inkSoft, modifier = Modifier.size(20.dp))
                    Text(t.label, fontSize = 9.sp, fontWeight = FontWeight.Bold, color = if (on) Color.White.copy(alpha = 0.92f) else PL.muted)
                }
            }
        }
    }
}

private data class Tool(val key: String, val label: String, val icon: ImageVector)

/* ─── Coin Page ─── */
@Composable private fun CoinPage() {
    Column(Modifier.fillMaxSize().padding(horizontal = 16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Spacer(Modifier.height(4.dp))
        SectionTitle("PeerCoins")
        Spacer(Modifier.height(2.dp))
        DarkCard(padding = 24.dp) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
                Box(Modifier.size(56.dp).clip(CircleShape).background(Brush.linearGradient(listOf(PL.gold, PL.goldDeep))), contentAlignment = Alignment.Center) {
                    Icon(Icons.Rounded.Star, null, tint = Color.White, modifier = Modifier.size(26.dp))
                }
                Spacer(Modifier.height(10.dp))
                Text("0", fontSize = 44.sp, fontWeight = FontWeight.ExtraBold, color = PL.gold, letterSpacing = (-2).sp)
                Text("PEERCOINS", fontSize = 10.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 2.5.sp)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            CoinTile(Modifier.weight(1f), "Matches", "0", PL.ink)
            CoinTile(Modifier.weight(1f), "Wins", "0", PL.green)
        }
        Text("Earn PeerCoins by playing and winning matches over PeerLink. Beat your rival by more, earn more. Redemption is coming soon.", fontSize = 12.sp, color = PL.inkSoft, lineHeight = 18.sp, modifier = Modifier.padding(4.dp))
    }
}

@Composable private fun CoinTile(m: Modifier, label: String, value: String, c: Color) {
    DarkCard(m, padding = 16.dp) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.fillMaxWidth()) {
            Text(value, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold, color = c)
            Text(label.uppercase(), fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 1.sp)
        }
    }
}

@Composable private fun PagerDots(current: Int) {
    Row(Modifier.fillMaxWidth().padding(vertical = 10.dp), horizontalArrangement = Arrangement.Center) {
        repeat(2) { i ->
            val on = i == current
            Box(Modifier.padding(horizontal = 3.5.dp).height(6.dp).width(if (on) 22.dp else 6.dp).clip(RoundedCornerShape(3.dp))
                .background(if (on) PL.gold else PL.lineSoft))
        }
    }
}

/* ═════════ SIDE PANELS ═════════ */
@Composable private fun SidePanel(open: Boolean, fromLeft: Boolean, onClose: () -> Unit, content: @Composable ColumnScope.() -> Unit) {
    AnimatedVisibility(open, enter = slideInHorizontally(tween(360)) { if (fromLeft) -it else it },
        exit = slideOutHorizontally(tween(300)) { if (fromLeft) -it else it }, modifier = Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxSize()) {
            if (!fromLeft) Spacer(Modifier.weight(1f))
            Box(Modifier.fillMaxHeight().fillMaxWidth(0.80f).statusBarsPadding()
                .shadow(30.dp, if (fromLeft) RoundedCornerShape(topEnd = 24.dp, bottomEnd = 24.dp) else RoundedCornerShape(topStart = 24.dp, bottomStart = 24.dp), clip = false)
                .clip(if (fromLeft) RoundedCornerShape(topEnd = 24.dp, bottomEnd = 24.dp) else RoundedCornerShape(topStart = 24.dp, bottomStart = 24.dp))
                .background(Brush.verticalGradient(listOf(Color(0xFF111827), Color(0xFF0B0F19))))
                .border(
                    width = 1.dp,
                    color = Color.White.copy(alpha = 0.06f),
                    shape = if (fromLeft) RoundedCornerShape(topEnd = 24.dp, bottomEnd = 24.dp) else RoundedCornerShape(topStart = 24.dp, bottomStart = 24.dp)
                )
            ) {
                Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState()), content = content)
            }
            if (fromLeft) Spacer(Modifier.weight(1f))
        }
    }
}

@Composable private fun SettingsMenu(isPaired: Boolean, onSetupPrime: () -> Unit) {
    var open by remember { mutableStateOf(-1) }
    val ctx = androidx.compose.ui.platform.LocalContext.current
    val prefs = remember { ctx.getSharedPreferences("peerlink_prefs", Context.MODE_PRIVATE) }
    var jitterOn by remember { mutableStateOf(prefs.getBoolean("jitter_buffer_enabled", true)) }
    Text("Menu", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink, modifier = Modifier.padding(bottom = 14.dp, start = 4.dp))
    Acc(0, open, "Settings", "Tools, blocking & Prime setup", Icons.Rounded.Tune, { open = if (open == 0) -1 else 0 }) {
        // Jitter Buffer — live toggle (smooths packet timing at the cost of a tiny delay)
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(10.dp))
            .clickable {
                jitterOn = !jitterOn
                prefs.edit().putBoolean("jitter_buffer_enabled", jitterOn).apply()
            }
            .padding(vertical = 7.dp, horizontal = 2.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Jitter Buffer", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = PL.ink)
                Text("Smooths packet timing for steadier gameplay", fontSize = 10.5.sp, color = PL.muted)
            }
            // Slim pill switch
            Box(Modifier.width(38.dp).height(22.dp).clip(RoundedCornerShape(100.dp))
                .background(if (jitterOn) PL.gold.copy(alpha = 0.25f) else Color.White.copy(alpha = 0.06f))
                .border(1.dp, if (jitterOn) PL.gold.copy(alpha = 0.5f) else PL.line, RoundedCornerShape(100.dp)),
                contentAlignment = if (jitterOn) Alignment.CenterEnd else Alignment.CenterStart) {
                Box(Modifier.padding(3.dp).size(16.dp).clip(CircleShape)
                    .background(if (jitterOn) PL.gold else PL.muted))
            }
        }
        Spacer(Modifier.height(4.dp))
        SettingRow("Call Blocker", "Silence calls during gameplay")
        SettingRow("Game Active", "Reduce background restrictions for eFootball")
        SettingRow("Wi-Fi Low-Latency", "Requests Android low-latency mode during a session")
        Spacer(Modifier.height(6.dp))
        GhostBtn("Set up Prime Mode", Icons.Rounded.AutoAwesome) { onSetupPrime() }
    }
    Acc(1, open, if (isPaired) "Prime Mode \u00b7 Ready" else "Prime Mode \u00b7 Not set up", "What it does & every feature", Icons.Rounded.Bolt, { open = if (open == 1) -1 else 1 }) {
        Para("Prime Mode keeps a small privileged control path for supported session actions. Pair once, then activate it when you want those tools available.")
                        Feat("Game Active", "Keeps eFootball in Android's active standby bucket while you play.")
        Feat("No Calls", "Silently rejects calls only while you're playing.")
        Feat("Auto", "Uses Prime to enable Wi-Fi when PeerLink needs it, then restores your previous state.")
    }
    Acc(2, open, "Rewards", "How PeerCoins work", Icons.Rounded.Stars, { open = if (open == 2) -1 else 2 }) {
        Para("You earn PeerCoins by playing and winning matches over PeerLink.")
        Para("Goal difference sweetens it \u2014 beat your rival by more, earn more.")
    }
}

@Composable private fun AdminMenu(ctx: Context, actions: PeerLinkActions) {
    var open by remember { mutableStateOf(0) }
    Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.padding(bottom = 14.dp, start = 4.dp)) {
        Text("Admin", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink)
        Spacer(Modifier.width(8.dp))
        Box(Modifier.clip(RoundedCornerShape(50)).background(PL.gold.copy(alpha = 0.12f)).padding(horizontal = 8.dp, vertical = 3.dp)) {
            Text("PRIVATE", fontSize = 8.sp, fontWeight = FontWeight.ExtraBold, color = PL.gold, letterSpacing = 1.2.sp)
        }
    }
    var devId by remember { mutableStateOf(TextFieldValue("")) }
    var key by remember { mutableStateOf("") }
    val clip = remember { ctx.getSystemService(Context.CLIPBOARD_SERVICE) as android.content.ClipboardManager }

    Acc(0, open, "Key Generator", "Issue an access key", Icons.Rounded.VpnKey, { open = if (open == 0) -1 else 0 }) {
        Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(PL.surface).padding(12.dp)) {
            Column {
                Text("THIS DEVICE ID", fontSize = 8.5.sp, color = PL.muted, letterSpacing = 1.sp, fontWeight = FontWeight.Bold)
                Text(actions.deviceId.ifBlank { "\u2014" }, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = PL.gold, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
            }
        }
        Spacer(Modifier.height(10.dp))
        Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(11.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(11.dp)).padding(10.dp, 9.dp)) {
            BasicTextField(devId, { devId = it.copy(text = it.text.uppercase()); key = "" }, singleLine = true,
                textStyle = androidx.compose.ui.text.TextStyle(PL.ink, 15.sp, FontWeight.SemiBold, fontFamily = FontFamily.Monospace),
                cursorBrush = SolidColor(PL.gold), modifier = Modifier.fillMaxWidth(),
                decorationBox = { inner -> Box { if (devId.text.isEmpty()) Text("Enter device ID", color = PL.muted, fontSize = 15.sp); inner() } })
        }
        Spacer(Modifier.height(10.dp))
        GhostBtn("Generate key", Icons.Rounded.Bolt) { if (devId.text.isNotBlank()) key = actions.generateKey(devId.text.trim()) }
        if (key.isNotBlank()) {
            Spacer(Modifier.height(10.dp))
            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(PL.surface).border(1.dp, PL.gold.copy(alpha = 0.4f), RoundedCornerShape(12.dp))
                .clickable { clip.setPrimaryClip(android.content.ClipData.newPlainText("key", key)); Toast.makeText(ctx, "Key copied", Toast.LENGTH_SHORT).show() }
                .padding(12.dp), contentAlignment = Alignment.Center) {
                Text(key, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = PL.gold, fontFamily = FontFamily.Monospace, letterSpacing = 1.5.sp)
            }
        }
    }

    var crashCount by remember { mutableStateOf(CrashLogger.getCrashCount(ctx)) }
    var report by remember { mutableStateOf<String?>(null) }
    Acc(1, open, "Crash Logs", "Diagnostics", Icons.Rounded.Warning, { open = if (open == 1) -1 else 1 }) {
        Text(if (crashCount > 0) "$crashCount crash${if (crashCount != 1) "es" else ""} recorded" else "No crashes recorded", fontSize = 12.5.sp, color = PL.inkSoft, fontWeight = FontWeight.SemiBold)
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            GhostBtn(if (report == null) "View" else "Hide", Icons.Rounded.Visibility, Modifier.weight(1f)) { report = if (report == null) (CrashLogger.getLastReport(ctx) ?: "No report") else null }
            GhostBtn("Copy", Icons.Rounded.ContentCopy, Modifier.weight(1f)) {
                val r = CrashLogger.getLastReport(ctx)
                if (r.isNullOrBlank()) Toast.makeText(ctx, "No crash report to copy", Toast.LENGTH_SHORT).show()
                else {
                    clip.setPrimaryClip(android.content.ClipData.newPlainText("crash", r))
                    Toast.makeText(ctx, "Crash log copied", Toast.LENGTH_SHORT).show()
                }
            }
            GhostBtn("Clear", Icons.Rounded.Delete, Modifier.weight(1f)) { CrashLogger.clearReport(ctx); crashCount = 0; report = null }
        }
        if (report != null) {
            Spacer(Modifier.height(10.dp))
            Box(Modifier.fillMaxWidth().heightIn(max = 180.dp).clip(RoundedCornerShape(10.dp)).background(PL.surface).verticalScroll(rememberScrollState()).padding(10.dp)) {
                Text(report ?: "", fontSize = 10.sp, color = PL.inkSoft, fontFamily = FontFamily.Monospace)
            }
        }
    }

    Acc(2, open, "Match Logs", "Save & export records", Icons.Rounded.Description, { open = if (open == 2) -1 else 2 }) {
        SettingRow("Save match logs", "Record every match")
        Spacer(Modifier.height(6.dp))
        GhostBtn("Export match logs", Icons.Rounded.FileDownload) { actions.exportMatchLogs(); Toast.makeText(ctx, "Exporting\u2026", Toast.LENGTH_SHORT).show() }
    }
}

@Composable private fun AdminUnlockDialog(onClose: () -> Unit, onSubmit: (String) -> Boolean) {
    var k by remember { mutableStateOf(TextFieldValue("")) }
    var err by remember { mutableStateOf(false) }
    AlertDialog(onDismissRequest = onClose,
        title = { Text("Admin access", fontWeight = FontWeight.Bold, color = PL.ink) },
        text = { Column {
            Text("Enter the master key to unlock admin tools.", fontSize = 13.sp, color = PL.inkSoft)
            Spacer(Modifier.height(12.dp))
            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(11.dp)).background(PL.surface).border(1.5.dp, if (err) PL.red else PL.line, RoundedCornerShape(11.dp)).padding(10.dp, 9.dp)) {
                BasicTextField(k, { k = it; err = false }, singleLine = true,
                    textStyle = androidx.compose.ui.text.TextStyle(PL.ink, 16.sp, FontWeight.SemiBold, fontFamily = FontFamily.Monospace),
                    cursorBrush = SolidColor(PL.gold), modifier = Modifier.fillMaxWidth(),
                    decorationBox = { inner -> Box { if (k.text.isEmpty()) Text("MASTER KEY", color = PL.muted, fontSize = 15.sp, letterSpacing = 1.sp); inner() } })
            }
            if (err) { Spacer(Modifier.height(6.dp)); Text("Incorrect key", color = PL.red, fontSize = 11.sp) }
        } },
        confirmButton = { TextButton({ if (!onSubmit(k.text)) err = true }) { Text("Unlock", color = PL.gold, fontWeight = FontWeight.Bold) } },
        dismissButton = { TextButton(onClose) { Text("Cancel", color = PL.muted) } }, containerColor = PL.surface)
}

@Composable private fun Acc(idx: Int, open: Int, title: String, sub: String, icon: ImageVector, onClick: () -> Unit, body: @Composable ColumnScope.() -> Unit) {
    Column(Modifier.fillMaxWidth().padding(bottom = 10.dp)
        .clip(RoundedCornerShape(16.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(16.dp))
    ) {
        Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).clip(RoundedCornerShape(12.dp)).background(PL.gold.copy(alpha = 0.1f)), contentAlignment = Alignment.Center) {
                Icon(icon, null, tint = PL.gold, modifier = Modifier.size(19.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(title, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = PL.ink)
                Text(sub, fontSize = 11.sp, color = PL.muted)
            }
            Icon(if (open == idx) Icons.Rounded.ExpandLess else Icons.Rounded.ExpandMore, null, tint = PL.muted)
        }
        AnimatedVisibility(open == idx) { Column(Modifier.padding(15.dp, 0.dp, 15.dp, 14.dp), content = body) }
    }
}

@Composable private fun GhostBtn(label: String, icon: ImageVector, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Box(modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp))
        .background(Brush.linearGradient(listOf(PL.gold.copy(alpha = 0.16f), PL.gold.copy(alpha = 0.07f))))
        .border(1.dp, PL.gold.copy(alpha = 0.3f), RoundedCornerShape(12.dp))
        .alpha(if (enabled) 1f else 0.5f).clickable(enabled = enabled, onClick = onClick).padding(12.dp), contentAlignment = Alignment.Center) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
            Icon(icon, null, tint = PL.gold, modifier = Modifier.size(16.dp))
            Text(label, color = PL.gold, fontWeight = FontWeight.Bold, fontSize = 13.sp)
        }
    }
}

@Composable private fun Para(t: String) = Text(t, fontSize = 12.5.sp, color = PL.inkSoft, lineHeight = 19.sp, modifier = Modifier.padding(bottom = 10.dp))
@Composable private fun Feat(t: String, d: String) = Column(Modifier.padding(bottom = 9.dp)) {
    Text(t, fontSize = 12.5.sp, fontWeight = FontWeight.Bold, color = PL.ink)
    Text(d, fontSize = 11.5.sp, color = PL.muted, lineHeight = 16.sp)
}
@Composable private fun SettingRow(t: String, d: String) {
    var on by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth().padding(vertical = 9.dp), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) { Text(t, fontSize = 13.5.sp, fontWeight = FontWeight.Bold, color = PL.ink); Text(d, fontSize = 11.sp, color = PL.muted) }
        Switch(on, { on = it }, colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = PL.gold))
    }
}

/* ───────────── Prime Mode setup — real GodMode backend ───────────── */
@Composable
fun PrimeSetupScreen(ctx: Context, onBack: () -> Unit) {
    val state by GodModeManager.state.collectAsState()
    val status by GodModeManager.status.collectAsState()
    val snap by GodModeManager.setupSnapshot.collectAsState()
    LaunchedEffect(Unit) { GodModeManager.refreshSetupState() }

    val isPaired = snap.pairedTrusted || snap.bootstrapped
    val isActive = state == GodModeManager.State.PRIME_MODE_ACTIVE
    val isBusy = state == GodModeManager.State.PAIRING || state == GodModeManager.State.CONNECTING ||
                 state == GodModeManager.State.BOOTSTRAPPING || state == GodModeManager.State.DISCOVERING
    var master by remember { mutableStateOf(GodModeManager.isApexMasterEnabled()) }

    val (heroLabel, heroColor) = when {
        isActive -> "Prime Mode Active" to PL.green
        state == GodModeManager.State.PAIRED_IDLE && snap.bootstrapped -> "Prime Mode Ready" to PL.green
        state == GodModeManager.State.PAIRED_IDLE -> "Paired — bootstrap pending" to PL.gold
        isBusy -> "Pairing…" to PL.indigo
        state == GodModeManager.State.ERROR -> "Prime Mode Error" to PL.red
        else -> "Not set up" to PL.muted
    }

    Column(Modifier.fillMaxSize().background(PL.bg).statusBarsPadding().verticalScroll(rememberScrollState())) {
        Row(Modifier.fillMaxWidth().padding(16.dp, 10.dp, 16.dp, 6.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(38.dp).clip(RoundedCornerShape(12.dp)).background(PL.surface).clickable { onBack() }, contentAlignment = Alignment.Center) {
                Icon(Icons.Rounded.ArrowBack, null, tint = PL.ink, modifier = Modifier.size(19.dp))
            }
            Spacer(Modifier.width(12.dp))
            Text("Prime Mode", fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink)
        }
        Column(Modifier.padding(16.dp, 4.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {

            // status hero
            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Column {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Box(Modifier.size(46.dp).clip(RoundedCornerShape(14.dp)).background(if (isPaired) PL.gold.copy(alpha = 0.16f) else PL.elevated), contentAlignment = Alignment.Center) {
                            Icon(if (isActive) Icons.Rounded.FlashOn else if (isPaired) Icons.Rounded.CheckCircle else Icons.Rounded.Lock, null, tint = if (isPaired) PL.gold else PL.muted, modifier = Modifier.size(22.dp))
                        }
                        Spacer(Modifier.width(13.dp))
                        Column(Modifier.weight(1f)) {
                            Text(heroLabel, fontSize = 16.sp, fontWeight = FontWeight.ExtraBold, color = PL.ink)
                            Text(status.ifBlank { "One-time pairing prepares Prime Mode" }, fontSize = 11.sp, color = PL.muted, lineHeight = 15.sp)
                        }
                        Box(Modifier.size(11.dp).clip(CircleShape).background(heroColor))
                    }
                    Spacer(Modifier.height(12.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        PrimeStatusPill(Modifier.weight(1f), "PAIR", snap.pairedTrusted || snap.bootstrapped)
                        PrimeStatusPill(Modifier.weight(1f), "BOOT", snap.bootstrapped)
                        PrimeStatusPill(Modifier.weight(1f), "SERVER", snap.primeServerAlive)
                    }
                }
            }

            if (!isPaired) {
                PrimeSetupStep("1", "Start pairing in PeerLink", "Tap below so PeerLink is ready to receive your pairing code. A notification will appear for the code.") {
                    GhostBtn(if (isBusy) "Starting…" else "Start pairing", Icons.Rounded.Bolt) { GodModeManager.startNotificationPairing(ctx) }
                }
                PrimeSetupStep("2", "Turn on Wireless Debugging", "Settings → Developer Options → Wireless Debugging → ON. Then tap \"Pair device with pairing code\" and note the 6-digit code.") {
                    GhostBtn("Open Developer Options", Icons.Rounded.Settings) { GodModeManager.openWirelessDebuggingSettings(ctx) }
                }
                PrimeSetupStep("3", "Enter the code in the notification", "PeerLink posts a notification — tap it and type the 6-digit pairing code from your phone. If it vanished, re-send it below.") {
                    GhostBtn("Re-send notification", Icons.Rounded.Notifications) { GodModeManager.startNotificationPairing(ctx) }
                }
            } else {
                Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(16.dp)).padding(16.dp)) {
                    Column {
                        Text("Master switch", fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 1.5.sp)
                        Spacer(Modifier.height(8.dp))
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("Prime Master", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = PL.ink)
                                Text("Enables supported Prime session actions", fontSize = 11.sp, color = PL.muted)
                            }
                            Switch(master, { master = it; GodModeManager.setApexMasterEnabled(it) }, colors = SwitchDefaults.colors(checkedThumbColor = Color.White, checkedTrackColor = PL.gold))
                        }
                        Spacer(Modifier.height(14.dp))
                        if (isActive) GhostBtn("Deactivate Prime Mode", Icons.Rounded.FlashOff) { GodModeManager.deactivateGodMode() }
                        else GhostBtn(if (isBusy) "Connecting…" else "Activate Now", Icons.Rounded.FlashOn, enabled = !isBusy) { GodModeManager.activateGodMode() }
                        Spacer(Modifier.height(10.dp))
                        Box(Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                            Text("Forget pairing", color = PL.muted, fontSize = 11.5.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.clip(RoundedCornerShape(8.dp)).clickable { GodModeManager.forgetPairing() }.padding(10.dp))
                        }
                    }
                }
            }

            // what it unlocks
            Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(16.dp)).padding(16.dp)) {
                Column {
                    Text("What Prime Mode unlocks", fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, color = PL.muted, letterSpacing = 1.5.sp)
                    Spacer(Modifier.height(8.dp))
                    Feat("Game Active", "Keeps eFootball in Android's active standby bucket while you play.")
                    Feat("No Calls", "Silently rejects calls only while you're playing.")
                    Feat("Auto", "Uses Prime to enable Wi-Fi when PeerLink needs it, then restores your previous state.")
                }
            }
            Spacer(Modifier.height(10.dp))
        }
    }
}

@Composable private fun PrimeStatusPill(modifier: Modifier, label: String, on: Boolean) =
    Box(modifier.clip(RoundedCornerShape(10.dp)).background(if (on) PL.green.copy(alpha = 0.14f) else PL.elevated).border(1.dp, if (on) PL.green.copy(alpha = 0.4f) else PL.line, RoundedCornerShape(10.dp)).padding(vertical = 8.dp), contentAlignment = Alignment.Center) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
            Box(Modifier.size(6.dp).clip(CircleShape).background(if (on) PL.green else PL.muted))
            Text(label, fontSize = 9.sp, fontWeight = FontWeight.ExtraBold, color = if (on) PL.green else PL.muted, letterSpacing = 1.sp)
        }
    }

@Composable private fun PrimeSetupStep(num: String, title: String, desc: String, action: @Composable () -> Unit) {
    Box(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(PL.surface).border(1.dp, PL.line, RoundedCornerShape(16.dp)).padding(16.dp)) {
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(26.dp).clip(CircleShape).background(PL.gold.copy(alpha = 0.16f)), contentAlignment = Alignment.Center) {
                    Text(num, fontSize = 12.sp, fontWeight = FontWeight.ExtraBold, color = PL.gold)
                }
                Spacer(Modifier.width(10.dp))
                Text(title, fontSize = 13.5.sp, fontWeight = FontWeight.Bold, color = PL.ink)
            }
            Spacer(Modifier.height(8.dp))
            Text(desc, fontSize = 11.5.sp, color = PL.muted, lineHeight = 16.sp, modifier = Modifier.padding(start = 36.dp, bottom = 10.dp))
            Box(Modifier.padding(start = 36.dp)) { action() }
        }
    }
}
