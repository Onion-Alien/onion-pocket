<p align="right"><img src="https://hits.sh/github.com/Onion-Alien/onion-pocket.svg?view=total&label=total%20visits&color=6b8e23" alt="total visits"> <img src="https://img.shields.io/github/downloads/Onion-Alien/onion-pocket/total?label=downloads&color=6b8e23" alt="downloads"></p>

<p align="center">
  <img src="docs/logo.svg" width="96" alt="">
</p>

<h1 align="center">Onion Pocket</h1>

<p align="center">
  <b>Your pads on your phone.</b> An add-on for
  <a href="https://github.com/Onion-Alien/onion-board">Onion Board</a>.<br>
  Scan a QR code on the PC and tap a pad on your phone: it plays on the PC, into
  Discord or your game like any pad.<br>
  Queue sounds, run the radio, change the speed and effects, switch your voice
  changer, type a line for others to hear, and send Spotify into the call, from your
  phone too.<br>
  iPhone or Android, nothing to install on the phone.
</p>

| On the PC: Settings → Remote | On the phone |
|---|---|
| ![Onion Pocket's card on Settings → Remote, with the QR code](docs/screenshots/settings.png) | <img src="docs/screenshots/phone.png" width="300" alt="The phone page: Onion Board's logo, category chips, colourful pads (two playing, with a white ring and level bars), Stop all and the volume, and the Pads, Radio, Sound, Voice and Apps tabs at the bottom"> |

| Radio | Sound |
|---|---|
| <img src="docs/screenshots/radio.png" width="300" alt="The Radio tab: the station playing with Random, Star, Live and Hear it myself, your Favorites, Recent and Popular stations, a search box, and Stop radio with the radio's volume"> | <img src="docs/screenshots/sound.png" width="300" alt="The Sound tab: speed slider with quick speeds, keep pitch, pitch, and the effects (bass, treble, muffle, reverb, echo, distortion) with Reset all"> |

| Voice | Apps |
|---|---|
| <img src="docs/screenshots/voice.png" width="300" alt="The Voice tab: the voice changer switch with the voices as chips and Random voice, a Say it box with Say it and Stop, and My mic: others hear my mic, mute my mic while a sound plays, hear what they hear"> | <img src="docs/screenshots/apps.png" width="300" alt="The Apps tab: Spotify, YouTube in Edge and VLC, each with Others hear it or Only me and a volume slider; VLC is not running"> |

## What your phone can do

- **Pads:** tap to play, by category or search, *Stop all*, *Pause*, the volume, and
  *Live / Muted* (mute you for everyone). *Tap: queue it* makes a tap play that sound
  after the ones playing now; *Play all* / *Shuffle all* queue a whole category, *Up
  next* shows what's coming (*Clear* empties it). *Random*, *Again* (the last sound)
  and *Save replay* (the last seconds you heard, as a new sound).
- **Radio:** play and stop the radio, your *Favorites*, *Recent* and *Popular*
  stations or a search, a random station, star a station, *Live* (others hear the
  radio) or *Only me*, *Hear it myself*, and the radio's volume.
- **Sound:** the live speed (with the 0.5x–2x quick speeds) and pitch, *Keep pitch*,
  bass, treble, muffle, reverb, echo and distortion, the presets (*Bass boosted*,
  *Underwater*, *Phone call*…), *Reset all*, and *Who's listening* (Discord, Steam
  voice, Vivox…), and *Hotkeys on* (off: the PC's keys type normally again).
- **Voice:** the voice changer on / off, pick a voice or a random one, *Say it* (type
  a line, others hear it in the computer voice), *Others hear my mic*, *Mute my mic
  while a sound plays*, *Hear what they hear*, and your saved voice combos.
- **Apps:** the programs on Onion Board's Apps tab: *Others hear it* sends that
  program's sound (Spotify, a video) to whoever's listening, with its own volume.

Whatever the phone changes moves on the PC too: the same sliders and buttons. The
Radio and Sound tabs need Onion Board 1.7.2 or newer, the queue and the Voice tab
1.9.24, the Apps tab, voice combos and *Hotkeys on* 2.5.0; with an older one the
phone shows what that board has. A tab switched off in Onion Board's Settings → Tabs
stays off on the phone.

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
- **Only the buttons above.** A phone can do what the list above says, nothing more:
  it can turn your mic on or off for others, but never hear it, and it never reads
  or sends files (*Save replay* only keeps the last seconds as a sound on the PC).
- **Plain HTTP on your Wi-Fi.** Someone on the same network who can read its
  traffic could take the key and play your sounds. Use it at home, not on public
  Wi-Fi. [SECURITY.md](SECURITY.md) has the details.
- **Phone can't connect?** When you tick *Let phones on this Wi-Fi use it*, Windows
  asks once (its admin prompt) to let phones through the firewall: say yes. Said no?
  Click *Let it through Windows Firewall*. And in Windows Settings → Network &
  internet → Wi-Fi, set your network to *Private*.

## Install

In Onion Board (newer than 1.6.8): **Settings → Remote → *Get Onion Pocket***. It
downloads this project's latest release from GitHub, checks it against the SHA-256
GitHub lists for it, and installs it; its card then takes that button's place. If it
can't be downloaded, the button just goes away and Onion Board carries on as before.

To try a build of your own instead: `python scripts/build_module.py` →
`dist/OnionPocket-module.zip`, then either start Onion Board with
`ONIONBOARD_ONION_POCKET_ZIP` set to that zip and click *Get Onion Pocket*, or unzip it
into `%APPDATA%\OnionBoard\modules\` and restart Onion Board.

To remove it, delete `%APPDATA%\OnionBoard\modules\onion-pocket`.

## Releasing

Raise `__version__` in `onion_pocket/__init__.py`, update `docs/RELEASE-NOTES.md`,
and push a matching tag (`v0.1.0`). `.github/workflows/release.yml` runs the checks,
builds the zip and publishes the release Onion Board downloads from.

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
| `docs/PHONE.md` | the research (what phones can and can't do) and the design |
| `scripts/demo_page.py` | the phone page in your browser with made-up sounds, no Onion Board needed; `--shot` remakes `docs/screenshots/phone.png` (`--view voice`, `--size 780x360`…) |
| `.github/workflows/checks.yml` | on every push: the secrets / personal-data scan over the whole history, gitleaks, ruff and the tests |
| `.github/workflows/release.yml` | on a `v*` tag: the checks, then the add-on zip published as a GitHub release |

## Developing

```
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\ruff check .
.venv\Scripts\python -m pytest
git config core.hooksPath .githooks
```

To work on the phone page's look: `.venv\Scripts\python scripts\demo_page.py` and open
the link it prints, in your browser's phone view (F12, device toolbar). Nothing
plays; it's the real page with a pretend board behind it.

The add-on runs inside Onion Board, which has no pip: it may only import the
standard library and PySide6 (`scripts/build_module.py` checks).

## License

Same as Onion Board: [LICENSE](LICENSE).
