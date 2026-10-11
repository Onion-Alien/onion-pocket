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
import json
from urllib.parse import quote

from . import __version__

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

STYLE += """
/* A short, self-contained dive before pairing. All artwork is drawn here. */
#dive { position:fixed; inset:0; z-index:100; display:grid; place-items:center;
  overflow:hidden; color:var(--text);
  background:radial-gradient(120% 60% at 0% 0%, #7c5cff33, transparent 60%),
    radial-gradient(90% 50% at 100% 0%, #ff4d8d24, transparent 60%), var(--bg);
  font-family:Arial, Helvetica, sans-serif; -webkit-font-smoothing:antialiased; }
.dive-logo { position:absolute; top:max(40px, env(safe-area-inset-top));
  left:50%; transform:translateX(-50%); display:flex; flex-direction:column;
  align-items:center; gap:16px; white-space:nowrap; font-size:clamp(26px, 7vw, 32px);
  font-weight:800; letter-spacing:-1px; }
.dive-logo svg { width:64px; height:64px;
  filter:drop-shadow(0 4px 10px #7c5cff30); }
.dive-logo em { font-style:normal; background:linear-gradient(90deg, #7c5cff, #ff4d8d);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.dive-loading { position:absolute; top:calc(50% + 132px);
  left:50%; transform:translateX(-50%); width:min(260px, 70vw); }
.dive-track { display:block; height:8px; border-radius:8px; overflow:hidden;
  background:#ffffff16; }
.dive-track i { display:block; height:100%; border-radius:inherit;
  background:linear-gradient(90deg, #7c5cff, #ff4d8d);
  transform-origin:left; animation:dive-progress-pending 3s steps(1, end) both; }
.dive-credit { position:absolute; bottom:max(20px, env(safe-area-inset-bottom));
  left:max(22px, env(safe-area-inset-left)); display:flex; align-items:baseline; gap:7px;
  color:var(--dim); }
.dive-credit span { font-size:9px; font-weight:600; text-transform:uppercase;
  letter-spacing:1.2px; }
.dive-credit strong { font-family:"Trebuchet MS", "Avenir Next", sans-serif;
  font-size:13px; font-weight:700; letter-spacing:-.2px;
  background:linear-gradient(90deg, #ae90ff, #ff80b5);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.dive-stage { width:min(360px, 90vw); }
.dive-stage svg { display:block; width:100%; overflow:hidden; }
.dive-bun { animation:dive-wait 2.8s ease-in-out both; transform-origin:320px 190px; }
.dive-flipper { animation:dive-kick .48s ease-in-out infinite alternate;
  transform-box:fill-box; transform-origin:50% 0%; }
.dive-left { animation:dive-left 2.8s ease-in-out both; }
.dive-right { animation:dive-right 2.8s ease-in-out both; }
.dive-light { animation:dive-light 2.8s linear both; }
.dive-thumb { animation:dive-thumb 2.8s ease-in-out both;
  transform-box:fill-box; transform-origin:center bottom; }
.dive-hand-left { transform-origin:300px 219px; animation:dive-grab-left 2.8s ease-in-out both; }
.dive-hand-right { transform-origin:340px 219px; animation:dive-grab-right 2.8s ease-in-out both; }
.dive-right-paw { transform-origin:351px 251px; animation:dive-wrist 2.8s ease-in-out both; }
.dive-bubble { animation:dive-bubble 2.4s ease-in infinite; }
.dive-bubble.b2 { animation-delay:-.8s; }
.dive-bubble.b3 { animation-delay:-1.6s; }
@keyframes dive-swim {
  0% { transform:translate(0,-25px) rotate(-8deg); }
  20% { transform:translate(-24px,10px) rotate(8deg); }
  38%, 55% { transform:translate(0,22px) rotate(0); }
  65%, 78% { transform:translate(0,0) rotate(-4deg); }
  100% { transform:translate(480px,-130px) rotate(20deg); }
}
@keyframes dive-grab-left { 0%, 30% { transform:rotate(0); }
  50%, 55% { transform:rotate(-38deg); } 65%, 100% { transform:rotate(0); } }
@keyframes dive-grab-right { 0%, 30% { transform:rotate(0); }
  50%, 55% { transform:rotate(38deg); } 68%, 100% { transform:rotate(-78deg); } }
@keyframes dive-wrist { 0%, 30% { transform:rotate(0); }
  50%, 55% { transform:rotate(-38deg); } 68%, 100% { transform:rotate(78deg); } }
@keyframes dive-kick { to { transform:rotate(22deg); } }
@keyframes dive-progress-complete {
  0% { transform:scaleX(0); } 10% { transform:scaleX(.15); }
  32% { transform:scaleX(.39); } 56% { transform:scaleX(.58); }
  78% { transform:scaleX(.84); } 96%, 100% { transform:scaleX(1); }
}
@keyframes dive-left { 0%, 30% { transform:translateX(-30px); }
  50%, 100% { transform:translateX(0); } }
@keyframes dive-right { 0%, 30% { transform:translateX(30px); }
  50%, 100% { transform:translateX(0); } }
@keyframes dive-light { 0%, 49% { opacity:0; } 52%, 100% { opacity:1; } }
@keyframes dive-thumb { 0%, 58% { transform:scaleY(.1); }
  68%, 100% { transform:scaleY(1); } }
@keyframes dive-bubble { from { transform:translateY(30px); opacity:0; }
  20% { opacity:.7; } to { transform:translateY(-180px); opacity:0; } }
@media (prefers-reduced-motion:reduce) {
  #dive * { animation:none; }
  .dive-hand-right { transform:rotate(-78deg); }
  .dive-right-paw { transform:rotate(78deg); }
}
@media (max-height:520px) {
  .dive-logo { top:max(16px, env(safe-area-inset-top)); font-size:22px; gap:8px; }
  .dive-logo svg { width:40px; height:40px; }
  .dive-stage { width:min(300px, 75vw); }
  .dive-loading { top:calc(50% + 105px); }
}
"""

