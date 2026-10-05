"""No piece of the Remote card is shown while it has no parent: on Windows each one
flashed up on the desktop as a little blank window of its own for a moment."""
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QPushButton, QWidget

from fakehost import FakeHost

from onion_pocket import addon, lan


def test_the_firewall_button_shows_inside_the_card(monkeypatch, qapp):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    monkeypatch.setattr(addon.sys, "platform", "win32")   # the button is Windows-only
    stray = []

    class Spy(QObject):
        def eventFilter(self, obj, ev):
            if (ev.type() in (QEvent.Show, QEvent.WinIdChange) and isinstance(obj, QWidget)
                    and obj.isWindow() and obj.parent() is None):
                stray.append(type(obj).__name__)
            return False

    spy = Spy()
    qapp.installEventFilter(spy)
    try:
        card = addon.create(FakeHost()).card()
        qapp.processEvents()
    finally:
        qapp.removeEventFilter(spy)
    assert stray == []
    assert any(b.text().startswith("Let it through") for b in card.findChildren(QPushButton))
