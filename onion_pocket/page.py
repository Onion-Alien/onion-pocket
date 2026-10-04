"""Onion Pocket's page: one HTML file with its style and
script inline, served by the app at / on the home network. No CDN, no fonts, no
picture files: the logo is inline SVG (the same mark as Onion Board's icon) and
the pads are CSS in each pad's own colour.

The key arrives in the link's #fragment (browsers never send that part), is kept in
the phone's localStorage and taken out of the address bar, and goes with every
request as X-Token. Sound names are put on the page as text, never as markup. The
Content-Security-Policy allows exactly this script and this style (by hash),
requests to this PC only, and data: images (the tab icon) only.
"""
from __future__ import annotations

import base64
import hashlib
from urllib.parse import quote

# Onion Board's mark (soundboard/theme.py paint_logo) on a 100 x 100 grid: a
# gradient squircle holding an onion whose layers read as sound waves.
_BULB = ("M50 27C{a} 36 {b} 42 {b} 59C{b} 74 {c} 81 50 81C{d} 81 {e} 74 {e} 59"
         "C{e} 42 {f} 36 50 27Z")


def _bulb(w: float) -> str:
    def n(v):
        return f"{v:g}"
    return _BULB.format(a=n(50 + w * 25), b=n(50 + w * 100), c=n(50 + w * 55),
                        d=n(50 - w * 55), e=n(50 - w * 100), f=n(50 - w * 25))


LOGO = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" aria-hidden="true">'
    '<defs><linearGradient id="g" gradientUnits="userSpaceOnUse" x1="0" y1="0" '
    'x2="100" y2="100"><stop offset="0" stop-color="#7c5cff"/>'
    '<stop offset="1" stop-color="#ff4d8d"/></linearGradient>'
    '<linearGradient id="h" x1="0" y1="0" x2="0" y2="1"><stop offset="0" '
    'stop-color="#fff" stop-opacity=".24"/><stop offset=".65" stop-color="#fff" '
    'stop-opacity="0"/></linearGradient></defs>'
    '<rect x="4" y="4" width="92" height="92" rx="26" fill="url(#g)"/>'
    '<rect x="4" y="4" width="92" height="92" rx="26" fill="url(#h)"/>'
    '<path d="M50 29C50 20 46 15 38 12M50 27C51 19 55 14 60 10" fill="none" '
    'stroke="#fff" stroke-width="5" stroke-linecap="round"/>'
    f'<path d="{_bulb(0.29)}" fill="#fff"/>'
    f'<path d="{_bulb(0.17)}{_bulb(0.07)}" fill="none" stroke="url(#g)" '
    'stroke-width="3.2" stroke-linecap="round"/>'
    '<path d="M46.4 81L44 87M50 81V87M53.6 81L56 87" stroke="#fff" stroke-width="3" '
    'stroke-linecap="round"/></svg>'
)

ICON = "data:image/svg+xml," + quote(LOGO, safe=" =:/,.()")