STYLE += """
.dive-versions { position:absolute; right:max(22px,env(safe-area-inset-right));
  bottom:max(20px,env(safe-area-inset-bottom)); text-align:right;
  font:600 10px/1.65 Arial,sans-serif; color:#a99abc; }
.dive-versions span { display:block; }
#connection-actions { display:none; gap:10px; margin:0 16px 16px; }
#connection-actions:has(button:not([hidden])) { display:flex; }
#connection-actions button[hidden] { display:none; }
#error-details { width:min(520px,calc(100vw - 32px)); box-sizing:border-box;
  max-height:calc(100dvh - 32px); overflow:auto; border:1px solid #51405f;
  border-radius:24px; padding:24px; color:#f4efff; background:#191322;
  box-shadow:0 24px 80px #0009; font-family:Arial,sans-serif; }
#error-details::backdrop { background:#090610b8; backdrop-filter:blur(7px); }
.error-heading { display:flex; align-items:start; justify-content:space-between; gap:12px; }
.error-heading h2 { margin:5px 0 12px; font-size:25px; letter-spacing:-.6px;
  text-transform:none; color:#f4efff; }
.error-kicker { color:#d29aff; font-weight:700; font-size:11px; letter-spacing:1.8px; }
#error-close { border-radius:50%; width:36px; height:36px; padding:0; font-size:24px; }
#error-summary { margin:0 0 16px; color:#c5b7d3; font-size:14px; line-height:1.5; }
#error-report { display:block; box-sizing:border-box; width:100%; height:260px;
  min-height:130px; resize:vertical; background:#100c18; color:#ded3ed;
  border:1px solid #40324f; border-radius:12px; padding:14px;
  font:12px/1.6 Consolas,monospace; white-space:pre-wrap; overflow-wrap:anywhere; }
.error-footer { display:flex; align-items:center; gap:12px; margin-top:16px; }
#error-copy { background:linear-gradient(115deg,#9660ec,#c45ab0); color:white;
  border:0; font-weight:700; font-size:12px; padding:9px 13px; border-radius:10px;
  flex-shrink:0; white-space:nowrap; }
#copy-status { font-size:12px; color:#c5b7d3; }
@media(max-height:540px) { #error-details { padding:18px; } #error-report { height:150px; } }
.dive-x-eyes { opacity:0; }
#dive:not(.connected) .dive-left { animation:none; transform:translateX(-30px); }
#dive:not(.connected) .dive-right { animation:none; transform:translateX(30px); }
#dive:not(.connected) .dive-light { animation:none; opacity:0; }
#dive:not(.connected) .dive-hand-left,
#dive:not(.connected) .dive-hand-right,
#dive:not(.connected) .dive-right-paw { animation:none; transform:rotate(0); }
#dive:not(.connected) .dive-thumb { animation:none; transform:scaleY(.1); }
#dive.connected .dive-bun { animation-name:dive-swim; }
#dive.connected .dive-track i { animation-name:dive-progress-complete;
  animation-delay:var(--dive-progress-delay, 0ms); }
#dive.connected .dive-bun, #dive.connected .dive-left, #dive.connected .dive-right,
#dive.connected .dive-hand-left, #dive.connected .dive-hand-right,
#dive.connected .dive-right-paw, #dive.connected .dive-thumb, #dive.connected .dive-light,
#dive.failed .dive-bun, #dive.failed .dive-eyes, #dive.failed .dive-x-eyes {
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-bun { animation-name:dive-sink; }
#dive.failed .dive-hand-right { animation:dive-down-arm 2.8s ease-in-out both;
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-right-paw { animation:dive-down-wrist 2.8s ease-in-out both;
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-thumb { animation:dive-thumb 2.8s ease-in-out both;
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-eyes { animation:dive-shut 2.8s steps(1, end) both;
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-x-eyes { animation:dive-cross 2.8s steps(1, end) both;
  animation-delay:var(--dive-delay, 0ms); }
#dive.failed .dive-track i { background:linear-gradient(90deg, #ff826f, #ff4d8d); }
@keyframes dive-wait { 0% { transform:translate(0,-25px) rotate(-8deg); }
  20% { transform:translate(-24px,10px) rotate(8deg); }
  38%, 100% { transform:translate(0,22px); } }
@keyframes dive-sink { 0% { transform:translate(0,-25px) rotate(-8deg); opacity:1; }
  20% { transform:translate(-24px,10px) rotate(8deg); }
  38%, 68% { transform:translate(0,22px); }
  80% { transform:translate(0,36px) rotate(4deg); opacity:1; }
  100% { transform:translate(0,180px) rotate(14deg); opacity:0; } }
@keyframes dive-down-arm { 0%, 38% { transform:rotate(0); }
  68%, 100% { transform:rotate(-78deg); } }
@keyframes dive-down-wrist { 0%, 38% { transform:rotate(0); }
  68%, 100% { transform:rotate(-102deg); } }
@keyframes dive-shut { 0% { opacity:1; } 75%, 100% { opacity:0; } }
@keyframes dive-cross { 0% { opacity:0; } 75%, 100% { opacity:1; } }
@keyframes dive-progress-pending {
  0% { transform:scaleX(0); } 10% { transform:scaleX(.15); }
  32% { transform:scaleX(.39); } 56% { transform:scaleX(.58); }
  78%, 100% { transform:scaleX(.84); }
}
@media (prefers-reduced-motion:reduce) {
  #dive * { animation:none !important; }
  #dive.failed .dive-eyes { opacity:0; }
  #dive.failed .dive-x-eyes { opacity:1; }
}
"""

