"""The home network side of Onion Pocket: this PC's address on it, the pairing link,
and the Windows Firewall rule.

The phone pairs by scanning a QR code of

    http://<this PC>:<port>/#k=<key>

The key lives in the #fragment, so the browser never sends it in a request line.

Windows Firewall blocks incoming connections it hasn't been told about.
`allow_firewall()` adds one rule, after Windows' admin prompt: this port, TCP,
Private networks only, from the local subnet only.
"""
from __future__ import annotations

import ipaddress
import logging
import socket
import sys

log = logging.getLogger(__name__)

FIREWALL_RULE = "OnionPocket"
# an address that's never on a real network (RFC 5737): "connecting" a UDP socket to it
# sends nothing, but makes the OS pick the interface its default route goes out of
_ROUTE_PROBE = "192.0.2.1"


def usable(addr: str) -> bool:
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        return False
    return ip.version == 4 and ip.is_private and not (ip.is_loopback or ip.is_link_local)


def lan_address() -> str | None:
    """This PC's IPv4 address on the home network, or None when it isn't on one."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect((_ROUTE_PROBE, 9))
            addr = s.getsockname()[0]
        if usable(addr):
            return addr
    except OSError:
        log.debug("no default route", exc_info=True)
    try:   # no default route (a LAN without internet): any private address it has
        addrs = socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return None
    return next((a for a in addrs if usable(a)), None)


def link(host: str, port: int, token: str) -> str:
    """What the QR code holds. The key is in the #fragment: browsers never send it."""
    return f"http://{host}:{port}/#k={token}"


def firewall_command(port: int) -> str:
    """The netsh commands (for cmd /c) that replace our one rule. `port` is an int, so
    nothing in it can be read as another command."""
    port = int(port)
    base = "netsh advfirewall firewall"
    return (f"{base} delete rule name={FIREWALL_RULE} & "
            f"{base} add rule name={FIREWALL_RULE} dir=in action=allow protocol=TCP "
            f"localport={port} profile=private remoteip=localsubnet")


def allow_firewall(port: int) -> bool:
    """Ask Windows (its admin prompt) to let phones on the home network reach `port`.
    True if the prompt was shown and accepted; the rule itself isn't read back."""
    if sys.platform != "win32":
        return False
    import ctypes
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "cmd.exe", f"/c {firewall_command(port)}", None, 0)
    except OSError:
        log.warning("couldn't ask for the firewall rule", exc_info=True)
        return False
    if rc <= 32:   # 5 = access denied: the prompt was turned down
        log.info("firewall rule not added (ShellExecute returned %s)", rc)
        return False
    log.info("firewall rule %s added for port %s", FIREWALL_RULE, port)
    return True