STYLE = """
:root { --bg:#0f0d17; --panel:#1b1826; --panel2:#242034; --line:#ffffff14;
  --text:#f4f2fb; --dim:#a29cb8; --accent:#7c5cff; --pink:#ff4d8d;
  --warn:#ffb020; --bad:#ff4d6d; --ok:#19d27a;
  --safe-b:env(safe-area-inset-bottom, 0px); }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html { background:var(--bg); }
body { margin:0; min-height:100vh; color:var(--text);
  font:15px/1.35 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background:
    radial-gradient(120% 60% at 0% 0%, #7c5cff33, transparent 60%),
    radial-gradient(90% 50% at 100% 0%, #ff4d8d24, transparent 60%),
    var(--bg);
  background-attachment:fixed; -webkit-user-select:none; user-select:none; }
button { font:inherit; color:var(--text); background:var(--panel2); border:0;
  border-radius:12px; padding:9px 12px; min-height:42px; cursor:pointer;
  transition:transform .08s ease, filter .15s ease, background .2s ease; }
button:active { transform:scale(.96); filter:brightness(1.25); }
button:focus-visible { outline:2px solid var(--text); outline-offset:2px; }

header { position:sticky; top:0; z-index:3; padding:14px 16px 6px;
  background:linear-gradient(var(--bg) 70%, #0f0d1700);
  padding-top:max(14px, env(safe-area-inset-top, 0px)); }
.brand { display:flex; align-items:center; gap:12px; }
.brand svg { width:42px; height:42px; flex:none;
  filter:drop-shadow(0 4px 10px #7c5cff55); }
.titles { flex:1; min-width:0; }
h1 { font-size:19px; margin:0; letter-spacing:.2px; white-space:nowrap; }
h1 em { font-style:normal; font-weight:600; background:linear-gradient(90deg,
  var(--accent), var(--pink)); -webkit-background-clip:text; background-clip:text;
  color:transparent; }
.state { display:flex; align-items:center; gap:6px; color:var(--dim); font-size:12.5px;
  margin-top:2px; }
.dot { width:8px; height:8px; border-radius:50%; background:var(--dim); flex:none; }
.dot.on { background:var(--ok); box-shadow:0 0 0 3px #19d27a2e; }
.dot.off { background:var(--bad); box-shadow:0 0 0 3px #ff4d6d2e; }

#live { display:flex; align-items:center; gap:7px; border-radius:999px;
  padding:8px 14px 8px 12px; font-weight:700; letter-spacing:.3px; }
#live::before { content:""; width:9px; height:9px; border-radius:50%;
  background:currentColor; }
#live.on { background:#19d27a24; color:var(--ok); box-shadow:inset 0 0 0 1.5px #19d27a66; }
#live.on::before { animation:beat 1.6s ease-in-out infinite; }
#live.off { background:#ff4d6d22; color:var(--bad); box-shadow:inset 0 0 0 1.5px #ff4d6d66; }

.tools { display:flex; gap:8px; margin-top:12px; }
#find { flex:1; min-width:0; font:inherit; color:var(--text); background:var(--panel);
  border:1px solid var(--line); border-radius:12px; padding:9px 12px; min-height:42px;
  -webkit-user-select:text; user-select:text; }
#find::placeholder { color:var(--dim); }
#find:focus { outline:none; border-color:#7c5cff99; }
.tools.hide { display:none; }
.chips { display:flex; gap:7px; overflow-x:auto; padding:12px 0 6px;
  scrollbar-width:none; }
.chips::-webkit-scrollbar { display:none; }
.chips[hidden] { display:none; }
.chip { flex:none; padding:6px 14px; min-height:34px; border-radius:999px;
  background:var(--panel); color:var(--dim); box-shadow:inset 0 0 0 1px var(--line); }
.chip.sel { color:#fff; background:linear-gradient(135deg, var(--accent), #9b6bff);
  box-shadow:0 4px 14px #7c5cff55; }
.chip b { font-weight:500; opacity:.6; margin-left:5px; font-size:12px; }

#msg { margin:4px 16px 8px; padding:10px 12px; border-radius:12px; color:#ffe2a8;
  background:#ffb0201a; box-shadow:inset 0 0 0 1px #ffb02040; }
#msg:empty { display:none; }

main { display:grid; grid-template-columns:repeat(auto-fill, minmax(102px, 1fr));
  gap:12px; padding:6px 16px calc(104px + var(--safe-b)); }
.pad { --c:var(--accent); position:relative; aspect-ratio:1 / 1; border-radius:20px;
  padding:11px; display:flex; flex-direction:column; justify-content:flex-end;
  align-items:flex-start; text-align:left; overflow:hidden; isolation:isolate;
  background:var(--c);
  background:linear-gradient(150deg, var(--c) 0%, color-mix(in oklab, var(--c) 58%, #000) 100%);
  box-shadow:0 8px 20px -8px color-mix(in oklab, var(--c) 70%, #000),
    inset 0 1px 0 #ffffff40; }
.pad::before { content:""; position:absolute; inset:0; z-index:-1;
  background:radial-gradient(120% 80% at 15% 0%, #ffffff38, transparent 55%); }
.pad .nm { font-weight:700; font-size:15.5px; line-height:1.2; padding-right:4px;
  word-break:break-word;
  text-shadow:0 1px 3px #00000066; display:-webkit-box; -webkit-line-clamp:2;
  -webkit-box-orient:vertical; overflow:hidden; }
.pad .eq { position:absolute; top:13px; right:12px; display:none; gap:3px;
  align-items:flex-end; height:16px; }
.pad .eq i { width:4px; border-radius:2px; background:#fff; height:40%;
  animation:eq .9s ease-in-out infinite; }
.pad .eq i:nth-child(2) { animation-delay:-.3s; height:100%; }
.pad .eq i:nth-child(3) { animation-delay:-.6s; height:65%; }
.pad.playing { box-shadow:0 0 0 3px #fff, 0 0 26px 2px var(--c); }
.pad.playing .eq { display:flex; }
@media (prefers-reduced-motion: no-preference) {
  .pad.hit::after { content:""; position:absolute; inset:0; background:#fff; opacity:0;
    animation:hit .35s ease-out; }
}

.empty { grid-column:1 / -1; text-align:center; color:var(--dim); padding:40px 20px;
  border-radius:20px; background:var(--panel); box-shadow:inset 0 0 0 1px var(--line); }
.empty .big { font-size:40px; display:block; margin-bottom:10px; }
.empty strong { display:block; color:var(--text); font-size:17px; margin-bottom:6px; }

.dock { position:fixed; left:0; right:0; bottom:0; z-index:4;
  padding:10px 16px calc(10px + var(--safe-b)); display:flex; gap:10px;
  background:#16131fd9; -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px);
  border-top:1px solid var(--line); }
#stop { flex:1; display:flex; align-items:center; justify-content:center; gap:9px;
  font-weight:700; min-height:50px; border-radius:14px;
  background:linear-gradient(135deg, #ff4d6d, #ff4d8d); box-shadow:0 6px 18px #ff4d6d44; }
#stop::before { content:""; width:12px; height:12px; border-radius:3px; background:#fff; }
.vol { display:flex; align-items:center; gap:4px; padding:4px; border-radius:14px;
  background:var(--panel); box-shadow:inset 0 0 0 1px var(--line); }
.vol button { width:42px; min-height:42px; padding:0; font-size:22px; line-height:1;
  background:transparent; }
.meter { width:52px; text-align:center; }
#vol { display:block; font-weight:700; font-variant-numeric:tabular-nums; }
.bar { display:block; height:3px; margin:4px 6px 0; border-radius:2px; background:#ffffff1c;
  overflow:hidden; }
#volbar { display:block; height:100%; width:0; border-radius:2px;
  background:linear-gradient(90deg, var(--accent), var(--pink)); transition:width .2s; }

@keyframes eq { 0%, 100% { height:30%; } 50% { height:100%; } }
@keyframes hit { from { opacity:.35; } to { opacity:0; } }
@keyframes beat { 0%, 100% { opacity:1; } 50% { opacity:.35; } }
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation:none !important; transition:none !important; }
}
@media (min-width: 560px) {
  main { grid-template-columns:repeat(auto-fill, minmax(128px, 1fr)); }
}
"""

