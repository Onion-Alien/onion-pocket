"""Preview the phone page in a browser, without Onion Board: the real page with a
pretend board behind it (made-up sounds, nothing plays). For working on the page's
look and for docs/screenshots/phone.png.

    python scripts/demo_page.py            # then open the link it prints
    python scripts/demo_page.py --many     # 30 sounds (shows the search box)

It answers only on 127.0.0.1. Use the browser's phone view (F12, device toolbar).
The README's picture is made with --shot: a phone-sized (390 x 780, scale 2) shot in
headless Edge or Chrome, with two pads playing:

    python scripts/demo_page.py --shot docs/screenshots/phone.png
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
COLORS = ["#ff5c8a", "#1fb5ff", "#ffb020", "#00c2b2", "#13ce66", "#7c5cff"]


def board(many: bool) -> dict:
    sounds = [{"id": f"s{i}", "name": n, "color": c, "categories": cats, "hotkey": ""}
              for i, (n, c, cats) in enumerate(SOUNDS)]
    if many:
        sounds += [{"id": f"x{i}", "name": n, "color": COLORS[i % len(COLORS)],
                    "categories": [], "hotkey": ""} for i, n in enumerate(EXTRA)]
    return {"sounds": sounds, "categories": ["Memes", "Fails", "Games"],
            "live": True, "volume": 80, "playing": {}}


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
        if action == "stop":
            st["playing"].clear()
        elif action == "live":
            st["live"] = not st["live"]
        elif action == "volume":
            st["volume"] = max(0, min(100, st["volume"] + (10 if q.get("step") == "up" else -10)))
        elif action != "status":
            return self._json(404, {"error": "no such action"})
        return self._json(200, {"live": st["live"], "volume": st["volume"],
                                "playing": list(st["playing"])})

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


def shot(url: str, out: Path, width=390, height=780, scale=2):
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
        call("Emulation.setEmulatedMedia", features=[
            {"name": "prefers-color-scheme", "value": "dark"},
            {"name": "prefers-reduced-motion", "value": "reduce"}])   # bars stand still
        call("Page.navigate", url=url)
        wait(2500)
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
    ap.add_argument("--playing", default="", metavar="IDS",
                    help="sounds that keep playing, e.g. s1,s4")
    ap.add_argument("--shot", type=Path, metavar="PNG",
                    help="save a phone-sized picture (two pads playing) and quit")
    args = ap.parse_args()
    Handler.state = board(args.many)
    playing = args.playing or ("s1,s4" if args.shot else "")
    Handler.state["playing"] = {i: float("inf") for i in playing.split(",") if i}
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/#k={KEY}"
    if args.shot:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        shot(url, args.shot)
        srv.shutdown()
        return
    print(f"Onion Pocket demo: {url}   (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
