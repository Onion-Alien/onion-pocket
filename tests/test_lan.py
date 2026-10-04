"""The home network side (onion_pocket/lan.py): the link, the firewall rule. Windows
Firewall itself is the stand-in from conftest.py (`firewall`): nothing here reads or
changes the real one."""
import pytest

from onion_pocket import lan

EXE = r"C:\Program Files\Onion Board\OnionBoard.exe"   # a space in it, like the real one


def stored(name="OnionPocket", action="Allow", port="7475", app=EXE, active="TRUE",
           profiles=("Private",)):
    """A rule as Windows keeps it in the registry."""
    parts = ["v2.33", f"Action={action}", f"Active={active}", "Dir=In", "Protocol=6"]
    parts += [f"Profile={p}" for p in profiles]
    parts += [f"LPort={port}"] if port else []
    parts += [f"App={app}"] if app else []
    return "|".join(parts + [f"Name={name}", ""])


def test_the_key_is_only_in_the_fragment():
    assert lan.link("pc.example", 7475, "k3y") == "http://pc.example:7475/#k=k3y"


def test_the_firewall_rule_is_narrow_and_nothing_else_can_ride_along():
    cmd = lan.firewall_command(7475)
    assert "localport=7475" in cmd and "profile=private" in cmd
    assert "remoteip=localsubnet" in cmd and "action=allow" in cmd and "protocol=TCP" in cmd
    assert "program=" not in cmd
    with pytest.raises(ValueError):
        lan.firewall_command("7475 & calc")


def test_the_program_part_has_the_same_limits_and_a_quoted_path():
    cmd = lan.firewall_command(7475, EXE)
    delete, rest = cmd.split(" & ", 1)
    assert delete == "netsh advfirewall firewall delete rule name=OnionPocket"
    port_rule, prog_rule = rest.split(" && ")
    assert f'program="{EXE}"' in prog_rule and "program" not in port_rule
    for rule in (port_rule, prog_rule):
        assert rule.startswith("netsh advfirewall firewall add rule name=OnionPocket ")
        for limit in ("dir=in", "action=allow", "protocol=TCP", "localport=7475",
                      "profile=private", "remoteip=localsubnet"):
            assert limit in rule.split()
    assert cmd.count('"') == 2   # only the path's own quotes


@pytest.mark.parametrize("path", [
    r'C:\x" & calc & "\a.exe',      # would close the quotes
    r"C:\%COMSPEC%\a.exe",          # cmd expands %...% even in quotes
    r"C:\x!PATH!\a.exe",            # and !...! with delayed expansion on
    "C:\\x\n calc\\a.exe",
    r"relative\a.exe",
    "",
])
def test_a_path_cmd_could_act_on_is_refused(path):
    assert not lan.quotable(path)
    with pytest.raises(ValueError):
        lan.firewall_command(7475, path)


def test_allow_firewall_asks_once_for_the_port_and_this_program(firewall, monkeypatch):
    monkeypatch.setattr(lan, "this_program", lambda: EXE)
    firewall.allow = True
    assert lan.allow_firewall(7475)
    assert firewall.asked == [f"/c {lan.firewall_command(7475, EXE)}"]
    firewall.allow = False   # the admin prompt turned down
    assert not lan.allow_firewall(7475)


def test_an_odd_program_path_still_gets_the_port_rule(firewall, monkeypatch):
    monkeypatch.setattr(lan, "this_program", lambda: r"C:\100%\pythonw.exe")
    lan.allow_firewall(7475)
    assert firewall.asked == [f"/c {lan.firewall_command(7475)}"]


def test_off_windows_nothing_is_asked(firewall, monkeypatch):
    monkeypatch.setattr(lan, "_WINDOWS", False)
    assert not lan.allow_firewall(7475) and firewall.asked == []
    assert lan.rule_state(7475, EXE) == "unknown"


def test_the_rule_is_read_back_without_admin(firewall):
    assert lan.rule_state(7475, EXE) == "missing"
    firewall.rules = [stored(app=""), stored()]          # what firewall_command adds
    assert lan.rule_state(7475, EXE) == "ok"
    assert lan.rule_state(7475, EXE.upper()) == "ok"     # paths ignore case on Windows
    assert lan.rule_state(8000, EXE) == "stale"          # the port changed
    assert lan.rule_state(7475, r"D:\Other\OnionBoard.exe") == "stale"   # app moved
    firewall.rules = [stored(app="")]                    # port only, as before
    assert lan.rule_state(7475, EXE) == "stale"
    firewall.rules = [stored(active="FALSE")]
    assert lan.rule_state(7475, EXE) == "stale"
    firewall.rules = [stored(name="Something else")]
    assert lan.rule_state(7475, EXE) == "missing"


def test_a_block_rule_for_the_program_wins(firewall):
    # what Cancel on Windows' own prompt leaves behind
    block = stored(name="onionboard.exe", action="Block", port="", profiles=("Private",))
    firewall.rules = [stored(), block]
    assert lan.rule_state(7475, EXE) == "blocked"
    firewall.rules = [stored(), stored(name="x", action="Block", port="", profiles=())]
    assert lan.rule_state(7475, EXE) == "blocked"        # no profile: all of them
    firewall.rules = [stored(), stored(name="x", action="Block", profiles=("Public",))]
    assert lan.rule_state(7475, EXE) == "ok"             # Public only: not ours to fix


def test_unreadable_rules_are_unknown(firewall, monkeypatch):
    def fail():
        raise OSError("access denied")
    monkeypatch.setattr(lan, "_read_rules", fail)
    assert lan.rule_state(7475, EXE) == "unknown"


def test_only_a_private_ipv4_address_will_do():
    addr = lan.lan_address()
    assert addr is None or lan.usable(addr)
    assert not lan.usable("127.0.0.1") and not lan.usable("::1") and not lan.usable("x")
