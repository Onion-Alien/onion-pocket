"""The add-on against a stand-in host (tests/fakehost.py): off by default, its own
key, starting only on a network, a hand-edited config, and its card on Settings."""
import pytest
from PySide6.QtWidgets import QCheckBox, QLabel, QPushButton

from fakehost import FakeHost
from onion_pocket import addon, lan, page
from onion_pocket.host import API_VERSION


@pytest.fixture
def host(qapp):
    return FakeHost()


def test_it_asks_for_a_short_list_and_serves_its_page(host):
    pocket = addon.create(host)
    srv, = host.servers
    assert srv.actions == addon.ACTIONS and srv.page == page.page()
    assert not {"mic", "voice", "replay", "help"} & set(srv.actions)   # never these
    assert set(addon.ACTIONS) <= set(host.actions)
    assert not srv.running and host.warned == [] and host.settings == {}   # off by default
    assert pocket.host is host and API_VERSION == host.api_version


def test_it_starts_only_when_on_and_on_a_network(host, monkeypatch):
    pocket = addon.create(host)
    host.settings.update(enabled=True, port=0)
    monkeypatch.setattr(lan, "lan_address", lambda: None)
    assert "network" in pocket.apply() and not pocket.server.running
    assert len(pocket.token) >= 24 and host.saves == 1        # its own key, made once
    assert pocket.apply("pc.example") == "" and pocket.server.running
    assert pocket.server.token == pocket.token and pocket.server.host == "pc.example"
    assert pocket.link() == f"http://pc.example:0/#k={pocket.token}"
    starts = pocket.server.starts
    assert pocket.apply("pc.example") == "" and pocket.server.starts == starts   # no restart
    host.settings["enabled"] = False
    pocket.apply()
    assert not pocket.server.running
    pocket.stop()


def test_a_refused_start_says_so_at_start_up(host, monkeypatch):
    host.settings.update(enabled=True, port=7475)
    monkeypatch.setattr(lan, "lan_address", lambda: None)
    addon.create(host)
    assert host.warned and "network" in host.warned[0]


def test_a_hand_edited_config_falls_back_to_safe_values(host):
    pocket = addon.create(host)
    host.settings.update(enabled="yes", port="7475; x", token=5)
    assert not pocket.enabled and pocket.port == addon.DEFAULT_PORT and pocket.token == ""
    host.settings.update(port=True)
    assert pocket.port == addon.DEFAULT_PORT


def test_its_card_pairs_with_a_code_and_forgets_phones(host, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    pocket = addon.create(host)
    card = pocket.card()
    heads = [lb.text() for lb in card.findChildren(QLabel)]
    assert "ONION POCKET: YOUR PADS ON YOUR PHONE" in heads
    code = next(lb for lb in card.findChildren(QLabel)
                if lb.accessibleName() == "QR code to pair a phone")
    box = next(b for b in card.findChildren(QCheckBox))
    assert code.pixmap().isNull() and not box.isChecked()
    box.setChecked(True)
    assert pocket.enabled and pocket.server.running and not code.pixmap().isNull()
    old = pocket.token
    next(b for b in card.findChildren(QPushButton) if b.text() == "Forget phones").click()
    assert pocket.token != old and pocket.server.token == pocket.token
    assert "✓ Forgotten" in host.flashed
    box.setChecked(False)
    assert not pocket.server.running and code.pixmap().isNull()


def test_the_card_says_why_it_could_not_start(host, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    pocket = addon.create(host)
    pocket.server.refuse = "port 7475 is already in use — pick another"
    card = pocket.card()
    next(b for b in card.findChildren(QCheckBox)).setChecked(True)
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "Couldn't start: port 7475 is already in use" in texts
