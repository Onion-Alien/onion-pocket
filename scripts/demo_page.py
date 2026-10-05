"""Preview the phone page in a browser, without Onion Board: the real page with a
pretend board behind it (made-up sounds, nothing plays). For working on the page's
look and for docs/screenshots/phone.png.

    python scripts/demo_page.py            # then open the link it prints
    python scripts/demo_page.py --many     # 30 sounds (shows the search box)
    python scripts/demo_page.py --old      # an Onion Board without Radio and Sound

It answers only on 127.0.0.1. Use the browser's phone view (F12, device toolbar).
The README's picture is made with --shot: a phone-sized (390 x 780, scale 2) shot in
headless Edge or Chrome, with two pads playing:

    python scripts/demo_page.py --shot docs/screenshots/phone.png
    python scripts/demo_page.py --shot docs/screenshots/radio.png --view radio
    python scripts/demo_page.py --shot docs/screenshots/sound.png --view sound
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from onion_pocket import page  # noqa: E402

KEY = "demo"
SOUNDS = [
    ("Airhorn", "#ff5c8a", ["Memes"]), ("Bruh", "#1fb5ff", ["Memes"]),
    ("Sad trombone", "#ffb020", ["Fails"]), ("Vine boom", "#00c2b2", ["Memes"]),
    ("Drum roll", "#13ce66", []), ("Applause", "#7c5cff", []),
    ("Crickets", "#5b8def", ["Fails"]), ("Level up", "#f5a623", ["Games"]),
    ("Oof", "#e8505b", ["Games", "Fails"]), ("Laugh track", "#b36bff", ["Memes"]),
    ("Siren", "#ff6b3d", []), ("Ding", "#2bc0e4", ["Games"]),
]
EXTRA = ["Wow", "Goat scream", "Thunder", "Door knock", "Cash register", "Whoosh",
         "Ghost", "Robot beep", "Piano chord", "Guitar riff", "Duck", "Cat meow",
         "Phone ring", "Hello there", "Nope", "Fire alarm", "Rain", "Kiss"]
STATIONS = [
    ("Lofi Beats 24/7", "The Netherlands", ["lofi", "chill"]),
    ("Classic Rock Hits", "United States", ["rock", "80s"]),
    ("Jazz Lounge", "France", ["jazz"]),
    ("Synthwave Nights", "Germany", ["synthwave", "electronic"]),
    ("Morning Talk", "United Kingdom", ["talk", "news"]),
    ("Pop Party Radio", "Brazil", ["pop", "dance"]),
    ("Ambient Space", "Iceland", ["ambient"]),
    ("Metal Forge", "Finland", ["metal"]),
]
KNOBS = [{"key": "bass", "label": "Bass", "lo": -12, "hi": 18, "unit": "dB"},
         {"key": "treble", "label": "Treble", "lo": -12, "hi": 12, "unit": "dB"},
         {"key": "muffle", "label": "Muffle", "lo": 0, "hi": 1, "unit": ""},
         {"key": "reverb", "label": "Reverb", "lo": 0, "hi": 1, "unit": ""},
         {"key": "echo", "label": "Echo", "lo": 0, "hi": 1, "unit": ""},
         {"key": "crunch", "label": "Distortion", "lo": 0, "hi": 1, "unit": ""}]
PRESETS = {"Bass boosted": {"bass": 12}, "Blown out": {"bass": 15, "crunch": 0.7},
           "Concert hall": {"reverb": 0.55}, "Canyon": {"echo": 0.6, "reverb": 0.2},
           "Underwater": {"muffle": 0.8, "reverb": 0.3, "bass": 4},
           "Phone call": {"bass": -12, "treble": -4, "muffle": 0.45, "crunch": 0.15}}
MODES = [("off", "Off (send as is)", "No shaping. Your sounds go out exactly as mixed."),
         ("discord", "Discord", "Shaped for Discord's voice chat."),
         ("game", "Vivox", "Shaped for Vivox game voice chat."),
         ("steam", "Steam voice", "Shaped for Steam voice chat.")]
COLORS = ["#ff5c8a", "#1fb5ff", "#ffb020", "#00c2b2", "#13ce66", "#7c5cff"]


def board(many: bool) -> dict:
    sounds = [{"id": f"s{i}", "name": n, "color": c, "categories": cats, "hotkey": ""}
              for i, (n, c, cats) in enumerate(SOUNDS)]
    if many:
        sounds += [{"id": f"x{i}", "name": n, "color": COLORS[i % len(COLORS)],
                    "categories": [], "hotkey": ""} for i, n in enumerate(EXTRA)]
    stations = [{"id": f"r{i}", "name": n, "country": c, "tags": t, "bitrate": 128,
                 "fav": i in (1, 2)} for i, (n, c, t) in enumerate(STATIONS)]
    return {"sounds": sounds, "categories": ["Memes", "Fails", "Games"],
            "live": True, "volume": 80, "playing": {},
            "speed": 1.25, "pitch": 2, "keep": True, "fx": {"bass": 12}, "mode": "discord",
            "stations": stations, "recent": ["r0", "r3"], "radio_on": "r0",
            "radio_live": True, "radio_hear": True, "radio_vol": 60}


def live(st) -> dict:
    fx = {k: v for k, v in st["fx"].items() if v}
    preset = next((n for n, a in PRESETS.items() if a == fx), "")
    return {"speed": st["speed"], "pitch": st["pitch"], "keep_pitch": st["keep"],
            "effects": fx, "preset": preset}


def radio(st) -> dict:
    on = next((s for s in st["stations"] if s["id"] == st["radio_on"]), None)
    return {"available": True, "on": on is not None, "connecting": False,
            "station": dict(on, playing=True) if on else None,
            "title": "Night Drive (lofi mix)" if on else "", "live": st["radio_live"],
            "hear": st["radio_hear"], "volume": st["radio_vol"], "last": True}


def modes(st) -> dict:
    label = next(lab for k, lab, _n in MODES if k == st["mode"])
    return {"mode": st["mode"], "mode_label": label,
            "modes": [{"key": k, "label": lab, "note": n} for k, lab, n in MODES]}


class Handler(BaseHTTPRequestHandler):
    state: dict = {}

    def log_message(self, *args):
        pass

    def _send(self, code, body, headers):
        self.send_response(code)
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlsplit(self.path).path != "/":
            return self._send(404, b"", {})
        body, headers = page.page()
        self._send(200, body, headers)

    def do_POST(self):
        url = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        if self.headers.get("X-Token") != KEY:
            return self._json(401, {"error": "wrong key"})
        st, action = self.state, url.path.removeprefix("/api/")
        now = time.monotonic()
        st["playing"] = {k: t for k, t in st["playing"].items() if t > now}
        if action == "sounds":
            return self._json(200, st["sounds"])
        if action == "categories":
            return self._json(200, st["categories"])
        if action == "play":
            st["playing"][q.get("id", "")] = now + 2.5
            return self._json(200, {"playing": q.get("id", "")})
        if not st.get("old"):
            answer = self._new(st, action, q)
            if answer is not None:
                return self._json(200, answer)
        if action == "stop":
            st["playing"].clear()
        elif action == "live":
            st["live"] = not st["live"]
        elif action == "volume":
            st["volume"] = max(0, min(100, st["volume"] + (10 if q.get("step") == "up" else -10)))
        elif action != "status":
            return self._json(404, {"error": "no such action"})
        status = {"live": st["live"], "volume": st["volume"], "playing": list(st["playing"])}
        if not st.get("old"):
            status.update(live(st), mode=st["mode"], radio=radio(st))
        return self._json(200, status)

    @staticmethod
    def _new(st, action, q):
        """The newer actions (Onion Board 1.7.2): speed, effects, mode, radio."""
        def flip(v):
            return not v if q.get("on", "toggle") == "toggle" else q["on"] == "1"

        def step(v, lo, hi, by):
            return max(lo, min(hi, v + (by if q.get("step") == "up" else -by)))
        if action == "speed":
            if "keep" in q:
                st["keep"] = not st["keep"]
            if "set" in q:
                st["speed"] = max(0.25, min(2.0, float(q["set"])))
            return live(st)
        if action == "pitch":
            if "set" in q:
                st["pitch"] = max(-12, min(12, round(float(q["set"]))))
            elif "step" in q:
                st["pitch"] = step(st["pitch"], -12, 12, 1)
            return live(st)
        if action == "effects":
            if not q:
                return {**live(st), "knobs": KNOBS, "presets": list(PRESETS)}
            if "preset" in q:
                st["fx"] = dict(PRESETS.get(q["preset"], {}))
            for k in KNOBS:
                if k["key"] in q:
                    st["fx"][k["key"]] = float(q[k["key"]])
            return live(st)
        if action == "reset":
            st.update(speed=1.0, pitch=0, fx={})
            return live(st)
        if action == "mode":
            st["mode"] = q.get("set", st["mode"])
            return modes(st)
        if action == "stations":
            which, words = q.get("list", "popular"), q.get("q", "").lower()
            found = st["stations"]
            if which == "favorites":
                found = [s for s in found if s["fav"]]
            elif which == "recent":
                found = [s for s in found if s["id"] in st["recent"]]
            elif which == "search":
                found = [s for s in found if words in (s["name"] + " ".join(s["tags"])).lower()]
            return {"list": which, "loading": False, "error": "",
                    "stations": [dict(s, playing=s["id"] == st["radio_on"]) for s in found]}
        if action == "radio":
            if "id" in q:
                st["radio_on"] = q["id"]
            else:
                st["radio_on"] = "" if st["radio_on"] else "r0"
            return radio(st)
        if action == "radio_random":
            st["radio_on"] = f"r{int(time.monotonic() * 1000) % len(STATIONS)}"
            return radio(st)
        if action == "radio_star":
            s = next(s for s in st["stations"] if s["id"] == q.get("id", st["radio_on"]))
            s["fav"] = flip(s["fav"])
            return {"id": s["id"], "fav": s["fav"]}
        if action in ("radio_live", "radio_hear"):
            st[action] = flip(st[action])
            return radio(st)
        if action == "radio_volume":
            st["radio_vol"] = step(st["radio_vol"], 0, 100, 10)
            return radio(st)
        return None

    def _json(self, code, data):
        self._send(code, json.dumps(data).encode(), {"Content-Type": "application/json"})


def browser() -> str:
    for name in ("msedge", "chrome", "google-chrome", "chromium"):
        if found := shutil.which(name):
            return found
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles")):
        for rel in (r"Microsoft\Edge\Application\msedge.exe",
                    r"Google\Chrome\Application\chrome.exe"):
            if base and (Path(base) / rel).exists():
                return str(Path(base) / rel)
    sys.exit("--shot needs Edge or Chrome")


def shot(url: str, out: Path, width=390, height=780, scale=2, view="pads"):
    """A phone-sized picture of url, through the browser's DevTools protocol (a
    headless window can't be made narrower than ~500 px; the emulated phone can)."""
    from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer, QUrl
    from PySide6.QtWebSockets import QWebSocket

    app = QCoreApplication.instance() or QCoreApplication([])
    profile = tempfile.mkdtemp(prefix="onion-pocket-shot-")
    proc = subprocess.Popen([browser(), "--headless=new", "--disable-gpu",
                             "--hide-scrollbars", "--remote-debugging-port=0",
                             f"--user-data-dir={profile}", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        port_file = Path(profile) / "DevToolsActivePort"
        for _ in range(100):
            if port_file.exists() and port_file.read_text().strip():
                break
            time.sleep(0.1)
        port = port_file.read_text().split()[0]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=10) as r:
            target = next(t for t in json.load(r) if t["type"] == "page")
        ws, replies, ids = QWebSocket(), {}, iter(range(1, 1000))
        ws.textMessageReceived.connect(lambda m: replies.update({json.loads(m).get("id"):
                                                                  json.loads(m)}))

        def wait(ms, until=lambda: False):
            loop = QEventLoop()
            timer = QTimer(singleShot=True, interval=ms, timeout=loop.quit)
            check = QTimer(interval=20, timeout=lambda: until() and loop.quit())
            timer.start()
            check.start()
            loop.exec()
            check.stop()

        def call(method, **params):
            i = next(ids)
            ws.sendTextMessage(json.dumps({"id": i, "method": method, "params": params}))
            wait(15000, lambda: i in replies)
            if "error" in replies.get(i, {"error": "timed out"}):
                sys.exit(f"{method}: {replies.get(i, {}).get('error', 'timed out')}")
            return replies[i]["result"]

        ws.open(QUrl(target["webSocketDebuggerUrl"]))
        wait(10000, lambda: ws.state().name == "ConnectedState")
        call("Emulation.setDeviceMetricsOverride", width=width, height=height,
             deviceScaleFactor=scale, mobile=True)
        call("Page.enable")
        call("Page.addScriptToEvaluateOnNewDocument", source=(
            "window.__errors=[];addEventListener('error',e=>__errors.push(String(e.message)));"
            "addEventListener('unhandledrejection',e=>__errors.push(String(e.reason)));"))
        call("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-color-scheme", "value": "dark"},
            {"name": "prefers-reduced-motion", "value": "reduce"}])   # bars stand still
        call("Page.navigate", url=url)
        wait(2500)
        if view != "pads":
            call("Runtime.evaluate", expression=f"document.getElementById('tab-{view}').click()")
            wait(1500)
        errors = call("Runtime.evaluate", expression="window.__errors || []",
                      returnByValue=True)["result"].get("value")
        if errors:
            print("page errors:", errors)
        png = call("Page.captureScreenshot", format="png")["data"]
        out.write_bytes(base64.b64decode(png))
        ws.close()
        del app
    finally:
        proc.terminate()
        proc.wait(10)
        shutil.rmtree(profile, ignore_errors=True)
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--port", type=int, default=7476)
    ap.add_argument("--many", action="store_true", help="30 sounds instead of 12")
    ap.add_argument("--old", action="store_true",
                    help="an older Onion Board: the pads only, no Radio or Sound tab")
    ap.add_argument("--view", choices=("pads", "radio", "sound"), default="pads",
                    help="the tab --shot shows")
    ap.add_argument("--playing", default="", metavar="IDS",
                    help="sounds that keep playing, e.g. s1,s4")
    ap.add_argument("--shot", type=Path, metavar="PNG",
                    help="save a phone-sized picture (two pads playing) and quit")
    args = ap.parse_args()
    Handler.state = board(args.many)
    Handler.state["old"] = args.old
    playing = args.playing or ("s1,s4" if args.shot else "")
    Handler.state["playing"] = {i: float("inf") for i in playing.split(",") if i}
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/#k={KEY}"
    if args.shot:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        shot(url, args.shot, view=args.view)
        srv.shutdown()
        return
    print(f"Onion Pocket demo: {url}   (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
