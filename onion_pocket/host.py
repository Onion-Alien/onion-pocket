"""What Onion Board looks like from Onion Pocket's side: the host a "remote" add-on
is created with (Onion Board's soundboard/ui/remotehost.py). Onion Pocket uses
nothing else of the app, so this is the whole contract; tests/fakehost.py stands in
for it in the tests.

API_VERSION is the host interface this add-on is written for. Onion Board loads a
"remote" add-on only when its api_version is one it can host (modules.REMOTE_API).
"""
from __future__ import annotations

from typing import Protocol

API_VERSION = 1


class Server(Protocol):
    """A control API server for the home network (Onion Board's RemoteControl with
    lan=True): local-network peers only, wrong keys locked out."""
    host: str
    port: int
    token: str
    error: str

    @property
    def running(self) -> bool: ...
    def start(self, port: int, token: str, host: str) -> bool: ...
    def stop(self) -> None: ...


class Host(Protocol):
    api_version: int
    name: str
    actions: tuple[str, ...]          # every control API action the board has

    @property
    def settings(self) -> dict: ...   # this add-on's own, on this PC only
    def save(self) -> None: ...
    def server(self, actions, page=None, name: str = "") -> Server: ...
    def new_token(self) -> str: ...
    def warn(self, text: str) -> None: ...
    # Settings' look, so the card matches the rest of Settings
    def card(self, title: str, hint: str = ""): ...      # -> (QFrame, QVBoxLayout)
    def button_row(self): ...
    def flash(self, button, text: str) -> None: ...
    def icon(self, button, name: str) -> None: ...
    def no_wheel(self, widget) -> None: ...
    # Optional, newer Onion Boards only (check with getattr): Windows Firewall rule
    # `name` for `port` and the app, after an admin prompt that names Onion Board
    # def allow_firewall(self, name: str, port: int) -> bool: ...
