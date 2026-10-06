"""Onion Pocket's page: one HTML file with its style and
script inline, served by the app at / on the home network. No CDN, no fonts, no
picture files: the logo is inline SVG (the same mark as Onion Board's icon) and
the pads are CSS in each pad's own colour.

Three tabs along the bottom: Pads, Radio (the Radio tab's stations and controls) and
Sound (the live speed, pitch and effects, and who's listening). A tab shows only when
the board's status says it has that part, so an older Onion Board gets the pads alone.

The key arrives in the link's #fragment (browsers never send that part), is kept in
the phone's localStorage and taken out of the address bar. With an Onion Board that
takes signed requests (host.signed_requests) the key itself never leaves the phone:
each request carries X-Sig, an HMAC-SHA256 of it made with the key, the time and a
one-time nonce (SHA-256 is written out in the script: http:// pages get no
crypto.subtle). Older ones get the key as X-Token. Sound names are put on the page
as text, never as markup. The Content-Security-Policy allows exactly this script and
this style (by hash), requests to this PC only, and data: images (the tab icon) only.
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
button:disabled { opacity:.45; cursor:default; }

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
  background:#16131ff2; -webkit-backdrop-filter:blur(16px); backdrop-filter:blur(16px);
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

[hidden] { display:none !important; }
body.tabbed main, .view { padding-bottom:calc(172px + var(--safe-b)); }
.dock { flex-direction:column; gap:10px; }
.row { display:flex; gap:10px; }
.vlabel { display:block; font-size:10.5px; color:var(--dim); text-transform:uppercase;
  letter-spacing:.6px; }
#ract, #reset { flex:1; font-weight:700; min-height:50px; border-radius:14px;
  background:linear-gradient(135deg, var(--accent), #9b6bff); box-shadow:0 6px 18px #7c5cff44; }
#ract.on { background:linear-gradient(135deg, #ff4d6d, #ff4d8d); box-shadow:0 6px 18px #ff4d6d44; }
#reset { background:var(--panel2); box-shadow:inset 0 0 0 1px var(--line); }
.tabs { display:flex; gap:6px; margin:0 -6px; }
.tab { flex:1; display:flex; flex-direction:column; align-items:center; gap:3px;
  min-height:48px; padding:6px 4px; background:transparent; color:var(--dim);
  font-size:12px; font-weight:600; border-radius:12px; }
.tab svg { width:22px; height:22px; fill:none; stroke:currentColor; stroke-width:2;
  stroke-linecap:round; stroke-linejoin:round; }
.tab.sel { color:#fff; background:#7c5cff2e; }
.tab.sel svg { stroke:#b9a6ff; }

.view { padding-left:16px; padding-right:16px; padding-top:6px; }
.card { background:var(--panel); border-radius:18px; padding:14px;
  box-shadow:inset 0 0 0 1px var(--line); margin-bottom:12px; }
.head { display:flex; align-items:baseline; justify-content:space-between; gap:10px;
  margin-bottom:8px; }
h2 { margin:0; font-size:13px; font-weight:700; color:var(--dim); text-transform:uppercase;
  letter-spacing:.7px; }
.val { font-weight:800; font-size:22px; font-variant-numeric:tabular-nums; }
.val.hot { color:var(--warn); }
input[type=range] { -webkit-appearance:none; appearance:none; width:100%; height:34px;
  background:transparent; margin:0; touch-action:pan-y; }
input[type=range]::-webkit-slider-runnable-track { height:6px; border-radius:3px;
  background:linear-gradient(90deg, var(--accent), var(--pink)); }
input[type=range]::-moz-range-track { height:6px; border-radius:3px;
  background:linear-gradient(90deg, var(--accent), var(--pink)); }
input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:26px; height:26px;
  margin-top:-10px; border-radius:50%; background:#fff; box-shadow:0 2px 8px #0008; }
input[type=range]::-moz-range-thumb { width:26px; height:26px; border:0; border-radius:50%;
  background:#fff; box-shadow:0 2px 8px #0008; }
.quick { display:flex; gap:6px; margin-top:6px; }
.quick button { flex:1; padding:6px 0; min-height:38px; font-size:13.5px;
  background:var(--panel2); }
.quick button.sel, .chip.sel { color:#fff; background:linear-gradient(135deg, var(--accent),
  #9b6bff); box-shadow:0 4px 14px #7c5cff55; }
.step { display:flex; align-items:center; gap:10px; }
.step button { width:46px; flex:none; font-size:22px; padding:0; }
.switch { display:flex; align-items:center; justify-content:space-between; gap:12px;
  width:100%; margin-top:10px; padding:10px 12px; text-align:left; background:var(--panel2); }
.switch::after { content:""; flex:none; width:42px; height:24px; border-radius:12px;
  background:#ffffff22; box-shadow:inset 0 0 0 1px var(--line);
  transition:background .2s; }
.switch[aria-pressed=true]::after { background:var(--ok); }
.fx { display:grid; grid-template-columns:78px 1fr 58px; align-items:center; gap:4px 10px; }
.fx label { color:var(--dim); font-size:14px; }
.fx output { text-align:right; font-weight:700; font-variant-numeric:tabular-nums;
  font-size:14px; }
.wrap { flex-wrap:wrap; overflow:visible; padding-bottom:0; }
select { width:100%; font:inherit; color:var(--text); background:var(--panel2);
  border:1px solid var(--line); border-radius:12px; padding:10px 12px; min-height:46px; }
.hint { color:var(--dim); font-size:13px; margin:8px 2px 0; }

.now { display:flex; flex-direction:column; gap:10px; }
.kicker { font-size:12px; color:var(--dim); text-transform:uppercase; letter-spacing:.7px; }
.kicker.on { color:var(--ok); }
#rname { display:block; font-size:19px; line-height:1.25; word-break:break-word; }
#rsub { display:block; color:var(--dim); font-size:13.5px; word-break:break-word; }
.now .row button { flex:1; }
#rstar.fav { color:var(--warn); }
.toggle[aria-pressed=true] { color:var(--ok); background:#19d27a1f;
  box-shadow:inset 0 0 0 1.5px #19d27a66; }
.seg { display:flex; gap:4px; padding:4px; border-radius:14px; background:var(--panel);
  box-shadow:inset 0 0 0 1px var(--line); margin-bottom:10px; }
.seg button { flex:1; min-height:38px; padding:6px 4px; font-size:13.5px;
  background:transparent; color:var(--dim); font-weight:600; }
.seg button.sel { color:#fff; background:linear-gradient(135deg, var(--accent), #9b6bff); }
#rfind { width:100%; font:inherit; color:var(--text); background:var(--panel);
  border:1px solid var(--line); border-radius:12px; padding:9px 12px; min-height:42px;
  margin-bottom:10px; -webkit-user-select:text; user-select:text; }
#rfind::placeholder { color:var(--dim); }
.stations { list-style:none; margin:0; padding:0; display:flex; flex-direction:column;
  gap:8px; }
.stations li { display:flex; gap:6px; }
.st { flex:1; min-width:0; display:flex; flex-direction:column; align-items:flex-start;
  text-align:left; gap:2px; background:var(--panel); padding:10px 12px;
  box-shadow:inset 0 0 0 1px var(--line); }
.st b { font-weight:650; max-width:100%; overflow:hidden; text-overflow:ellipsis;
  white-space:nowrap; }
.st span { color:var(--dim); font-size:12.5px; max-width:100%; overflow:hidden;
  text-overflow:ellipsis; white-space:nowrap; }
.st.playing { box-shadow:0 0 0 2px var(--ok); background:#19d27a14; }
.st.playing b::before { content:"\\25B6\\FE0E  "; color:var(--ok); }
.star { width:48px; flex:none; font-size:20px; padding:0; background:var(--panel);
  color:var(--dim); box-shadow:inset 0 0 0 1px var(--line); }
.star.fav { color:var(--warn); }
.note { color:var(--dim); font-size:13px; margin:0 2px 8px; }
.note:empty { display:none; }

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
let view = "pads", st = {}, knobs = null, modes = null;
let rlist = "", rquery = "", rpoll = 0, rtries = 0, rtimer = 0;
const held = {};       // control id -> until when the status mustn't move it (a thumb on it)
const QUICK = [0.5, 0.75, 1, 1.25, 1.5, 2];
const SIGNED = {signed};   // the board checks signatures: the key never goes over the Wi-Fi
let skew = 0;              // the PC's clock minus this phone's, in seconds

// SHA-256 and HMAC in plain JS: on http:// pages crypto.subtle doesn't exist.
const K256 = new Uint32Array([
  0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
  0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
  0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
  0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
  0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
  0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
  0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
  0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2]);
function sha256(bytes) {
  const n = bytes.length, blocks = ((n + 9 + 63) >> 6) << 6, m = new Uint8Array(blocks);
  m.set(bytes); m[n] = 0x80;
  const dv = new DataView(m.buffer);
  dv.setUint32(blocks - 8, Math.floor(n / 0x20000000)); dv.setUint32(blocks - 4, n << 3);
  const h = new Uint32Array([0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,
                             0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19]);
  const w = new Uint32Array(64);
  const r = (x, k) => (x >>> k) | (x << (32 - k));
  for (let o = 0; o < blocks; o += 64) {
    for (let i = 0; i < 16; i++) { w[i] = dv.getUint32(o + i * 4); }
    for (let i = 16; i < 64; i++) {
      const a = w[i - 15], b = w[i - 2];
      w[i] = w[i - 16] + (r(a, 7) ^ r(a, 18) ^ (a >>> 3)) + w[i - 7]
             + (r(b, 17) ^ r(b, 19) ^ (b >>> 10));
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i++) {
      const t1 = (hh + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g))
                  + K256[i] + w[i]) >>> 0;
      const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
      hh = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
    }
    h[0] += a; h[1] += b; h[2] += c; h[3] += d; h[4] += e; h[5] += f; h[6] += g; h[7] += hh;
  }
  const out = new Uint8Array(32), ov = new DataView(out.buffer);
  for (let i = 0; i < 8; i++) { ov.setUint32(i * 4, h[i]); }
  return out;
}
function hmac(keyBytes, msgBytes) {
  let k = keyBytes.length > 64 ? sha256(keyBytes) : keyBytes;
  const pad = (x) => {
    const p = new Uint8Array(64).fill(x);
    k.forEach((v, i) => { p[i] ^= v; });
    return p;
  };
  const cat = (a, b) => {
    const c = new Uint8Array(a.length + b.length);
    c.set(a); c.set(b, a.length);
    return c;
  };
  return sha256(cat(pad(0x5c), sha256(cat(pad(0x36), msgBytes))));
}
function b64url(bytes) {
  let s = ""; bytes.forEach((v) => { s += String.fromCharCode(v); });
  return btoa(s).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

function sign(url) {
  const u = new URL(url, location.href), enc = new TextEncoder();
  const ts = String(Math.floor(Date.now() / 1000) + skew);
  const r = new Uint8Array(18);
  crypto.getRandomValues(r);
  const n = b64url(r);
  return ts + "." + n + "." +
    b64url(hmac(enc.encode(key), enc.encode(ts + "." + n + ".POST " + u.pathname + u.search)));
}

function store(k) { try { k ? localStorage.setItem("ob-key", k)
                            : localStorage.removeItem("ob-key"); } catch (e) {} }
function stored() { try { return localStorage.getItem("ob-key") || ""; }
                    catch (e) { return ""; } }

function say(text) { $("msg").textContent = text || ""; }
function state(cls, text) { $("dot").className = "dot " + cls; $("state").textContent = text; }

async function api(path, again) {
  const url = "/api/" + path, used = skew;
  let r;
  try {
    r = await fetch(url, { method: "POST", cache: "no-store",
                           headers: SIGNED ? { "X-Sig": sign(url) } : { "X-Token": key } });
  } catch (e) {
    state("off", "Can't reach the PC");
    say("Can't reach Onion Board. Is it running, with Onion Pocket on, and is " +
        "this phone on the same Wi-Fi?");
    throw e;
  }
  state("on", "Connected to your PC");
  if (r.status === 401) {
    if (SIGNED && !again && key) {   // this phone's clock is off: sign by the PC's
      const b = await r.json().catch(() => null);
      const s = b && Number.isFinite(b.now) ? b.now - Math.floor(Date.now() / 1000) : skew;
      // (`used`: requests sent together all retry, not just the first one back)
      if (Math.abs(s - used) > 30) { skew = s; return api(path, true); }
    }
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

// Slider moves go one after another, so the last one sent is the one that stays.
let chain = Promise.resolve();
function send(path) {
  const p = chain.then(() => api(path));
  chain = p.catch(() => {});
  return p;
}
function hold(id, ms) { held[id] = Date.now() + (ms || 1500); }
function free(id) { return !(held[id] > Date.now()); }
function press(el, on) { el.setAttribute("aria-pressed", on ? "true" : "false"); }
function num(v, d) { const n = Number(v); return Number.isFinite(n) ? n : d; }
function q(v) { return encodeURIComponent(v); }

function color(c) { return /^#[0-9a-fA-F]{3,8}$/.test(c || "") ? c : ""; }

// ------------------------------------------------------------------ pads
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
  const qy = query.trim().toLowerCase();
  const shown = sounds.filter((s) => (!cat || (s.categories || []).includes(cat))
                                     && (!qy || (s.name || "").toLowerCase().includes(qy)));
  if (!shown.length) {
    grid.appendChild(sounds.length
      ? emptyCard("\\u{1F50D}", "Nothing here", qy ? "No sound matches that search."
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
    await api("play?id=" + q(id));
    say(""); playing.add(id); markPlaying();
  } catch (e) {}
}

// ------------------------------------------------------------------ tabs
function hasRadio() { return !!st.radio; }
function hasSound() { return st.speed !== undefined; }

function drawTabs() {
  const radio = hasRadio(), sound = hasSound();
  $("tab-radio").hidden = !radio;
  $("tab-sound").hidden = !sound;
  $("tabs").hidden = !radio && !sound;
  document.body.classList.toggle("tabbed", radio || sound);
  if ((view === "radio" && !radio) || (view === "sound" && !sound)) { show("pads"); }
}

function show(v) {
  view = v;
  for (const name of ["pads", "radio", "sound"]) {
    $("tab-" + name).classList.toggle("sel", name === v);
    $("tab-" + name).setAttribute("aria-selected", name === v ? "true" : "false");
  }
  $("pads").hidden = v !== "pads";
  $("padhead").hidden = v !== "pads";
  $("radio").hidden = v !== "radio";
  $("sound").hidden = v !== "sound";
  $("stop").hidden = v !== "pads";
  $("ract").hidden = v !== "radio";
  $("reset").hidden = v !== "sound";
  $("vlabel").textContent = v === "radio" ? "Radio" : "Sounds";
  drawVolume();
  if (v === "radio") { loadStations(); }
  if (v === "sound") { loadSound(); }
  window.scrollTo(0, 0);
}

function drawVolume() {
  const r = st.radio || {};
  const v = Math.max(0, Math.min(100, num(view === "radio" ? r.volume : st.volume, 0)));
  $("vol").textContent = v + "%";
  $("volbar").style.width = Math.min(100, v) + "%";
}

// ------------------------------------------------------------------ sound: speed, pitch, effects
function fmtX(v) { return +num(v, 1).toFixed(2) + "x"; }
function fmtSt(v) { v = Math.round(num(v, 0)); return (v > 0 ? "+" : "") + v + " st"; }
function fmtFx(k, v) {
  v = num(v, 0);
  if (k.unit === "dB") { v = Math.round(v); return (v > 0 ? "+" : "") + v + " dB"; }
  return Math.round(v * 100) + "%";
}

function slider(el, sendIt, label) {
  let t = 0, last = 0;
  const go = () => { last = Date.now(); sendIt(el.value); };
  el.addEventListener("input", () => {
    hold(el.id);
    if (label) { label(el.value); }
    clearTimeout(t);
    const wait = 200 - (Date.now() - last);
    if (wait <= 0) { go(); } else { t = setTimeout(go, wait); }
  });
  el.addEventListener("change", () => { hold(el.id); clearTimeout(t); go(); });
}

function liveSend(path) { return send(path).then(drawLive, () => {}); }

function buildSound() {
  const quick = $("quick");
  for (const s of QUICK) {
    const b = document.createElement("button");
    b.textContent = s + "x";
    b.dataset.v = String(s);
    b.addEventListener("click", () => { $("speed").value = s; liveSend("speed?set=" + s); });
    quick.appendChild(b);
  }
  slider($("speed"), (v) => liveSend("speed?set=" + v),
         (v) => { $("speedv").textContent = fmtX(v); });
  slider($("pitch"), (v) => liveSend("pitch?set=" + v),
         (v) => { $("pitchv").textContent = fmtSt(v); });
  $("pdown").addEventListener("click", () => liveSend("pitch?step=down"));
  $("pup").addEventListener("click", () => liveSend("pitch?step=up"));
  $("keep").addEventListener("click", () => liveSend("speed?keep=toggle"));
  $("reset").addEventListener("click", () => liveSend("reset"));
  $("mode").addEventListener("change", (e) => {
    hold("mode", 3000);
    send("mode?set=" + q(e.target.value)).then(drawModes, () => {});
  });
}

async function loadSound() {
  if (!knobs) {
    try {
      const fx = await api("effects");
      knobs = fx.knobs || []; buildFx(fx.presets || []); drawLive(fx);
    } catch (e) {}
  }
  if (!modes && st.mode !== undefined) {
    try { drawModes(await api("mode")); } catch (e) {}
  }
}

function buildFx(presets) {
  const box = $("fx");
  box.replaceChildren();
  for (const k of knobs) {
    const id = "fx-" + k.key;
    const lab = document.createElement("label");
    lab.textContent = k.label; lab.htmlFor = id;
    const r = document.createElement("input");
    r.type = "range"; r.id = id; r.min = k.lo; r.max = k.hi;
    r.step = k.unit === "dB" ? 1 : 0.05; r.value = 0;
    const out = document.createElement("output");
    out.id = id + "-v"; out.textContent = fmtFx(k, 0);
    slider(r, (v) => liveSend("effects?" + q(k.key) + "=" + v),
           (v) => { out.textContent = fmtFx(k, v); });
    box.append(lab, r, out);
  }
  const pb = $("presets");
  pb.replaceChildren();
  for (const name of presets) {
    const b = document.createElement("button");
    b.className = "chip"; b.textContent = name; b.dataset.name = name;
    b.addEventListener("click", () =>
      liveSend("effects?preset=" + q(b.classList.contains("sel") ? "none" : name)));
    pb.appendChild(b);
  }
}

function drawLive(s) {
  if (!s || s.speed === undefined) { return; }
  const speed = num(s.speed, 1), pitch = num(s.pitch, 0);
  if (free("speed")) {
    $("speed").value = speed;
    $("speedv").textContent = fmtX(speed);
    $("speedv").classList.toggle("hot", speed > 2.0001);
  }
  for (const b of $("quick").children) {
    b.classList.toggle("sel", Math.abs(num(b.dataset.v, 0) - speed) < 0.001);
  }
  if (free("pitch")) {
    $("pitch").value = pitch;
    $("pitchv").textContent = fmtSt(pitch);
    $("pitchv").classList.toggle("hot", Math.abs(pitch) > 12);
  }
  press($("keep"), !!s.keep_pitch);
  const fx = s.effects || {};
  for (const k of knobs || []) {
    const id = "fx-" + k.key, el = $(id);
    if (el && free(id)) {
      el.value = num(fx[k.key], 0);
      $(id + "-v").textContent = fmtFx(k, fx[k.key]);
    }
  }
  for (const b of $("presets").children) {
    b.classList.toggle("sel", b.dataset.name === s.preset);
  }
}

function drawModes(m) {
  if (!m || !m.modes) { return; }
  modes = m.modes;
  const sel = $("mode");
  sel.replaceChildren();
  for (const d of modes) {
    const o = document.createElement("option");
    o.value = d.key;
    o.textContent = d.key === "off" ? "Off" : d.label;
    sel.appendChild(o);
  }
  drawMode(m.mode);
}

function drawMode(key) {
  if (!modes || key === undefined) { return; }
  if (!modes.some((d) => d.key === key)) { modes = null; loadSound(); return; }   // a new one
  if (free("mode")) { $("mode").value = key; }
  const d = modes.find((x) => x.key === $("mode").value);
  $("modenote").textContent = d ? d.note || "" : "";
}

// ------------------------------------------------------------------ radio
function drawRadio(r) {
  if (!r) { return; }
  $("roff").hidden = r.available !== false;
  $("ron").hidden = r.available === false;
  $("ract").disabled = r.available === false || (!r.on && !r.last);
  if (r.available === false) { return; }
  const s = r.station;
  $("rstate").textContent = r.connecting ? "Tuning in…" : r.on ? "Playing" : "Radio";
  $("rstate").className = "kicker" + (r.on && !r.connecting ? " on" : "");
  $("rname").textContent = s ? s.name : "Nothing playing";
  $("rsub").textContent = s ? (r.title || [s.country, ...(s.tags || [])].filter(Boolean)
                                                                        .join(" · "))
                            : "Pick a station below.";
  $("ract").textContent = r.on ? "Stop radio" : "Play radio";
  $("ract").classList.toggle("on", !!r.on);
  $("rstar").disabled = !s;
  $("rstar").textContent = s && s.fav ? "★ Starred" : "☆ Star";
  $("rstar").classList.toggle("fav", !!(s && s.fav));
  press($("rlive"), !!r.live);
  $("rlive").textContent = r.live ? "Live: others hear it" : "Only me";
  press($("rhear"), !!r.hear);
  const now = s ? s.id : "";
  for (const b of document.querySelectorAll(".st")) {
    b.classList.toggle("playing", b.dataset.id === now);
  }
}

function radioSend(path) {
  return send(path).then((r) => { st.radio = r; drawRadio(r); drawVolume(); }, () => {});
}

function stationRow(s) {
  const li = document.createElement("li");
  const b = document.createElement("button");
  b.className = "st" + (s.playing ? " playing" : "");
  b.dataset.id = s.id;
  const n = document.createElement("b");
  n.textContent = s.name;
  const sub = document.createElement("span");
  sub.textContent = [s.country, ...(s.tags || [])].filter(Boolean).join(" · ") || " ";
  b.append(n, sub);
  b.addEventListener("click", () => {
    if (navigator.vibrate) { navigator.vibrate(12); }
    radioSend("radio?id=" + q(s.id));
  });
  const star = document.createElement("button");
  star.className = "star" + (s.fav ? " fav" : "");
  star.textContent = s.fav ? "★" : "☆";
  star.setAttribute("aria-label", s.fav ? "Unstar " + s.name : "Star " + s.name);
  star.addEventListener("click", () => {
    send("radio_star?id=" + q(s.id) + "&on=toggle").then((a) => {
      s.fav = !!a.fav;
      star.className = "star" + (s.fav ? " fav" : "");
      star.textContent = s.fav ? "★" : "☆";
      status();
    }, () => {});
  });
  li.append(b, star);
  return li;
}

function drawSeg() {
  for (const b of $("rlists").children) {
    b.classList.toggle("sel", !rquery.trim() && b.dataset.list === rlist);
  }
}

async function loadStations() {
  clearTimeout(rpoll);
  const words = rquery.trim();
  const which = words ? "search" : (rlist || "favorites");
  let body;
  try {
    body = await api("stations?list=" + which + (words ? "&q=" + q(words) : ""));
  } catch (e) { return; }
  if (rquery.trim() !== words || (!words && which !== (rlist || "favorites"))) { return; }
  if (!rlist && !words) {       // first look: favourites if there are any, else popular
    rlist = (body.stations || []).length ? "favorites" : "popular";
    drawSeg();
    if (rlist === "popular") { loadStations(); return; }
  }
  const list = $("stations");
  list.replaceChildren();
  for (const s of body.stations || []) { list.appendChild(stationRow(s)); }
  let note = "";
  if (body.error) { note = "Can't reach the station directory: " + body.error; }
  else if (body.loading) { note = words ? "Searching…" : "Finding stations…"; }
  else if (!(body.stations || []).length) {
    note = words ? "No station matches that."
         : which === "favorites" ? "No favorites yet: tap ☆ beside a station to keep it here."
         : which === "recent" ? "Stations you play show up here."
         : "No stations.";
  }
  $("rnote").textContent = note;
  if (body.loading && rtries++ < 15) { rpoll = setTimeout(loadStations, 1200); }
}

function buildRadio() {
  for (const b of $("rlists").children) {
    b.addEventListener("click", () => {
      rlist = b.dataset.list; rquery = ""; $("rfind").value = ""; rtries = 0;
      drawSeg(); loadStations();
    });
  }
  $("rfind").addEventListener("input", (e) => {
    rquery = e.target.value; rtries = 0; drawSeg();
    clearTimeout(rtimer);
    rtimer = setTimeout(loadStations, 450);
  });
  $("ract").addEventListener("click", () => radioSend("radio?on=toggle"));
  $("rrandom").addEventListener("click", () =>
    radioSend("radio_random" + (rlist && !rquery.trim() ? "?list=" + rlist : "")));
  $("rstar").addEventListener("click", () =>
    send("radio_star?on=toggle").then(() => {
      status();
      if (rlist === "favorites") { loadStations(); }
    }, () => {}));
  $("rlive").addEventListener("click", () => radioSend("radio_live?on=toggle"));
  $("rhear").addEventListener("click", () => radioSend("radio_hear?on=toggle"));
}

// ------------------------------------------------------------------ status, start
async function status() {
  try {
    st = await api("status");
    playing = new Set(st.playing || []);
    markPlaying();
    const live = $("live");
    live.textContent = st.live ? "Live" : "Muted";
    live.className = st.live ? "on" : "off";
    drawTabs();
    drawVolume();
    drawLive(st);
    drawMode(st.mode);
    drawRadio(st.radio);
  } catch (e) {}
}

async function load() {
  if (!key) { state("", "Not paired"); drawPads(); return; }
  try {
    const [list, names] = await Promise.all([api("sounds"), api("categories")]);
    sounds = list || [];
    cats = names || [];
    if (cat && !cats.includes(cat)) { cat = ""; }
    say(""); drawChips(); drawPads(); await status();
    if (view === "radio") { loadStations(); }
    if (view === "sound") { loadSound(); }
  } catch (e) {}
}

function poll() {
  clearInterval(timer);
  if (document.visibilityState === "visible" && key) { timer = setInterval(status, 2000); }
}

function volume(step) {
  const path = (view === "radio" ? "radio_volume" : "volume") + "?step=" + step;
  api(path).then(status, () => {});
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
  $("down").addEventListener("click", () => volume("down"));
  $("up").addEventListener("click", () => volume("up"));
  $("find").addEventListener("input", (e) => { query = e.target.value; drawPads(); });
  for (const name of ["pads", "radio", "sound"]) {
    $("tab-" + name).addEventListener("click", () => show(name));
  }
  buildSound();
  buildRadio();
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
  <div id="padhead">
    <div id="tools" class="tools hide">
      <input id="find" type="search" placeholder="Search sounds" aria-label="Search sounds"
        autocomplete="off" enterkeyhint="search">
    </div>
    <div id="chips" class="chips" hidden></div>
  </div>
</header>
<div id="msg" role="status"></div>
<main id="pads"></main>

<section id="radio" class="view" hidden>
  <div id="roff" class="empty" hidden><span class="big">&#x1F4FB;</span>
    <strong>Radio is off on the PC</strong>It's switched off in Onion Board's Settings,
    Privacy &amp; security.</div>
  <div id="ron">
    <div class="card now">
      <div><span id="rstate" class="kicker">Radio</span>
        <strong id="rname">Nothing playing</strong><span id="rsub"></span></div>
      <div class="row">
        <button id="rrandom" title="Play a random station">&#x1F500; Random</button>
        <button id="rstar" title="Keep this station in Favorites">&#x2606; Star</button>
      </div>
      <div class="row">
        <button id="rlive" class="toggle" aria-pressed="false"
          title="Whether others hear the radio">Only me</button>
        <button id="rhear" class="toggle" aria-pressed="false"
          title="Also play the radio into your headphones">Hear it myself</button>
      </div>
    </div>
    <div id="rlists" class="seg" role="tablist">
      <button data-list="favorites">&#x2605; Favorites</button>
      <button data-list="recent">Recent</button>
      <button data-list="popular">Popular</button>
    </div>
    <input id="rfind" type="search" placeholder="Search stations, genres, countries"
      aria-label="Search radio stations" autocomplete="off" enterkeyhint="search">
    <p id="rnote" class="note" role="status"></p>
    <ul id="stations" class="stations"></ul>
  </div>
</section>

<section id="sound" class="view" hidden>
  <div class="card">
    <div class="head"><h2>Speed</h2><span id="speedv" class="val">1x</span></div>
    <input id="speed" type="range" min="0.25" max="2" step="0.05" value="1"
      aria-label="Speed">
    <div id="quick" class="quick"></div>
    <button id="keep" class="switch" aria-pressed="true">Keep pitch when changing speed</button>
  </div>
  <div class="card">
    <div class="head"><h2>Pitch</h2><span id="pitchv" class="val">0 st</span></div>
    <div class="step">
      <button id="pdown" aria-label="Pitch down">&minus;</button>
      <input id="pitch" type="range" min="-12" max="12" step="1" value="0" aria-label="Pitch">
      <button id="pup" aria-label="Pitch up">+</button>
    </div>
  </div>
  <div class="card">
    <div class="head"><h2>Effects</h2></div>
    <div id="fx" class="fx"></div>
    <div id="presets" class="chips wrap"></div>
  </div>
  <div class="card">
    <div class="head"><h2>Who's listening</h2></div>
    <select id="mode" aria-label="Who's listening"></select>
    <p id="modenote" class="hint"></p>
  </div>
  <p class="hint">Speed, pitch and effects change every sound while it plays, like the
    speed button on the PC's Sounds tab: your sounds themselves stay as they are.</p>
</section>

<nav class="dock">
  <div class="row">
    <button id="stop" title="Stop every sound">Stop all</button>
    <button id="ract" hidden>Play radio</button>
    <button id="reset" hidden title="Back to 1x, no pitch change, no effects">Reset all</button>
    <div class="vol">
      <button id="down" title="Quieter" aria-label="Quieter">&minus;</button>
      <span class="meter"><span id="vlabel" class="vlabel">Sounds</span>
        <span id="vol" aria-label="Volume">&ndash;</span>
        <span class="bar"><span id="volbar"></span></span></span>
      <button id="up" title="Louder" aria-label="Louder">+</button>
    </div>
  </div>
  <div id="tabs" class="tabs" role="tablist" hidden>
    <button id="tab-pads" class="tab sel" role="tab" aria-selected="true">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="3" width="7.5" height="7.5" rx="2"/>
        <rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/>
        <rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/>
        <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/></svg>Pads</button>
    <button id="tab-radio" class="tab" role="tab" aria-selected="false" hidden>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="8" width="18" height="13" rx="3"/>
        <path d="M7 8 17 3"/>
        <circle cx="15.5" cy="14.5" r="2.5"/>
        <path d="M6.5 12.5h4M6.5 16.5h4"/></svg>Radio</button>
    <button id="tab-sound" class="tab" role="tab" aria-selected="false" hidden>
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 3v18M12 3v18M19 3v18"/>
        <circle cx="5" cy="15" r="2.2"/>
        <circle cx="12" cy="8" r="2.2"/>
        <circle cx="19" cy="13" r="2.2"/></svg>Sound</button>
  </div>
</nav>
<script>{script}</script>
</body>
</html>
"""


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def page(signed: bool = False) -> tuple[bytes, dict]:
    """(body, headers) for host.server(page=…). `signed`: the board takes X-Sig, so
    the script signs requests instead of sending the key."""
    script = SCRIPT.replace("{signed}", "true" if signed else "false")
    html = (BODY.replace("{icon}", ICON).replace("{logo}", LOGO)
            .replace("{style}", STYLE).replace("{script}", script))
    csp = ("default-src 'none'; "
           f"script-src {_sha(script)}; style-src {_sha(STYLE)}; "
           "img-src data:; connect-src 'self'; base-uri 'none'; form-action 'none'; "
           "frame-ancestors 'none'")
    return html.encode("utf-8"), {
        "Content-Type": "text/html; charset=utf-8",
        "Content-Security-Policy": csp,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-store",
    }
