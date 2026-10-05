"""The add-on against a stand-in host (tests/fakehost.py): off by default, its own
key, starting only on a network, a hand-edited config, and its card on Settings."""
import sys
import threading

import pytest
import shiboken6
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QPushButton, QSpinBox

from fakehost import FakeHost
from onion_pocket import addon, lan, page
from onion_pocket.host import API_VERSION


@pytest.fixture
def host(qapp):
    return FakeHost()


def answered(pocket):
    """Wait for Windows' admin prompt (asked on a thread) to be answered and handled."""
    t = pocket.asking
    if t is not None:
        t.join(5)
        assert not t.is_alive(), "the firewall prompt never finished"
    QApplication.processEvents()
    assert pocket.asking is None


def test_it_asks_for_a_short_list_and_serves_its_page(host):
    pocket = addon.create(host)
    srv, = host.servers
    assert srv.actions == addon.ACTIONS and srv.page == page.page()
    assert not {"mic", "voice", "replay", "help"} & set(srv.actions)   # never these
    assert set(addon.ACTIONS) <= set(host.actions)
    assert not srv.running and host.warned == [] and host.settings == {}   # off by default
    assert pocket.host is host and API_VERSION == host.api_version


def test_an_older_board_gets_only_the_actions_it_has(host):
    """Onion Board 1.7.1 has no speed, radio…: the add-on still loads, with the pads."""
    from fakehost import OLD_ACTIONS
    host.actions = OLD_ACTIONS
    addon.create(host)
    srv, = host.servers
    assert srv.actions == tuple(a for a in addon.ACTIONS if a in OLD_ACTIONS)
    assert "play" in srv.actions and "radio" not in srv.actions and "speed" not in srv.actions


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
    answered(pocket)
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
    answered(pocket)
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "Couldn't start: port 7475 is already in use" in texts


def ok_rule(port=7475):
    from test_lan import stored
    return [stored(app="", port=str(port)), stored(port=str(port), app=lan.this_program())]