INTRO = """
<div id="dive" aria-label="Onion Pocket opening animation">
  <div class="dive-logo">{intro-logo}<span>Onion <em>Pocket</em></span></div>
  <div class="dive-stage">
    <svg viewBox="0 0 640 400" aria-hidden="true">
      <g fill="none" stroke="#59b9c1" stroke-width="2" opacity=".7">
        <circle class="dive-bubble" cx="220" cy="280" r="5"/>
        <circle class="dive-bubble b2" cx="420" cy="260" r="8"/>
        <circle class="dive-bubble b3" cx="390" cy="300" r="4"/>
      </g>
      <g stroke="#2b2340" stroke-width="3" stroke-linejoin="round">
        <g class="dive-bun">
          <g transform="translate(320 190) scale(1.25) translate(-320 -190)">
          <ellipse cx="364" cy="228" rx="13" ry="12" fill="#fbf7f2"/>
          <ellipse cx="320" cy="224" rx="34" ry="36" fill="#fbf7f2"/>
          <ellipse cx="320" cy="233" rx="22" ry="24" fill="#ece3da" stroke="none"/>
          <g class="dive-flipper" fill="#a68afa">
            <path d="M293 249Q276 260 276 280Q297 283 306 255Z"/>
            <path d="M336 250Q350 264 354 281Q332 283 324 256Z"/>
          </g>
          <ellipse cx="298" cy="135" rx="13" ry="37" transform="rotate(-12 298 135)"
            fill="#fbf7f2"/>
          <ellipse cx="341" cy="137" rx="13" ry="35" transform="rotate(17 341 137)" fill="#fbf7f2"/>
          <ellipse cx="298" cy="136" rx="6" ry="25" transform="rotate(-12 298 136)"
            fill="#ffb3c7" stroke="none"/>
          <ellipse cx="341" cy="138" rx="6" ry="23" transform="rotate(17 341 138)"
            fill="#ffb3c7" stroke="none"/>
          <ellipse cx="320" cy="183" rx="43" ry="37" fill="#fbf7f2"/>
          <path d="M279 180Q273 135 320 141Q366 141 362 182" fill="none" stroke="#a68afa"
            stroke-width="9"/>
          <rect x="271" y="170" width="13" height="27" rx="6" fill="#a68afa"/>
          <rect x="356" y="170" width="13" height="27" rx="6" fill="#a68afa"/>
          <rect x="287" y="169" width="66" height="27" rx="12" fill="#83e5e4"
            fill-opacity=".65" stroke="#386175"/>
          <path d="M293 175l14-2M331 175l12-2" stroke="#d7ffff" stroke-width="3"
            stroke-linecap="round"/>
          <g class="dive-eyes">
          <ellipse cx="306" cy="183" rx="3" ry="5" fill="#2b2340" stroke="none"/>
          <ellipse cx="335" cy="183" rx="3" ry="5" fill="#2b2340" stroke="none"/>
          </g>
          <g class="dive-x-eyes" fill="none" stroke-linecap="round">
            <path d="M302 179l8 8M310 179l-8 8M331 179l8 8M339 179l-8 8"/>
          </g>
          <path d="M316 198Q320 204 325 198M311 207Q320 214 330 206" fill="none"
            stroke-linecap="round"/>
          {badge}
          </g>
        </g>
        <g class="dive-left">
          <path d="M70 310C120 310 145 328 210 310S267 290 297 290" fill="none"
            stroke="#485269" stroke-width="12" stroke-linecap="round"/>
          <path d="M70 307C120 307 145 325 210 307S267 287 297 287" fill="none"
            stroke="#93a5bd" stroke-width="3" stroke-linecap="round"/>
          <rect x="290" y="277" width="30" height="26" rx="5" fill="#9e7ce5"/>
          <path d="M311 283v14M301 283v14" stroke="#c6b0fb"/>
        </g>
        <g class="dive-right">
          <path d="M570 310C520 310 495 328 430 310S373 290 343 290" fill="none"
            stroke="#485269" stroke-width="12" stroke-linecap="round"/>
          <path d="M570 307C520 307 495 325 430 307S373 287 343 287" fill="none"
            stroke="#93a5bd" stroke-width="3" stroke-linecap="round"/>
          <rect x="320" y="279" width="31" height="22" rx="4" fill="#ece3da"/>
          <path d="M337 283v14M344 283v14" stroke="#9aa0b4"/>
        </g>
        <g class="dive-light" stroke="#79f5ce" fill="#79f5ce">
          <circle cx="326" cy="290" r="4" stroke="none"/>
          <path d="M312 265l-7-10M333 264l5-11M321 317v10" stroke-width="2"/>
        </g>
        <g class="dive-bun">
          <g transform="translate(320 190) scale(1.25) translate(-320 -190)">
            <g class="dive-hand-left">
              <path d="M300 219Q289 230 285 251" fill="none" stroke-width="18"
                stroke-linecap="round"/>
              <path d="M300 219Q289 230 285 251" fill="none" stroke="#fbf7f2"
                stroke-width="12" stroke-linecap="round"/>
              <circle cx="285" cy="251" r="9" fill="#fbf7f2"/>
              <path d="M281 252h6" stroke="#c6bdb7" stroke-width="1.5"/>
            </g>
            <g class="dive-hand-right">
              <path d="M340 219Q350 230 351 251" fill="none" stroke-width="18"
                stroke-linecap="round"/>
              <path d="M340 219Q350 230 351 251" fill="none" stroke="#fbf7f2"
                stroke-width="12" stroke-linecap="round"/>
              <g class="dive-right-paw">
                <path class="dive-thumb" d="M346 248V234Q346 228 350 228Q355 228 355 234V248Z"
                  fill="#fbf7f2"/>
                <circle cx="351" cy="251" r="9" fill="#fbf7f2"/>
                <path d="M348 253h6" stroke="#c6bdb7" stroke-width="1.5"/>
              </g>
            </g>
          </g>
        </g>
      </g>
    </svg>
  </div>
  <div class="dive-loading" role="status" aria-label="Loading">
    <span class="dive-track" aria-hidden="true"><i></i></span>
  </div>
  <div class="dive-credit"><span>An app by</span> <strong>Onion Alien</strong></div>
  <div class="dive-versions" aria-label="App versions">
    <span id="dive-pocket-version"></span><span id="dive-board-version"></span>
  </div>
</div>
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

const BUILD = {build};
let faults = [], attempts = 0, pairingSecret = "";
function safeDetail(value, limit = 16000) {
  let text = String(value ?? "");
  for (const secret of [key, pairingSecret]) {
    if (secret) { text = text.split(secret).join("[redacted]"); }
  }
  text = text.replace(/([#?&]k=)[^\\s&]+/g, "$1[redacted]")
    .replace(/(X-Token|X-Sig|Authorization)(\\s*[:=]\\s*)[^\\r\\n]+/gi, "$1$2[redacted]");
  return text.length > limit ? text.slice(0, limit) + " [details truncated]" : text;
}
function fault(error, endpoint = "Browser page", code = "Unavailable", elapsed = 0, detail = "") {
  if (error?.pocketRecorded) { return; }
  if (error && typeof error === "object") { error.pocketRecorded = true; }
  faults.push({ time:new Date().toISOString(), endpoint:safeDetail(endpoint), code,
    elapsed:Math.round(elapsed), name:error?.name || "Error",
    message:safeDetail(error?.message || error), stack:safeDetail(error?.stack || "Not supplied"),
    detail:safeDetail(detail) });
  faults = faults.slice(-8);
  $("error-view").hidden = false;
}
function errorReport() {
  const lines = ["ONION POCKET — CONNECTION REPORT", "", "Captured: " + new Date().toISOString(),
    "Onion Pocket: " + BUILD.pocket,
    "Page build: connection-intro-v2",
    "Onion Board: " + (st?.version || BUILD.board || "Unavailable"),
    "Host API: " + (BUILD.api || "Unavailable"), "Page: " + location.origin + location.pathname,
    "Browser: " + navigator.userAgent, "Viewport: " + innerWidth + " × " + innerHeight,
    "Online hint: " + navigator.onLine + " (does not confirm PC access)",
    "Authentication: " + (SIGNED ? "Signed request" : "Token request"),
    "Paired: " + Boolean(key), "Load attempts: " + attempts, ""];
  faults.forEach((f, i) => lines.push("FAILURE " + (i + 1) + " / " + f.time,
    "Request / location: " + f.endpoint, "HTTP status: " + f.code,
    "Duration: " + f.elapsed + " ms", f.name + ": " + f.message,
    "Server details: " + (f.detail || "Not supplied"),
    "Browser stack / file / line:", f.stack, ""));
  lines.push("Backend crash file / traceback: not exposed by Onion Board's API.",
    "For internal server errors, match the timestamp above to Onion Board's desktop log.",
    "Pairing keys and authentication headers are excluded. Review before sharing.");
  return safeDetail(lines.join("\\n"), 150000);
}
function showError() {
  $("error-report").value = errorReport();
  $("error-summary").textContent = faults.at(-1)?.message || "The connection could not complete.";
  $("copy-status").textContent = "Select or copy the report to share it.";
  if (!$("error-details").open) { $("error-details").showModal(); }
}
async function copyError() {
  const text = $("error-report").value;
  try {
    if (!navigator.clipboard?.writeText) { throw new Error("Clipboard unavailable"); }
    await navigator.clipboard.writeText(text);
    $("copy-status").textContent = "Report copied.";
  } catch (e) {
    $("error-report").focus(); $("error-report").select();
    let copied = false;
    try { copied = document.execCommand("copy"); } catch (e) {}
    $("error-report").scrollTop = 0; $("error-report").scrollLeft = 0;
    $("copy-status").textContent = copied ? "Report copied." : "Report selected. Hold to copy.";
  }
}

async function api(path, again, signal) {
  const url = "/api/" + path, used = skew;
  const begun = performance.now();
  let r;
  try {
    r = await fetch(url, { method: "POST", cache: "no-store", signal,
                           headers: SIGNED ? { "X-Sig": sign(url) } : { "X-Token": key } });
  } catch (e) {
    fault(e, "POST " + url, "No response", performance.now() - begun);
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
      if (Math.abs(s - used) > 30) { skew = s; return api(path, true, signal); }
    }
    const error = new Error("Pairing expired or rejected. Scan Onion Pocket's QR code again.");
    fault(error, "POST " + url, 401, performance.now() - begun);
    key = ""; store("");
    state("off", "Not paired");
    say("This phone isn't paired (or the PC made a new key). Scan the QR code in " +
        "Onion Board: Settings, Remote, Onion Pocket.");
    drawPads();
    throw error;
  }
  if (r.status === 429) { say("Too many wrong keys from this phone: wait a minute."); }
  const body = await r.json().catch(() => null);
  if (!r.ok && body && body.error && r.status !== 429) { say(body.error); }
  if (!r.ok) {
    const error = new Error(body?.error || "HTTP " + r.status + " " + r.statusText);
    const detail = body ? JSON.stringify(Object.fromEntries(
      ["error", "detail", "message", "traceback", "file", "line"].filter(k => k in body)
        .map(k => [k, body[k]])), null, 2) : "No JSON error body returned";
    fault(error, "POST " + url, r.status, performance.now() - begun, detail);
    state("off", "Connection failed");
    throw error;
  }
  if (body === null) {
    const error = new Error("The PC returned an empty or invalid JSON response.");
    fault(error, "POST " + url, r.status, performance.now() - begun);
    throw error;
  }
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
async function status(options = {}) {
  try {
    st = await api("status", false, options?.signal);
    if ($("dive-board-version") && st.version) {
      $("dive-board-version").textContent = "Board v" + st.version;
    }
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
    return true;
  } catch (e) { fault(e); return false; }
}

async function load(options = {}) {
  attempts++;
  if (!key) {
    state("", "Not paired"); drawPads();
    fault(new Error("This phone is not paired. Scan Onion Pocket's QR code in Onion Board."));
    return false;
  }
  try {
    const [list, names] = await Promise.all([
      api("sounds", false, options?.signal), api("categories", false, options?.signal)]);
    sounds = list || [];
    cats = names || [];
    if (cat && !cats.includes(cat)) { cat = ""; }
    say(""); drawChips(); drawPads();
    if (!await status(options)) { return false; }
    if (view === "radio") { loadStations(); }
    if (view === "sound") { loadSound(); }
    $("retry").hidden = true;
    $("error-view").hidden = true;
    $("error-details").close();
    return true;
  } catch (e) { fault(e); return false; }
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
  $("dive-pocket-version").textContent = "Pocket v" + BUILD.pocket;
  $("dive-board-version").textContent = BUILD.board
    ? "Board v" + BUILD.board : "Board version unavailable";
  let introDone = false;
  let introTimer;
  let outcome = null, revealAt = 3000;
  const started = performance.now(), controller = new AbortController();
  function result(ok) {
    if (introDone || outcome !== null) { return; }
    outcome = ok;
    const elapsed = performance.now() - started;
    const poseTime = Math.min(elapsed, ok ? 1800 : 1900);
    const dive = $("dive");
    dive.style.setProperty("--dive-delay", "-" + poseTime + "ms");
    dive.style.setProperty("--dive-progress-delay", "-" + elapsed + "ms");
    dive.classList.add(ok ? "connected" : "failed");
    revealAt = Math.max(3000, elapsed + 2800 - poseTime);
  }
  function finishIntro() {
    if (introDone) { return; }
    if (outcome === null) {
      controller.abort(new DOMException(
        "The PC did not finish loading within 3 seconds.", "TimeoutError"));
      result(false);
    }
    const remaining = revealAt - (performance.now() - started);
    if (remaining > 10) { introTimer = setTimeout(finishIntro, remaining); return; }
    introDone = true;
    clearTimeout(introTimer);
    $("dive").remove();
    $("pocket-app").inert = false;
    $("retry").hidden = outcome || !key;
    poll();
  }
  const m = /[#&]k=([A-Za-z0-9_-]+)/.exec(location.hash);
  if (m) {
    key = m[1]; store(key);
    history.replaceState(null, "", location.pathname);   // the key off the screen
  } else {
    key = stored();
  }
  pairingSecret = key;
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
  $("error-view").addEventListener("click", showError);
  $("error-close").addEventListener("click", () => $("error-details").close());
  $("error-copy").addEventListener("click", copyError);
  $("error-details").addEventListener("click", e => {
    if (e.target === $("error-details")) {
      const box = e.target.getBoundingClientRect();
      if (e.clientX < box.left || e.clientX > box.right ||
          e.clientY < box.top || e.clientY > box.bottom) {
        e.target.close();
      }
    }
  });
  $("retry").addEventListener("click", async () => {
    clearInterval(timer);
    const button = $("retry"), retryController = new AbortController();
    button.disabled = true; button.textContent = "Connecting…";
    const timeout = setTimeout(() => retryController.abort(
      new DOMException("The PC did not respond within 8 seconds.", "TimeoutError")), 8000);
    try {
      const ok = await load({ signal:retryController.signal });
      button.hidden = ok || !key;
      if (!ok) { showError(); }
    } finally {
      clearTimeout(timeout); button.disabled = false; button.textContent = "Try again"; poll();
    }
  });
  window.addEventListener("error", e => fault(e.error || new Error(e.message),
    (e.filename || "Browser page") + ":" + e.lineno + ":" + e.colno));
  window.addEventListener("unhandledrejection", e => fault(e.reason));
  document.addEventListener("visibilitychange", () => {
    if (!introDone) { return; }
    poll();
    if (document.visibilityState === "visible") { load(); }
  });
  introTimer = setTimeout(finishIntro, 3000);
  load({ signal:controller.signal }).then(result);
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
{intro}
<div id="pocket-app" inert>
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
<div id="connection-actions">
  <button id="retry" hidden>Try again</button>
  <button id="error-view" hidden>Error details</button>
</div>
<dialog id="error-details" aria-labelledby="error-title" aria-describedby="error-summary">
  <div class="error-heading"><div><span class="error-kicker">CONNECTION REPORT</span>
    <h2 id="error-title">Let's find the problem.</h2></div>
    <button id="error-close" aria-label="Close error details" autofocus>&times;</button></div>
  <p id="error-summary"></p>
  <textarea id="error-report" readonly spellcheck="false"
    aria-label="Full diagnostic report"></textarea>
  <div class="error-footer"><button id="error-copy">Copy report</button>
    <span id="copy-status" role="status"></span></div>
</dialog>
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
</div>
<script>{script}</script>
</body>
</html>
"""


