# Onion Board on phones: what's possible

Research notes, checked 2026-10. Nothing here is built yet. Claims we couldn't
confirm from an official page are marked *unverified*.

## Summary

- **Phone as a remote for the PC app: possible.** A page served by the PC over the
  home Wi-Fi works, using the control API we already have (`soundboard/remote.py`).
- **A standalone phone soundboard that other apps hear: impossible** on stock Android
  and iOS. There's no API that lets one app feed another app's mic.

## Status

**Built: Onion Pocket, an Onion Board add-on (this repo).** It lives entirely on
Settings → Remote: *Let phones on this Wi-Fi use it*, the QR code, *Copy the link*,
*Forget phones*, *Let it through Windows Firewall*, the port. The phone page has pads
by category, *Stop all*, *Live / Muted* and the volume, and (0.2.0, with Onion
Board 1.7.2+) a Radio tab and a Sound tab for the live speed, pitch, effects and
who's listening. It follows the design below:
its own key, local-network peers only, wrong-key lock-out, a short action list, a
hash-only CSP.

Tested: this repo's tests (a stand-in host), Onion Board's tests with
its side merged, the built zip installed into Onion Board and its card rendered,
the page driven in headless Chromium at phone size against a real server, and a real
QR decoder reading the codes back.

**How it's split**, like Onion Watch:

| Where | What |
|---|---|
| this repo, `onion_pocket/` | the add-on: its card, the phone page, QR codes, this PC's LAN address, the firewall rule. `host.py` is the whole contract with Onion Board |
| this repo, `scripts/build_module.py` | `dist/OnionPocket-module.zip`, which Onion Board installs into `%APPDATA%\OnionBoard\modules\onion-pocket` |
| Onion Board (newer than 1.6.8) | the "remote" add-on kind, the host (`soundboard/ui/remotehost.py`), the lan options of the control API server, its card on Settings → Remote |

**Not done yet:**
- Tried on a real phone and a real Windows PC (firewall prompt, Private / Public
  network, iPhone Safari and Android Chrome).
- Getting it to users: Onion Board installs Onion Watch from its public GitHub
  release; this repo is private, so for now the zip is installed by hand (README).
- Telling the user when Windows calls the network *Public* (the firewall rule only
  covers Private).
- Following the PC's address when it changes while the app runs (a router restart):
  until then, untick and tick the box, or restart the app.
