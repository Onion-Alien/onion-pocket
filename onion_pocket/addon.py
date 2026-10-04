"""Onion Pocket: your pads on your phone, over the home Wi-Fi. An Onion Board
add-on of kind "remote": it talks to the board only through the host it's created
with (host.py describes it; Onion Board's soundboard/ui/remotehost.py is the real
one), and lives entirely in its card on Settings → Remote.

Off unless *Let phones on this Wi-Fi use it* is ticked. Then a control API server
(host.server: local-network peers only, wrong keys locked out) listens on this PC's
address on the home network and serves the phone page (page.py) at /. The phone
pairs by scanning a QR code (qr.py) of the link in lan.py.

Its settings (host.settings): `enabled`, `port`, and `token`, its own key, never the
Stream Deck one. The key is compared with secrets.compare_digest by the server and
never logged; *Forget phones* makes a new one. Plain HTTP: on a home network TLS
would mean a certificate warning on every phone. Someone on the same Wi-Fi who can
read that traffic could take the key and play or stop your sounds, so the card says
to use it at home, not on public Wi-Fi. The phone gets ACTIONS only: never the mic,
the voice changer or saving the replay.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QHBoxLayout, QLabel, QPushButton,
                               QSpinBox, QVBoxLayout)

from . import lan, page, qr

log = logging.getLogger(__name__)

DEFAULT_PORT = 7475
ACTIONS = ("status", "sounds", "categories", "play", "stop", "pause", "random", "last",
           "category", "volume", "live")
QR_PX = 200   # the pairing code's size on screen


def create(host):
    return Pocket(host)


def qr_pixmap(text: str, px: int = QR_PX) -> QPixmap:
    """`text` as a QR code, black on white with the quiet zone the spec asks for,
    whatever the theme: phone cameras want that contrast."""
    m = qr.encode(text)
    n = len(m) + 8                                  # four light modules each side
    scale = max(1, px // n)
    pm = QPixmap(px, px)
    pm.fill(QColor("#ffffff"))
    p = QPainter(pm)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#000000"))
    off = (px - scale * n) // 2 + 4 * scale
    for y, row in enumerate(m):
        for x, dark in enumerate(row):
            if dark:
                p.drawRect(off + x * scale, off + y * scale, scale, scale)
    p.end()
    return pm


class Pocket:
    def __init__(self, host):
        self.host = host
        self.server = host.server(ACTIONS, page.page(), "Onion Pocket")
        err = self.apply()
        if err:
            host.warn(f"Onion Pocket is off: {err}.")

    # ------------------------------------------------------------------ settings
    @property
    def enabled(self) -> bool:
        return self.host.settings.get("enabled") is True

    @property
    def port(self) -> int:
        p = self.host.settings.get("port", DEFAULT_PORT)
        return p if isinstance(p, int) and not isinstance(p, bool) and 0 <= p <= 65535 \
            else DEFAULT_PORT

    @property
    def token(self) -> str:
        t = self.host.settings.get("token")
        return t if isinstance(t, str) else ""

    def _set(self, **values):
        self.host.settings.update(values)
        self.host.save()

    # ------------------------------------------------------------------ the server
    def apply(self, address: str | None = None) -> str:
        """Start or stop the server to match the settings. Returns an error ("" if
        fine). `address` is for the tests; otherwise this PC's on the network."""
        srv = self.server
        if not self.enabled:
            srv.stop()
            return ""
        if not self.token:
            self._set(token=self.host.new_token())
        address = address or lan.lan_address()
        if address is None:
            srv.stop()
            srv.error = "this PC isn't on a network: connect it to your Wi-Fi or router"
            return srv.error
        if (srv.running and srv.host == address and srv.port == self.port
                and srv.token == self.token):
            return ""
        srv.start(self.port, self.token, address)
        return srv.error

    def link(self) -> str:
        return lan.link(self.server.host, self.server.port, self.token)

    def stop(self):
        self.server.stop()

    # ------------------------------------------------------------------ the card
    def card(self, parent=None):
        """Onion Pocket's card on Settings → Remote: on / off, the QR code to pair a
        phone, a new key, the firewall rule, the port."""
        h = self.host
        card, cv = h.card(
            "Onion Pocket: your pads on your phone",
            "Scan the code with your phone's camera, and a tap on a pad plays it here. "
            "iPhone or Android, in the browser: nothing to install. Use it on your home "
            "Wi-Fi, not on public Wi-Fi: anyone on the same network who gets the link "
            "can play and stop your sounds (never your mic).")
        on = QCheckBox("Let phones on this Wi-Fi use it")
        on.setChecked(self.enabled)
        cv.addWidget(on)
        row = QHBoxLayout()
        row.setSpacing(14)
        code = QLabel()
        code.setAccessibleName("QR code to pair a phone")
        code.setFixedSize(QR_PX, QR_PX)
        code.setAlignment(Qt.AlignCenter)
        row.addWidget(code, 0, Qt.AlignTop)
        side = QVBoxLayout()
        state = QLabel()
        state.setWordWrap(True)
        state.setTextInteractionFlags(Qt.TextSelectableByMouse)
        side.addWidget(state)
        btns = h.button_row()
        copy = QPushButton("Copy the link")
        h.icon(copy, "copy")
        copy.setToolTip("The same link as the code, with the key in it: send it only to "
                        "your own phone")
        btns.addWidget(copy)
        forget = QPushButton("Forget phones")
        forget.setToolTip("Make a new key: every paired phone has to scan the new code")
        btns.addWidget(forget)
        side.addLayout(btns)
        fw = QPushButton("Let it through Windows Firewall…")
        fw.setToolTip("Windows asks for permission once. The rule only lets in phones on "
                      "this network, only on a network Windows calls Private, and stops "
                      "Windows' own pop-up about this app")
        side.addWidget(fw)
        prow = QHBoxLayout()
        prow.addWidget(QLabel("Port"))
        port = QSpinBox()
        port.setRange(1024, 65535)
        port.setValue(self.port)
        port.setAccessibleName("Onion Pocket port")
        h.no_wheel(port)
        prow.addWidget(port)
        prow.addStretch(1)
        side.addLayout(prow)
        hint = QLabel("Phone can't connect? Click <b>Let it through Windows Firewall</b>, "
                      "and in Windows Settings → Network &amp; internet → Wi-Fi, set this "
                      "network to <b>Private</b>.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        side.addWidget(hint)
        side.addStretch(1)
        row.addLayout(side, 1)
        cv.addLayout(row)

        def refresh(err: str = ""):
            for w in (copy, forget, fw, port):
                w.setEnabled(self.enabled)
            live = self.enabled and not err and self.server.running
            code.setPixmap(qr_pixmap(self.link()) if live else QPixmap())
            code.setText("" if live else "Off")
            if not self.enabled:
                state.setText("Off: phones can't reach Onion Board.")
            elif not live:
                state.setText(f"Couldn't start: {err or self.server.error}")
            else:
                text = ("On. Scan the code with your phone's camera and open the link. "
                        "The phone must be on the same Wi-Fi as this PC.")
                if lan.rule_state(self.port) == "blocked":
                    text += (" Windows Firewall is blocking this app (its prompt was "
                             "cancelled once): in Windows Security → Firewall & "
                             "network protection → Allow an app through firewall, tick "
                             "Private next to it.")
                state.setText(text)

        def ask_firewall():
            """The rule, after one line saying why Windows is about to ask."""
            state.setText("Windows will ask once so phones can reach Onion Board.")
            state.repaint()   # before Windows' prompt takes the screen
            ok = lan.allow_firewall(self.port, host=h)
            h.flash(fw, "✓ Allowed" if ok else "Not changed")

        def set_on(b: bool):
            self._set(enabled=b)
            # before the server listens on the network: with our rule in place first,
            # Windows has nothing to pop up about
            if b and lan.rule_state(self.port) in ("missing", "stale"):
                ask_firewall()
            refresh(self.apply())

        def set_port():
            if port.value() != self.port:
                self._set(port=port.value())
                if self.enabled and lan.rule_state(self.port) == "stale":
                    ask_firewall()   # the rule was for the old port: move it
                refresh(self.apply())

        def new_key():
            self._set(token=h.new_token())
            refresh(self.apply())
            h.flash(forget, "✓ Forgotten")

        def copy_link():
            QApplication.clipboard().setText(self.link())
            h.flash(copy, "✓ Copied")

        def firewall():
            ask_firewall()
            refresh(self.apply())

        on.toggled.connect(set_on)
        port.editingFinished.connect(set_port)
        forget.clicked.connect(new_key)
        copy.clicked.connect(copy_link)
        fw.clicked.connect(firewall)
        refresh()
        card.pocket_on = on   # for the tests
        return card