def _sha(text: str) -> str:
    return "'sha256-" + base64.b64encode(hashlib.sha256(text.encode()).digest()).decode() + "'"


def page(signed: bool = False, board_version: str = "", api_version: int = 0) -> tuple[bytes, dict]:
    """(body, headers) for host.server(page=…). `signed`: the board takes X-Sig, so
    the script signs requests instead of sending the key."""
    build = json.dumps({"pocket": __version__, "board": board_version, "api": api_version})
    script = (SCRIPT.replace("{signed}", "true" if signed else "false")
              .replace("{build}", build.replace("<", "\\u003c")))
    html = (BODY.replace("{icon}", ICON).replace("{logo}", LOGO).replace("{intro}", INTRO)
            .replace("{intro-logo}", LOGO.replace('id="g"', 'id="dive-g"')
                     .replace('id="h"', 'id="dive-h"').replace("url(#g)", "url(#dive-g)")
                     .replace("url(#h)", "url(#dive-h)"))
            .replace("{badge}", '<g class="dive-badge" transform="translate(310 222) scale(.2)">'
                     + LOGO[LOGO.index(">") + 1:-6]
                     .replace('id="g"', 'id="badge-g"').replace('id="h"', 'id="badge-h"')
                     .replace("url(#g)", "url(#badge-g)").replace("url(#h)", "url(#badge-h)")
                     + "</g>")
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
