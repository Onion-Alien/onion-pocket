# Security

Report a vulnerability privately to the author through GitHub (Onion Board's
*Report a security problem* link, or a private security advisory), not in a public
issue.

## What Onion Pocket does on the network

| When | Where | Why |
|---|---|---|
| You tick *Let phones on this Wi-Fi use it* (Settings → Remote; off by default) | listens on this PC's address on the local network only (port 7475 unless you change it), through Onion Board's control API server; answers only local-network addresses (private / link-local) | serves the phone page and lets a phone on your Wi-Fi list, play, stop and pause sounds, change the volume and category, mute you, run the radio (Onion Board then fetches the stations it asks for or searches, from its usual station directory) and change the live speed, pitch, effects and who's listening. Never the mic, the voice changer, the replay or files |
| You tick the box and Windows Firewall has no rule for it yet, or you click *Let it through Windows Firewall* | Windows Firewall (no network traffic) | after a line on the card and Windows' admin prompt, one inbound rule named `OnionPocket` in two parts with the same limits (that port, TCP, Private networks, local subnet only): one for the port, one for the app itself (`OnionBoard.exe`, or `pythonw.exe` when run from source). The app part is what stops Windows' own "has blocked some features" pop-up. Say no and nothing changes. Moving the port or the app replaces the rule (one more prompt). To check whether the rule is there, the add-on reads Windows' list of firewall rules from the registry, which needs no admin rights and changes nothing |

Nothing else. No telemetry, no internet, nothing loaded from anywhere else.

## The key

- Its own key, separate from Onion Board's *Remote control* key, made with
  `secrets.token_urlsafe(24)` and compared with `secrets.compare_digest`.
- The phone gets it in the QR code's `#fragment`: browsers never send that part to
  any server. The page keeps it in the phone's `localStorage`, takes it out of the
  address bar. With Onion Board 1.9.4 or newer the key itself never goes over the
  Wi-Fi again: each request carries `X-Sig`, an HMAC-SHA256 made with the key over
  the time, a one-time random nonce and the request itself. Onion Board takes each
  signature once, only for that request, and only within 5 minutes of its own clock
  (a phone whose clock is off is told the PC's time and signs again). Older Onion
  Boards get the key as an `X-Token` header, as before.
- Stored in Onion Board's `config.json` (`remote_addons`), never exported with a
  backup and never logged. *Forget phones* replaces it.
- An address that gets it wrong 5 times in a row is ignored for a minute.

## What someone else on your Wi-Fi can do

It's plain HTTP: on a home network, TLS would mean a certificate warning on every
phone. With Onion Board 1.9.4 or newer, someone who can read the Wi-Fi's traffic
sees only one-time signatures, never the key, and can't send them again. Someone
who can go further and change that traffic on its way (pretend to be the PC) could
still hand the phone a page of their own and take the key; with an older Onion
Board, just reading the traffic is enough. With the key they could play, stop or
mute your sounds, run the radio or change the live effects until you click *Forget
phones*. They can't read files, hear your mic or the call, change Onion Board's
other settings, or reach the PC from outside your network. Onion Board 1.9.4 and
newer also don't listen at all on a network Windows calls Public. On shared or
public Wi-Fi, leave it off.

## The page

One HTML file served by the PC. Its Content-Security-Policy allows only its own
script and style (by hash), requests to the PC it came from (`connect-src 'self'`)
and `data:` images, which is only its own tab icon (the logo, drawn in SVG). Nothing
loads from anywhere else: no CDN, no web fonts, no pictures from the PC. Sound names
are put on the page as text, never as markup.