def test_nothing_asks_windows_without_a_click(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    host.settings.update(enabled=True, port=7475)
    pocket = addon.create(host)         # on at start-up, no rule: no prompt
    pocket.card()
    pocket.apply()
    assert pocket.server.running and firewall.asked == []


def test_ticking_it_on_asks_windows_once_before_listening(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    pocket = addon.create(host)
    card = pocket.card()
    said = []
    running_when_asked = []

    def elevate(params, wait_s=60.0):
        said.append(" ".join(lb.text() for lb in card.findChildren(QLabel)))
        running_when_asked.append(pocket.server.running)
        firewall.rules = ok_rule()
        return True
    monkeypatch.setattr(lan, "_elevate", elevate)
    card.pocket_on.setChecked(True)
    answered(pocket)
    assert len(said) == 1 and running_when_asked == [False]
    assert "Windows will ask once so phones can reach Onion Board" in said[0]
    assert pocket.server.running and "✓ Allowed" in host.flashed
    card.pocket_on.setChecked(False)
    card.pocket_on.setChecked(True)     # the rule is there now: no second prompt
    answered(pocket)
    assert len(said) == 1


def test_saying_no_keeps_it_on_with_the_hint(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)     # firewall.allow is False: the prompt turned down
    answered(pocket)
    assert len(firewall.asked) == 1 and pocket.server.running
    assert "Not changed" in host.flashed
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "On. Scan the code" in texts and "Phone can't connect?" in texts


def test_off_windows_there_is_no_firewall_to_ask(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    monkeypatch.setattr(sys, "platform", "linux")
    asked = []
    host.allow_firewall = lambda name, port: asked.append((name, port)) or False
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)     # lan still thinks it's Windows: the card mustn't ask
    assert asked == [] and firewall.asked == [] and pocket.server.running
    assert "Not changed" not in host.flashed
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "On. Scan the code" in texts and "Phone can't connect?" in texts
    assert "Windows" not in texts
    assert not any(b.isVisibleTo(card) for b in card.findChildren(QPushButton)
                   if "Firewall" in b.text())


def test_a_rule_for_the_old_port_or_copy_is_updated(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    host.settings.update(enabled=True, port=7475)
    firewall.rules = ok_rule(7475)
    pocket = addon.create(host)
    card = pocket.card()
    spin = next(s for s in card.findChildren(QSpinBox))
    spin.setValue(7476)
    spin.editingFinished.emit()
    answered(pocket)
    assert firewall.asked == [f"/c {lan.firewall_command(7476, lan.this_program())}"]
    firewall.rules = ok_rule(7476)
    card.pocket_on.setChecked(False)
    monkeypatch.setattr(lan, "this_program", lambda: r"C:\Somewhere else\OnionBoard.exe")
    card.pocket_on.setChecked(True)     # the app moved: the rule is moved with it
    answered(pocket)
    assert len(firewall.asked) == 2 and r'program="C:\Somewhere else' in firewall.asked[1]


def test_the_button_asks_too_and_a_block_is_explained(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    host.settings.update(enabled=True, port=7475)
    pocket = addon.create(host)
    card = pocket.card()
    next(b for b in card.findChildren(QPushButton)
         if b.text().startswith("Let it through")).click()
    answered(pocket)
    assert len(firewall.asked) == 1
    from test_lan import stored
    firewall.rules = ok_rule() + [stored(name="x", action="Block", port="",
                                         app=lan.this_program())]
    card.pocket_on.setChecked(False)
    card.pocket_on.setChecked(True)     # blocked: asking again can't help
    assert len(firewall.asked) == 1
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "Windows Firewall is blocking this app" in texts and "Python" not in texts


def test_a_newer_onion_board_adds_the_rule_itself_so_its_prompt_names_it(host, firewall,
                                                                          monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    asked = []
    host.allow_firewall = lambda name, port: asked.append((name, port)) or True
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)
    answered(pocket)
    assert asked == [(lan.FIREWALL_RULE, 7475)] and firewall.asked == []   # no cmd.exe
    assert "✓ Allowed" in host.flashed


def test_onion_board_failing_to_add_the_rule_is_just_not_changed(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")

    def boom(name, port):
        raise OSError("no")
    host.allow_firewall = boom
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)
    answered(pocket)
    assert "Not changed" in host.flashed and firewall.asked == []


def test_onion_board_keeps_running_while_windows_asks(host, firewall, monkeypatch):
    """The prompt is waited for on a thread: on the UI thread, Onion Board froze until
    it was answered."""
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    up, answer = threading.Event(), threading.Event()

    def elevate(params, wait_s=60.0):
        up.set()
        answer.wait(5)
        firewall.rules = ok_rule()
        return True
    monkeypatch.setattr(lan, "_elevate", elevate)
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)     # returns at once, with the prompt still up
    assert up.wait(5) and pocket.asking is not None and not pocket.server.running
    texts = " ".join(lb.text() for lb in card.findChildren(QLabel))
    assert "answer its prompt" in texts and "Couldn't start" not in texts
    next(b for b in card.findChildren(QPushButton)
         if b.text().startswith("Let it through")).click()   # no second prompt meanwhile
    again = pocket.card()                # Settings reopened while it's up
    texts = " ".join(lb.text() for lb in again.findChildren(QLabel))
    assert "answer its prompt" in texts and "Couldn't start" not in texts
    answer.set()
    answered(pocket)
    assert pocket.server.running and host.flashed.count("✓ Allowed") == 1


def test_settings_closed_before_the_answer_still_starts_it(host, firewall, monkeypatch):
    monkeypatch.setattr(lan, "lan_address", lambda: "pc.example")
    answer = threading.Event()

    def elevate(params, wait_s=60.0):
        answer.wait(5)
        return True
    monkeypatch.setattr(lan, "_elevate", elevate)
    monkeypatch.setattr(host, "flash", lambda button, text: button.objectName())
    pocket = addon.create(host)
    card = pocket.card()
    card.pocket_on.setChecked(True)
    card.deleteLater()                  # Settings closed
    QApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert not shiboken6.isValid(card)
    answer.set()
    answered(pocket)
    assert pocket.server.running