- Pad pictures on the phone (needs an endpoint that reads the pictures' files, so
  the author's say-so first; the pads show their colour and name until then), and
  an iPhone home-screen icon (iOS doesn't take an SVG one; the tab icon is SVG).
- Removing it from Settings → Add-ons (that card only knows Onion Watch today).
- The Linux port.

## Routes

**Works?** ✅ works · 🟡 partly / with caveats · ❌ no.
**Effort** is for our side only: S = days, M = a week or two, L = more.

| Platform | Route | Works? | What the user does | What we'd build | Effort |
|---|---|---|---|---|---|
| Android, iOS | **Phone remote**: a web page served by the PC app over Wi-Fi | ✅ | Settings → Remote → *Phones on this Wi-Fi* → scan the QR code | Design below | M |
| Android, iOS | Native remote app | ✅ but not worth it | Install from a store | Store accounts, and Android 17's local-network permission. The web page does the same job | L |
| Android | Standalone soundboard heard in Discord or a game **on the phone** | ❌ | — | — | — |
| iOS | The same | ❌ | — | — | — |
| Android, iOS | Discord's own soundboard in a mobile call | ✅ (Discord feature) | Use the call's soundboard tray | Nothing | — |
| Android | Phone mic → PC as an input (like WO Mic) | ✅ | — | Possible, but nobody has asked for it | L |

### Why a standalone phone soundboard can't work

- **Android:** an app can't write into another app's microphone. When two apps
  capture at once, a voice call always gets the real mic. Playback capture
  (MediaProjection) only *copies* other apps' output. `REMOTE_SUBMIX` needs
  `CAPTURE_AUDIO_OUTPUT`, which is "not for use by third-party applications". A
  virtual mic needs root or a custom ROM. Playing through the speaker so the mic picks
  it up is what existing apps do, and the call's echo cancellation tends to remove it.
  ([sharing audio input](https://developer.android.com/media/platform/sharing-audio-input),
  [playback capture](https://developer.android.com/media/platform/av-capture),
  [CAPTURE_AUDIO_OUTPUT](https://developer.android.com/reference/android/Manifest.permission#CAPTURE_AUDIO_OUTPUT))
- **iOS:** virtual audio devices (Audio Server Plug-ins) exist on macOS only.
  Inter-App Audio has been deprecated since iOS 13. An AUv3 effect runs only inside
  its host app. An app can play *alongside* a call (`.mixWithOthers`), but the call
  only hears it through the air.
  ([audio server plug-ins](https://developer.apple.com/documentation/coreaudio/building-an-audio-server-plug-in-and-driver-extension),
  [Inter-App Audio deprecation](https://developer.apple.com/documentation/audiotoolbox/audiooutputunitpublish(_:_:_:_:)),
  [mixWithOthers](https://developer.apple.com/documentation/avfaudio/avaudiosession/categoryoptions-swift.struct/mixwithothers))
- What people can already do on a phone is Discord's own soundboard in a call
  ([Discord](https://discord.com/blog/how-to-use-the-discord-soundboard-add-more-sounds)).
  We have nothing to add there.

### Phone remote: minimal design

The phone shows a pad grid. Pressing a pad calls the existing control API, and the
sound plays on the PC as if the pad had been clicked.

1. **Opt-in, off by default.** A new box: Settings → Remote → *Let phones on this
   Wi-Fi use it*. The loopback API for Stream Deck and scripts stays exactly as it is.
2. **A second listener** bound to the PC's LAN address only, not all interfaces, on
   its own port. It is started only while the box is ticked.
3. **Its own token**, separate from the Stream Deck one, so leaking one doesn't
   leak the other. *Forget phones* replaces it. It's compared with
   `secrets.compare_digest` and never logged.
4. **Pairing by QR code.** The code holds `http://<this PC>:<port>/m#k=<token>`. The
   token sits in the URL **fragment**, so the browser never sends it in a request line
   or a log. The page reads it, keeps it in `localStorage` and sends it as `X-Token`.
5. **Host check** as today, but for the bound LAN address. Requests for any other
   `Host` are refused, so DNS rebinding still fails. No CORS headers.
6. **A smaller set of endpoints:** status, sounds, categories, play, stop, pause,
   random, last, category, volume, live; since 0.2.0 also speed, pitch, effects,
   reset, mode and the radio's. Mic, voice and replay stay loopback-only
   until we decide otherwise. A pad-picture endpoint can come later.
7. **The page ships with the app.** It's a single HTML file with inline JS, no CDN,
   and sent with a hash-only `Content-Security-Policy` (`default-src 'none'`). Its
   logo is Onion Board's mark as inline SVG and everything else is CSS, so there are
   no third-party assets. `scripts/demo_page.py` serves it with made-up sounds for
   working on its look.
8. **Plain HTTP, no TLS, in v1.** On a LAN, TLS means a self-signed warning on every
   phone, or a custom CA, which iOS makes you install as a profile and then fully
   trust by hand ([Apple](https://support.apple.com/en-us/102390)). The comparable
   tools mostly don't use TLS either: Companion has it as an option, and OBS
   WebSocket and Home Assistant are off by default. Without HTTPS the page isn't a
   secure context, so it gets no service worker, no install prompt and no wake lock
   ([MDN](https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts)). A
   button grid doesn't need them. iOS 26 Safari can add any site to the Home Screen
   as a web app ([WebKit](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/)).
   Doing the same over HTTP on Android Chrome is *unverified*.
9. **Firewall (Windows).** When the box is ticked, add one inbound rule for
   `OnionBoard.exe`: Private profile only, remote address *Local subnet*. (Done:
   a port part and a program part, `sys.executable`; a port-only rule doesn't stop
   Windows' first-listen pop-up, which names the program by its version info.) This needs
   elevation: a UAC prompt, or the installer. Without a rule, Windows' first-listen
   prompt gives a non-admin user block rules whatever they click
   ([Microsoft](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/rules)).
   If the network is set to *Public*, say so instead of opening it. On Linux the port
   only needs a note about ufw / firewalld.
10. **Failed tokens.** After a few 401s from one address, ignore it for a minute. The
    token is 192 bits, so this cuts log noise, not real guessing risk.
11. **A `SECURITY.md` row:** "You turn on *Phones on this Wi-Fi* (off by default) |
    listens on this PC's LAN address, port N | lets a phone on the same network play /
    stop sounds; needs the phone key from the QR code; plain HTTP, local subnet only |
    — (this network)".

**Threats, honestly.** Someone else on the same Wi-Fi can read the token off plain
HTTP and then play, stop or mute your sounds until you press *Forget phones*. They
**can't** read files, change settings, hear your mic or the call, or reach the PC
from outside the LAN. On shared or public Wi-Fi, leave the remote off. The app
should say this next to the box.

**Platform notes.** iOS Safari doesn't need the Local Network permission
([TN3179](https://developer.apple.com/documentation/technotes/tn3179-understanding-local-network-privacy)).
Android 17 adds `ACCESS_LOCAL_NETWORK` for apps that target API 37. Once Chrome
targets it, Chrome itself may ask the user once (*unverified*)
([Android](https://developer.android.com/privacy-and-security/local-network-permission)).
Chrome's Local Network Access prompts don't affect a page that the PC serves from
its own address. They would if the page were hosted on a public site, so don't host
it on one ([Chrome](https://developer.chrome.com/blog/local-network-access)).

**Comparable tools:**

| Tool | Pairing | Auth | TLS |
|---|---|---|---|
| Stream Deck Mobile | QR code from the desktop app | paired device | unknown |
| Bitfocus Companion | browse to the PC's address | optional admin password | optional, self-signed or your own certificate |
| OBS WebSocket 5 | type in the address | optional password, challenge-response | none |
| Home Assistant | URL or companion app | login, long-lived tokens | off by default |
| Deckboard | IP or QR code | unknown | unknown |

## Recommendation

Build the phone remote (M) as designed above. It reuses `remote.py`'s dispatch and
only adds a listener, a token, a page and a QR code. A native app and a phone-mic
input can wait until someone asks for them.

## Open questions

- Phone remote: should *mic* / *voice* / *Live* be allowed from the phone? Is a UAC
  prompt acceptable for the firewall rule, or should the installer always add it
  (dormant until the box is ticked)?
- Does the Linux port ship `remote.py` as is? If so, the same design applies there,
  without the firewall step.
