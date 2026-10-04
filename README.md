# Onion Pocket

**Your pads on your phone.** An add-on for [Onion Board](https://github.com/Onion-Alien/onion-board):
scan a QR code on the PC, and your pads open in your phone's browser. Tap one and it
plays on the PC, into Discord or your game like any pad. iPhone or Android, nothing
to install on the phone.

| On the PC: Settings → Remote | On the phone |
|---|---|
| ![Onion Pocket's card on Settings → Remote, with the QR code](docs/screenshots/settings.png) | <img src="docs/screenshots/phone.png" width="300" alt="The phone page: pads by category, Stop all, Live / Muted, volume"> |

## How it works

While it's on, Onion Board runs a tiny web server on your PC that only answers on
your home network. The QR code is just that server's address with the phone's key:
`http://<your PC>:7475/#k=…`. The phone's camera opens it like any link, the page
comes from your PC, and a tap sends "play this sound" back to it. The phone itself
never plays anything: phones don't let one app put sound into another app's mic,
so the PC still does the playing ([docs/PHONE.md](docs/PHONE.md) has the research).

- **Off by default.** Settings → Remote → *Let phones on this Wi-Fi use it*.
- **Only your network.** It answers only addresses on your local network, and only
  with its own key (in the QR code; separate from the Stream Deck key). *Forget
  phones* makes a new key. An address that gets the key wrong 5 times is ignored
  for a minute.
- **Never your mic.** A phone can play, stop and pause sounds, change the volume
  and category, and mute you (*Live / Muted*). Never the mic, the voice changer
  or the instant replay.
- **Plain HTTP on your Wi-Fi.** Someone on the same network who can read its
  traffic could take the key and play your sounds. Use it at home, not on public
  Wi-Fi. [SECURITY.md](SECURITY.md) has the details.
- **Phone can't connect?** *Let it through Windows Firewall* (Windows asks once),
  and in Windows Settings → Network & internet → Wi-Fi, set your network to
  *Private*.

## Install

It needs an Onion Board that hosts "remote" add-ons (the change in
[`app-side/`](app-side/), not in a release yet).

1. `python scripts/build_module.py` → `dist/OnionPocket-module.zip`
2. Unzip it into `%APPDATA%\OnionBoard\modules\` (you get
   `modules\onion-pocket\module.json`), then restart Onion Board.
3. Settings → Remote → *Onion Pocket*.

To remove it, delete `%APPDATA%\OnionBoard\modules\onion-pocket`.

## Code

| file | what it does |
|---|---|
| `onion_pocket/addon.py` | `create(host)`: the add-on, starting and stopping its server, and its card on Settings → Remote |
| `onion_pocket/host.py` | what Onion Board looks like from here: the whole contract (`API_VERSION`) |
| `onion_pocket/lan.py` | this PC's address on the home network, the pairing link, the Windows Firewall rule |
| `onion_pocket/page.py` | the phone page: one HTML file, inline style and script, a hash-only Content-Security-Policy |
| `onion_pocket/qr.py` | QR codes drawn in code (byte mode, level M, versions 1–10) |
| `scripts/build_module.py` | the add-on zip Onion Board installs; refuses imports Onion Board doesn't ship |
| `scripts/check_sensitive.py` | secrets / personal-data scan, also the pre-commit hook |
| `tests/` | offscreen tests against a stand-in host (`tests/fakehost.py`) |
| `app-side/` | the Onion Board change that hosts "remote" add-ons, as a patch, until it's merged |
| `docs/PHONE.md` | the research (what phones can and can't do) and the design |

## Developing

```
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\ruff check .
.venv\Scripts\python -m pytest
git config core.hooksPath .githooks
```

The add-on runs inside Onion Board, which has no pip: it may only import the
standard library and PySide6 (`scripts/build_module.py` checks).

## License

Same as Onion Board: [LICENSE](LICENSE).
