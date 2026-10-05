"""A host that is nothing but onion_pocket.host.Host: what Onion Board looks like
from the add-on's side. Settings live in memory, and the server only records what
it's asked to do; Onion Board's own tests cover the real server (its page, keys,
lock-out and local peers)."""
from __future__ import annotations

import secrets

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from onion_pocket.host import API_VERSION

ACTIONS = ("status", "sounds", "categories", "play", "stop", "pause", "random", "last",
           "category", "volume", "live", "voice", "mic", "replay", "speed", "pitch",
           "effects", "reset", "mode", "stations", "radio", "radio_random", "radio_star",
           "radio_live", "radio_hear", "radio_volume", "help")
OLD_ACTIONS = ACTIONS[:ACTIONS.index("replay") + 1] + ("help",)   # Onion Board 1.7.1


class FakeServer:
    def __init__(self, actions, page, name):
        self.actions, self.page, self.name = tuple(actions), page, name
        self.host, self.port, self.token, self.error = "127.0.0.1", 0, "", ""
        self.running = False
        self.starts = 0
        self.refuse = ""                       # start() fails with this error

    def start(self, port, token, host):
        self.port, self.token, self.host = port, token, host
        self.starts += 1
        self.error, self.running = self.refuse, not self.refuse
        return self.running

    def stop(self):
        self.running = False


class FakeHost:
    api_version = API_VERSION
    name = "Test Board"
    actions = ACTIONS

    def __init__(self):
        self.settings: dict = {}
        self.saves = 0
        self.warned: list[str] = []
        self.flashed: list[str] = []
        self.servers: list[FakeServer] = []

    def save(self):
        self.saves += 1

    def server(self, actions, page=None, name=""):
        unknown = set(actions) - set(self.actions)
        if unknown:
            raise ValueError(f"no such actions: {sorted(unknown)}")
        s = FakeServer(actions, page, name)
        self.servers.append(s)
        return s

    @staticmethod
    def new_token():
        return secrets.token_urlsafe(24)

    def warn(self, text):
        self.warned.append(text)

    @staticmethod
    def card(title, hint=""):
        card = QFrame()
        v = QVBoxLayout(card)
        t = QLabel(title.upper())
        t.setObjectName("section")
        v.addWidget(t)
        if hint:
            v.addWidget(QLabel(hint))
        return card, v

    @staticmethod
    def button_row():
        return QHBoxLayout()

    def flash(self, button, text):
        self.flashed.append(text)

    def icon(self, button, name):
        pass

    def no_wheel(self, widget):
        pass
