"""Onion Pocket's page: one HTML file with its style and
script inline, served by the app at / on the home network. No CDN, no fonts, no
pictures: everything it shows is drawn with CSS.

The key arrives in the link's #fragment (browsers never send that part), is kept in
the phone's localStorage and taken out of the address bar, and goes with every
request as X-Token. Sound names are put on the page as text, never as markup. The
Content-Security-Policy allows exactly this script and this style (by hash) and
requests to this PC only.
"""
from __future__ import annotations

import base64
import hashlib

STYLE = """
:root { --bg:#14121c; --card:#211e2e; --text:#f1eff8; --dim:#a9a4bd; --accent:#7c5cff;
  --warn:#ffb020; --bad:#ff5c8a; --ok:#13ce66; }
* { box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
html, body { margin:0; background:var(--bg); color:var(--text);
  font:15px/1.35 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
header { position:sticky; top:0; z-index:2; background:var(--bg); padding:12px 16px 8px; }
.top { display:flex; align-items:center; gap:8px; }
h1 { font-size:17px; margin:0; flex:1; }
.dot { width:10px; height:10px; border-radius:50%; background:var(--dim); flex:none; }
.dot.on { background:var(--ok); }
.dot.off { background:var(--bad); }
button { font:inherit; color:var(--text); background:var(--card); border:0;
  border-radius:10px; padding:9px 12px; min-height:40px; }
button:active { filter:brightness(1.3); }
#live.on { background:var(--ok); color:#04140b; }
#live.off { background:var(--bad); }
.chips { display:flex; gap:6px; overflow-x:auto; padding:8px 0 2px; scrollbar-width:none; }
.chips::-webkit-scrollbar { display:none; }
.chip { flex:none; padding:6px 12px; min-height:32px; border-radius:16px; }
.chip.sel { background:var(--accent); }
#msg { margin:8px 16px; color:var(--warn); }
#msg:empty { display:none; }
main { display:grid; grid-template-columns:repeat(auto-fill, minmax(104px, 1fr));
  gap:10px; padding:8px 16px 24px; }
.pad { position:relative; aspect-ratio:1 / 1; border-radius:14px; padding:10px;
  display:flex; align-items:flex-end; text-align:left; font-weight:600;
  overflow:hidden; word-break:break-word; background:var(--accent);
  text-shadow:0 1px 2px rgba(0,0,0,.45); }
.pad.playing { outline:3px solid var(--text); outline-offset:-3px; }
.pad.playing::after { content:"\\25B6"; position:absolute; top:8px; right:10px; }
.row2 { margin-top:8px; }
.grow { flex:1; }
.empty { grid-column:1 / -1; color:var(--dim); text-align:center; padding:40px 0; }
"""

SCRIPT = """
"use strict";
const $ = (id) => document.getElementById(id);
let key = "", sounds = [], cat = "", playing = new Set(), timer = 0;

function store(k) { try { k ? localStorage.setItem("ob-key", k)
                            : localStorage.removeItem("ob-key"); } catch (e) {} }
function stored() { try { return localStorage.getItem("ob-key") || ""; }
                    catch (e) { return ""; } }

function say(text) { $("msg").textContent = text || ""; }

async function api(path) {
  let r;
  try {
    r = await fetch("/api/" + path, { method: "POST", headers: { "X-Token": key },
                                       cache: "no-store" });
  } catch (e) {
    $("dot").className = "dot off";
    say("Can't reach Onion Board. Is it running, with Onion Pocket on, and is " +
        "this phone on the same Wi-Fi?");
    throw e;
  }
  $("dot").className = "dot on";
  if (r.status === 401) {
    key = ""; store("");
    say("This phone isn't paired (or the PC made a new key). Scan the QR code in " +
        "Onion Board: Settings, Remote, Onion Pocket.");
    throw new Error("unpaired");
  }
  if (r.status === 429) { say("Too many wrong keys from this phone: wait a minute."); }
  const body = await r.json().catch(() => null);
  if (!r.ok && body && body.error && r.status !== 429) { say(body.error); }
  if (!r.ok) { throw new Error(String(r.status)); }
  return body;
}

function color(c) { return /^#[0-9a-fA-F]{3,8}$/.test(c || "") ? c : ""; }

function drawChips(cats) {
  const box = $("chips");
  box.replaceChildren();
  for (const name of ["", ...cats]) {
    const b = document.createElement("button");
    b.className = "chip" + (name === cat ? " sel" : "");
    b.textContent = name || "All";
    b.addEventListener("click", () => { cat = name; drawChips(cats); drawPads(); });
    box.appendChild(b);
  }
}

function drawPads() {
  const grid = $("pads");
  grid.replaceChildren();
  const shown = sounds.filter((s) => !cat || (s.categories || []).includes(cat));
  if (!shown.length) {
    const p = document.createElement("div");
    p.className = "empty";
    p.textContent = sounds.length ? "No sounds in this category." : "No sounds yet.";
    grid.appendChild(p);
    return;
  }
  for (const s of shown) {
    const b = document.createElement("button");
    b.className = "pad" + (playing.has(s.id) ? " playing" : "");
    b.textContent = s.name;
    b.dataset.id = s.id;
    const c = color(s.color);
    if (c) { b.style.background = c; }
    b.addEventListener("click", () => play(s.id));
    grid.appendChild(b);
  }
}

function markPlaying() {
  for (const b of document.querySelectorAll(".pad")) {
    b.classList.toggle("playing", playing.has(b.dataset.id));
  }
}

async function play(id) {
  if (navigator.vibrate) { navigator.vibrate(12); }
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
    $("vol").textContent = st.volume + "%";
  } catch (e) {}
}

async function load() {
  if (!key) { return; }
  try {
    const [list, cats] = await Promise.all([api("sounds"), api("categories")]);
    sounds = list || [];
    if (cat && !cats.includes(cat)) { cat = ""; }
    say(""); drawChips(cats || []); drawPads(); status();
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
  document.addEventListener("visibilitychange", () => {
    poll();
    if (document.visibilityState === "visible") { load(); }
  });
  if (!key) {
    say("Scan the QR code in Onion Board (Settings, Remote, Onion Pocket) to " +
        "pair this phone.");
  }
  load(); poll();
}

start();
"""

BODY = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#14121c">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Onion Board">
<meta name="referrer" content="no-referrer">
<title>Onion Board</title>
<style>{style}</style>
</head>
<body>
<header>
  <div class="top">
    <span id="dot" class="dot"></span>
    <h1>Onion Board</h1>
    <button id="live" title="Live / Muted: muted, nobody hears your sounds">Live</button>
  </div>
  <div class="top row2">
    <button id="stop" title="Stop every sound">&#9632; Stop all</button>
    <span class="grow"></span>
    <button id="down" title="Sounds quieter" aria-label="Quieter">&minus;</button>
    <span id="vol" aria-label="Volume">&ndash;</span>
    <button id="up" title="Sounds louder" aria-label="Louder">+</button>
  </div>
  <div id="chips" class="chips"></div>
</header>
<div id="msg" role="status"></div>
<main id="pads"></main>
<script>{script}</script>
</body>
</html>
"""


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def page() -> tuple[bytes, dict]:
    """(body, headers) for host.server(page=…)."""
    html = BODY.replace("{style}", STYLE).replace("{script}", SCRIPT)
    csp = ("default-src 'none'; "
           f"script-src {_sha(SCRIPT)}; style-src {_sha(STYLE)}; "
           "connect-src 'self'; base-uri 'none'; form-action 'none'; "
           "frame-ancestors 'none'")
    return html.encode("utf-8"), {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