SCRIPT = """
"use strict";
const $ = (id) => document.getElementById(id);
let key = "", sounds = [], cats = [], cat = "", query = "";
let playing = new Set(), timer = 0;

function store(k) { try { k ? localStorage.setItem("ob-key", k)
                            : localStorage.removeItem("ob-key"); } catch (e) {} }
function stored() { try { return localStorage.getItem("ob-key") || ""; }
                    catch (e) { return ""; } }

function say(text) { $("msg").textContent = text || ""; }
function state(cls, text) { $("dot").className = "dot " + cls; $("state").textContent = text; }

async function api(path) {
  let r;
  try {
    r = await fetch("/api/" + path, { method: "POST", headers: { "X-Token": key },
                                       cache: "no-store" });
  } catch (e) {
    state("off", "Can't reach the PC");
    say("Can't reach Onion Board. Is it running, with Onion Pocket on, and is " +
        "this phone on the same Wi-Fi?");
    throw e;
  }
  state("on", "Connected to your PC");
  if (r.status === 401) {
    key = ""; store("");
    state("off", "Not paired");
    say("This phone isn't paired (or the PC made a new key). Scan the QR code in " +
        "Onion Board: Settings, Remote, Onion Pocket.");
    drawPads();
    throw new Error("unpaired");
  }
  if (r.status === 429) { say("Too many wrong keys from this phone: wait a minute."); }
  const body = await r.json().catch(() => null);
  if (!r.ok && body && body.error && r.status !== 429) { say(body.error); }
  if (!r.ok) { throw new Error(String(r.status)); }
  return body;
}

function color(c) { return /^#[0-9a-fA-F]{3,8}$/.test(c || "") ? c : ""; }

function drawChips() {
  const box = $("chips");
  box.replaceChildren();
  box.hidden = !cats.length;
  for (const name of ["", ...cats]) {
    const b = document.createElement("button");
    b.className = "chip" + (name === cat ? " sel" : "");
    b.textContent = name || "All";
    const n = document.createElement("b");
    n.textContent = String(name ? sounds.filter((s) => (s.categories || []).includes(name)).length
                                : sounds.length);
    b.appendChild(n);
    b.addEventListener("click", () => { cat = name; drawChips(); drawPads(); });
    box.appendChild(b);
  }
}

function emptyCard(big, title, text) {
  const p = document.createElement("div");
  p.className = "empty";
  const i = document.createElement("span");
  i.className = "big"; i.textContent = big;
  const t = document.createElement("strong");
  t.textContent = title;
  p.append(i, t, document.createTextNode(text));
  return p;
}

function drawPads() {
  const grid = $("pads");
  grid.replaceChildren();
  $("tools").classList.toggle("hide", sounds.length < 13);
  if (!key) {
    grid.appendChild(emptyCard("\\u{1F4F7}", "Pair this phone",
      "On the PC: Onion Board, Settings, Remote, Onion Pocket. Scan the code there " +
      "with this phone's camera."));
    return;
  }
  const q = query.trim().toLowerCase();
  const shown = sounds.filter((s) => (!cat || (s.categories || []).includes(cat))
                                     && (!q || (s.name || "").toLowerCase().includes(q)));
  if (!shown.length) {
    grid.appendChild(sounds.length
      ? emptyCard("\\u{1F50D}", "Nothing here", q ? "No sound matches that search."
                                                  : "No sounds in this category.")
      : emptyCard("\\u{1F3B5}", "No sounds yet", "Add some in Onion Board on the PC."));
    return;
  }
  for (const s of shown) {
    const b = document.createElement("button");
    b.className = "pad" + (playing.has(s.id) ? " playing" : "");
    b.dataset.id = s.id;
    b.setAttribute("aria-label", s.name);
    const c = color(s.color);
    if (c) { b.style.setProperty("--c", c); }
    const eq = document.createElement("span");
    eq.className = "eq";
    eq.append(document.createElement("i"), document.createElement("i"),
              document.createElement("i"));
    const n = document.createElement("span");
    n.className = "nm";
    n.textContent = s.name;
    b.append(eq, n);
    b.addEventListener("click", () => play(s.id, b));
    grid.appendChild(b);
  }
}

function markPlaying() {
  for (const b of document.querySelectorAll(".pad")) {
    b.classList.toggle("playing", playing.has(b.dataset.id));
  }
}

async function play(id, b) {
  if (navigator.vibrate) { navigator.vibrate(12); }
  b.classList.remove("hit"); void b.offsetWidth; b.classList.add("hit");
  try {
    await api("play?id=" + encodeURIComponent(id));
    say(""); playing.add(id); markPlaying();
  } catch (e) {}
}

async function status() {
  try {
    const st = await api("status");
    playing = new Set(st.playing || []);
    markPlaying();
    const live = $("live");
    live.textContent = st.live ? "Live" : "Muted";
    live.className = st.live ? "on" : "off";
    const v = Math.max(0, Math.min(100, Number(st.volume) || 0));
    $("vol").textContent = v + "%";
    $("volbar").style.width = v + "%";
  } catch (e) {}
}

async function load() {
  if (!key) { state("", "Not paired"); drawPads(); return; }
  try {
    const [list, names] = await Promise.all([api("sounds"), api("categories")]);
    sounds = list || [];
    cats = names || [];
    if (cat && !cats.includes(cat)) { cat = ""; }
    say(""); drawChips(); drawPads(); status();
  } catch (e) {}
}

function poll() {
  clearInterval(timer);
  if (document.visibilityState === "visible" && key) { timer = setInterval(status, 2000); }
}

function start() {
  const m = /[#&]k=([A-Za-z0-9_-]+)/.exec(location.hash);
  if (m) {
    key = m[1]; store(key);
    history.replaceState(null, "", location.pathname);   // the key off the screen
  } else {
    key = stored();
  }
  $("stop").addEventListener("click", () => api("stop").then(status, () => {}));
  $("live").addEventListener("click", () => api("live?on=toggle").then(status, () => {}));
  $("down").addEventListener("click", () => api("volume?step=down").then(status, () => {}));
  $("up").addEventListener("click", () => api("volume?step=up").then(status, () => {}));
  $("find").addEventListener("input", (e) => { query = e.target.value; drawPads(); });
  document.addEventListener("visibilitychange", () => {
    poll();
    if (document.visibilityState === "visible") { load(); }
  });
  load(); poll();
}

start();
"""

