# CLAUDE.md

Guidance for AI coding agents working in this repo.

## Treat this repo as public

It's private for now, but it's meant to be published like Onion Board and Onion
Watch, history included:

- **Never write personal or machine-specific data** into the repo: user names, real
  names, e-mails, `C:\Users\<name>\…` paths, host names, IPs (other than
  `127.0.0.1`, and `192.0.2.1` in `lan.py`, a documentation address that is never
  on a real network), LAN details, names of the author's other projects or
  machines. Use `%APPDATA%`, `Path.home()`, `example.com`, placeholders.
- **Never commit secrets** or anything from `%APPDATA%\OnionBoard\` (config, keys,
  logs).
- **Never add binaries or third-party assets.** The QR codes are drawn in code;
  the screenshots in `docs/screenshots/` are made for this project from made-up
  sounds.
- New network access must be added to `SECURITY.md`. No telemetry.

Run `python scripts/check_sensitive.py` before committing. It's also the
pre-commit hook: `git config core.hooksPath .githooks`.

## Working in the code

- Checks: `.venv\Scripts\ruff check .` and `.venv\Scripts\python -m pytest`.
  Tests use Qt's offscreen platform and a stand-in host (`tests/fakehost.py`): no
  window, no server, no network.
- The add-on runs inside Onion Board, which has no pip: import only the standard
  library and PySide6 (QtCore, QtGui, QtWidgets). `scripts/build_module.py` refuses
  anything else.
- It reaches Onion Board only through the host (`onion_pocket/host.py`). Anything
  it needs from the app is added to the host on Onion Board's side
  (`soundboard/ui/remotehost.py`) first, with `API_VERSION` raised when the
  contract changes.
- Never widen what a phone can do (`addon.ACTIONS`) to the mic, the voice changer
  or anything that reads files, without the author's say-so.
- Don't launch Onion Board or anything that opens windows without asking first.
- Edit files with UTF-8-safe tools (Windows PowerShell 5.1 mangles UTF-8).
