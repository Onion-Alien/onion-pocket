"""The home network side (onion_pocket/lan.py): the link, the firewall rule."""
import pytest

from onion_pocket import lan


def test_the_key_is_only_in_the_fragment():
    assert lan.link("pc.example", 7475, "k3y") == "http://pc.example:7475/#k=k3y"


def test_the_firewall_rule_is_narrow_and_nothing_else_can_ride_along():
    cmd = lan.firewall_command(7475)
    assert "localport=7475" in cmd and "profile=private" in cmd
    assert "remoteip=localsubnet" in cmd and "action=allow" in cmd and "protocol=TCP" in cmd
    with pytest.raises(ValueError):
        lan.firewall_command("7475 & calc")


def test_only_a_private_ipv4_address_will_do():
    addr = lan.lan_address()
    assert addr is None or lan.usable(addr)
    assert not lan.usable("127.0.0.1") and not lan.usable("::1") and not lan.usable("x")