BODY = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0f0d17">
<meta name="color-scheme" content="dark">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Onion Board">
<meta name="referrer" content="no-referrer">
<link rel="icon" type="image/svg+xml" href="{icon}">
<title>Onion Board</title>
<style>{style}</style>
</head>
<body>
<header>
  <div class="brand">
    {logo}
    <div class="titles">
      <h1>Onion Board <em>Pocket</em></h1>
      <div class="state"><span id="dot" class="dot"></span><span id="state">Connecting…</span></div>
    </div>
    <button id="live" title="Live / Muted: muted, nobody hears your sounds">Live</button>
  </div>
  <div id="tools" class="tools hide">
    <input id="find" type="search" placeholder="Search sounds" aria-label="Search sounds"
      autocomplete="off" enterkeyhint="search">
  </div>
  <div id="chips" class="chips" hidden></div>
</header>
<div id="msg" role="status"></div>
<main id="pads"></main>
<nav class="dock">
  <button id="stop" title="Stop every sound">Stop all</button>
  <div class="vol">
    <button id="down" title="Sounds quieter" aria-label="Quieter">&minus;</button>
    <span class="meter"><span id="vol" aria-label="Volume">&ndash;</span>
      <span class="bar"><span id="volbar"></span></span></span>
    <button id="up" title="Sounds louder" aria-label="Louder">+</button>
  </div>
</nav>
<script>{script}</script>
</body>
</html>
"""


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def page() -> tuple[bytes, dict]:
    """(body, headers) for host.server(page=…)."""
    html = (BODY.replace("{icon}", ICON).replace("{logo}", LOGO)
            .replace("{style}", STYLE).replace("{script}", SCRIPT))
    csp = ("default-src 'none'; "
           f"script-src {_sha(SCRIPT)}; style-src {_sha(STYLE)}; "
           "img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
           "frame-ancestors 'none'")
    return html.encode("utf-8"), {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
