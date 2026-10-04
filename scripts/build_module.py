"""Build Onion Pocket as an Onion Board add-on module: dist/OnionPocket-module.zip.

    onion-pocket/
        module.json     id, name, version, kind "remote", api_version, package,
                        entry, and the third-party modules it imports
        onion_pocket/   the package
        LICENSE

Onion Board unzips it into %APPDATA%\\OnionBoard\\modules\\onion-pocket and loads
the package from there. The built app has no pip, so the add-on may only import what
Onion Board ships: here, the standard library and PySide6's QtCore / QtGui /
QtWidgets (ALLOWED). Anything else fails the build.

The zip is the same byte for byte for the same source (fixed file times, sorted
entries), so its SHA-256 only changes when the code does.

Usage: python scripts/build_module.py [--out DIR]   (prints the zip's path and SHA-256)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = "onion_pocket"
ENTRY = "onion_pocket.addon"
MODULE_ID = "onion-pocket"
ZIP_NAME = "OnionPocket-module.zip"
ALLOWED = {"PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"}
DESCRIPTION = ("Your pads on your phone: scan a QR code on Settings → Remote and tap a "
               "pad on your phone to play it on this PC, over your home Wi-Fi. iPhone or "
               "Android, in the browser.")
FIXED_TIME = (2026, 1, 1, 0, 0, 0)


def package_files() -> list[Path]:
    return sorted((ROOT / PACKAGE).glob("*.py"))


def outside_imports(files: list[Path]) -> set[str]:
    """Every module the package imports from outside itself (relative imports and
    __future__ aside)."""
    found: set[str] = set()
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"), str(path))):
            if isinstance(node, ast.Import):
                found.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and not node.level:
                found.add(node.module or "")
    return {n for n in found if n != "__future__" and n.split(".")[0] != PACKAGE}


def third_party(names: set[str]) -> list[str]:
    return sorted(n for n in names if n.split(".")[0] not in sys.stdlib_module_names)


def manifest(imports: list[str]) -> dict:
    sys.path.insert(0, str(ROOT))
    from onion_pocket import __version__
    from onion_pocket.host import API_VERSION
    return {"id": MODULE_ID, "name": "Onion Pocket", "version": __version__,
            "description": DESCRIPTION, "kind": "remote", "api_version": API_VERSION,
            "package": PACKAGE, "entry": ENTRY, "imports": imports}


def _add(z: zipfile.ZipFile, name: str, data: bytes):
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    z.writestr(info, data)


def build(out: Path) -> Path:
    files = package_files()
    imports = third_party(outside_imports(files))
    bad = [n for n in imports if n not in ALLOWED]
    if bad:
        raise SystemExit("the add-on imports what Onion Board doesn't ship: " + ", ".join(bad))
    entries = {f"{MODULE_ID}/module.json":
               (json.dumps(manifest(imports), indent=1, ensure_ascii=False) + "\n").encode(),
               f"{MODULE_ID}/LICENSE": (ROOT / "LICENSE").read_bytes()}
    for path in files:
        entries[f"{MODULE_ID}/{path.relative_to(ROOT).as_posix()}"] = path.read_bytes()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name in sorted(entries):
            _add(z, name, entries[name])
    out.mkdir(parents=True, exist_ok=True)
    dest = out / ZIP_NAME
    dest.write_bytes(buf.getvalue())
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "dist")
    args = ap.parse_args(argv)
    dest = build(args.out)
    print(dest)
    print(hashlib.sha256(dest.read_bytes()).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
