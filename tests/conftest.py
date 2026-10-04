"""Test setup: Qt on the offscreen platform (no window ever appears), and the repo
on the path so `import onion_pocket` finds the package."""
import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class FakeFirewall:
    """Stands in for Windows Firewall in every test: `rules` is what lan reads
    (stored-rule strings), `asked` every command that would have run as admin, and
    `allow` whether the admin prompt is accepted. Nothing reaches the real one."""

    def __init__(self):
        self.rules: list[str] = []
        self.asked: list[str] = []
        self.allow = False

    def read(self):
        from onion_pocket import lan
        return [lan._parse(r) for r in self.rules]

    def elevate(self, params, wait_s=60.0):
        self.asked.append(params)
        return self.allow


@pytest.fixture(autouse=True)
def firewall(monkeypatch):
    from onion_pocket import lan
    fake = FakeFirewall()
    monkeypatch.setattr(lan, "_read_rules", fake.read)
    monkeypatch.setattr(lan, "_elevate", fake.elevate)
    monkeypatch.setattr(lan, "_WINDOWS", True)   # the Windows paths, on any OS
    return fake
