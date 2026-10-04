"""The home network side of Onion Pocket: this PC's address on it, the pairing link,
and the Windows Firewall rule.

The phone pairs by scanning a QR code of

    http://<this PC>:<port>/#k=<key>

The key lives in the #fragment, so the browser never sends it in a request line.

Windows Firewall blocks incoming connections it hasn't been told about, and the
first time a program listens on the network with no rule naming that program, it
pops up "Windows Defender Firewall has blocked some features of <program>" (a rule
for the port alone doesn't stop that). `allow_firewall()` adds our one rule, after
Windows' admin prompt, in two parts with the same limits (this port, TCP, Private
networks only, from the local subnet only):
  - for the port: what phones need, and
  - for this program (`this_program()`: OnionBoard.exe, or pythonw.exe from source):
    what tells Windows not to ask.
Cancel on Windows' own prompt makes block rules for the program, and a block rule
beats any allow rule: `rule_state()` reports that as "blocked".
"""
from __future__ import annotations

import ipaddress
import logging
import ntpath
import os
import socket
import sys

log = logging.getLogger(__name__)

FIREWALL_RULE = "OnionPocket"
# an address that's never on a real network (RFC 5737): "connecting" a UDP socket to it
# sends nothing, but makes the OS pick the interface its default route goes out of
_ROUTE_PROBE = "192.0.2.1"
_WINDOWS = sys.platform == "win32"
# where Windows Firewall keeps local rules; readable without admin rights
_RULES_KEY = (r"SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters"
              r"\FirewallPolicy\FirewallRules")
# in quotes, cmd.exe still expands %...% (and !...! with delayed expansion on), and a
# " would end the quotes (Windows paths can't hold one anyway)
_UNSAFE = frozenset('"%!\r\n\t')


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


# ------------------------------------------------------------------ Windows Firewall
def this_program() -> str:
    """The program Windows sees listening: OnionBoard.exe, or pythonw.exe from source."""
    return sys.executable


def quotable(path: str | None) -> bool:
    """Whether `path` can go in the netsh command, in quotes."""
    return bool(path) and not (_UNSAFE & set(path)) and ntpath.isabs(path)


def firewall_command(port: int, program: str | None = None) -> str:
    """The netsh commands (for cmd /c) that replace our rule: the port, and the program
    when given. `port` is an int, and the program's path goes in quotes with anything
    cmd.exe would still act on there refused, so nothing can be read as another
    command."""
    port = int(port)
    base = "netsh advfirewall firewall"
    limits = f"localport={port} profile=private remoteip=localsubnet"
    add = f"{base} add rule name={FIREWALL_RULE} dir=in action=allow protocol=TCP"
    cmd = f"{base} delete rule name={FIREWALL_RULE} & {add} {limits}"
    if program is not None:
        if not quotable(program):
            raise ValueError(f"can't put this path in a command: {program!r}")
        cmd += f' && {add} program="{program}" {limits}'
    return cmd


def _parse(value: str) -> dict[str, list[str]]:
    """One stored rule, 'v2.33|Action=Allow|Dir=In|LPort=7475|App=…|Name=…|', as
    {key: [values]} (Profile can repeat)."""
    rule: dict[str, list[str]] = {}
    for part in value.split("|")[1:]:
        key, sep, val = part.partition("=")
        if sep:
            rule.setdefault(key, []).append(val)
    return rule


def _read_rules() -> list[dict[str, list[str]]]:
    """Every local firewall rule (a few ms; no admin, no child process)."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, _RULES_KEY) as key:
        count = winreg.QueryInfoKey(key)[1]
        values = [winreg.EnumValue(key, i)[1] for i in range(count)]
    return [_parse(v) for v in values if isinstance(v, str)]


def _same_file(stored: str, path: str) -> bool:
    def norm(p):
        return ntpath.normcase(ntpath.normpath(os.path.expandvars(p)))
    return bool(stored) and norm(stored) == norm(path)


def rule_state(port: int, program: str | None = None) -> str:
    """Whether Windows Firewall lets phones reach `port` without asking, read without
    admin rights:
      "ok"       our rule is there, for this port and this program
      "missing"  no rule of ours
      "stale"    our rule is for another port or another copy of the app
      "blocked"  Windows blocks this program (Cancel on its prompt): ours can't win
      "unknown"  not Windows, or the rules couldn't be read"""
    if not _WINDOWS:
        return "unknown"
    program = program or this_program()
    try:
        rules = _read_rules()
    except OSError:
        log.debug("couldn't read the firewall rules", exc_info=True)
        return "unknown"

    def first(rule, key):
        return rule.get(key, [""])[0]

    def applies(rule, action):
        return (first(rule, "Active").upper() == "TRUE" and first(rule, "Dir") == "In"
                and first(rule, "Action") == action)

    for r in rules:   # no Profile listed means every profile
        if (applies(r, "Block") and "Private" in r.get("Profile", ["Private"])
                and _same_file(first(r, "App"), program)):
            return "blocked"
    ours = [r for r in rules if first(r, "Name") == FIREWALL_RULE]
    if not ours:
        return "missing"
    if any(applies(r, "Allow") and first(r, "LPort") == str(int(port))
           and _same_file(first(r, "App"), program) for r in ours):
        return "ok"
    return "stale"


def _elevate(params: str, wait_s: float = 60.0) -> bool:
    """Run `cmd.exe <params>` hidden, after Windows' admin prompt, and wait for it.
    True if the prompt was accepted and it exited 0. The only place anything runs as
    admin."""
    import ctypes
    from ctypes import wintypes

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG),
                    ("hwnd", wintypes.HWND), ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE), ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE),
                    ("hProcess", wintypes.HANDLE)]

    SEE_MASK_NOCLOSEPROCESS, SW_HIDE, WAIT_OBJECT_0 = 0x40, 0, 0
    info = SHELLEXECUTEINFOW(cbSize=ctypes.sizeof(SHELLEXECUTEINFOW),
                             fMask=SEE_MASK_NOCLOSEPROCESS, lpVerb="runas",
                             lpFile="cmd.exe", lpParameters=params, nShow=SW_HIDE)
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    if not shell32.ShellExecuteExW(ctypes.byref(info)):   # 1223: the prompt was turned down
        log.info("firewall rule not added (error %s)", ctypes.get_last_error())
        return False
    if not info.hProcess:
        return False
    try:
        if kernel32.WaitForSingleObject(info.hProcess, int(wait_s * 1000)) != WAIT_OBJECT_0:
            log.warning("the firewall command didn't finish in %s s", wait_s)
            return False
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
        if code.value:
            log.warning("the firewall command failed (exit code %s)", code.value)
        return code.value == 0
    finally:
        kernel32.CloseHandle(info.hProcess)


def allow_firewall(port: int, program: str | None = None) -> bool:
    """Ask Windows (its admin prompt) to let phones on the home network reach `port`,
    and this program listen without Windows' own prompt. Waits for the rule, so the
    server can start right after. True if allowed and added. Only ever called from a
    click on the card."""
    if not _WINDOWS:
        return False
    program = program or this_program()
    if not quotable(program):
        log.info("the program's path can't go in a command: the port rule only")
        program = None
    try:
        ok = _elevate(f"/c {firewall_command(port, program)}")
    except OSError:
        log.warning("couldn't ask for the firewall rule", exc_info=True)
        return False
    if ok:
        log.info("firewall rule %s added for port %s", FIREWALL_RULE, port)
    return ok
