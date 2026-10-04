# Security

Report a vulnerability privately to the author through GitHub (Onion Board's
*Report a security problem* link, or a private security advisory), not in a public
issue.

## What Onion Pocket does on the network

| When | Where | Why |
|---|---|---|
| You tick *Let phones on this Wi-Fi use it* (Settings → Remote; off by default) | listens on this PC's address on the local network only (port 7475 unless you change it), through Onion Board's control API server; answers only local-network addresses (private / link-local) | serves the phone page and lets a phone on your Wi-Fi list, play, stop and pause sounds, change the volume and category, and mute you. Never the mic, the voice changer or the replay |
| You click *Let it through Windows Firewall* | Windows Firewall (no network traffic) | after Windows' admin prompt, one inbound rule: that port, TCP, Private networks, local subnet only |

Nothing else. No telemetry, no internet, nothing loaded from anywhere else.

## The key

- Its own key, separate from Onion Board's *Remote control* key, made with
  `secrets.token_urlsafe(24)` and compared with `secrets.compare_digest`.
- The phone gets it in the QR code's `#fragment`: browsers never send that part to
  any server. The page keeps it in the phone's `localStorage`, takes it out of the
  address bar, and sends it as an `X-Token` header.
- Stored in Onion Board's `config.json` (`remote_addons`), never exported with a
  backup and never logged. *Forget phones* replaces it.
- An address that gets it wrong 5 times in a row is ignored for a minute.

## What someone else on your Wi-Fi can do

It's plain HTTP: on a home network, TLS would mean a certificate warning on every
phone. So someone on the same network who can read its traffic could take the key
and then play, stop or mute your sounds until you click *Forget phones*. They
can't read files, change settings, hear your mic or the call, or reach the PC from
outside your network. On shared or public Wi-Fi, leave it off.

## The page

One HTML file served by the PC. Its Content-Security-Policy allows only its own
script and style (by hash) and requests to the PC it came from
(`connect-src 'self'`). Sound names are put on the page as text, never as markup.
